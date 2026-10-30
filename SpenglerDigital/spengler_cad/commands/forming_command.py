"""Befehl «Rundblech / Umformung»: Rundbleche ohne Einschnitte beurteilen und (Scheibe/Kegel) als Drehkörper modellieren.

Fusion-Laschen funktionieren nur an geraden Kanten. Durchgehende Ränder an runden Blechen modelliert das
Add-in deshalb als Drehkörper aus dem Querschnitt (Biegerechnung aus der App). Es entstehen keine
Einschnitte oder Lappen. Der Körper ist KEIN Fusion-Blechkörper; Zuschnitt und Umformzone liefert die
Rechnung in forming/forming.py (theoretisch, als solche gekennzeichnet).
"""
import os

import adsk.core

from ..core import units
from ..diagnostics import logger
from ..forming import forming as fo
from ..manufacturing import dxf_writer
from ..geometry import fusion_adapter as fa
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..ui import help_content
from . import base, export_command

BID = "spenglerRundblech"
FAELLE = [("scheibe", "Scheibe mit aufgebogenem Rand"), ("kragen", "Kragen an rundem Ausschnitt (nur Beurteilung)"), ("kegel", "Kegelstumpf / konischer Übergang")]
Z = {}


def erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    Z["mat"] = MaterialBibliothek().liste()
    fall = inp.addDropDownCommandInput("fall", "Fall", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, t) in enumerate(FAELLE):
        fall.listItems.add(t, i == 0)
    inp.addValueInput("r", "Radius (Blechmitte) / unten", "mm", adsk.core.ValueInput.createByString("100 mm"))
    inp.addValueInput("h", "Randhöhe / Kegelhöhe", "mm", adsk.core.ValueInput.createByString("20 mm"))
    inp.addValueInput("w", "Randwinkel", "deg", adsk.core.ValueInput.createByString("90 deg"))
    inp.addValueInput("r2", "Radius oben (Kegel)", "mm", adsk.core.ValueInput.createByString("50 mm"))
    md = inp.addDropDownCommandInput("material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle)
    for m in Z["mat"]:
        md.listItems.add("%s (%.2f mm)" % (m["name"], m["thickness"]), m["id"] == e.get("defaultMaterialId"))
    if Z["mat"] and md.selectedItem is None:
        md.listItems.item(0).isSelected = True
    vd = inp.addDropDownCommandInput("verfahren", "Werkstattverfahren", adsk.core.DropDownStyles.TextListDropDownStyle)
    Z["verf"] = list(fo.VERFAHREN.keys())
    for k in Z["verf"]:
        vd.listItems.add(fo.VERFAHREN[k], k == e["forming"]["defaultProcess"])
    inp.addBoolValueInput("schnitte", "Einschnitte/Lappen ausdrücklich erlauben", True, "", bool(e["forming"]["cutsAllowed"]))
    inp.addBoolValueInput("modell", "Körper in Fusion erzeugen", True, "", True)
    inp.addBoolValueInput("flach", "Zuschnitt als flachen Körper mit Biegelinien erzeugen", True, "", True)
    inp.addBoolValueInput("dxf", "Zuschnitt als DXF speichern", True, "", True)
    inp.addTextBoxCommandInput("erg", "Beurteilung", "", 9, True)
    inp.addBoolValueInput("hilfe", "Hilfe", False, "", False)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, geaendert)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, ausfuehren)
    _rechnen(inp)


def _rechnen(inp):
    fall = FAELLE[inp.itemById("fall").selectedItem.index][0]
    r, h = units.cm_zu_mm(inp.itemById("r").value), units.cm_zu_mm(inp.itemById("h").value)
    w = units.rad_zu_grad(inp.itemById("w").value)
    r2 = units.cm_zu_mm(inp.itemById("r2").value)
    m = Z["mat"][inp.itemById("material").selectedItem.index] if Z["mat"] and inp.itemById("material").selectedItem else None
    verf = Z["verf"][inp.itemById("verfahren").selectedItem.index]
    for id_, sichtbar in (("w", fall != "kegel"), ("r2", fall == "kegel")):
        inp.itemById(id_).isVisible = sichtbar
    inp.itemById("modell").isVisible = fall != "kragen"
    inp.itemById("flach").isVisible = fall != "kragen"   # beim Kragen gibt es keine Aussenkontur
    if fall == "scheibe":
        e = fo.scheibe_mit_rand(r, h, w)
    elif fall == "kragen":
        e = fo.kragen(r, h, w)
    else:
        e = fo.kegelstumpf(r, r2, h)
    b = fo.beurteilen(e, verf, m, inp.itemById("schnitte").value)
    z = ["Konstruierbar: %s · Abwickelbar: %s · Herstellbar: %s" % (
        "ja" if b["konstruierbar"] else "nein", "ja" if b["abwickelbar"] else "nein (Umformung nötig)",
        {True: "ja", False: "nein", None: "nicht beurteilbar"}[b.get("herstellbar")])]
    if fall == "scheibe":
        z.append("Rohling theoretisch: Ø %.1f mm (ohne Biegezugabe)" % b["rohling_durchmesser"])
    if fall == "kragen" and b.get("rohling_loch_radius"):
        z.append("Loch im Rohling theoretisch: Ø %.1f mm" % (2 * b["rohling_loch_radius"]))
    if fall == "kegel" and not b.get("zylinder"):
        z.append("Abwicklung: Kreisringsektor R %.1f / %.1f mm, Winkel %.1f°" % (b["R_innen"], b["R_aussen"], b["oeffnungswinkel"]))
    if b.get("dehnung_rand"):
        z.append("Tangentiale Dehnung am Rand: %+.1f %%" % (b["dehnung_rand"] * 100))
    z += b["hinweise"]
    inp.itemById("erg").text = "<br>".join(z)
    return fall, r, h, w, r2, m, b


def geaendert(args):
    if args.input.id == "hilfe":
        base.melden("Hilfe", help_content.text("rundblech"))
        return
    try:
        _rechnen(args.inputs)
    except ValueError as e:
        args.inputs.itemById("erg").text = "✗ %s" % e


def _zuschnitt_ausgeben(inp, fall, b, m):
    """Zuschnitt (theoretisch) als DXF und/oder flacher Körper mit Biegelinien. → Text für den Bericht. Fehler hier stoppen den Befehl nicht."""
    z = []
    mit_dxf, mit_koerper = inp.itemById("dxf").value, inp.itemById("flach").value and fall != "kragen"
    if not (mit_dxf or mit_koerper):
        return ""
    try:
        zs = fo.zuschnitt(b)
    except ValueError as ex:
        return "\n\nKein Zuschnitt: %s" % ex
    titel = "Rundblech %s" % fall
    if mit_dxf:
        try:
            ordner = export_command._exportordner(Einstellungen().laden())
            pfad = os.path.join(ordner, "Rundblech_%s_Zuschnitt.dxf" % fall)
            dxf_writer.elemente_dxf(zs, titel).speichern(pfad)
            z.append("Zuschnitt-DXF: %s" % pfad)
        except Exception as ex:
            logger.ausnahme("Zuschnitt-DXF")
            z.append("DXF nicht gespeichert: %s" % base.fehlertext(ex))
    if mit_koerper:
        try:
            if not m:
                raise fa.AdapterFehler("für den flachen Körper ist ein Materialprofil (Dicke) nötig")
            _, hinweise = fa.abwicklung_koerper(fa.design().activeComponent, zs, m["thickness"], "Abwicklung %s" % titel)
            z.append("Flacher Körper «Abwicklung %s» erzeugt (Biegelinien als Kanten, theoretischer Zuschnitt)." % titel)
            z += hinweise
        except Exception as ex:
            logger.ausnahme("Zuschnitt-Körper")
            z.append("Flacher Körper nicht erzeugt: %s" % base.fehlertext(ex))
    return "\n\n" + "\n".join(z)


@base.sicher("Rundblech")
def _ausfuehren(self, args):
    inp = args.command.commandInputs
    fall, r, h, w, r2, m, b = _rechnen(inp)
    text = inp.itemById("erg").text.replace("<br>", "\n")
    if inp.itemById("modell").value and fall != "kragen":
        if not m:
            raise fa.AdapterFehler("Für das Modell ist ein Materialprofil (Dicke) nötig.")
        t = m["thickness"]
        if fall == "scheibe":
            ri = m.get("innerRadius")
            if ri is None:
                raise fa.AdapterFehler("Für den Drehkörper braucht das Materialprofil einen Innenradius.")
            kontur = fo.drehprofil_scheibe(r, h, t, ri, w)
            kontur = [(x, y) for x, y in kontur]
        else:
            # Kegelmantel: Mantellinie mit Dicke (senkrecht versetzt)
            import math
            dx, dz = r2 - r, h
            L = math.hypot(dx, dz)
            nx, nz = -dz / L * t / 2, dx / L * t / 2
            kontur = [(r + nx, nz), (r2 + nx, h + nz), (r2 - nx, h - nz), (r - nx, -nz)]
        if min(x for x, _ in kontur) < 0:
            raise fa.AdapterFehler("Querschnitt kreuzt die Drehachse – Masse prüfen.")
        comp = fa.design().activeComponent
        feat = fa.drehkoerper(comp, kontur, "Rundblech %s" % fall)
        fa.markieren(feat, {"rundblech": fall, "r": r, "h": h, "material": m["name"]})
        text = "Körper erzeugt (Drehkörper, kein Blechkörper, ohne Einschnitte).\n\n" + text
    text += _zuschnitt_ausgeben(inp, fall, b, m)
    logger.info("Rundblech", fall=fall, r=r, h=h, herstellbar=b.get("herstellbar"))
    base.melden("Rundblech / Umformung", text)


def ausfuehren(args):
    _ausfuehren(None, args)


def registrieren():
    return base.befehl_definieren(BID, "Rundblech / Umformung", "Rundbleche, Kragen und Kegel ohne Einschnitte: Beurteilung (stauchen/strecken) und Drehkörper.", erstellt)

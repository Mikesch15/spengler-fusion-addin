"""Befehl «Quetschfalte an Ecke»: an der Ecke, an der zwei Aufkantungen zusammenlaufen, die Quetschfalte ins Blechteil bauen (Anwender 6. 11. 2026,
Variante a: das Teil selbst wird verändert; Zuschnitt und DXF der Ecke kommen vom Add-in, Fusions Abwicklung wird auf solchen Teilen nicht benutzt).
Eingabe: je eine ebene Fläche der beiden Aufkantungen und die Richtung (hinten links / hinten rechts, von der Sichtseite aus gesehen). Höhen, Winkel
und Blechdicke liest das Add-in aus dem Modell. NICHT live geprüft."""
import os
import time

import adsk.core
import adsk.fusion

from ..core import quetschfalte as qf
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..manufacturing import quetschfalte_dxf
from ..storage import paths
from . import base

BID = "spenglerQuetschfalte"
RICHTUNGEN = ["hinten rechts", "hinten links"]


def _flaeche(inp, id_):
    s = inp.itemById(id_)
    if s is None or s.selectionCount < 1:
        return None
    return adsk.fusion.BRepFace.cast(s.selection(0).entity)


def _richtung(inp):
    d = inp.itemById("richtung")
    return RICHTUNGEN[d.selectedItem.index] if d.selectedItem else RICHTUNGEN[0]


def erstellt(args):
    if base.gesperrt(args, BID):
        return
    cmd = args.command
    inp = cmd.commandInputs
    for id_, titel, tip in (("flaeche1", "Aufkantung 1", "Eine ebene Fläche der ersten Aufkantung (Innen- oder Aussenseite)"),
                            ("flaeche2", "Aufkantung 2", "Eine ebene Fläche der zweiten Aufkantung (Innen- oder Aussenseite)")):
        s = inp.addSelectionInput(id_, titel, tip)
        s.addSelectionFilter("PlanarFaces")
        s.setSelectionLimits(0, 1)
    rd = inp.addDropDownCommandInput("richtung", "Falte liegt", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, r in enumerate(RICHTUNGEN):
        rd.listItems.add(r, i == 0)
    inp.addBoolValueInput("dxf", "Zuschnitt der Ecke als DXF und Zeichnung speichern", True, "", True)
    inp.addTextBoxCommandInput("info", "Ecke", "Bitte die beiden Aufkantungen wählen, die an der Ecke zusammenlaufen (je eine ebene Fläche).<br>"
                               "Die Falte wird auf der nicht sichtbaren Seite (Aussenseite) hinter einer der beiden Aufkantungen angefügt. "
                               "«Links/rechts» gilt vom Blick von der Sichtseite auf die Ecke.", 6, True)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, geaendert)
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, ausfuehren)


def _analyse(inp):
    f1, f2 = _flaeche(inp, "flaeche1"), _flaeche(inp, "flaeche2")
    if f1 is None or f2 is None:
        return None, "Bitte beide Aufkantungen wählen."
    try:
        a = fa.quetschfalte_analysieren(f1, f2, _richtung(inp))
        return a, None
    except fa.AdapterFehler as e:
        return None, str(e)
    except Exception as e:
        logger.ausnahme("Quetschfalte analysieren")
        return None, "Analyse fehlgeschlagen: %s" % ((str(e).strip().splitlines() or [type(e).__name__])[-1])


@base.sicher("Quetschfalte")
def _geaendert_innen(self, args):
    inp = args.inputs
    a, fehler = _analyse(inp)
    inp.itemById("info").formattedText = ("<b>Bereit.</b><br>" + fa.quetschfalte_text(a).replace("\n", "<br>")) if a else "<font color='#b3261e'>%s</font>" % fehler


def geaendert(args):
    _geaendert_innen(None, args)


def pruefen(args):
    try:
        a, fehler = _analyse(args.inputs)
        args.areInputsValid = a is not None
    except Exception:
        args.areInputsValid = False


@base.sicher("Quetschfalte")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    a, fehler = _analyse(inp)
    if a is None:
        base.melden("Quetschfalte", fehler, True)
        return
    von = fa.zeitleiste_stand()
    name = a["koerper"].name
    try:
        objekte = fa.quetschfalte_bauen(a)
    except fa.AdapterFehler as e:
        base.melden("Quetschfalte", "Nicht gebaut: %s%s" % (e, "" if getattr(e, "rueckbau_ok", True) else
                    "\n\nACHTUNG: Der Rückbau war unvollständig – bitte mit Strg+Z zurücknehmen."), True)
        return
    fa.zeitleiste_gruppieren(von, "Spengler: Quetschfalte")
    zeilen = ["Quetschfalte gebaut (%d Objekte, zwei Lagen auf der Aussenseite), Teil «%s»." % (len(objekte), name), fa.quetschfalte_text(a)]
    if a.get("hinweise_bau"):
        zeilen.append("Ecke: " + "; ".join(a["hinweise_bau"]) + ".")
    if inp.itemById("dxf").value:
        try:
            ordner = os.path.join(paths.daten_ordner(), "Quetschfalte")
            os.makedirs(ordner, exist_ok=True)
            stamm = os.path.join(ordner, "Quetschfalte_%s" % time.strftime("%Y%m%d_%H%M%S"))
            z = a["zuschnitt"]
            quetschfalte_dxf.ecke_dxf(z, "Quetschfalte %s" % a["richtung"]).speichern(stamm + ".dxf")
            with open(stamm + ".svg", "w", encoding="utf-8") as f:
                f.write(qf.svg_zuschnitt(z))
            with open(stamm + "_gefaltet.svg", "w", encoding="utf-8") as f:
                f.write(qf.svg_gefaltet(z, a["wand"]))
            zeilen.append("Zuschnitt der Ecke (DXF) und Zeichnungen: %s.*" % stamm)
        except Exception:
            logger.ausnahme("Quetschfalte: DXF")
            zeilen.append("Zuschnitt-DXF konnte nicht gespeichert werden (Details im Protokoll).")
    zeilen.append("Hinweis: Fusions «Abwicklung & DXF» ist für dieses Teil gesperrt. Zuschnitt = der Ausschnitt der Ecke; die Abwicklung des ganzen Teils mit "
                  "Quetschfalte folgt. Biegezugaben und Lagendicke sind noch nicht eingerechnet. Nicht live geprüft.")
    base.melden("Quetschfalte", "\n\n".join(zeilen))


def ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return base.befehl_definieren(BID, "Quetschfalte an Ecke", "An der Ecke zweier Aufkantungen die Quetschfalte ins Blechteil bauen (Zuschnitt der Ecke als DXF).", erstellt)

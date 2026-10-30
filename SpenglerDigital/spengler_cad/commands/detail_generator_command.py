"""Befehle «3D-Detail erfassen» und «3D-Detail anwenden».

Erfassen (geführtes Authoring): Der Benutzer modelliert sein Detail (z. B. einen eigenen Doppelfalzabschluss)
in einer EIGENEN Komponente und legt die variablen Masse als Fusion-Benutzerparameter an. Im Befehl wählt er
die Komponente, die Anschlusskante, optional die Bezugsfläche und markiert die variablen Parameter.
Gespeichert werden: die Komponente als .f3d (Benutzerdatenordner), das lokale Koordinatensystem der
Anschlusskante, Parameter, Kompatibilität (Kantenlänge, Dicke) und die Zeitachsen-Features als Namen.

Anwenden: Vorlage wählen, Zielkante (und optional Bezugsfläche) wählen, variable Werte eingeben →
Passung prüfen → Vorschau → Import als neue Komponente, Ausrichtung T = Ziel · Anker⁻¹, Parameter setzen.
Standardmässig wird das Detail ins Zielbauteil integriert (Basis-Feature + Kombinieren, keine Komponente);
ohne Haken «integrieren» bleibt es eine eigene Komponente. Es wird keine automatische
Parametrisierung beliebiger Körper behauptet.
"""
import os
import tempfile

import adsk.core
import adsk.fusion

from .. import VERSION
from ..core import models, units
from ..details import detail_validation, frames
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.template_repository import VorlagenRepository
from ..ui import help_content
from . import base

BID_ERFASSEN = "spenglerDetailErfassen"
BID_ANWENDEN = "spenglerDetailAnwenden"
Z = {}


# ====================================================================== Erfassen
def erfassen_erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    s = inp.addSelectionInput("komp", "Detail-Komponente", "Komponente (Occurrence), die das Detail enthält")
    s.addSelectionFilter("Occurrences")
    s.setSelectionLimits(1, 1)
    k = inp.addSelectionInput("kante", "Anschlusskante", "Gerade Kante, an der das Detail später angesetzt wird")
    k.addSelectionFilter("LinearEdges")
    k.setSelectionLimits(1, 1)
    f = inp.addSelectionInput("flaeche", "Bezugsfläche (optional)", "Fläche, deren Normale die Z-Richtung des Anschlusses bestimmt")
    f.addSelectionFilter("PlanarFaces")
    f.setSelectionLimits(0, 1)
    inp.addStringValueInput("name", "Name", "")
    inp.addStringValueInput("kategorie", "Kategorie", models.KATEGORIE_OHNE)
    inp.addStringValueInput("beschreibung", "Beschreibung", "")
    dd = inp.addDropDownCommandInput("params", "Variable Parameter", adsk.core.DropDownStyles.CheckBoxDropDownStyle)
    Z["up"] = fa.benutzerparameter()
    for p in Z["up"]:
        dd.listItems.add("%s = %s" % (p["name"], p["expression"]), False)
    if not Z["up"]:
        inp.addTextBoxCommandInput("keine", "", "Keine Fusion-Benutzerparameter im Dokument – das Detail wird ohne variable Masse gespeichert.", 2, True)
    inp.addTextBoxCommandInput("info", "", help_content.text("details").replace("\n", "<br>"), 6, True)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, erfassen_ausfuehren)


@base.sicher("3D-Detail erfassen")
def _erfassen(self, args):
    inp = args.command.commandInputs
    occ = adsk.fusion.Occurrence.cast(inp.itemById("komp").selection(0).entity)
    kante = adsk.fusion.BRepEdge.cast(inp.itemById("kante").selection(0).entity)
    if occ is None:   # Live-Test 30.10.: gewählt war keine Komponente (Occurrence) – Ausnahme «NoneType hat kein component»
        occ = getattr(kante, "assemblyContext", None)
    if occ is None:
        raise fa.AdapterFehler("Als «Detail-Komponente» bitte die Komponente (Eintrag im Browser links oder im Modell) wählen, in der das Detail liegt – "
                               "gewählt wurde etwas anderes, z. B. ein Körper oder das oberste Dokument. Das Detail muss in einer eigenen Komponente stehen.")
    fsel = inp.itemById("flaeche")
    flaeche = adsk.fusion.BRepFace.cast(fsel.selection(0).entity) if fsel.selectionCount else None
    # Koordinaten im System der Komponente (so liegt sie nach dem Export/Import im eigenen Ursprung)
    k_nat = kante.nativeObject or kante
    f_nat = (flaeche.nativeObject or flaeche) if flaeche else None
    if k_nat.body.parentComponent != occ.component:
        raise fa.AdapterFehler("Die Anschlusskante muss zur gewählten Detail-Komponente gehören.")
    rahmen = fa.kantenrahmen(k_nat, f_nat)
    name = inp.itemById("name").value.strip()
    if not name:
        raise fa.AdapterFehler("Bitte einen Namen eingeben.")
    v = models.neue_detailvorlage(name)
    v["category"] = inp.itemById("kategorie").value.strip() or models.KATEGORIE_OHNE
    v["description"] = inp.itemById("beschreibung").value
    v["anchor"].update({"frame": rahmen, "edgeLength": units.cm_zu_mm(k_nat.length), "edgeType": "gerade"})
    dd = inp.itemById("params")
    for i in range(dd.listItems.count):
        if dd.listItems.item(i).isSelected:
            p = Z["up"][i]
            einheit = "mm" if p["unit"] in ("mm", "cm", "m", "in") else ("deg" if p["unit"] in ("deg", "rad") else "")
            wert = units.cm_zu_mm(p["value"]) if einheit == "mm" else (units.rad_zu_grad(p["value"]) if einheit == "deg" else p["value"])
            v["parameters"].append(dict(models.parameter(p["name"], p["name"], einheit, round(wert, 6), beschreibung=p["comment"]),
                                        fusionName=p["name"], originalExpression=p["expression"]))
        else:
            v["fixedParameters"].append({"name": Z["up"][i]["name"], "expression": Z["up"][i]["expression"]})
    t = fa.blechdicke_mm(k_nat.body)
    v["compatibility"].update({"thickness": t, "edgeType": "gerade"})
    try:
        tl = fa.design().timeline
        v["featureMapping"] = [tl.item(i).name for i in range(tl.count)]
    except Exception:
        pass
    v["source"]["componentName"] = occ.component.name
    v["source"]["fusionVersion"] = adsk.core.Application.get().version
    v["metadata"]["addin"] = VERSION
    tmp = os.path.join(tempfile.mkdtemp(prefix="spengler_"), "detail.f3d")
    fa.komponente_exportieren(occ.component, tmp)
    repo = VorlagenRepository()
    v["source"]["file"] = repo.geometrie_ablegen(tmp, v["id"], 1)
    f, w = detail_validation.pruefe_detailvorlage(v)
    if f:
        raise fa.AdapterFehler("\n".join(f))
    gesp = repo.speichern(v)
    logger.info("Detail erfasst", id=gesp["id"], parameter=[p["name"] for p in v["parameters"]])
    base.melden("3D-Detail erfassen", "Gespeichert: %s (Version %s)\nVariable Parameter: %s\n%s" % (
        gesp["name"], gesp["version"], ", ".join(p["name"] for p in v["parameters"]) or "keine", "\n".join(w)))


def erfassen_ausfuehren(args):
    _erfassen(None, args)


# ====================================================================== Anwenden
def anwenden_erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    Z["details"] = VorlagenRepository().liste("detailvorlage")
    Z["pids"] = []
    if not Z["details"]:
        inp.addTextBoxCommandInput("leer", "", "<b>Noch keine 3D-Detailvorlagen.</b><br>Zuerst mit «3D-Detail erfassen» ein eigenes Detail speichern.", 2, True)
    dd = inp.addDropDownCommandInput("detail", "Detailvorlage", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, d in enumerate(Z["details"]):
        dd.listItems.add("%s  [V%s]" % (d["name"], d.get("version")), i == 0)
    k = inp.addSelectionInput("kante", "Zielkante / Falzende", "Gerade Kante, an der das Detail angesetzt wird")
    k.addSelectionFilter("LinearEdges")
    k.setSelectionLimits(1, 1)
    f = inp.addSelectionInput("flaeche", "Bezugsfläche (optional)", "Fläche für die Z-Richtung (sonst die grössere Nachbarfläche)")
    f.addSelectionFilter("PlanarFaces")
    f.setSelectionLimits(0, 1)
    inp.addBoolValueInput("drehen", "Um 180° wenden (Richtung der Kante umkehren)", True, "", False)
    inp.addBoolValueInput("integrieren", "Ins bestehende Modell integrieren (keine eigene Komponente)", True, "", True)
    inp.addGroupCommandInput("parameter", "Parameter")
    inp.addTextBoxCommandInput("pruefung", "Passung", "", 5, True)
    inp.addBoolValueInput("hilfe", "Hilfe", False, "", False)
    _params(inp)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, anwenden_geaendert)
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, anwenden_pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.executePreview, anwenden_vorschau)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, anwenden_ausfuehren)


def _detail(inp):
    dd = inp.itemById("detail")
    return Z["details"][dd.selectedItem.index] if Z["details"] and dd.selectedItem else None


def _params(inp):
    for pid in Z["pids"]:
        x = inp.itemById(pid)
        if x:
            x.deleteMe()
    Z["pids"] = []
    d = _detail(inp)
    grp = adsk.core.GroupCommandInput.cast(inp.itemById("parameter"))
    for p in (d or {}).get("parameters", []):
        e = p.get("unit") or ""
        x = grp.children.addValueInput("d_" + p["name"], p.get("label") or p["name"], e,
                                       adsk.core.ValueInput.createByString(("%s %s" % (p.get("default") or 0, e)).strip()))
        Z["pids"].append("d_" + p["name"])


def _passung(inp):
    d = _detail(inp)
    sel = inp.itemById("kante")
    if not d or not sel.selectionCount:
        return None, ["Detailvorlage und Zielkante wählen."], []
    kante = adsk.fusion.BRepEdge.cast(sel.selection(0).entity)
    k = fa.kante_beschreiben(kante)
    ok, gruende, hinweise = detail_validation.passung(d, k)
    from ..core.validation import pruefe_werte
    gruende += pruefe_werte(d.get("parameters", []), _werte(inp, d))
    return kante, gruende, hinweise


def _werte(inp, d):
    w = {}
    for p in d.get("parameters", []):
        x = inp.itemById("d_" + p["name"])
        if x is not None:
            w[p["name"]] = units.cm_zu_mm(x.value) if p.get("unit") == "mm" else (units.rad_zu_grad(x.value) if p.get("unit") == "deg" else x.value)
    return w


def anwenden_geaendert(args):
    inp = args.inputs
    if args.input.id == "detail":
        _params(inp)
    if args.input.id == "hilfe":
        base.melden("Hilfe", help_content.text("details"))
        return
    _, gruende, hinweise = _passung(inp)
    inp.itemById("pruefung").text = "<br>".join(["✗ " + g for g in gruende] + ["• " + h for h in hinweise]) or "✓ passt"


def anwenden_pruefen(args):
    try:
        _, gruende, _ = _passung(args.inputs)
        args.areInputsValid = not gruende
    except Exception:
        args.areInputsValid = False


def _einsetzen(inp, integrieren=False):
    """Detail importieren, ausrichten, Parameter setzen, optional ins Modell integrieren.

    Live-Test 30.10.: «Access violation – no RTTI data» beim Anwenden. Wahrscheinliche Ursache: die gewählte Kante (BRepEdge) wurde nach dem
    Import weiterbenutzt, obwohl der Import das Dokument verändert. Alles, was von Kante/Körper gebraucht wird, wird deshalb VOR dem Import
    gelesen; danach wird der Zielkörper über seinen entityToken frisch geholt. Jede Phase steht in der Fehlermeldung."""
    phase = "Prüfen"
    try:
        d = _detail(inp)
        kante, gruende, hinweise = _passung(inp)
        if gruende:
            raise fa.AdapterFehler("\n".join(gruende))
        phase = "Ziel bestimmen"
        fsel = inp.itemById("flaeche")
        flaeche = adsk.fusion.BRepFace.cast(fsel.selection(0).entity) if fsel.selectionCount else None
        ziel = fa.kantenrahmen(kante, flaeche)
        if inp.itemById("drehen").value:
            ende = [o + x * units.cm_zu_mm(kante.length) for o, x in zip(ziel["origin"], ziel["x"])]
            ziel = frames.rahmen_aus_kante(ende, ziel["origin"], ziel["z"])
        ziel_body_token = kante.body.entityToken     # vor dem Import lesen – die Kante ist danach evtl. ungültig
        werte = _werte(inp, d)
        T = frames.ausrichtung(d["anchor"]["frame"], ziel)
        repo = VorlagenRepository()
        f3d = repo.geometrie_pfad(d["source"]["file"])
        if not os.path.exists(f3d):
            raise fa.AdapterFehler("Quellgeometrie fehlt: %s" % f3d)
        phase = "Import"
        root = fa.design().rootComponent
        occ, neue_param = fa.detail_importieren(f3d, root)
        phase = "Ausrichten"
        occ.transform = fa.matrix_fusion(T)
        phase = "Parameter setzen"
        nach_fusion = {}
        for p in d.get("parameters", []):
            e = p.get("unit")
            nach_fusion[p["fusionName"]] = units.fusion_ausdruck_mm(werte[p["name"]]) if e == "mm" else (
                units.fusion_ausdruck_grad(werte[p["name"]]) if e == "deg" else str(werte[p["name"]]))
        zuordnung, offen = detail_validation.parameter_zuordnen(list(nach_fusion), neue_param)
        gesetzt, fehlend = fa.parameter_setzen({zuordnung[n]: a for n, a in nach_fusion.items() if n in zuordnung})
        fehlend += offen
        if any(zuordnung[n] != n for n in zuordnung):
            hinweise = hinweise + ["Parameter beim Import umbenannt: " + ", ".join("%s → %s" % (n, zuordnung[n]) for n in zuordnung if zuordnung[n] != n)]
        phase = "Markieren"
        fa.markieren(occ, {"detailId": d["id"], "detailVersion": d.get("version"), "werte": werte, "addin": VERSION})
        phase = "Kollisionsprüfung"
        ziel_body = fa.koerper_neu(ziel_body_token)
        andere = [b for b in root.bRepBodies if b.entityToken != ziel_body_token]
        koll = fa.kollision(occ, andere)
        cf = None
        if integrieren:
            phase = "Integration"
            if ziel_body is None:
                raise fa.AdapterFehler("Der Zielkörper ist nach dem Import nicht mehr auffindbar.")
            try:
                cf, warn = fa.detail_integrieren(occ, ziel_body, neue_param)
            except fa.AdapterFehler:
                fa.entfernen([occ])   # Import wieder entfernen; Basis-/Kombinieren-Feature hat detail_integrieren selbst zurückgebaut
                raise
            hinweise = hinweise + warn
        return d, occ, gesetzt, fehlend, hinweise, koll, cf
    except fa.AdapterFehler as e:
        if phase in ("Prüfen", "Ziel bestimmen") or str(e).startswith(phase):
            raise
        raise fa.AdapterFehler("%s: %s" % (phase, e))
    except Exception as e:
        logger.ausnahme("Detail einsetzen", phase=phase)
        raise fa.AdapterFehler("%s: Fusion meldet: %s" % (phase, (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)))


def anwenden_vorschau(args):
    try:
        _einsetzen(args.command.commandInputs)   # Vorschau: nur Import + Ausrichtung; Fusion verwirft sie selbst
        args.isValidResult = False
    except Exception:
        logger.ausnahme("Detail-Vorschau")


@base.sicher("3D-Detail anwenden")
def _anwenden(self, args):
    inp = args.command.commandInputs
    integr = inp.itemById("integrieren").value
    d, occ, gesetzt, fehlend, hinweise, koll, cf = _einsetzen(inp, integr)
    if cf is not None:
        z = ["Detail «%s» (Version %s) ins Modell integriert (Zeitverlauf: Basis-Feature + «Kombinieren»)." % (d["name"], d.get("version"))]
    else:
        z = ["Detail «%s» (Version %s) eingesetzt als Komponente «%s»." % (d["name"], d.get("version"), occ.name)]
    if gesetzt:
        z.append("Parameter gesetzt: " + ", ".join(gesetzt))
    if fehlend:
        z.append("WARNUNG – Parameter nicht gefunden (Detail behält Originalmasse): " + ", ".join(fehlend))
    if koll and cf is None:
        z.append("Hinweis: Begrenzungsrahmen überschneidet sich mit: %s – bitte Kollision prüfen." % ", ".join(koll))
    z += hinweise
    if cf is None:
        z.append("Das Detail ist eine eigene Komponente und wurde nicht mit dem Blech vereinigt.")
    else:
        z.append("Die Detailmasse sind beim Anwenden festgelegt (keine nachträgliche Parametrisierung). Alles ist ein Rückgängig-Schritt (Strg+Z).")
    logger.info("Detail angewendet", id=d["id"], version=d.get("version"), fehlend=fehlend)
    base.melden("3D-Detail anwenden", "\n".join(z), bool(fehlend))


def anwenden_ausfuehren(args):
    _anwenden(None, args)


def registrieren():
    return [base.befehl_definieren(BID_ERFASSEN, "3D-Detail erfassen", "Eigenes 3D-Blechdetail mit Anschlusskante und variablen Parametern als Vorlage speichern.", erfassen_erstellt),
            base.befehl_definieren(BID_ANWENDEN, "3D-Detail anwenden", "Eigene 3D-Detailvorlage an eine Kante/ein Falzende ansetzen – mit Passungsprüfung und Vorschau.", anwenden_erstellt)]

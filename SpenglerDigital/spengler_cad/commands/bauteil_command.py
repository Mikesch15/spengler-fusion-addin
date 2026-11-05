"""Befehl «Bauteil erstellen»: baut aus einer Bauteilvorlage (in der Palette angelegt) ein Blech – gerade mit Länge oder entlang eines Grundrissverlaufs
(Strecken mit Richtungswechseln, auch als geschlossener Ring) – mit den Kantenfolgen an Verlaufskante, Gegenkante und Stirnseiten. NICHT live in Fusion geprüft."""
import adsk.core

from .. import VERSION
from ..core import auftrag as auftrag_logik, bauteil, grundriss, short_syntax, statusanzeige, template_engine, units, vorlagen_reihenfolge
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..storage.template_repository import VorlagenRepository
from . import base

BID = "spenglerBauteil"
Z = {}


def _vorlagen(e):
    alle = VorlagenRepository(projekt_ordner=e.get("projectLibraryFolder") or None).liste("bauteilvorlage")
    geordnet, Z["marken"] = vorlagen_reihenfolge.ordnen([v for v in alle if not v.get("_fehler")], (e.get("ui") or {}).get("zuletztBauteil"))
    return geordnet


@base.sicher("Bauteil erstellen")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    if base.gesperrt(args, BID):
        return
    e = Einstellungen().laden()
    Z.clear()
    Z.update({"marken": {}, "mat": MaterialBibliothek().liste(), "param_ids": []})
    Z["vorlagen"] = _vorlagen(e)
    if not Z["vorlagen"]:
        raise fa.AdapterFehler("Es gibt noch keine Bauteilvorlage. Bitte in «Vorlagen & Einstellungen» → Register «Bauteile» eine anlegen.")
    if not Z["mat"]:
        raise fa.AdapterFehler("Es gibt noch kein Materialprofil (Vorlagen & Einstellungen → Materialien).")
    inp.addTextBoxCommandInput("status", "", statusanzeige.html("gelb", "Vorlage und Masse wählen."), 3, True)
    dd = inp.addDropDownCommandInput("vorlage", "Bauteil", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, v in enumerate(Z["vorlagen"]):
        m = Z["marken"].get(v.get("id"))
        dd.listItems.add((m + " " if m else "") + "%s  [%s]" % (v["name"], v.get("category")), i == 0)
    inp.addTextBoxCommandInput("kurzinfo", "", "", 2, True)
    md = inp.addDropDownCommandInput("material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle)
    vorgabe = auftrag_logik.material_vorgabe(e, Z["mat"])
    for m in Z["mat"]:
        md.listItems.add("%s (%.2f mm)" % (m["name"], m["thickness"]), m["id"] == vorgabe)
    if md.selectedItem is None:
        md.listItems.item(0).isSelected = True
    inp.addStringValueInput("name", "Name des Bauteils", "")
    inp.addValueInput("laenge", "Länge", "mm", adsk.core.ValueInput.createByString("1000 mm"))
    inp.addStringValueInput("verlauf", "Verlauf (Strecken und Winkel)", "")
    inp.addBoolValueInput("ring", "Geschlossener Ring", True, "", False)
    sd = inp.addDropDownCommandInput("seite", "Blech liegt", adsk.core.DropDownStyles.TextListDropDownStyle)
    sd.listItems.add("links vom Verlauf", True)
    sd.listItems.add("rechts vom Verlauf", False)
    inp.addGroupCommandInput("parameter", "Masse")
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, _geaendert)
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, _pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)
    _vorlage_gewaehlt(inp)


def erstellt(args):
    _erstellt(None, args)


def _vorlage(inp):
    sel = inp.itemById("vorlage").selectedItem
    return Z["vorlagen"][sel.index] if sel is not None else None


def _material(inp):
    sel = inp.itemById("material").selectedItem
    return Z["mat"][sel.index] if sel is not None else None


def _vorlage_gewaehlt(inp):
    """Parameterfelder, Verlaufsfelder und Vorgaben zur gewählten Vorlage."""
    grp = adsk.core.GroupCommandInput.cast(inp.itemById("parameter"))
    for pid in Z["param_ids"]:
        x = inp.itemById(pid)
        if x:
            x.deleteMe()
    Z["param_ids"] = []
    v = _vorlage(inp)
    if v is None:
        return
    for p in v.get("parameters", []):
        if not p.get("variable", True):
            continue
        pid = "p_" + p["name"]
        einheit = {"mm": "mm", "deg": "deg"}.get(p.get("unit"), "")
        start = adsk.core.ValueInput.createByString(("%s %s" % (p["default"], einheit)).strip() if p.get("default") is not None else ("0 %s" % einheit if einheit else "0"))
        x = grp.children.addValueInput(pid, p.get("label") or p["name"], einheit, start)
        x.tooltip = (p.get("description") or "")
        Z["param_ids"].append(pid)
    g = (v.get("verlauf") or {}).get("art") == "grundriss"
    inp.itemById("laenge").isVisible = not g
    inp.itemById("verlauf").isVisible = g
    inp.itemById("ring").isVisible = g
    inp.itemById("seite").isVisible = True
    inp.itemById("verlauf").value = (v.get("verlauf") or {}).get("beispiel") or ""
    inp.itemById("seite").listItems.item(0 if (v.get("verlauf") or {}).get("seite", "links") != "rechts" else 1).isSelected = True
    inp.itemById("name").value = v.get("name") or "Bauteil"
    teile = [v["description"]] if v.get("description") else []
    teile += ["<i>%s: %s</i>" % (models_text(s), t) for s, t in bauteil.texte_der_vorlage(v).items() if t]
    inp.itemById("kurzinfo").formattedText = "<br>".join(teile)


def models_text(s):
    from ..core.models import SEITEN_TEXT
    return SEITEN_TEXT[s]


def _werte(inp, v):
    werte = {}
    for p in v.get("parameters", []):
        x = inp.itemById("p_" + p["name"])
        if x is None:
            continue
        werte[p["name"]] = units.cm_zu_mm(x.value) if p.get("unit") == "mm" else (units.rad_zu_grad(x.value) if p.get("unit") == "deg" else x.value)
    return werte


def _plan(inp):
    """→ (Plan, Fehlertext)."""
    v = _vorlage(inp)
    if v is None:
        return None, "Keine Vorlage gewählt."
    try:
        p = bauteil.plan(v, _werte(inp, v), _material(inp), inp.itemById("verlauf").value, units.cm_zu_mm(inp.itemById("laenge").value),
                         inp.itemById("seite").selectedItem.index == 0, inp.itemById("ring").value)
        return p, None
    except (template_engine.VorlagenFehler, grundriss.VerlaufFehler, short_syntax.KurzschriftFehler) as ex:
        return None, str(ex).splitlines()[0]
    except Exception as ex:
        logger.ausnahme("Bauteil planen")
        return None, "Berechnung nicht möglich: %s" % ex


def _status(inp):
    p, fehler = _plan(inp)
    if fehler:
        inp.itemById("status").formattedText = statusanzeige.html("rot", fehler)
    else:
        inp.itemById("status").formattedText = statusanzeige.html("gruen", "Bereit: " + p["text"]) + ("<br>" + "<br>".join(p["warnungen"]) if p["warnungen"] else "")
    return p, fehler


def _geaendert(args):
    try:
        if args.input.id == "vorlage":
            _vorlage_gewaehlt(args.inputs)
        _status(args.inputs)
    except Exception:
        logger.ausnahme("Bauteil: Eingabe geändert")


def _pruefen(args):
    try:
        p, fehler = _plan(args.inputs)
        args.areInputsValid = fehler is None
    except Exception:
        args.areInputsValid = False


def bauen(p, v, mat, name, frage=None):
    """Baut das Bauteil in einer NEUEN Komponente. → (Bericht, Hinweise). Bei JEDEM Fehler wird die halbfertige Komponente wieder entfernt (fa.abbruch_mit_rueckbau)."""
    g = p["geometrie"]
    von = fa.zeitleiste_stand()
    comp = fa.neue_komponente(name)
    try:
        body = fa.blech_aus_profil(comp, g["schleifen"], mat["thickness"])
        dicke = fa.blechdicke_mm(body) or mat["thickness"]
        bericht = ["Grundblech erzeugt: %s." % p["text"]]
        if abs(dicke - mat["thickness"]) > 0.01:
            bericht.append("⚠ Die Blechregel in Fusion hat %.2f mm, das Material «%s» %.2f mm – bitte die Blechregel anpassen." % (dicke, mat["name"], mat["thickness"]))
        ketten = fa.kanten_nach_ketten(body, g["ketten"])
        hinweise = []
        for seite in ("verlauf", "gegen", "start", "ende"):
            ops = p["seiten"].get(seite) or []
            if not ops or seite not in ketten:
                continue
            markierung = {"vorlageId": v["id"], "vorlageVersion": v.get("version"), "vorlageName": v["name"], "seite": seite, "material": mat, "operationen": ops, "addin": VERSION}
            feats = fa.kanten_folge_bauen(ketten[seite], ops, dicke, markierung, hinweise,
                                          (lambda text: frage("Gehrung nicht möglich", text)) if frage else None)
            bericht.append("%s: %d Feature(s) an %d Kante(n)." % (models_text(seite), len(feats), len(ketten[seite])))
    except Exception as ex:
        logger.ausnahme("Bauteil abgebrochen")
        fa.abbruch_mit_rueckbau(comp, ex, "Bauteil «%s»" % name)
    if fa.zeitleiste_gruppieren(von, "Spengler: %s" % name):
        bericht.append("In der Zeitleiste als Gruppe abgelegt – ein Strg+Z nimmt alles zurück.")
    return bericht, hinweise


@base.sicher("Bauteil erstellen")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    v = _vorlage(inp)
    mat = _material(inp)
    p, fehler = _plan(inp)
    if fehler:
        raise fa.AdapterFehler(fehler)
    name = inp.itemById("name").value.strip() or v["name"]
    g = p["geometrie"]
    bericht, hinweise = bauen(p, v, mat, name, base.frage)
    try:
        e = Einstellungen().laden()
        auftrag_logik.material_merken(e, mat["id"])
        e.setdefault("ui", {})["zuletztBauteil"] = vorlagen_reihenfolge.merken(e["ui"].get("zuletztBauteil"), v["id"])
        Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Bauteil: Einstellungen nicht gespeichert")
    logger.info("Bauteil erstellt", vorlage=v["id"], flaeche=g["flaeche"], laenge=g["laenge"], ring=g["geschlossen"])
    base.melden("Bauteil erstellen", "\n".join(bericht + hinweise + ["", "Bitte Richtung der Kanten und die Ecken ansehen (nicht live geprüft)."]))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Bauteil erstellen", "Baut aus einer Bauteilvorlage ein Blech mit Breite, Verlauf (gerade oder Grundriss, auch als Ring) und Kantenfolgen.", erstellt)]

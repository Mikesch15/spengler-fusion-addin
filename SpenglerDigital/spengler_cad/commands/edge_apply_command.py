"""Befehl «Kanten bearbeiten»: eigene Kantenvorlage auf eine oder mehrere Blechkanten anwenden.

Ablauf: Auswahl prüfen → Bauplan → Vorschau (executePreview, Fusion verwirft sie selbst) → OK →
Operationen je Kante → Ergebnisprüfung. Fehlt bei einer Kante ein Schritt, wird diese Kante wieder
zurückgebaut; der ganze Befehl ist ein Rückgängig-Schritt in Fusion.
"""
import adsk.core
import adsk.fusion

from .. import VERSION
from ..core import auftrag as auftrag_logik, operation_plan, short_syntax, statusanzeige, template_engine, vorlagen_reihenfolge
from ..core.models import BuildResult, kopie
from ..diagnostics import logger
from ..geometry import edge_resolver, fusion_adapter as fa
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..storage.template_repository import VorlagenRepository
from ..ui import help_content
from . import base

BID = "spenglerKantenBearbeiten"
Z = {}   # Zustand des offenen Dialogs


def _vorlagen():
    e = Einstellungen().laden()
    alle = VorlagenRepository(projekt_ordner=e.get("projectLibraryFolder") or None).liste("kantenvorlage")
    geordnet, Z["marken"] = vorlagen_reihenfolge.ordnen(alle, (e.get("ui") or {}).get("zuletzt"))
    return geordnet


def erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    if base.gesperrt(args, BID):
        return
    e = Einstellungen().laden()
    cmd.okButtonText = "Kanten bauen"
    Z.clear()
    Z["marken"] = {}
    Z.update({"vorlagen": _vorlagen(), "materialien": MaterialBibliothek().liste(), "einst": e, "param_ids": []})
    # Erst der Blechkörper, dann dessen Kanten – bei mehreren Blechen nebeneinander ist so klar, wofür die Kanten gelten.
    inp.addTextBoxCommandInput("status", "", statusanzeige.html("gelb", "Schritt 1: Blechkörper wählen."), 2, True)
    kb = inp.addSelectionInput("koerper", "Blechkörper", help_content.TOOLTIPS["koerper"])
    kb.addSelectionFilter("SolidBodies")
    kb.setSelectionLimits(1, 1)
    sel = inp.addSelectionInput("kanten", "Kanten", help_content.TOOLTIPS["kanten"])
    sel.addSelectionFilter("Edges")
    sel.setSelectionLimits(1, 0)
    sel.isEnabled = False
    if not Z["vorlagen"]:
        inp.addTextBoxCommandInput("leer", "", "<b>Die Vorlagenbibliothek ist leer.</b><br>Bitte zuerst unter «Vorlagen & Einstellungen» "
                                   "eine eigene Kantenvorlage anlegen. Im Expertenmodus kann unten eine Folge direkt eingegeben werden.", 3, True)
    dd = inp.addDropDownCommandInput("vorlage", "Vorlage", adsk.core.DropDownStyles.TextListDropDownStyle)
    dd.tooltip = help_content.TOOLTIPS["vorlage"]
    for i, v in enumerate(Z["vorlagen"]):
        dd.listItems.add((Z["marken"].get(v.get("id")) + " " if Z["marken"].get(v.get("id")) else "") + "%s  [%s, V%s]" % (v["name"], v.get("category"), v.get("version")), i == 0)
    inp.addTextBoxCommandInput("kurzinfo", "", "", 2, True)
    md = inp.addDropDownCommandInput("material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle)
    md.tooltip = help_content.TOOLTIPS["material"]
    for m in Z["materialien"]:
        md.listItems.add("%s (%.2f mm)" % (m["name"], m["thickness"]), m["id"] == auftrag_logik.material_vorgabe(e, Z["materialien"]))
    if Z["materialien"] and md.selectedItem is None:
        md.listItems.item(0).isSelected = True
    inp.addGroupCommandInput("parameter", "Parameter")
    ex = inp.addBoolValueInput("experte", "Expertenmodus", True, "", e["ui"]["mode"] == "experte")
    ex.tooltip = help_content.TOOLTIPS["experte"]
    f = inp.addStringValueInput("folge", "Folge (Kurzschrift)", "")
    f.tooltip = help_content.TOOLTIPS["folge"]
    inp.addBoolValueInput("speichern", "Angepasste Folge als neue Vorlage speichern", True, "", False)
    inp.addBoolValueInput("vorschau", "Vorschau anzeigen", True, "", True)
    inp.addTextBoxCommandInput("plan", "Bauplan", "", 8, True)
    inp.addBoolValueInput("hilfe", "Hilfe", False, "", False)
    _parameter_aufbauen(inp)
    _kurzinfo(inp)
    _sichtbarkeit(inp)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, geaendert)
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.executePreview, vorschau)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, ausfuehren)


def _gewaehlte_vorlage(inp):
    dd = inp.itemById("vorlage")
    if not Z["vorlagen"] or dd.selectedItem is None:
        return None
    return Z["vorlagen"][dd.selectedItem.index]


def _kurzinfo(inp):
    """Beschreibung und Kurzschrift der gewählten Vorlage direkt im Dialog (Kurzhilfe)."""
    try:
        v = _gewaehlte_vorlage(inp)
        if v is None:
            return
        teile = []
        if v.get("description"):
            teile.append(v["description"])
        try:
            teile.append("<i>Folge: %s</i>" % short_syntax.als_text(v.get("operations") or []))
        except Exception:
            pass
        inp.itemById("kurzinfo").text = "<br>".join(teile)
    except Exception:
        logger.ausnahme("Kurzinfo")


def _material(inp):
    md = inp.itemById("material")
    if not Z["materialien"] or md.selectedItem is None:
        return None
    return Z["materialien"][md.selectedItem.index]


def _parameter_aufbauen(inp):
    grp = adsk.core.GroupCommandInput.cast(inp.itemById("parameter"))
    for pid in Z["param_ids"]:
        x = inp.itemById(pid)
        if x:
            x.deleteMe()
    Z["param_ids"] = []
    v = _gewaehlte_vorlage(inp)
    if v:
        for p in v.get("parameters", []):
            if not p.get("variable", True):
                continue
            pid = "p_" + p["name"]
            einheit = {"mm": "mm", "deg": "deg"}.get(p.get("unit"), "")
            if p.get("default") is not None:
                start = adsk.core.ValueInput.createByString(("%s %s" % (p["default"], einheit)).strip())
            else:
                start = adsk.core.ValueInput.createByString("0 %s" % einheit if einheit else "0")
            x = grp.children.addValueInput(pid, p.get("label") or p["name"], einheit, start)
            x.tooltip = (p.get("description") or "") + ("  Bereich %s … %s %s" % (p.get("min"), p.get("max"), einheit) if p.get("min") is not None or p.get("max") is not None else "")
            Z["param_ids"].append(pid)
        inp.itemById("folge").value = short_syntax.als_text(v.get("operations", []))


def _werte(inp):
    from ..core import units
    v = _gewaehlte_vorlage(inp)
    werte = {}
    for p in (v or {}).get("parameters", []):
        x = inp.itemById("p_" + p["name"])
        if x is None:
            continue
        if p.get("unit") == "mm":
            werte[p["name"]] = units.cm_zu_mm(x.value)
        elif p.get("unit") == "deg":
            werte[p["name"]] = units.rad_zu_grad(x.value)
        else:
            werte[p["name"]] = x.value
    return werte


def _vorlage_effektiv(inp):
    """Gewählte Vorlage – im Expertenmodus mit der bearbeiteten Kurzschrift (als Kopie, Original unverändert)."""
    v = _gewaehlte_vorlage(inp)
    experte = inp.itemById("experte").value
    text = inp.itemById("folge").value.strip()
    if experte and text and (v is None or text != short_syntax.als_text(v.get("operations", []))):
        if v is None:
            return template_engine.vorlage_aus_kurzschrift("Direkteingabe", text), True
        neu = kopie(v)
        neu["operations"] = short_syntax.zerlege(text)
        neu["name"] = v["name"] + " (angepasst)"
        return neu, True
    return v, False


def _koerper(inp):
    sel = inp.itemById("koerper")
    if sel is None or sel.selectionCount == 0:
        return None
    return adsk.fusion.BRepBody.cast(sel.selection(0).entity)


def _fremde(inp, kanten):
    """Nummern (ab 1) der Kanten, die NICHT auf dem gewählten Körper liegen."""
    k = _koerper(inp)
    return [i for i, e in enumerate(kanten, 1) if k is None or fa.kante_gehoert_zu(e, k) is False]


def _kanten(inp):
    sel = inp.itemById("kanten")
    return [adsk.fusion.BRepEdge.cast(sel.selection(i).entity) for i in range(sel.selectionCount)]


def _plan(inp):
    try:
        v, angepasst = _vorlage_effektiv(inp)
    except short_syntax.KurzschriftFehler as e:
        return None, "Kurzschrift: %s" % e
    if v is None:
        return None, "Keine Vorlage gewählt."
    if _koerper(inp) is None:
        return None, "Zuerst den Blechkörper wählen, dann seine Kanten."
    roh = _kanten(inp)
    fremd = _fremde(inp, roh)
    if fremd:
        return None, "Kante %s liegt nicht auf dem gewählten Körper – bitte nur Kanten dieses Körpers wählen." % ", ".join(map(str, fremd))
    kanten = [fa.kante_beschreiben(k, i) for i, k in enumerate(roh, 1)]
    plan = operation_plan.erstelle(v, _werte(inp), _material(inp), kanten)
    if angepasst:
        plan["validation"]["warnings"].append("Folge im Expertenmodus angepasst – gilt nur für diese Ausführung%s." % (
            ", wird als neue Vorlage gespeichert" if inp.itemById("speichern").value else ""))
    for k in kanten:
        if k.get("frei") is None and k.get("blech"):
            plan["validation"]["warnings"].append("%s: ob es eine Aussenkante ist, liess sich nicht feststellen." % k["text"])
    return plan, None


def _schluessel(inp, mit_kanten=True):
    """Alles, was den Bauplan bestimmt, ohne an Geometrie zu rühren (während der Vorschau sind Kantenverweise evtl. ungültig)."""
    sel = inp.itemById("kanten")
    kb = inp.itemById("koerper")
    teile = [kb.selectionCount, kb.selection(0).entity.entityToken if kb.selectionCount else "", sel.selectionCount, inp.itemById("experte").value, inp.itemById("folge").value, inp.itemById("speichern").value]
    if mit_kanten:
        teile += [sel.selection(i).entity.entityToken for i in range(sel.selectionCount)]   # welche Kanten – wirft bei ungültigen Verweisen → kein Treffer
    for i in ("vorlage", "material"):
        d = inp.itemById(i)
        teile.append(d.selectedItem.index if d.selectedItem is not None else -1)
    for pid in Z.get("param_ids", []):
        x = inp.itemById(pid)
        teile.append(x.expression if x is not None else None)
    return tuple(teile)


def _ausfuehrbar(plan, fehler):
    try:
        return fehler is None and operation_plan.ist_ausfuehrbar(plan)
    except Exception:
        return False


def _plan_gemerkt(inp):
    """Wie _plan, aber merkt sich das Ergebnis je Eingabestand. Schlägt die Berechnung fehl (z. B. weil die Vorschau die gewählten Kanten
    verändert hat), gilt das zuletzt berechnete Ergebnis – sonst bliebe OK bei eingeschalteter Vorschau gesperrt (Live-Test 5.4)."""
    try:
        k = _schluessel(inp)
    except Exception:
        k = None
    if k is not None and Z.get("plan_merk", (None,))[0] == k:
        return Z["plan_merk"][1], Z["plan_merk"][2]
    try:
        grob = _schluessel(inp, mit_kanten=False)
    except Exception:
        grob = None
    try:
        plan, fehler = _plan(inp)
    except Exception:
        if Z.get("plan_merk"):
            logger.ausnahme("Bauplan während der Vorschau nicht neu berechenbar – letzter Stand gilt")
            return Z["plan_merk"][1], Z["plan_merk"][2]
        raise
    ok = _ausfuehrbar(plan, fehler)
    # Live-Test: Mit Vorschau ist die gewählte Kante schon umgebaut (nicht mehr freie Aussenkante / andere Verweise) → der Plan wäre «nicht
    # ausführbar» und OK gesperrt. Gleiche Eingaben (nur die Kantenverweise weichen ab) wie bei einem zuvor ausführbaren Plan: dieser gilt.
    if not ok and grob is not None and Z.get("plan_grob") and Z["plan_grob"][0] == grob:
        logger.info("Bauplan: Kante durch die Vorschau verändert – zuletzt ausführbarer Stand gilt")
        return Z["plan_grob"][1], Z["plan_grob"][2]
    if ok and grob is not None:
        Z["plan_grob"] = (grob, plan, fehler)
    Z["plan_merk"] = (k, plan, fehler)
    return plan, fehler


def _sichtbarkeit(inp):
    ex = inp.itemById("experte").value
    inp.itemById("folge").isVisible = ex
    inp.itemById("speichern").isVisible = ex


def geaendert(args):
    inp = args.inputs
    i = args.input
    if i.id == "vorlage":
        _parameter_aufbauen(inp)
        _kurzinfo(inp)
    if i.id == "experte":
        _sichtbarkeit(inp)
    if i.id == "koerper":
        kanten = inp.itemById("kanten")
        kanten.isEnabled = inp.itemById("koerper").selectionCount > 0
        if kanten.isEnabled:
            kanten.hasFocus = True
        elif kanten.selectionCount:
            kanten.clearSelection()
    if i.id == "kanten" and not Z.get("bereinigt"):
        _fremde_entfernen(inp)
    if i.id == "hilfe":
        base.melden("Hilfe", help_content.text("kanten") + "\n\n" + help_content.text("kurzschrift"))
        return
    plan, fehler = _plan_gemerkt(inp)
    inp.itemById("plan").text = (fehler or operation_plan.beschreibung(plan)).replace("\n", "<br>")
    _status(inp, plan, fehler)


def _fremde_entfernen(inp):
    """Kanten, die nicht zum gewählten Körper gehören, wieder aus der Auswahl nehmen (bei mehreren Blechen nebeneinander). Fehler hier sind harmlos:
    die Prüfung des Bauplans meldet fremde Kanten ohnehin."""
    try:
        sel = inp.itemById("kanten")
        k = _koerper(inp)
        if k is None or sel.selectionCount == 0:
            return
        alle = [sel.selection(i).entity for i in range(sel.selectionCount)]
        gut = [e for e in alle if fa.kante_gehoert_zu(adsk.fusion.BRepEdge.cast(e), k) is not False]
        if len(gut) == len(alle):
            return
        Z["bereinigt"] = True
        try:
            sel.clearSelection()
            for e in gut:
                sel.addSelection(e)
        finally:
            Z["bereinigt"] = False
        logger.info("Kanten anderer Körper aus der Auswahl genommen", entfernt=len(alle) - len(gut))
    except Exception:
        logger.ausnahme("Fremde Kanten entfernen")


def _status(inp, plan, fehler):
    try:
        farbe, text = statusanzeige.ampel(plan, fehler, inp.itemById("koerper").selectionCount > 0, inp.itemById("kanten").selectionCount)
        inp.itemById("status").text = statusanzeige.html(farbe, text)
    except Exception:
        logger.ausnahme("Statusanzeige")


def pruefen(args):
    try:
        plan, fehler = _plan_gemerkt(args.inputs)
        args.areInputsValid = fehler is None and operation_plan.ist_ausfuehrbar(plan)
    except Exception:
        logger.ausnahme("Kanten prüfen")
        args.areInputsValid = False


def _bauen(inp, ergebnis, frage=None):
    """frage(titel, text) → bool: Rückfrage vor einem Bau OHNE Gehrung (nur beim OK; in der Vorschau None = nie ohne Gehrung bauen)."""
    plan, fehler = _plan(inp)
    if fehler or not operation_plan.ist_ausfuehrbar(plan):
        ergebnis.fehler.append(fehler or "; ".join(plan["validation"]["errors"]))
        return plan
    ergebnis.warnungen += plan["validation"]["warnings"]
    markierung = {"vorlageId": plan["templateId"], "vorlageVersion": plan["templateVersion"], "vorlageName": plan["templateName"],
                  "werte": plan["values"], "material": plan["material"], "operationen": plan["operations"], "addin": VERSION}
    t = (plan.get("material") or {}).get("thickness")
    tokens = edge_resolver.merken([z["ref"] for z in plan["targets"] if z["geeignet"]])
    logger.info("Kanten bearbeiten", vorlage=plan["templateId"], version=plan["templateVersion"], kanten=len(tokens), folge=short_syntax.als_text(plan["operations"]))
    ops = plan["operations"]
    try:
        gruppen = fa.gruppen_bilden([z["ref"] for z in plan["targets"] if z["geeignet"]])
    except Exception:
        logger.ausnahme("Kantengruppen nicht bestimmbar – es wird einzeln gebaut")
        gruppen = [[i] for i in range(len(tokens))]
    ohne_gehrung = set()
    for gruppe in gruppen:
        einzeln = list(gruppe)
        if len(gruppe) >= 2 and ops and (ops[0]["typ"] != "umschlag" or len(ops) == 1):
            nrn = [i + 1 for i in gruppe]
            try:
                kanten = [edge_resolver.aufloesen(tokens[i]) for i in gruppe]
                body_name, body_token = kanten[0].body.name, kanten[0].body.entityToken
                hinw = []
                feats = fa.folge_anbringen_gruppe(kanten, ops, t, markierung, hinw)
                ergebnis.warnungen += ["Kanten %s: %s" % ("+".join(map(str, nrn)), h) for h in hinw]
                ergebnis.ausgefuehrt.append("Kanten %s: gemeinsamer Flansch mit Gehrung, %d Feature(s)" % ("+".join(map(str, nrn)), len(feats)))
                ergebnis.geometrie.append(body_name)
                body = fa.koerper_neu(body_token)
                if body is None:
                    ergebnis.warnungen.append("Kanten %s: Körper nach dem Bauen nicht eindeutig auffindbar – Ergebnis bitte selbst prüfen." % "+".join(map(str, nrn)))
                else:
                    for p in fa.koerper_pruefen(body):
                        ergebnis.warnungen.append("Kanten %s: %s" % ("+".join(map(str, nrn)), p))
                einzeln = []
            except fa.AdapterFehler as e:
                logger.warnung("Gruppe nicht gemeinsam gebaut", kanten=nrn, grund=e)
                text_nrn = "+".join(map(str, nrn))
                if frage is not None and frage("Gehrung nicht möglich", fa.gehrung_frage_text(text_nrn, str(e)[:600])):
                    ergebnis.warnungen.append("Kanten %s: gemeinsamer Flansch (Gehrung) nicht möglich – auf deine Bestätigung je Kante OHNE Gehrung gebaut (Ecken stumpf). Grund: %s" % (text_nrn, e))
                    ohne_gehrung.update(gruppe)
                else:
                    ergebnis.fehler.append("Kanten %s: nicht gebaut – gemeinsamer Flansch mit Gehrung nicht möglich%s. Grund: %s" % (
                        text_nrn, " (beim OK wirst du gefragt, ob ohne Gehrung gebaut werden soll)" if frage is None else ", Bau ohne Gehrung abgelehnt", e))
                    ergebnis.zurueckgesetzt = ergebnis.zurueckgesetzt or getattr(e, "rueckbau_ok", True)
                    einzeln = []
        for i in einzeln:
            nr, tok = i + 1, tokens[i]
            try:
                kante = edge_resolver.aufloesen(tok)
                body_name, body_token = kante.body.name, kante.body.entityToken
                hinw = []
                feats = fa.folge_anbringen(kante, ops, t, markierung, hinw)
                ergebnis.warnungen += ["Kante %d: %s" % (nr, h) for h in hinw]
                ergebnis.ausgefuehrt.append("Kante %d: %d Schritt(e)%s" % (nr, len(feats), " – OHNE Gehrung (Ecke stumpf)" if i in ohne_gehrung else ""))
                ergebnis.geometrie.append(body_name)
                body = fa.koerper_neu(body_token)
                if body is None:
                    ergebnis.warnungen.append("Kante %d: Körper nach dem Bauen nicht eindeutig auffindbar – Ergebnis bitte selbst prüfen." % nr)
                else:
                    for p in fa.koerper_pruefen(body):
                        ergebnis.warnungen.append("Kante %d: %s" % (nr, p))
            except fa.AdapterFehler as e:
                ergebnis.fehler.append("Kante %d: %s" % (nr, e))
                ergebnis.zurueckgesetzt = ergebnis.zurueckgesetzt or getattr(e, "rueckbau_ok", True)
    # Gehrung nicht gebaut (Rückfall je Kante): Bericht mit Protokoll und Bildschirmfoto automatisch an die eigene Firma – so sieht der Entwickler Fusions
    # Antwort, ohne dass jemand «Protokoll senden» drücken muss. Ein Fehler hier ändert nichts am Ergebnis.
    gehrung = [w for w in ergebnis.warnungen if "Gehrung" in w and ("nicht möglich" in w or "nicht gemeinsam" in w)]
    if gehrung:
        try:
            if base.fehlerbericht_senden("Kanten bearbeiten (Gehrung nicht gebaut)", "\n".join(gehrung)):
                ergebnis.warnungen.append("Bericht mit Protokoll und Bildschirmfoto wurde an Spengler Digital gesendet.")
        except Exception:
            logger.ausnahme("Bericht zur Gehrung")
    return plan


def vorschau(args):
    inp = args.command.commandInputs
    if not inp.itemById("vorschau").value:
        return
    try:
        r = BuildResult()
        _bauen(inp, r)
        args.isValidResult = False   # Fusion baut beim OK erneut – die Vorschau wird verworfen
        if r.fehler:
            inp.itemById("plan").text = ("Vorschau: " + r.text()).replace("\n", "<br>")
    except Exception:
        logger.ausnahme("Vorschau")


@base.sicher("Kanten bearbeiten")
def _ausfuehren(self, args):
    inp = args.command.commandInputs
    r = BuildResult()
    von = fa.zeitleiste_stand()
    plan = _bauen(inp, r, base.frage)
    if not r.fehler:
        if fa.zeitleiste_gruppieren(von, "Spengler: %s" % (plan.get("templateName") or "Kantenfolge")):
            r.ausgefuehrt.append("In der Zeitleiste als Gruppe «Spengler: %s» abgelegt – ein Strg+Z nimmt alles zurück." % (plan.get("templateName") or "Kantenfolge"))
        try:
            e = Einstellungen().laden()
            geaendert_ = auftrag_logik.material_merken(e, ((plan.get("material") or {}).get("id")))
            e.setdefault("ui", {})["zuletzt"] = vorlagen_reihenfolge.merken(e["ui"].get("zuletzt"), plan.get("templateId"))
            Einstellungen().speichern(e)
            if geaendert_:
                r.ausgefuehrt.append("Material «%s» gilt jetzt für diesen Auftrag (Kanten, Zuschnitt, Kalkulation)." % (plan["material"].get("name") or ""))
        except Exception:
            logger.ausnahme("Material des Auftrags nicht gemerkt")
    v, angepasst = _vorlage_effektiv(inp)
    if angepasst and inp.itemById("speichern").value and not r.fehler:
        v = kopie(v)
        v.pop("id", None)   # neue Vorlage mit neuer ID – das Original bleibt unverändert
        try:
            gesp = VorlagenRepository().speichern(v)
            r.ausgefuehrt.append("Neue Vorlage gespeichert: %s" % gesp["name"])
        except Exception as e:
            r.warnungen.append("Vorlage nicht gespeichert: %s" % e)
    logger.info("Ergebnis", **r.als_dict())
    base.melden("Kanten bearbeiten", r.text(), bool(r.fehler))
    return plan


def ausfuehren(args):
    _ausfuehren(None, args)


def registrieren():
    return base.befehl_definieren(BID, "Kanten bearbeiten", "Eigene Kantenvorlage (Flansch/Umschlag-Folge) auf gewählte Blechkanten anwenden – mit Vorschau.", erstellt)

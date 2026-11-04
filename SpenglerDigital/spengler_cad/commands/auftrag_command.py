"""Befehl «Neuer Auftrag»: legt in Fusion die Ordner für einen Auftrag an («<Nummer> <Objekt>», optional in einem Jahresordner, mit den
Unterordnern aus den Einstellungen) und merkt Nummer/Objekt für Stückliste, Etiketten und Werkstattblatt. NICHT live in Fusion geprüft."""
import datetime

import adsk.core

from ..core import abgleich, auftrag
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.settings_service import Einstellungen
from . import base

BID = "spenglerNeuerAuftrag"
BID_WAHL = "spenglerAuftragWaehlen"
BID_ABGLEICH = "spenglerAuftraegeAbgleichen"
Z = {"liste": [], "treffer": [], "status": {}, "app": {}, "abgleich": None}


def _plan(inp, e):
    return auftrag.plan(e.get("auftrag"), inp.itemById("nummer").value, inp.itemById("objekt").value, inp.itemById("jahr").value)


def erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    inp.addStringValueInput("nummer", "Auftragsnummer", "")
    inp.addStringValueInput("objekt", "Objekt (z. B. Strasse Nr., Ort)", "")
    if a["jahresordner"]:
        inp.addIntegerSpinnerCommandInput("jahr", "Jahr", 2000, 2100, 1, datetime.date.today().year)
    else:
        inp.addIntegerSpinnerCommandInput("jahr", "Jahr (nicht verwendet)", 2000, 2100, 1, datetime.date.today().year).isEnabled = False
    inp.addBoolValueInput("speichern", "Aktuelles Dokument im Ordner «%s» speichern" % a["rollen"]["modelle"], True, "", False)
    inp.addBoolValueInput("appprojekt", "Auch als Projekt in der App anlegen (falls es die Nummer dort noch nicht gibt)", True, "", True)
    inp.addTextBoxCommandInput("plan", "", "", 5, True)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, lambda x: _anzeigen(x.inputs))
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, _pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)
    _anzeigen(inp)


def _anzeigen(inp):
    e = Einstellungen().laden()
    try:
        p = _plan(inp, e)
        text = "Wird angelegt:<br>%s/%s<br>Unterordner: %s" % (p["wurzel"] or "(Projekt)", "/".join(p["pfad"]), ", ".join(p["unterordner"]) or "keine")
    except Exception as ex:      # AuftragsFehler = Eingabe unvollständig; alles andere (z. B. leere Felder) ebenso nur anzeigen
        text = "⚠ %s" % (ex if isinstance(ex, auftrag.AuftragsFehler) else "Bitte Nummer und Objekt eingeben.")
    inp.itemById("plan").formattedText = text


def _pruefen(args):
    try:
        _plan(args.inputs, Einstellungen().laden())
        args.areInputsValid = True
    except Exception:
        args.areInputsValid = False


@base.sicher("Neuer Auftrag")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    e = Einstellungen().laden()
    p = _plan(inp, e)
    pfad, hinweise = fa.auftrag_ordner_anlegen(p)
    nummer, objekt = auftrag.zerlegen(p["name"])
    _merken(e, nummer, objekt, int(p["pfad"][0]) if len(p["pfad"]) > 1 else None)
    try:        # Fertigungsstatus «offen» in der App – ohne Anmeldung/Netz einfach weglassen
        from ..storage.cloud_client import Cloud
        c = Cloud(timeout=6)
        if c.angemeldet:
            c.status_setzen(nummer, "offen")
    except Exception:
        logger.warnung("Fertigungsstatus beim neuen Auftrag nicht gesetzt")
    gespeichert = ""
    if inp.itemById("appprojekt").value:
        gespeichert += "\n\n" + _projekt_in_app(nummer, objekt)
    if inp.itemById("speichern").value:
        a = auftrag.pruefe_einstellung(e.get("auftrag"))
        gespeichert += "\n\n" + fa.dokument_im_auftrag_speichern(p["wurzel"], p["name"], a["rollen"]["modelle"])
    base.melden("Neuer Auftrag", "Ordner angelegt:\n%s\nUnterordner: %s%s%s" % (
        pfad, ", ".join(p["unterordner"]) or "keine", ("\n\n" + "\n".join(hinweise)) if hinweise else "", gespeichert))


def _projekt_in_app(nummer, objekt, cloud=None):
    """Projekt zur Auftragsnummer in der App anlegen, falls es dort noch fehlt. → Meldungstext (nie eine Ausnahme: die Ordner in Fusion sind dann schon angelegt,
    ein Problem bei der App wird nur gemeldet)."""
    from ..storage.cloud_client import Cloud, CloudFehler
    try:
        c = cloud or Cloud(timeout=10)
        if not c.angemeldet:
            return "App: nicht angemeldet – Projekt nicht angelegt (Register Konto, danach «Aufträge abgleichen»)."
        vorhanden = c.projekt_zu_auftrag(nummer)
        if vorhanden:
            return "App: Projekt %s gibt es schon («%s»)." % (nummer, vorhanden.get("name") or vorhanden.get("object") or "")
        neu = c.projekt_anlegen(nummer, objekt)
        return "App: Projekt %s «%s» angelegt." % (nummer, neu.get("name") or objekt)
    except CloudFehler as ex:
        logger.warnung("Projekt in der App nicht angelegt", fehler=ex)
        return "App: Projekt NICHT angelegt – %s" % ex
    except Exception as ex:
        logger.ausnahme("Projekt in der App nicht angelegt")
        return "App: Projekt NICHT angelegt – %s" % (str(ex) or type(ex).__name__)


def _merken(e, nummer, objekt, jahr):
    """Auftrag als aktiven merken (für Stückliste, Etiketten, Werkstattblatt, lokalen Exportordner) – ein Fehler hier verhindert nichts."""
    try:
        alt = e.get("order") or {}
        e["order"] = {"objekt": objekt, "auftrag": nummer, "jahr": jahr}
        if isinstance(e.get("ablagen"), dict):
            e["ablagen"]["aktiv"] = ""                  # ein Auftrag ersetzt eine aktive Ablage
        if alt.get("auftrag") == nummer and alt.get("materialId"):
            e["order"]["materialId"] = alt["materialId"]
        Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Auftragsangaben nicht gespeichert")


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Neuer Auftrag", "Legt Auftragsordner mit Jahr und Unterordnern (Modelle, Pläne, Export) in Fusion an.", erstellt)]


# ---------------------------------------------------------------- Auftrag wählen (+ Dokument im Auftrag speichern, Fertigungsstatus)
def _cloud_lesen(funktion, standard):
    """Angemeldet: Abfrage bei der App; Fehler/offline/abgemeldet → Standardwert (die Liste funktioniert auch ohne App)."""
    try:
        from ..storage.cloud_client import Cloud
        c = Cloud(timeout=6)
        return funktion(c) if c.angemeldet else standard
    except Exception:
        logger.warnung("App nicht erreichbar (Auftragsliste)")
        return standard


@base.sicher("Auftrag wählen")
def _waehlen_erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    Z["liste"] = fa.auftraege_lesen(a["wurzelOrdner"])
    if not Z["liste"]:
        raise fa.AdapterFehler("Im Stammordner «%s» wurden keine Aufträge («Nummer Objekt») gefunden." % a["wurzelOrdner"])
    Z["status"] = _cloud_lesen(lambda c: c.status_alle(), {})
    Z["app"] = {}
    inp.addStringValueInput("suche", "Suchen (Nummer oder Objekt)", "")
    inp.addDropDownCommandInput("auftrag", "Auftrag", adsk.core.DropDownStyles.TextListDropDownStyle)
    _liste_fuellen(inp, "", (e.get("order") or {}).get("auftrag"))
    st = inp.addDropDownCommandInput("status", "Fertigungsstatus setzen", adsk.core.DropDownStyles.TextListDropDownStyle)
    st.listItems.add("– unverändert –", True)
    for k, t in auftrag.STATUS:
        st.listItems.add(t, False)
    inp.addTextBoxCommandInput("info", "", "", 3, True)
    inp.addBoolValueInput("speichern", "Aktuelles Dokument im Ordner «%s» speichern" % a["rollen"]["modelle"], True, "", False)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, _geaendert)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _waehlen_ausfuehren)
    _info(inp)


def waehlen_erstellt(args):
    _waehlen_erstellt(None, args)


def _liste_fuellen(inp, text, aktiv=None):
    dd = inp.itemById("auftrag")
    dd.listItems.clear()
    t = (text or "").strip().lower()
    Z["treffer"] = [x for x in Z["liste"] if t in x["name"].lower()][:200]
    for i, x in enumerate(Z["treffer"]):
        dd.listItems.add(auftrag.listentext(x, Z["status"]), i == 0 or (aktiv is not None and x["nummer"] == aktiv))


def _gewaehlt(inp):
    sel = inp.itemById("auftrag").selectedItem
    return Z["treffer"][sel.index] if sel is not None and sel.index < len(Z["treffer"]) else None


def _info(inp):
    x = _gewaehlt(inp)
    if x is None:
        inp.itemById("info").formattedText = ""
        return
    if x["nummer"] not in Z["app"]:
        Z["app"][x["nummer"]] = _cloud_lesen(lambda c: c.projekt_zu_auftrag(x["nummer"]), None)
    p = Z["app"][x["nummer"]]
    inp.itemById("info").formattedText = ("App: %s%s – Status in der App: %s" % (p.get("name") or "", (", " + p["customer"]) if p.get("customer") else "", p.get("status") or "?")
                                          if p else "Kein passender Auftrag in der App gefunden (oder nicht angemeldet).")


def _geaendert(args):
    if args.input.id == "suche":
        _liste_fuellen(args.inputs, args.input.value)
        _info(args.inputs)
    elif args.input.id == "auftrag":
        _info(args.inputs)


@base.sicher("Auftrag wählen")
def _waehlen_innen(self, args):
    inp = args.command.commandInputs
    x = _gewaehlt(inp)
    if x is None:
        raise fa.AdapterFehler("Kein Auftrag gewählt.")
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    _merken(e, x["nummer"], x["objekt"], x["jahr"])
    text = "Aktiver Auftrag: %s" % x["name"]
    st = inp.itemById("status").selectedItem
    if st is not None and st.index > 0:
        schluessel = auftrag.STATUS[st.index - 1][0]
        try:
            from ..storage.cloud_client import Cloud
            Cloud(timeout=8).status_setzen(x["nummer"], schluessel)
            text += "\nFertigungsstatus: %s" % auftrag.STATUS_TEXT[schluessel]
        except Exception as ex:
            logger.ausnahme("Fertigungsstatus nicht gesetzt")
            text += "\nFertigungsstatus NICHT gesetzt: %s" % base.fehlertext(ex)
    if inp.itemById("speichern").value:
        text += "\n\n" + fa.dokument_im_auftrag_speichern(a["wurzelOrdner"], x["name"], a["rollen"]["modelle"])
    base.melden("Auftrag wählen", text)


def _waehlen_ausfuehren(args):
    _waehlen_innen(None, args)


def registrieren_wahl():
    return [base.befehl_definieren(BID_WAHL, "Auftrag wählen", "Vorhandenen Auftrag aus der Ordnerstruktur wählen (aktiv für Stückliste, Etiketten, Export), Fertigungsstatus setzen und das Dokument darin speichern.", waehlen_erstellt)]


# ---------------------------------------------------------------- Aufträge abgleichen (App ↔ Fusion-Ordner)
MAX_ZEILEN = 40


@base.sicher("Aufträge abgleichen")
def _abgleich_erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    from ..storage.cloud_client import Cloud
    c = Cloud(timeout=12)
    if not c.angemeldet:
        raise fa.AdapterFehler("Für den Abgleich zuerst unter «Konto» mit dem App-Konto anmelden.")
    projekte = c.projekte_lesen()
    ordner = fa.auftraege_lesen(a["wurzelOrdner"])
    Z["abgleich"] = abgleich.vergleiche(projekte, ordner)
    erg = Z["abgleich"]
    g1 = inp.addGroupCommandInput("g1", "In der App, aber kein Ordner in Fusion → Ordner anlegen (%d)" % len(erg["nur_app"]))
    for i, x in enumerate(erg["nur_app"][:MAX_ZEILEN]):
        g1.children.addBoolValueInput("a%d" % i, x["ordnername"], True, "", True)
    g2 = inp.addGroupCommandInput("g2", "In Fusion, aber kein Projekt in der App → Projekt in der App anlegen (%d)" % len(erg["nur_fusion"]))
    for i, x in enumerate(erg["nur_fusion"][:MAX_ZEILEN]):
        g2.children.addBoolValueInput("f%d" % i, x["name"], True, "", True)
    zeilen = ["In beiden: %d" % len(erg["beide"])]
    if erg["abweichend"]:
        zeilen.append("Unterschiedliches Objekt (nichts geändert): " + "; ".join("%s: App «%s» / Fusion «%s»" % (p["order_no"], p.get("object") or "", o["objekt"]) for p, o in erg["abweichend"][:6]))
    if erg["uebersprungen"]:
        zeilen.append("Nicht übernehmbar: " + "; ".join("%s (%s)" % (p.get("name") or p.get("id"), g) for p, g in erg["uebersprungen"][:6]))
    if erg["archiviert"]:
        zeilen.append("%d archivierte Projekte der App werden ignoriert." % erg["archiviert"])
    if len(erg["nur_app"]) > MAX_ZEILEN or len(erg["nur_fusion"]) > MAX_ZEILEN:
        zeilen.append("Es werden höchstens %d Einträge je Liste angezeigt; den Rest beim nächsten Abgleich." % MAX_ZEILEN)
    inp.addTextBoxCommandInput("info", "", "<br>".join(zeilen), 5, True)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _abgleich_ausfuehren)


def abgleich_erstellt(args):
    _abgleich_erstellt(None, args)


@base.sicher("Aufträge abgleichen")
def _abgleich_innen(self, args):
    from ..storage.cloud_client import Cloud
    inp = args.command.commandInputs
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    erg = Z["abgleich"]
    c = Cloud(timeout=12)
    meldungen, fehler = [], []
    for i, x in enumerate(erg["nur_app"][:MAX_ZEILEN]):
        if not inp.itemById("a%d" % i).value:
            continue
        p = x["projekt"]
        try:
            plan = auftrag.plan(e.get("auftrag"), p["order_no"], x["ordnername"].split(" ", 1)[1], x["jahr"] or datetime.date.today().year)
            pfad, _ = fa.auftrag_ordner_anlegen(plan)
            meldungen.append("Ordner angelegt: %s" % pfad)
        except Exception as ex:
            logger.ausnahme("Abgleich: Ordner")
            fehler.append("%s: %s" % (x["ordnername"], base.fehlertext(ex)))
    for i, o in enumerate(erg["nur_fusion"][:MAX_ZEILEN]):
        if not inp.itemById("f%d" % i).value:
            continue
        pr = abgleich.projekt_aus_ordner(o)
        try:
            c.projekt_anlegen(pr["order_no"], pr["object"], pr["name"])
            meldungen.append("Projekt in der App angelegt: %s %s" % (pr["order_no"], pr["object"]))
        except Exception as ex:
            logger.warnung("Abgleich: Projekt", fehler=ex)
            fehler.append("%s %s: %s" % (pr["order_no"], pr["object"], base.fehlertext(ex)))
    logger.info("Aufträge abgeglichen", angelegt=len(meldungen), fehler=len(fehler))
    base.melden("Aufträge abgleichen", ("\n".join(meldungen) or "Nichts angelegt.") + (("\n\nNicht geklappt:\n" + "\n".join(fehler)) if fehler else ""), bool(fehler) and not meldungen)


def _abgleich_ausfuehren(args):
    _abgleich_innen(None, args)


def registrieren_abgleich():
    return [base.befehl_definieren(BID_ABGLEICH, "Aufträge abgleichen", "Vergleicht die Projekte der App mit den Auftragsordnern in Fusion und legt Fehlendes auf der jeweils anderen Seite an (nach Ihrer Auswahl).", abgleich_erstellt)]

"""Befehl «Neuer Auftrag»: legt in Fusion die Ordner für einen Auftrag an («<Nummer> <Objekt>», optional in einem Jahresordner, mit den
Unterordnern aus den Einstellungen) und merkt Nummer/Objekt für Stückliste, Etiketten und Werkstattblatt. NICHT live in Fusion geprüft."""
import datetime

import adsk.core

from ..core import auftrag
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.settings_service import Einstellungen
from . import base

BID = "spenglerNeuerAuftrag"
BID_WAHL = "spenglerAuftragWaehlen"
Z = {"liste": []}


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
    except auftrag.AuftragsFehler as ex:
        text = "⚠ %s" % ex
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
    gespeichert = ""
    if inp.itemById("speichern").value:
        a = auftrag.pruefe_einstellung(e.get("auftrag"))
        gespeichert = "\n\n" + fa.dokument_im_auftrag_speichern(p["wurzel"], p["name"], a["rollen"]["modelle"])
    base.melden("Neuer Auftrag", "Ordner angelegt:\n%s\nUnterordner: %s%s%s" % (
        pfad, ", ".join(p["unterordner"]) or "keine", ("\n\n" + "\n".join(hinweise)) if hinweise else "", gespeichert))


def _merken(e, nummer, objekt, jahr):
    """Auftrag als aktiven merken (für Stückliste, Etiketten, Werkstattblatt, lokalen Exportordner) – ein Fehler hier verhindert nichts."""
    try:
        e["order"] = {"objekt": objekt, "auftrag": nummer, "jahr": jahr}
        Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Auftragsangaben nicht gespeichert")


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Neuer Auftrag", "Legt Auftragsordner mit Jahr und Unterordnern (Modelle, Pläne, Export) in Fusion an.", erstellt)]


# ---------------------------------------------------------------- Auftrag wählen (+ Dokument im Auftrag speichern)
@base.sicher("Auftrag wählen")
def _waehlen_erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    Z["liste"] = fa.auftraege_lesen(a["wurzelOrdner"])
    if not Z["liste"]:
        raise fa.AdapterFehler("Im Stammordner «%s» wurden keine Aufträge («Nummer Objekt») gefunden." % a["wurzelOrdner"])
    inp.addStringValueInput("suche", "Suchen (Nummer oder Objekt)", "")
    dd = inp.addDropDownCommandInput("auftrag", "Auftrag", adsk.core.DropDownStyles.TextListDropDownStyle)
    _liste_fuellen(inp, "")
    aktiv = (e.get("order") or {}).get("auftrag")
    for i in range(dd.listItems.count):
        if aktiv and dd.listItems.item(i).name.startswith(aktiv + " "):
            dd.listItems.item(i).isSelected = True
    inp.addBoolValueInput("speichern", "Aktuelles Dokument im Ordner «%s» speichern" % a["rollen"]["modelle"], True, "", False)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, lambda x: x.input.id == "suche" and _liste_fuellen(x.inputs, x.input.value))
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _waehlen_ausfuehren)


def waehlen_erstellt(args):
    _waehlen_erstellt(None, args)


def _liste_fuellen(inp, text):
    dd = inp.itemById("auftrag")
    dd.listItems.clear()
    t = (text or "").strip().lower()
    treffer = [a for a in Z["liste"] if t in a["name"].lower()]
    for i, a in enumerate(treffer[:200]):
        dd.listItems.add(a["name"], i == 0)


@base.sicher("Auftrag wählen")
def _waehlen_innen(self, args):
    inp = args.command.commandInputs
    sel = inp.itemById("auftrag").selectedItem
    if sel is None:
        raise fa.AdapterFehler("Kein Auftrag gewählt.")
    name = sel.name
    z = next(a for a in Z["liste"] if a["name"] == name)
    e = Einstellungen().laden()
    a = auftrag.pruefe_einstellung(e.get("auftrag"))
    _merken(e, z["nummer"], z["objekt"], z["jahr"])
    text = "Aktiver Auftrag: %s" % name
    if inp.itemById("speichern").value:
        text += "\n\n" + fa.dokument_im_auftrag_speichern(a["wurzelOrdner"], name, a["rollen"]["modelle"])
    base.melden("Auftrag wählen", text)


def _waehlen_ausfuehren(args):
    _waehlen_innen(None, args)


def registrieren_wahl():
    return [base.befehl_definieren(BID_WAHL, "Auftrag wählen", "Vorhandenen Auftrag aus der Ordnerstruktur wählen (aktiv für Stückliste, Etiketten, Export) und das Dokument darin speichern.", waehlen_erstellt)]

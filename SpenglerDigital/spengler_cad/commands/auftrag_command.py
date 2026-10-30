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
    try:   # für Stückliste/Etiketten merken – ein Fehler hier verhindert nichts
        e["order"] = {"objekt": objekt, "auftrag": nummer}
        Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Auftragsangaben nicht gespeichert")
    base.melden("Neuer Auftrag", "Ordner angelegt:\n%s\nUnterordner: %s%s\n\nDas Dokument speichern Sie wie gewohnt im Ordner «%s»." % (
        pfad, ", ".join(p["unterordner"]) or "keine", ("\n\n" + "\n".join(hinweise)) if hinweise else "",
        p["unterordner"][0] if p["unterordner"] else p["name"]))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Neuer Auftrag", "Legt Auftragsordner mit Jahr und Unterordnern (Modelle, Pläne, Export) in Fusion an.", erstellt)]

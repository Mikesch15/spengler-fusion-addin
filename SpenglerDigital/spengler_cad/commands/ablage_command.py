"""Befehl «Andere Ablage»: Modelle ohne Kundenauftrag (z. B. ein Wettbewerbsmodell) in einem frei gewählten Fusion-Ordner ablegen. Der Ordner wird bei Bedarf angelegt, das Dokument
dort gespeichert, die Ablage als aktiv gesetzt (alle Befehle arbeiten dann ohne Auftrag, Exporte liegen im eigenen Ordner). NICHT live in Fusion geprüft."""
import adsk.core

from ..core import ablage as logik
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.settings_service import Einstellungen
from . import base

BID = "spenglerAblage"
NEU = "– neue Ablage anlegen –"
Z = {"liste": [], "ordner": []}


@base.sicher("Andere Ablage")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    ab = e.get("ablagen") or logik.standard()
    Z["liste"] = list(ab.get("liste", []))
    try:
        Z["ordner"] = fa.ordner_liste(3)
    except Exception:
        logger.ausnahme("Ordnerliste")
        Z["ordner"] = []
    dd = inp.addDropDownCommandInput("ablage", "Ablage", adsk.core.DropDownStyles.TextListDropDownStyle)
    for a in Z["liste"]:
        dd.listItems.add(("● " if a["name"] == ab.get("aktiv") else "") + "%s  [%s]" % (a["name"], logik.pfad_text(a["pfad"])), False)
    dd.listItems.add(NEU, not Z["liste"])
    if dd.selectedItem is None:
        dd.listItems.item(0).isSelected = True
    inp.addStringValueInput("name", "Name der Ablage", "")
    inp.addStringValueInput("pfad", "Fusion-Ordner", "")
    vo = inp.addDropDownCommandInput("vorhanden", "Vorhandener Ordner übernehmen", adsk.core.DropDownStyles.TextListDropDownStyle)
    vo.listItems.add("– wählen –", True)
    for p in Z["ordner"]:
        vo.listItems.add(" / ".join(p), False)
    inp.addBoolValueInput("speichern", "Aktuelles Dokument in diesem Ordner speichern", True, "", True)
    inp.addBoolValueInput("aktiv", "Als aktive Ablage setzen (Befehle arbeiten ohne Auftrag)", True, "", True)
    inp.addBoolValueInput("entfernen", "Diese Ablage aus der Liste entfernen (der Fusion-Ordner bleibt)", True, "", False)
    inp.addTextBoxCommandInput("info", "", "Für Modelle, die zu keinem Kundenauftrag gehören. Der Ordnerpfad gilt im aktiven Fusion-Projekt, z. B. <i>Wettbewerbe/Schweizermeisterschaft</i> – fehlende "
                               "Ordner werden angelegt. Liegt ein Dokument später in diesem Ordner, erkennt das Add-in die Ablage von selbst.", 4, True)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, _geaendert)
    base.handler(adsk.core.ValidateInputsEventHandler, cmd.validateInputs, _pruefen)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)
    _fuellen(inp)


def erstellt(args):
    _erstellt(None, args)


def _gewaehlt(inp):
    sel = inp.itemById("ablage").selectedItem
    return Z["liste"][sel.index] if sel is not None and sel.index < len(Z["liste"]) else None


def _fuellen(inp):
    a = _gewaehlt(inp)
    inp.itemById("name").value = a["name"] if a else ""
    inp.itemById("pfad").value = logik.pfad_text(a["pfad"]) if a else ""
    inp.itemById("name").isEnabled = a is None


def _geaendert(args):
    try:
        i = args.input.id
        if i == "ablage":
            _fuellen(args.inputs)
        elif i == "vorhanden" and args.inputs.itemById("vorhanden").selectedItem.index > 0:
            args.inputs.itemById("pfad").value = "/".join(Z["ordner"][args.inputs.itemById("vorhanden").selectedItem.index - 1])
    except Exception:
        logger.ausnahme("Ablage: Eingabe geändert")


def _pruefen(args):
    try:
        inp = args.inputs
        if inp.itemById("entfernen").value:
            args.areInputsValid = _gewaehlt(inp) is not None
            return
        logik.hinzufuegen(logik.standard(), inp.itemById("name").value, logik.pfad_aus_text(inp.itemById("pfad").value))
        args.areInputsValid = True
    except logik.AblageFehler:
        args.areInputsValid = False
    except Exception:
        args.areInputsValid = False


@base.sicher("Andere Ablage")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    e = Einstellungen().laden()
    ab = e.get("ablagen") or logik.standard()
    if inp.itemById("entfernen").value:
        a = _gewaehlt(inp)
        e["ablagen"] = logik.entfernen(ab, a["name"])
        Einstellungen().speichern(e)
        base.melden("Andere Ablage", "Die Ablage «%s» wurde aus der Liste entfernt. Der Fusion-Ordner «%s» bleibt unverändert." % (a["name"], logik.pfad_text(a["pfad"])))
        return
    name = inp.itemById("name").value.strip()
    pfad = logik.pfad_aus_text(inp.itemById("pfad").value)
    ab = logik.hinzufuegen(ab, name, pfad)
    text = []
    if inp.itemById("speichern").value:
        text.append(fa.dokument_in_ordner_speichern(pfad))
    else:
        _, neu = fa.ordner_pfad(pfad, True)
        text.append(("Ordner angelegt: %s." % "/".join(neu)) if neu else "Der Ordner «%s» besteht schon." % logik.pfad_text(pfad))
    if inp.itemById("aktiv").value:
        ab["aktiv"] = name
        e["order"] = {"objekt": "", "auftrag": "", "jahr": None}          # ein aktiver Auftrag würde die Ablage überstimmen
        text.append("«%s» ist jetzt die aktive Ablage: Befehle arbeiten ohne Auftrag, Exporte liegen im eigenen Ordner, es wird nichts in die App gesendet." % name)
    e["ablagen"] = ab
    Einstellungen().speichern(e)
    logger.info("Ablage", name=name, pfad=logik.pfad_text(pfad), aktiv=bool(inp.itemById("aktiv").value))
    base.melden("Andere Ablage", "\n".join(text))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Andere Ablage", "Modelle ohne Kundenauftrag (z. B. ein Wettbewerbsmodell) in einem frei gewählten Fusion-Ordner ablegen und ohne Auftrag arbeiten.", erstellt)]

"""Befehl «Vorlage aus App-Massaufnahme»: liest eine Massaufnahme (Freies Profil/Dachrandblech) des aktiven Auftrags aus der App (nur lesen) und legt
daraus eine Kantenvorlage im CAD an. NICHT live in Fusion/App geprüft."""
import adsk.core

from ..core import app_profil, lernen
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.cloud_client import Cloud
from ..storage.settings_service import Einstellungen
from ..storage.template_repository import VorlagenRepository
from . import base, export_command

BID = "spenglerVorlageAusApp"
Z = {"liste": [], "auftrag": ""}


@base.sicher("Vorlage aus App-Massaufnahme")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    angaben = export_command.auftrag_angaben(e)
    if not angaben["auftrag"]:
        raise fa.AdapterFehler("Kein aktiver Auftrag. Bitte zuerst «Auftrag wählen» oder das Dokument im Auftragsordner speichern.")
    c = Cloud(timeout=10)
    if not c.angemeldet:
        raise fa.AdapterFehler("Für die App-Daten zuerst unter «Konto» anmelden.")
    Z["auftrag"] = angaben["auftrag"]
    Z["liste"] = c.massaufnahmen_zum_auftrag(angaben["auftrag"])
    if not Z["liste"]:
        raise fa.AdapterFehler("In der App gibt es zum Auftrag %s keine Massaufnahme «Freies Profil» oder «Dachrandblech» (oder der Auftrag wurde dort nicht gefunden)." % angaben["auftrag"])
    dd = inp.addDropDownCommandInput("aufnahme", "Massaufnahme in der App", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, m in enumerate(Z["liste"]):
        dd.listItems.add("%s (%s, %s)" % (m.get("title") or "ohne Titel", m["type"], m.get("workflow_status") or "?"), i == 0)
    inp.addStringValueInput("name", "Name der Vorlage", "")
    inp.addStringValueInput("kategorie", "Kategorie", "Aus der App")
    inp.addTextBoxCommandInput("info", "", "Übernommen werden Schenkel und Winkel; der erste Schenkel (bestehendes Blech) entfällt. Richtung und Bezug bitte im Editor prüfen.", 3, True)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)


def erstellt(args):
    _erstellt(None, args)


@base.sicher("Vorlage aus App-Massaufnahme")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    m = Z["liste"][inp.itemById("aufnahme").selectedItem.index]
    ops, hinweise = app_profil.operationen_aus_app((m.get("data") or {}).get("schenkel"))
    if not ops:
        raise fa.AdapterFehler("Die Massaufnahme enthält keine Biegung, aus der eine Vorlage entstehen könnte.")
    name = inp.itemById("name").value.strip() or (m.get("title") or "Profil aus der App")
    v, f, w = lernen.vorlage_aus_schritten(name, ops, inp.itemById("kategorie").value,
                                           "Aus der Massaufnahme «%s» der App übernommen (Schenkel und Winkel)." % (m.get("title") or m["id"]))
    if v is None:
        raise fa.AdapterFehler("Die Vorlage ist nicht gültig:\n" + "\n".join(f))
    gespeichert = VorlagenRepository().speichern(v)
    logger.info("Vorlage aus App-Massaufnahme", name=gespeichert["name"], massaufnahme=m["id"], schritte=lernen.kurzschrift(ops))
    base.melden("Vorlage aus der App", "Vorlage «%s» angelegt (Kurzschrift: %s).\n\n%s" % (gespeichert["name"], lernen.kurzschrift(ops), "\n".join(hinweise + w)))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Vorlage aus App-Massaufnahme", "Übernimmt Schenkel und Winkel einer Massaufnahme des aktiven Auftrags aus der App als Kantenvorlage.", erstellt)]

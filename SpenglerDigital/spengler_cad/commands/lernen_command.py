"""Befehl «Vorlage aus Profil lernen»: liest die Flansch-/Saum-Features des offenen Dokuments (nur Werte) und legt daraus eine Kantenvorlage an.
Verändert das Modell nicht. NICHT live in Fusion geprüft."""
import adsk.core

from ..core import lernen
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.template_repository import VorlagenRepository
from . import base

BID = "spenglerVorlageLernen"
Z = {"features": [], "hinweise": []}
MAX = 30


@base.sicher("Vorlage aus Profil lernen")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    Z["features"], Z["hinweise"] = fa.profil_features_lesen()
    if not Z["features"]:
        raise fa.AdapterFehler("Im offenen Dokument wurden keine Flansch- oder Saum-Features in der Zeitleiste gefunden.%s" % (
            (" " + " ".join(Z["hinweise"])) if Z["hinweise"] else ""))
    inp.addStringValueInput("name", "Name der Vorlage", "Gelerntes Profil")
    inp.addStringValueInput("kategorie", "Kategorie", "Gelernt")
    g = inp.addGroupCommandInput("schritte", "Schritte aus der Zeitleiste (Reihenfolge wie dort)")
    g.isExpanded = True
    for i, f in enumerate(Z["features"][:MAX]):
        g.children.addBoolValueInput("f%d" % i, "%d. %s – %s" % (i + 1, f["name"], lernen.beschreibung(f)), True, "", f.get("laenge_mm") is not None)
    inp.addTextBoxCommandInput("info", "", "Gelesen werden nur die Werte. Richtung und Bezug der Masse bitte danach im Editor prüfen.", 3, True)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)


def erstellt(args):
    _erstellt(None, args)


@base.sicher("Vorlage aus Profil lernen")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    gewaehlt = [f for i, f in enumerate(Z["features"][:MAX]) if inp.itemById("f%d" % i).value]
    if not gewaehlt:
        raise fa.AdapterFehler("Kein Schritt gewählt.")
    ops, hinweise, fehler = lernen.schritte_aus_features(gewaehlt)
    if fehler:
        raise fa.AdapterFehler("Nicht alle gewählten Schritte sind lesbar:\n" + "\n".join(fehler))
    v, f, w = lernen.vorlage_aus_schritten(inp.itemById("name").value, ops, inp.itemById("kategorie").value)
    if v is None:
        raise fa.AdapterFehler("Die Vorlage ist nicht gültig:\n" + "\n".join(f))
    gespeichert = VorlagenRepository().speichern(v)
    logger.info("Vorlage gelernt", name=v["name"], schritte=lernen.kurzschrift(ops))
    base.melden("Vorlage gelernt", "Vorlage «%s» angelegt (Kurzschrift: %s).\n\n%s\n\nBitte im Register «Kantenvorlagen» der Palette öffnen und prüfen." % (
        gespeichert["name"], lernen.kurzschrift(ops), "\n".join(hinweise + w)))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Vorlage aus Profil lernen", "Liest die Flansche und Säume eines vorhandenen Profils (nur Werte) und legt daraus eine Kantenvorlage an.", erstellt)]

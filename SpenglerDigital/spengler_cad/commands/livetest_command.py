"""Befehl «Live-Test»: prüft die Fusion-Funktionen des Add-ins automatisch in neuen Testdokumenten (Flansch, Umschlag, Gehrung, Versatz,
Abwicklung, DXF …) und schickt den Bericht an Spengler Digital. Verändert keine Dokumente des Benutzers. NICHT live in Fusion geprüft."""
import datetime
import os

import adsk.core

from .. import VERSION
from ..core import livetest_bericht as bericht
from ..diagnostics import logger
from ..storage import paths
from . import base

BID = "spenglerLiveTest"


def _senden(ergebnisse, text):
    from ..storage.cloud_client import Cloud
    c = Cloud(paths.daten_ordner(), timeout=20)
    if not c.angemeldet:
        return False
    auff = bericht.auffaelliges(ergebnisse)
    c.test_speichern({"test_id": bericht.TEST_ID, "text": "Live-Test %s: %s" % (VERSION, bericht.kurz(ergebnisse)),
                      "status": bericht.gesamtstatus(ergebnisse),
                      "notiz": ("; ".join("%s: %s" % (e["name"], (e.get("detail") or "").splitlines()[0] if e.get("detail") else "") for e in auff))[:4000] or "Alles ok.",
                      "protokoll": (text + "\n\n--- Protokoll ---\n" + logger.ende())[-19000:], "addin_version": VERSION,
                      "fusion_version": logger.fusion_version(),
                      "geaendert_am": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    return True


@base.sicher("Live-Test")
def _ausfuehren_innen(self, args):
    from ..diagnostics import live_test
    senden = args.command.commandInputs.itemById("senden").value
    ui = base.ui()
    ergebnisse, kopf = live_test.ausfuehren()
    text = bericht.text(ergebnisse, kopf)
    datei = os.path.join(paths.daten_ordner(), "livetest.txt")
    try:
        with open(datei, "w", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        datei = ""
    logger.info("Live-Test", ergebnis=bericht.kurz(ergebnisse))
    gesendet = False
    if senden:
        try:
            gesendet = _senden(ergebnisse, text)
        except Exception:
            logger.ausnahme("Live-Test nicht gesendet")
    base.melden("Live-Test", "%s\n\n%s\n\n%s%s" % (bericht.kurz(ergebnisse), bericht.meldung(ergebnisse),
                "Bericht an Spengler Digital gesendet." if gesendet else ("Nicht gesendet (nicht angemeldet oder ausgeschaltet)." if senden else "Nicht gesendet."),
                ("\nBericht-Datei: " + datei) if datei else ""), bericht.gesamtstatus(ergebnisse) == "fehler" and not gesendet)


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


@base.sicher("Live-Test")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    inp.addTextBoxCommandInput("info", "", "<b>Prüft die Fusion-Funktionen automatisch.</b><br>"
                               "Das Add-in baut in neuen, leeren Dokumenten ein Test-Blech und probiert Flansch, Umschlag, Gehrung, Versatz, Abwicklung "
                               "und DXF durch. Ihre Dokumente bleiben unberührt; die Testdokumente werden ohne Speichern geschlossen.<br><br>"
                               "Dauer etwa 1–2 Minuten. Fusion reagiert währenddessen nicht – bitte nichts anklicken.", 7, True)
    inp.addBoolValueInput("senden", "Ergebnis an Spengler Digital senden", True, "", True)
    cmd.okButtonText = "Test starten"
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)


def erstellt(args):
    _erstellt(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Live-Test", "Prüft die Fusion-Funktionen des Add-ins automatisch (Flansch, Umschlag, Gehrung, Versatz, "
                                   "Abwicklung, DXF) in Testdokumenten und sendet den Bericht.", erstellt)]

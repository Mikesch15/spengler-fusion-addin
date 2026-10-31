"""Selbsttest nach einem Update: prüft einmal je Add-in-Version, welche Fusion-Funktionen in DIESER Fusion-Version vorhanden sind, und meldet das
Ergebnis (Testpunkt 97.001) an die eigene Firma – so sieht der Entwickler früh, was in einer Fusion-Version fehlt. Verändert nichts im Modell."""
import datetime
import os

from .. import VERSION
from ..storage import json_store, paths
from . import fusion_capabilities, logger

TEST_ID = "97.001"


def _datei(wurzel=None):
    return os.path.join(wurzel or paths.daten_ordner(), "selbsttest.json")


def noetig(wurzel=None):
    d = json_store.lesen(_datei(wurzel)) or {}
    return d.get("version") != VERSION


def ausfuehren(app, cloud=None, wurzel=None, fusion_version=""):
    """→ (alles_ok, Text) oder None, wenn kein Design offen ist (dann später nochmal). Meldet angemeldet an die App; merkt sich die Version."""
    try:
        if getattr(app.activeProduct, "rootComponent", None) is None:
            return None
    except Exception:
        return None
    f = fusion_capabilities.pruefen(app)
    fehlt = [t for ok, t in f.values() if not ok]
    text = fusion_capabilities.text(f)
    json_store.schreiben(_datei(wurzel), {"version": VERSION, "zeit": datetime.datetime.now().isoformat(timespec="seconds"), "fehlt": fehlt})
    try:
        if cloud is not None and cloud.angemeldet:
            cloud.test_speichern({"test_id": TEST_ID, "text": "Selbsttest nach Update auf %s" % VERSION, "status": "fehler" if fehlt else "ok",
                                  "notiz": ("Fehlt: " + "; ".join(fehlt))[:4000] if fehlt else "Alle geprüften Fusion-Funktionen vorhanden.",
                                  "protokoll": text[:19000], "addin_version": VERSION, "fusion_version": str(fusion_version),
                                  "geaendert_am": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    except Exception:
        logger.warnung("Selbsttest-Ergebnis nicht an die App übermittelt")
    logger.info("Selbsttest nach Update", version=VERSION, fehlt=len(fehlt))
    return (not fehlt), text

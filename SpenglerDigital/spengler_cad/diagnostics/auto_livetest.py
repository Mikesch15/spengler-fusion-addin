"""Live-Test ohne Knopfdruck (Anwender 6. 11. 2026: «damit der Live-Test automatisch läuft»). Reine Logik, ohne Fusion testbar.

Zwei Auslöser – beide nur, wenn angemeldet und in den Einstellungen eingeschaltet:
1. NACH UPDATE: einmal je Add-in-Version beim ersten Fusion-Start mit der neuen Version (kurz nach dem Start, ca. 3–5 Min.).
2. FERN-AUSLÖSUNG: der Entwickler setzt den Testpunkt 97.900 in der Cloud auf «offen»; läuft Fusion und ist mindestens UNTAETIG_S
   untätig (kein Befehl gestartet, kein Befehl aktiv), führt das Add-in den Live-Test aus und setzt 97.900 auf «ok».
Fusion selbst muss laufen – ohne Bildschirm/Cloud lässt sich Fusion nicht starten."""
import datetime
import os

from .. import VERSION
from ..storage import json_store, paths

ANFRAGE_ID = "97.900"
UNTAETIG_S = 600          # 10 Minuten ohne Befehl
ABFRAGE_S = 300           # alle 5 Minuten nachsehen


def _datei(wurzel=None):
    return os.path.join(wurzel or paths.daten_ordner(), "livetest_auto.json")


def noetig_nach_update(wurzel=None):
    return (json_store.lesen(_datei(wurzel)) or {}).get("version") != VERSION


def gelaufen(wurzel=None, ausloeser=""):
    json_store.schreiben(_datei(wurzel), {"version": VERSION, "zeit": datetime.datetime.now().isoformat(timespec="seconds"), "ausloeser": ausloeser})


def anfrage_offen(zeilen):
    """zeilen = cloud.test_liste() → True, wenn der Testpunkt 97.900 auf «offen» steht."""
    return any(z.get("test_id") == ANFRAGE_ID and z.get("status") == "offen" for z in (zeilen or []))


def untaetig(letzte_aktivitaet, jetzt, aktiver_befehl=None, schwelle_s=UNTAETIG_S):
    """True, wenn seit `schwelle_s` Sekunden kein Befehl gestartet wurde und keiner läuft (Fusions Leerlauf-Befehl heisst «SelectCommand»)."""
    if aktiver_befehl not in (None, "", "SelectCommand"):
        return False
    return (jetzt - letzte_aktivitaet) >= schwelle_s


def erledigt_zeile(ergebnis_kurz):
    return {"test_id": ANFRAGE_ID, "text": "Live-Test auf Anforderung – erledigt mit %s" % VERSION, "status": "ok",
            "notiz": ("Ergebnis: %s (Bericht unter 97.002)" % ergebnis_kurz)[:4000], "addin_version": VERSION,
            "geaendert_am": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}

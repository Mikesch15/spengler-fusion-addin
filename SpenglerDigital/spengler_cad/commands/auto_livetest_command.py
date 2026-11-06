"""Automatischer Live-Test (Logik: diagnostics/auto_livetest): nach jedem Update einmal beim Start und auf Fern-Anforderung bei Leerlauf.
Fusion-API-Aufrufe NUR im Hauptthread (Custom Event); der Hintergrund-Thread fragt nur die Cloud ab. NICHT live geprüft."""
import threading
import time

import adsk.core

from ..diagnostics import auto_livetest as al
from ..diagnostics import logger
from . import base

EREIGNIS = "spenglerAutoLivetest"
Z = {"aktiv": time.time(), "stop": None, "laeuft": False}


def _einstellung(schluessel):
    from ..storage.settings_service import Einstellungen
    try:
        return Einstellungen().laden().get("cloud", {}).get(schluessel, False) is True      # nur wenn ausdrücklich eingeschaltet
    except Exception:
        return False


def _cloud():
    from ..storage.cloud_client import Cloud
    return Cloud(timeout=10)


def _befehl_gestartet(args):
    Z["aktiv"] = time.time()


def _aktiver_befehl():
    try:
        return base.ui().activeCommand
    except Exception:
        return None


def _ausloesen(args):
    """Hauptthread: Live-Test ausführen. additionalInfo = «update» oder «fern»."""
    grund = adsk.core.CustomEventArgs.cast(args).additionalInfo
    if Z["laeuft"]:
        return
    if not al.untaetig(Z["aktiv"], time.time(), _aktiver_befehl(), schwelle_s=al.UNTAETIG_S if grund == "fern" else 0):
        return                                    # es läuft ein Befehl bzw. inzwischen wieder gearbeitet – beim nächsten Mal erneut
    Z["laeuft"] = True
    try:
        from . import livetest_command
        from ..core import livetest_bericht
        logger.info("Automatischer Live-Test startet", ausloeser=grund)
        ergebnisse, gesendet = livetest_command.lauf(senden=True, melden=False)
        al.gelaufen(ausloeser=grund)
        if grund == "fern":
            try:
                _cloud().test_speichern(al.erledigt_zeile(livetest_bericht.kurz(ergebnisse)))
            except Exception:
                logger.ausnahme("Fern-Anforderung nicht als erledigt gemeldet")
        logger.info("Automatischer Live-Test beendet", ausloeser=grund, gesendet=gesendet)
        if grund == "update":
            base.melden("Live-Test nach Update", "Der Live-Test lief automatisch nach dem Update (Testdokumente, Ihre Dokumente unverändert):\n%s\n\n%s\n\n"
                        "Abschaltbar unter Vorlagen & Einstellungen, Abschnitt «Beim Start»." % (livetest_bericht.kurz(ergebnisse),
                                                                              "Bericht an Spengler Digital gesendet." if gesendet else "Bericht NICHT gesendet."))
    except Exception:
        logger.ausnahme("Automatischer Live-Test")
    finally:
        Z["aktiv"] = time.time()
        Z["laeuft"] = False


def _schleife(stop):
    app = adsk.core.Application.get()
    if stop.wait(45):                              # Fusion erst fertig starten lassen
        return
    try:
        if _einstellung("livetestAutoNachUpdate") and al.noetig_nach_update() and _cloud().angemeldet:
            app.fireCustomEvent(EREIGNIS, "update")
    except Exception:
        logger.ausnahme("Automatischer Live-Test (nach Update)")
    while not stop.wait(al.ABFRAGE_S):
        try:
            if Z["laeuft"] or not _einstellung("livetestAutoFern"):
                continue
            c = _cloud()
            # nur Zeit prüfen – der aktive Befehl ist eine Fusion-API-Abfrage und wird im Hauptthread (_ausloesen) geprüft
            if c.angemeldet and al.untaetig(Z["aktiv"], time.time()) and al.anfrage_offen(c.test_liste()):
                app.fireCustomEvent(EREIGNIS, "fern")
        except Exception:
            logger.warnung("Fern-Anforderung Live-Test nicht abgefragt")


def starten():
    app = adsk.core.Application.get()
    try:
        app.unregisterCustomEvent(EREIGNIS)
    except Exception:
        pass
    ev = app.registerCustomEvent(EREIGNIS)
    base.handler(adsk.core.CustomEventHandler, ev, _ausloesen)
    base.handler(adsk.core.ApplicationCommandEventHandler, base.ui().commandStarting, _befehl_gestartet)
    stop = threading.Event()
    Z["stop"] = stop
    threading.Thread(target=_schleife, args=(stop,), daemon=True, name="SpenglerAutoLivetest").start()


def stoppen():
    if Z["stop"] is not None:
        Z["stop"].set()
    try:
        adsk.core.Application.get().unregisterCustomEvent(EREIGNIS)
    except Exception:
        pass

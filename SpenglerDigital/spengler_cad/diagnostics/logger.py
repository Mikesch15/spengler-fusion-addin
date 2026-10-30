"""Zentrales Diagnoseprotokoll im Benutzerdatenordner (protokoll/spengler_cad.log, rotierend).

Protokolliert: Add-in-/Fusion-Version, Befehl, Vorlagen-ID/-Version, Operation, betroffene Geometrie
(nur technische Kennungen), Warnungen/Fehler, API-Fähigkeiten. Keine Dateiinhalte, keine Kundendaten.
"""
import datetime
import os
import traceback

from .. import VERSION

_MAX = 2 * 1024 * 1024
_kontext = {"fusion": ""}


def _pfad():
    try:
        from ..storage import paths
        return os.path.join(paths.unterordner("protokoll"), "spengler_cad.log")
    except Exception:
        import tempfile
        return os.path.join(tempfile.gettempdir(), "spengler_cad.log")


def pfad():
    return _pfad()


def fusion_version():
    return _kontext["fusion"]


def ende(zeilen=150, max_zeichen=19000):
    """Letzte Protokollzeilen (für Testergebnisse); leer, wenn es kein Protokoll gibt."""
    try:
        with open(_pfad(), encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-zeilen:])[-max_zeichen:]
    except Exception:
        return ""


def setze_fusion_version(v):
    _kontext["fusion"] = str(v)


def schreibe(stufe, text, **daten):
    try:
        p = _pfad()
        if os.path.exists(p) and os.path.getsize(p) > _MAX:
            alt = p + ".1"
            if os.path.exists(alt):
                os.remove(alt)
            os.replace(p, alt)
        zusatz = " ".join("%s=%s" % (k, _kurz(v)) for k, v in daten.items())
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s [%s] v%s F%s %s %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), stufe, VERSION,
                                                 _kontext["fusion"], text, zusatz))
    except Exception:
        pass  # Protokoll darf nie den Befehl stören


def _kurz(v):
    s = str(v).replace("\n", " | ")
    return s if len(s) < 3500 else s[:3500] + "…"


def info(text, **d):
    schreibe("INFO", text, **d)


def warnung(text, **d):
    schreibe("WARN", text, **d)


def fehler(text, **d):
    schreibe("FEHLER", text, **d)


def ausnahme(text, **d):
    schreibe("FEHLER", text, trace=traceback.format_exc(), **d)

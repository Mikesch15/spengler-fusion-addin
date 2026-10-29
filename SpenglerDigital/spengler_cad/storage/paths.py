"""Speicherorte. Benutzerdaten liegen IMMER ausserhalb des Add-in-Ordners, damit ein Update
(Add-in-Ordner ersetzen) keine Vorlagen, Materialien oder Einstellungen löscht.

  Windows: %APPDATA%\\SpenglerDigitalCAD
  macOS:   ~/Library/Application Support/SpenglerDigitalCAD
  sonst:   ~/.spengler_digital_cad
Für Tests und Sonderfälle: Umgebungsvariable SPENGLER_CAD_DATEN.
"""
import os
import sys

ADDIN_ORDNER = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SYSTEM_VORLAGEN = os.path.join(ADDIN_ORDNER, "templates", "system")


class PfadFehler(RuntimeError):
    pass


def daten_ordner():
    p = os.environ.get("SPENGLER_CAD_DATEN")
    if not p:
        if sys.platform.startswith("win"):
            p = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "SpenglerDigitalCAD")
        elif sys.platform == "darwin":
            p = os.path.expanduser("~/Library/Application Support/SpenglerDigitalCAD")
        else:
            p = os.path.expanduser("~/.spengler_digital_cad")
    p = os.path.abspath(p)
    if ist_innerhalb(p, ADDIN_ORDNER):
        raise PfadFehler("Der Benutzerdatenordner darf nicht im Add-in-Ordner liegen (Updates würden ihn löschen): %s" % p)
    return p


def ist_innerhalb(pfad, ordner):
    a, b = os.path.normcase(os.path.abspath(pfad)), os.path.normcase(os.path.abspath(ordner))
    return a == b or a.startswith(b.rstrip(os.sep) + os.sep)


UNTERORDNER = {
    "kanten": os.path.join("vorlagen", "kanten"),
    "details": os.path.join("vorlagen", "details"),
    "geometrie": os.path.join("vorlagen", "details", "geometrie"),
    "versionen": os.path.join("vorlagen", "versionen"),
    "papierkorb": os.path.join("vorlagen", "papierkorb"),
    "materialien": "materialien",
    "sicherungen": "sicherungen",
    "protokoll": "protokoll",
    "export": "export",
}

# Was zu den Benutzerdaten gehört (Sicherung/Wiederherstellung/Migration)
DATEN_INHALT = ("datenformat.json", "einstellungen.json", "vorlagen", "materialien")


def unterordner(name, wurzel=None):
    p = os.path.join(wurzel or daten_ordner(), UNTERORDNER[name])
    os.makedirs(p, exist_ok=True)
    return p

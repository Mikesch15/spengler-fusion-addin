"""Tabellen im Statusdokument aus dem Code erzeugen (Unterstützungsmatrix, Machbarkeit, Kantenwerkzeug, Prototyp-Analyse).
Aufruf: python3 docs/status_tabellen.py   – ersetzt die Blöcke zwischen <!-- AUTO:name --> und <!-- /AUTO:name --> in ANFORDERUNGEN_STATUS.md."""
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))

from spengler_cad.core import machbarkeit_gekruemmt as mg  # noqa: E402
from spengler_cad.core import unterstuetzung as u  # noqa: E402

BLOECKE = {"matrix": u.als_markdown, "machbarkeit": u.machbarkeit_markdown, "kantenwerkzeug": u.kantenwerkzeug_markdown, "prototyp": mg.als_markdown}
PFAD = os.path.join(HIER, "ANFORDERUNGEN_STATUS.md")


def inhalt(name):
    return "<!-- AUTO:%s -->\n%s\n<!-- /AUTO:%s -->" % (name, BLOECKE[name](), name)


def aktualisieren(text):
    for name in BLOECKE:
        text = re.sub(r"<!-- AUTO:%s -->.*?<!-- /AUTO:%s -->" % (name, name), lambda m, n=name: inhalt(n), text, flags=re.S)
    return text


if __name__ == "__main__":
    with open(PFAD, encoding="utf-8") as f:
        t = f.read()
    n = aktualisieren(t)
    with open(PFAD, "w", encoding="utf-8") as f:
        f.write(n)
    print("Statustabellen aktualisiert" if n != t else "Statustabellen unverändert")

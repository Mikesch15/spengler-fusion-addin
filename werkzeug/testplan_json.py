"""Testplan für die Palette erzeugen (Werkzeug für die Entwicklung, wird NICHT mit dem Add-in ausgeliefert).

  python3 werkzeug/testplan_json.py     docs/Testanleitung.md → palette/testplan.json

Jede Tabellenzeile «| ☐ | Schritt | Erwartet |» wird ein Testpunkt mit der Kennung <Block>.<Nr> (z. B. 6.9).
Die Kennungen sind die Schlüssel der Ergebnisse (lokal und in der Cloud); beim Umordnen der Anleitung ändern sie sich.
Block «Rückmeldung» entfällt: die Ergebnisse gehen direkt aus der Palette in die Cloud.
"""
import json
import os
import re

HIER = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.path.join(HIER, "..", "SpenglerDigital")
QUELLE = os.path.join(ADDIN, "docs", "Testanleitung.md")
ZIEL = os.path.join(ADDIN, "palette", "testplan.json")


def _text(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s.strip())
    return re.sub(r"`(.+?)`", r"\1", s).replace("&amp;", "&")


def lesen(pfad=QUELLE):
    bloecke, aktuell = [], None
    for zeile in open(pfad, encoding="utf-8").read().split("\n"):
        m = re.match(r"^## (\d+)\. (.+)$", zeile)
        if m:
            aktuell = {"nr": int(m.group(1)), "titel": _text(m.group(2)), "hinweis": "", "punkte": []}
            bloecke.append(aktuell)
            continue
        if aktuell is None:
            continue
        if zeile.startswith("| ☐ |"):
            zellen = [z.strip() for z in zeile.strip().strip("|").split("|")]
            if len(zellen) < 2 or zellen[1] in ("Schritt", "Was schicken"):
                continue
            aktuell["punkte"].append({"id": "%d.%d" % (aktuell["nr"], len(aktuell["punkte"]) + 1), "text": _text(zellen[1]),
                                      "erwartet": _text(zellen[2]) if len(zellen) > 2 and zellen[2] not in ("–", "-") else ""})
        elif zeile.strip() and not zeile.startswith("|") and not zeile.startswith("#") and not aktuell["punkte"]:
            aktuell["hinweis"] = (aktuell["hinweis"] + " " + _text(zeile)).strip()
    return [b for b in bloecke if b["punkte"] and b["titel"] != "Rückmeldung"]


if __name__ == "__main__":
    plan = lesen()
    with open(ZIEL, "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "bloecke": plan}, f, ensure_ascii=False, indent=1)
    print("%s: %d Blöcke, %d Testpunkte" % (ZIEL, len(plan), sum(len(b["punkte"]) for b in plan)))

"""Materialbestellliste über einen ganzen Auftrag (mehrere Dokumente): gespeicherte Teile je Dokument zusammenführen und rechnen.

Der Stand je Dokument wird beim Ausführen von «Stückliste & Zuschnitt» im Benutzerordner abgelegt (auftraege/<Nummer>.json)."""
import datetime
import os

from ..storage import json_store, paths
from . import material_calculator


def _datei(nummer, wurzel=None):
    return os.path.join(wurzel or paths.daten_ordner(), "auftraege", json_store.dateiname_sicher("%s" % nummer) + ".json")


def teile_merken(nummer, dokument, teile, wurzel=None):
    """Stand dieses Dokuments für den Auftrag speichern (ersetzt den früheren Stand desselben Dokuments)."""
    if not nummer or not dokument:
        return False
    pfad = _datei(nummer, wurzel)
    d = json_store.lesen(pfad) or {"auftrag": str(nummer), "dokumente": {}}
    schlank = [{k: t.get(k) for k in ("nr", "name", "materialId", "flaeche", "breite", "laenge", "stueck")} for t in teile]
    d["dokumente"][dokument] = {"stand": datetime.datetime.now().isoformat(timespec="seconds"), "teile": schlank}
    json_store.schreiben(pfad, d)
    return True


def teile_lesen(nummer, wurzel=None):
    return (json_store.lesen(_datei(nummer, wurzel)) or {}).get("dokumente", {})


def bestellung(nummer, materialien, einstellungen=None, wurzel=None):
    """→ {'dokumente': [...], 'teile': [...], 'erg': Ergebnis von material_calculator, 'text': str}"""
    dok = teile_lesen(nummer, wurzel)
    teile = []
    for name, d in dok.items():
        for t in d["teile"]:
            teile.append(dict(t, dokument=name))
    if not teile:
        return {"dokumente": [], "teile": [], "erg": None, "text": "Für Auftrag %s liegen noch keine gespeicherten Teile vor. Zuerst in jedem Dokument «Stückliste & Zuschnitt» ausführen." % nummer}
    erg = material_calculator.berechne(teile, materialien, einstellungen)
    z = ["Materialbestellliste Auftrag %s (%d Dokument(e), %d Teile)" % (nummer, len(dok), sum(int(t.get("stueck") or 1) for t in teile)), ""]
    for name, d in sorted(dok.items()):
        z.append("  %s – Stand %s, %d Teile" % (name, d["stand"].replace("T", " "), len(d["teile"])))
    z += ["", material_calculator.bericht_text(erg)]
    return {"dokumente": sorted(dok), "teile": teile, "erg": erg, "text": "\n".join(z)}

"""Einstellungen laden/speichern. Fehlende Felder werden mit Programmstandards ergänzt, unbekannte bleiben erhalten."""
import os

from ..core.models import SCHEMA, kopie, standard_einstellungen
from . import json_store, paths


class EinstellungsFehler(RuntimeError):
    pass


def _ergaenzen(ziel, standard):
    for k, v in standard.items():
        if k not in ziel:
            ziel[k] = kopie(v)
        elif isinstance(v, dict) and isinstance(ziel[k], dict):
            _ergaenzen(ziel[k], v)
    return ziel


class Einstellungen(object):
    def __init__(self, wurzel=None):
        self.wurzel = wurzel or paths.daten_ordner()
        self.pfad = os.path.join(self.wurzel, "einstellungen.json")

    def laden(self):
        d = json_store.lesen(self.pfad)
        if d is None:
            return standard_einstellungen()
        if (d.get("schemaVersion") or 0) > SCHEMA["einstellungen"]:
            d["_nurLesen"] = True   # neuere Programmversion: lesen ja, überschreiben nein
            return _ergaenzen(d, standard_einstellungen())
        return _ergaenzen(d, standard_einstellungen())

    def speichern(self, d):
        if d.get("_nurLesen"):
            raise EinstellungsFehler("Die Einstellungen stammen aus einer neueren Programmversion und werden nicht überschrieben.")
        n = d.get("nesting", {})
        for k in ("kerf", "margin"):
            if not isinstance(n.get(k), (int, float)) or n.get(k) < 0:
                raise EinstellungsFehler("Zuschnitt: %s muss eine Zahl ≥ 0 sein." % k)
        from ..manufacturing.parts_list import etiketten_pruefen
        f, _ = etiketten_pruefen(d.get("labels") or {})
        if f:
            raise EinstellungsFehler(" ".join(f))
        if d.get("ui", {}).get("mode") not in ("standard", "experte"):
            raise EinstellungsFehler("Modus muss «standard» oder «experte» sein.")
        d = kopie(d)
        d["schemaVersion"] = SCHEMA["einstellungen"]
        d["typ"] = "einstellungen"
        json_store.schreiben(self.pfad, d)
        return d

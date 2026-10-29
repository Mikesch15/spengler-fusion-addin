"""Materialprofile des Benutzers. Die Bibliothek beginnt LEER – keine erfundenen Fertigungswerte."""
import os
import shutil

from ..core.models import SCHEMA, jetzt, kopie, neue_id
from . import json_store, paths


class MaterialFehler(RuntimeError):
    pass


def pruefe_material(m):
    f = []
    if not (m.get("name") or "").strip():
        f.append("Das Materialprofil braucht einen Namen.")
    try:
        if not float(m.get("thickness")) > 0:
            f.append("Blechdicke muss grösser als 0 mm sein.")
    except (TypeError, ValueError):
        f.append("Blechdicke fehlt oder ist keine Zahl.")
    for feld, label, gt0 in (("density", "Dichte", True), ("innerRadius", "Innenradius", False), ("kFactor", "K-Faktor", False)):
        w = m.get(feld)
        if w is None:
            continue
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0 or (gt0 and w == 0):
            f.append("%s ist ungültig." % label)
    if isinstance(m.get("kFactor"), (int, float)) and not (0 <= m["kFactor"] <= 1):
        f.append("K-Faktor muss zwischen 0 und 1 liegen.")
    for s in m.get("sheets") or []:
        if not (isinstance(s, (list, tuple)) and len(s) == 2 and all(isinstance(x, (int, float)) and x > 0 for x in s)):
            f.append("Tafelformat %r ist ungültig (Breite, Länge in mm)." % (s,))
    for c in m.get("coils") or []:
        if not (isinstance(c, (int, float)) and c > 0):
            f.append("Rollenbreite %r ist ungültig." % (c,))
    lim = m.get("formingLimits") or {}
    for feld in ("shrinkMaxPercent", "stretchMaxPercent"):
        w = lim.get(feld)
        if w is not None and (not isinstance(w, (int, float)) or w < 0 or w > 100):
            f.append("Umformgrenze %s ist ungültig (0–100 %%)." % feld)
    return f


class MaterialBibliothek(object):
    def __init__(self, wurzel=None):
        self.wurzel = wurzel or paths.daten_ordner()

    def _ordner(self):
        return paths.unterordner("materialien", self.wurzel)

    def liste(self):
        out = []
        for n in sorted(os.listdir(self._ordner())):
            if n.endswith(".json") and not n.startswith("."):
                m = json_store.lesen(os.path.join(self._ordner(), n))
                if isinstance(m, dict) and m.get("typ") == "materialprofil":
                    m["_nurLesen"] = (m.get("schemaVersion") or 0) > SCHEMA["materialprofil"]
                    out.append(m)
        return sorted(out, key=lambda m: (m.get("name") or "").lower())

    def holen(self, mid):
        for m in self.liste():
            if m["id"] == mid:
                return m
        raise MaterialFehler("Materialprofil %s nicht gefunden." % mid)

    def speichern(self, m):
        f = pruefe_material(m)
        if f:
            raise MaterialFehler("Materialprofil nicht gespeichert:\n" + "\n".join(f))
        m = kopie(m)
        m.pop("_nurLesen", None)
        if (m.get("schemaVersion") or 0) > SCHEMA["materialprofil"]:
            raise MaterialFehler("Dieses Profil stammt aus einer neueren Programmversion und wird nicht verändert.")
        m["schemaVersion"] = SCHEMA["materialprofil"]
        m["typ"] = "materialprofil"
        m["thickness"] = float(m["thickness"])
        m.setdefault("id", neue_id("mat"))
        m["modified"] = jetzt()
        json_store.schreiben(os.path.join(self._ordner(), json_store.dateiname_sicher(m["id"]) + ".json"), m)
        return m

    def loeschen(self, mid, bestaetigt=False):
        if not bestaetigt:
            raise MaterialFehler("Löschen braucht eine ausdrückliche Bestätigung.")
        self.holen(mid)
        q = os.path.join(self._ordner(), json_store.dateiname_sicher(mid) + ".json")
        ziel = os.path.join(paths.unterordner("papierkorb", self.wurzel), "material_%s_%s.json" % (json_store.dateiname_sicher(mid), jetzt().replace(":", "-")))
        shutil.move(q, ziel)
        return ziel

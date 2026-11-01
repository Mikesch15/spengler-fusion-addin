"""Kantenvorlage aus einem vorhandenen Profil lernen: gelesene Werte der Flansch-/Saum-Features → Operationen. Reine Logik ohne Fusion.

Gelesen werden nur WERTE (Winkel, Länge, Radius) in der Reihenfolge der Zeitleiste – nichts wird verändert. Die Richtung jedes Schritts
(links/rechts in Laufrichtung) lässt sich aus den Werten allein nicht sicher ableiten; sie wird als «nicht geprüft» gemeldet."""
import math

from . import models, short_syntax, validation

ROLLEN = {   # Rollen/Namen von Parametern → Feld (Kleinbuchstaben, Teilstring genügt)
    "winkel": ("angle", "winkel"),
    "laenge": ("height", "höhe", "hoehe", "distance", "abstand", "length", "länge", "laenge"),
    "radius": ("radius",),
}


def feld_zu_rolle(text):
    t = (text or "").lower()
    for feld, namen in ROLLEN.items():
        if any(n in t for n in namen):
            return feld
    return None


def schritte_aus_features(features):
    """features: [{'art': 'flansch'|'umschlag', 'name': str, 'winkel_grad': float|None, 'laenge_mm': float|None, 'radius_mm': float|None, 'gespiegelt': bool}]
    (in Zeitleistenreihenfolge) → (Operationen, Hinweise, Fehler). Fehlende Pflichtwerte (Länge, Winkel beim Flansch) → Fehler je Feature."""
    ops, hinweise, fehler = [], [], []
    for i, f in enumerate(features, 1):
        name = f.get("name") or "Feature %d" % i
        L = f.get("laenge_mm")
        if not isinstance(L, (int, float)) or L <= 0:
            fehler.append("%s: Länge nicht lesbar." % name)
            continue
        if f["art"] == "umschlag":
            ops.append({"typ": "umschlag", "winkel": -180.0 if f.get("gespiegelt") else 180.0, "laenge": round(L, 2), "radius": None})
            continue
        w = f.get("winkel_grad")
        if not isinstance(w, (int, float)) or not 0 < abs(w) < 180:
            fehler.append("%s: Winkel nicht lesbar." % name)
            continue
        w = abs(w) * (-1 if f.get("gespiegelt") else 1)
        r = f.get("radius_mm")
        ops.append({"typ": "flansch", "winkel": round(w, 2), "laenge": round(L, 2),
                    "radius": round(r, 3) if isinstance(r, (int, float)) and r > 0 else None})
    if len(ops) > 1:
        hinweise.append("Die Richtung der Schritte 2 ff. (links/rechts relativ zur Laufrichtung) lässt sich aus den Werten nicht ablesen: alle Schritte "
                        "stehen mit dem Vorzeichen des ersten – bitte in der Vorschau des Editors prüfen und Vorzeichen ändern.")
        erster = ops[0]["winkel"] < 0
        for op in ops[1:]:
            if op["typ"] == "flansch":
                op["winkel"] = -abs(op["winkel"]) if erster else abs(op["winkel"])
            else:
                op["winkel"] = -180.0 if erster else 180.0
    hinweise.append("Längen sind so gelesen, wie Fusion sie anzeigt (Bezug aussen/innen/tangential nicht übernommen); Masse bitte prüfen.")
    return ops, hinweise, fehler


def vorlage_aus_schritten(name, ops, kategorie="Gelernt", beschreibung=""):
    """→ (Vorlage, Fehler, Warnungen). Fehler → keine Vorlage."""
    if not (name or "").strip():
        return None, ["Bitte einen Namen für die Vorlage eingeben."], []
    v = models.neue_kantenvorlage(name.strip(), operations=ops)
    v["category"] = (kategorie or "").strip() or v["category"]
    v["description"] = beschreibung or "Aus einem vorhandenen Profil gelesen (Werte, Richtung bitte prüfen)."
    f, w = validation.pruefe_kantenvorlage(v)
    return (None if f else v), f, w


def beschreibung(f):
    """Kurztext zu einem gelesenen Feature für die Auswahlliste."""
    teile = []
    if f.get("winkel_grad") is not None:
        teile.append("%g°" % round(f["winkel_grad"], 2))
    if f.get("laenge_mm") is not None:
        teile.append("%g mm" % round(f["laenge_mm"], 2))
    if f.get("radius_mm") is not None:
        teile.append("Ri %g" % round(f["radius_mm"], 2))
    return "%s%s" % ("Saum" if f["art"] == "umschlag" else "Flansch", (" " + ", ".join(teile)) if teile else " (Werte nicht lesbar)")


def grad(radiant):
    return math.degrees(radiant)


def kurzschrift(ops):
    return short_syntax.als_text(ops)

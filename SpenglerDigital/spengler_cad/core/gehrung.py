"""Geometrische Prüfung einer Gehrungsecke (reine Rechnung, ohne Fusion testbar).

An einer Ecke zweier Kanten (Richtungen e1, e2 von der Ecke weg, Blechnormale nb) entstehen bei echter Gehrung an jedem Flansch eine ebene
Stirnfläche, deren Normale in der Blechebene liegt (n ⟂ nb) und mit beiden Kanten etwa denselben Winkel einschliesst (|n·e1| ≈ |n·e2|).
Liegen die zwei Gehrungsflächen dicht beieinander (Abstand ≈ Gehrungsspalt), ist die Ecke sauber geschlossen; ein grosser Abstand ist ein
Eckspalt, fehlende Gehrungsflächen bedeuten «stumpfe Ecke». Volumen oder Flächenzahl allein beweisen das nicht."""
import math


def _skal(a, b):
    return sum(x * y for x, y in zip(a, b))


def _abstand(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def gehrungsflaechen(kandidaten, e1, e2, nb, ecke, reichweite_mm=None):
    """kandidaten: [(id, normale, mittelpunkt)] (Einheiten egal, aber einheitlich mit ecke). → ids der Gehrungsflächen in Eckennähe.
    reichweite: nur Flächen, deren Mittelpunkt näher als dies an der Ecke liegt (Standard: alle)."""
    treffer = []
    for i, n, c in kandidaten:
        if abs(_skal(n, nb)) > 0.2:
            continue                                   # Normale nicht in der Blechebene (Ober-/Unterseite)
        a1, a2 = abs(_skal(n, e1)), abs(_skal(n, e2))
        if a1 < 0.2 or a2 < 0.2 or a1 > 0.98 or a2 > 0.98:
            continue                                   # parallel oder senkrecht zu einer Kante: Flanschfläche, keine Gehrung
        if abs(a1 - a2) > 0.15:
            continue                                   # nicht auf der Winkelhalbierenden
        if reichweite_mm is not None and _abstand(c, ecke) > reichweite_mm:
            continue
        treffer.append(i)
    return treffer


def bewerte_eckspalt(abstand_mm, dicke_mm, toleranz_mm=None):
    """Kleinster Abstand der Gehrungsflächen → ('ok'|'fehler'|'unbekannt', Text). Toleranz Standard: 1 × Blechdicke + 0.5 mm (Gehrungsspalt der Blechregel)."""
    if abstand_mm is None:
        return "unbekannt", "Eckspalt nicht messbar."
    tol = toleranz_mm if toleranz_mm is not None else (dicke_mm or 1.0) + 0.5
    if abstand_mm <= tol:
        return "ok", "Eckspalt %.2f mm (≤ %.2f mm) – Gehrung geschlossen." % (abstand_mm, tol)
    return "fehler", "Eckspalt %.2f mm – grösser als %.2f mm, die Ecke ist offen." % (abstand_mm, tol)


def diagnose(kandidaten, e1, e2, nb, ecke, n_max=8):
    """Kurztext der eckennächsten ebenen Flächen: Abstand zur Ecke, |n·nb|, |n·e1|, |n·e2| – zeigt, WARUM keine Gehrungsfläche erkannt wurde
    (z. B. stumpfe Ecke: Stirnfläche ⟂ einer Kante, |n·e| = 1)."""
    z = sorted(kandidaten, key=lambda k: _abstand(k[2], ecke))[:n_max]
    return "; ".join("d %.1f mm, nb %.2f, e1 %.2f, e2 %.2f" % (_abstand(c, ecke), abs(_skal(n, nb)), abs(_skal(n, e1)), abs(_skal(n, e2)))
                     for _i, n, c in z) or "keine"


def stossflaechen(kandidaten, e1, e2, nb, ecke, min_hoehe, reichweite):
    """Stossecke (Live 0.4.59: Fusions «isMiteredCorners» an zwei Kanten erzeugt KEINE 45°-Gehrung, die Flansch-Stirnflächen stehen senkrecht zu
    ihrer Kante): ebene Flächen mit Normale in der Blechebene und parallel zu e1 bzw. e2, Mittelpunkt mindestens `min_hoehe` über dem Blech
    (schliesst Freischnittflächen direkt an der Ecke aus) und höchstens `reichweite` von der Ecke (schliesst die langen Seitenflächen aus).
    → (ids ⟂ e1, ids ⟂ e2)."""
    s1, s2 = [], []
    for i, n, c in kandidaten:
        if abs(_skal(n, nb)) > 0.2:
            continue
        rel = tuple(x - y for x, y in zip(c, ecke))
        if abs(_skal(rel, nb)) < min_hoehe or _abstand(c, ecke) > reichweite:
            continue
        if abs(_skal(n, e1)) > 0.98:
            s1.append(i)
        elif abs(_skal(n, e2)) > 0.98:
            s2.append(i)
    return s1, s2

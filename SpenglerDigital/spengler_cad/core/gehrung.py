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

"""Kantenreferenzen zuverlässig auflösen.

Nach jedem neuen Feature können früher gelesene BRepEdge-Objekte ungültig werden. Deshalb wird für
jede gewählte Kante vor dem Bauen der entityToken gemerkt und vor der Bearbeitung über
design.findEntityByToken neu aufgelöst. Liefert Fusion keine oder mehrere Kanten, wird diese Kante
NICHT bearbeitet (nicht raten).
"""
import adsk.fusion

from .fusion_adapter import AdapterFehler, design


def merken(edges):
    out = []
    for e in edges:
        try:
            out.append(e.entityToken)
        except Exception:
            raise AdapterFehler("Die Kante liefert keine stabile Referenz (entityToken).")
    return out


def aufloesen(token):
    treffer = [adsk.fusion.BRepEdge.cast(x) for x in design().findEntityByToken(token)]
    treffer = [t for t in treffer if t and t.isValid]
    if len(treffer) != 1:
        raise AdapterFehler("Kante nicht mehr eindeutig auffindbar (%d Treffer) – sie wurde evtl. durch einen vorherigen Schritt verändert." % len(treffer))
    return treffer[0]

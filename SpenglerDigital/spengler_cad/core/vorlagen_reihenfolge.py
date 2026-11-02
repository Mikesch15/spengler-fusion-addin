"""Reihenfolge der Vorlagen im Dialog: zuletzt benutzte zuerst, dann Favoriten, dann der Rest (Reihenfolge der Bibliothek bleibt erhalten)."""


def ordnen(vorlagen, zuletzt):
    """→ (Liste, Markierungen {id: '↻'|'★'|''}). zuletzt: Vorlagen-IDs, neueste zuerst."""
    pos = {vid: i for i, vid in enumerate(zuletzt or [])}
    kenn = lambda v: v.get("id")
    neu = sorted(vorlagen, key=lambda v: (0 if kenn(v) in pos else 1 if v.get("favorite") else 2, pos.get(kenn(v), 0)))
    mark = {kenn(v): ("↻" if kenn(v) in pos else "★" if v.get("favorite") else "") for v in vorlagen}
    return neu, mark


def merken(zuletzt, vorlage_id, maximal=5):
    if not vorlage_id:
        return list(zuletzt or [])
    return ([vorlage_id] + [x for x in (zuletzt or []) if x != vorlage_id])[:maximal]

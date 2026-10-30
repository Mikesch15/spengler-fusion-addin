"""Prüfung vor dem Export: Warnungen (nie ein Abbruch) zu Teilen, Material und Biegungen. Reine Logik, Schwellen aus den Einstellungen."""


def standard():
    return {"minSchenkel": 10.0, "minRadiusFaktor": 1.0}


def pruefe_teile(teile, einstellung=None):
    """teile: [{'name', 'nr' (oder ''), 'material' (Profil oder None), 'dicke' (mm oder None), 'abwicklung' (bool), 'operationen' ([{typ,winkel,laenge,radius}] oder None),
    'ri' (Materialradius, mm oder None)}] → Liste von Warntexten."""
    s = dict(standard(), **(einstellung or {}))
    w, gesehen = [], {}
    for t in teile:
        n = t.get("name") or "Teil"
        if not t.get("material"):
            w.append("%s: kein Materialprofil zugeordnet." % n)
        if t.get("nr") in (None, ""):
            w.append("%s: keine Teilenummer." % n)
        else:
            gesehen.setdefault(str(t["nr"]), []).append(n)
        if t.get("abwicklung") is False:
            w.append("%s: keine Fusion-Abwicklung – Mass/Gewicht nur geschätzt." % n)
        dicke = t.get("dicke")
        for i, op in enumerate(t.get("operationen") or [], 1):
            art = "Umschlag" if op.get("typ") == "umschlag" else "Flansch"
            L = op.get("laenge")
            if isinstance(L, (int, float)) and L < s["minSchenkel"]:
                w.append("%s, Schritt %d (%s): Schenkel %.1f mm ist kürzer als %.1f mm." % (n, i, art, L, s["minSchenkel"]))
            r = op.get("radius") if op.get("radius") is not None else t.get("ri")
            if isinstance(r, (int, float)) and dicke and r < s["minRadiusFaktor"] * dicke:
                w.append("%s, Schritt %d (%s): Innenradius %.2f mm ist kleiner als %.2f × Dicke (%.2f mm)." % (n, i, art, r, s["minRadiusFaktor"], dicke))
    for nr, namen in gesehen.items():
        if len(namen) > 1:
            w.append("Teilenummer %s mehrfach vergeben: %s." % (nr, ", ".join(namen)))
    return w

"""Prüfungen für Vorlagen, Parameterwerte und Operationen. Rückgabe immer (fehler, warnungen) als Textlisten."""
from .expressions import AusdruckFehler, berechne, gueltiger_name, namen_in
from .models import EINHEITEN_PARAMETER

MATERIAL_NAMEN = {"t", "ri", "k"}   # stehen in Ausdrücken immer zur Verfügung (aus dem Materialprofil)
OP_TYPEN = ("flansch", "umschlag")
BEZUEGE = ("aussen", "innen", "tangential")          # Fusion: FlangeHeightDatumTypes (Aussenflächen / Innenflächen / tangential zur Biegung)
LAGEN = ("kante", "innen", "aussen", "tangential")   # Fusion: BendPositionTypes (StartEdge / Inside / Outside / TangentToSide)


def _zahl(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def pruefe_parameter(params):
    fehler, warn = [], []
    namen = set()
    for i, p in enumerate(params, 1):
        n = p.get("name", "")
        if not gueltiger_name(n):
            fehler.append("Parameter %d: «%s» ist kein gültiger Name (Buchstaben, Ziffern, _; nicht mit Ziffer beginnen)." % (i, n))
        elif n in MATERIAL_NAMEN:
            fehler.append("Parameter «%s»: der Name ist für Materialwerte reserviert (t = Dicke, ri = Innenradius, k = K-Faktor)." % n)
        elif n in namen:
            fehler.append("Parameter «%s» ist doppelt." % n)
        namen.add(n)
        if p.get("unit", "mm") not in EINHEITEN_PARAMETER:
            fehler.append("Parameter «%s»: Einheit «%s» unbekannt (mm, deg oder leer)." % (n, p.get("unit")))
        lo, hi, d = p.get("min"), p.get("max"), p.get("default")
        for name, w in (("Minimum", lo), ("Maximum", hi), ("Standardwert", d)):
            if w is not None and not _zahl(w):
                fehler.append("Parameter «%s»: %s muss eine Zahl sein." % (n, name))
        if _zahl(lo) and _zahl(hi) and lo > hi:
            fehler.append("Parameter «%s»: Minimum %g ist grösser als Maximum %g." % (n, lo, hi))
        if _zahl(d) and ((_zahl(lo) and d < lo) or (_zahl(hi) and d > hi)):
            fehler.append("Parameter «%s»: Standardwert %g liegt ausserhalb des Bereichs." % (n, d))
        if d is None and p.get("variable", True) is False:
            fehler.append("Parameter «%s» ist fest, hat aber keinen Wert." % n)
    return fehler, warn


def pruefe_operationen(ops, bekannte_namen):
    fehler, warn = [], []
    if not ops:
        fehler.append("Die Vorlage hat keine Operation. Mindestens ein Flansch oder Umschlag ist nötig.")
    erlaubt = set(bekannte_namen) | MATERIAL_NAMEN
    for i, op in enumerate(ops, 1):
        typ = op.get("typ")
        if typ not in OP_TYPEN:
            fehler.append("Schritt %d: unbekannte Operation «%s» (erlaubt: Flansch, Umschlag)." % (i, typ))
            continue
        for feld, label in (("winkel", "Winkel"), ("laenge", "Länge"), ("radius", "Radius")):
            w = op.get(feld)
            if w is None or w == "":
                if feld != "radius":
                    fehler.append("Schritt %d: %s fehlt." % (i, label))
                continue
            if _zahl(w):
                continue
            try:
                unbekannt = namen_in(w) - erlaubt
            except AusdruckFehler as e:
                fehler.append("Schritt %d, %s: %s" % (i, label, e))
                continue
            if unbekannt:
                fehler.append("Schritt %d, %s: unbekannte Parameter %s." % (i, label, ", ".join(sorted(unbekannt))))
        w, L, r = op.get("winkel"), op.get("laenge"), op.get("radius")
        if typ == "flansch" and _zahl(w):
            if w == 0 or abs(w) >= 180:
                fehler.append("Schritt %d: Flanschwinkel %g° ungültig (erlaubt: zwischen -180° und 180°, nicht 0)." % (i, w))
            elif abs(w) > 135:
                warn.append("Schritt %d: Flanschwinkel %g° ist sehr spitz – für 180° einen Umschlag verwenden." % (i, w))
        if op.get("bezug") and op["bezug"] not in BEZUEGE:
            fehler.append("Schritt %d: Massbezug «%s» unbekannt (erlaubt: %s)." % (i, op["bezug"], ", ".join(sorted(BEZUEGE))))
        if op.get("bezug") and typ == "umschlag":
            fehler.append("Schritt %d: ein Umschlag hat keinen Massbezug (nur die Lage der Biegung)." % i)
        if op.get("lage") and op["lage"] not in LAGEN:
            fehler.append("Schritt %d: Lage «%s» unbekannt (erlaubt: %s)." % (i, op["lage"], ", ".join(sorted(LAGEN))))
        if typ == "umschlag" and _zahl(w) and abs(abs(w) - 180) > 1e-9:
            fehler.append("Schritt %d: ein Umschlag hat immer ±180°." % i)
        if _zahl(L) and L <= 0:
            fehler.append("Schritt %d: Länge muss grösser als 0 sein." % i)
        if _zahl(r) and r < 0:
            fehler.append("Schritt %d: Radius darf nicht negativ sein." % i)
    return fehler, warn


def pruefe_kantenvorlage(v):
    fehler, warn = [], []
    if not (v.get("name") or "").strip():
        fehler.append("Die Vorlage braucht einen Namen.")
    f, w = pruefe_parameter(v.get("parameters", []))
    fehler += f
    warn += w
    f, w = pruefe_operationen(v.get("operations", []), [p.get("name") for p in v.get("parameters", [])])
    fehler += f
    warn += w
    c = v.get("constraints", {}) or {}
    if _zahl(c.get("thicknessMin")) and _zahl(c.get("thicknessMax")) and c["thicknessMin"] > c["thicknessMax"]:
        fehler.append("Dickenbereich: Minimum ist grösser als Maximum.")
    benutzt = set()
    for op in v.get("operations", []):
        for feld in ("winkel", "laenge", "radius"):
            if isinstance(op.get(feld), str):
                try:
                    benutzt |= namen_in(op[feld])
                except AusdruckFehler:
                    pass
    for p in v.get("parameters", []):
        if p.get("name") and p["name"] not in benutzt:
            warn.append("Parameter «%s» wird in keiner Operation verwendet." % p["name"])
    return fehler, warn


def pruefe_werte(params, werte):
    """Eingegebene Werte gegen Bereich/Einheit prüfen."""
    fehler = []
    for p in params:
        n = p["name"]
        if n not in werte or werte[n] is None:
            fehler.append("Wert für «%s» fehlt." % (p.get("label") or n))
            continue
        try:
            x = float(werte[n])
        except (TypeError, ValueError):
            fehler.append("«%s»: «%s» ist keine Zahl." % (p.get("label") or n, werte[n]))
            continue
        e = " " + p.get("unit") if p.get("unit") else ""
        if _zahl(p.get("min")) and x < p["min"] - 1e-9:
            fehler.append("«%s» = %g%s ist kleiner als das Minimum %g%s." % (p.get("label") or n, x, e, p["min"], e))
        if _zahl(p.get("max")) and x > p["max"] + 1e-9:
            fehler.append("«%s» = %g%s ist grösser als das Maximum %g%s." % (p.get("label") or n, x, e, p["max"], e))
    return fehler


def pruefe_aufgeloest(ops, dicke):
    """Nach dem Einsetzen der Werte: geometrische Mindestbedingungen."""
    fehler, warn = [], []
    for i, op in enumerate(ops, 1):
        if op["laenge"] <= 0:
            fehler.append("Schritt %d: berechnete Länge %.2f mm ist nicht grösser als 0." % (i, op["laenge"]))
        if op["typ"] == "flansch" and (op["winkel"] == 0 or abs(op["winkel"]) >= 180):
            fehler.append("Schritt %d: berechneter Winkel %.2f° ist ungültig." % (i, op["winkel"]))
        if op.get("radius") is not None and op["radius"] < 0:
            fehler.append("Schritt %d: berechneter Radius ist negativ." % i)
        if dicke and op["laenge"] < 2 * dicke:
            warn.append("Schritt %d: Schenkel %.2f mm ist kürzer als die doppelte Blechdicke." % (i, op["laenge"]))
    return fehler, warn


def eval_sicher(text, werte):
    try:
        return berechne(text, werte), None
    except AusdruckFehler as e:
        return None, str(e)

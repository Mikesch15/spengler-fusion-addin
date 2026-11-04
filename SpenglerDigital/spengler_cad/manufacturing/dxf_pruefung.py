"""Prüfung einer DXF-Datei der Fusion-Abwicklung – damit ein fehlerhafter oder unvollständiger Export nicht als Erfolg gemeldet wird.
Geprüft werden: zeichenbare Elemente vorhanden, Aussenmasse gegen die erwarteten Masse der Abwicklung, Einheit (mm), offene Konturen, doppelte Linien.
Die Aussenmasse stammen aus dem DXF selbst (nicht aus Fusions Körper) – das ist die unabhängige Gegenprobe.
SCHWER (→ Export gilt als fehlgeschlagen): keine Elemente, Masse weichen ab, Einheit nicht mm.  HINWEIS (→ Export gilt, aber mit Warnung): offene Konturen, doppelte Linien.
Reine Rechnung ohne Fusion. Der Aufbau der echten Fusion-DXF (Ebenen, Einheitenangabe) ist NICHT live geprüft; fehlt die Einheitenangabe, ist das nur ein Hinweis."""
import math

from . import dxf_lesen

EINHEITEN = {0: "ohne Einheit", 1: "Zoll", 2: "Fuss", 4: "mm", 5: "cm", 6: "m"}


def einheit(text):
    """$INSUNITS aus dem Kopf der DXF → Zahl oder None (keine Angabe)."""
    paare = dxf_lesen._paare(text)
    for i, (c, v) in enumerate(paare):
        if c == "9" and v == "$INSUNITS" and i + 1 < len(paare):
            try:
                return int(float(paare[i + 1][1]))
            except ValueError:
                return None
        if c == "2" and v == "ENTITIES":
            break
    return None


def _schluessel(p, g=0.01):
    return (round(p[0] / g), round(p[1] / g))


def _enden(e):
    """Endpunkte eines Elements (für die Kontur-Prüfung) – Kreis/geschlossene Polylinie haben keine."""
    if e["typ"] == "linie":
        return [e["p"][0], e["p"][1]]
    if e["typ"] == "poly":
        return [] if e["zu"] else [e["p"][0], e["p"][-1]]
    if e["typ"] == "bogen":
        c, r = e["c"], e["r"]
        return [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a))) for a in (e["a0"], e["a1"])]
    return []


def _konturen(elemente):
    """Anzahl zusammenhängender Konturen ohne Biegelinien (über gemeinsame Endpunkte verbunden; Kreis/geschlossene Polylinie = eigene Kontur)."""
    eltern = {}

    def wurzel(k):
        eltern.setdefault(k, k)
        while eltern[k] != k:
            eltern[k] = eltern[eltern[k]]
            k = eltern[k]
        return k
    einzeln = 0
    for el in elemente:
        if dxf_lesen.BIEGE.search(el.get("layer", "")):
            continue
        enden = [_schluessel(p) for p in _enden(el)]
        if not enden:
            einzeln += 1
            continue
        a = wurzel(enden[0])
        for b in enden[1:]:
            eltern[wurzel(b)] = a
    return einzeln + len({wurzel(k) for k in list(eltern)})


def pruefe(text, erwartet_breite=None, erwartet_laenge=None, toleranz_mm=1.0, erwartete_konturen=None):
    """→ {'ok', 'probleme' [schwer], 'hinweise', 'masse' (kleiner, grösser) oder None, 'elemente', 'doppelte', 'offene_enden', 'einheit', 'konturen'}
    erwartete_konturen: bekannte Anzahl (Aussenkontur + Löcher) – weicht sie ab, ist das ein Hinweis auf unerwartete Zusatzprofile."""
    probleme, hinweise = [], []
    try:
        elemente, ignoriert = dxf_lesen.lesen(text)
    except Exception as ex:
        return {"ok": False, "probleme": ["Die DXF-Datei lässt sich nicht lesen (%s)." % ex], "hinweise": [], "masse": None, "elemente": 0, "doppelte": 0, "offene_enden": 0, "einheit": None}
    if ignoriert:
        hinweise.append("%d Kurve(n) (Spline/Ellipse) werden hier nicht mitgeprüft." % ignoriert)
    e = einheit(text)
    if e is not None and e != 4:
        probleme.append("Die DXF ist nicht in Millimetern (Einheit: %s)." % EINHEITEN.get(e, e))
    elif e is None:
        hinweise.append("Die DXF enthält keine Einheitenangabe – mm wird angenommen.")
    if not elemente:
        probleme.append("Die DXF enthält keine zeichenbaren Elemente (Linien, Bögen, Kreise, Polylinien).")
        return {"ok": False, "probleme": probleme, "hinweise": hinweise, "masse": None, "elemente": 0, "doppelte": 0, "offene_enden": 0, "einheit": e}
    x0, y0, x1, y1 = dxf_lesen._grenzen(elemente)
    masse = tuple(sorted((x1 - x0, y1 - y0)))
    if erwartet_breite is not None and erwartet_laenge is not None:
        soll = tuple(sorted((float(erwartet_breite), float(erwartet_laenge))))
        if any(abs(a - b) > toleranz_mm for a, b in zip(masse, soll)):
            verh = [a / b for a, b in zip(masse, soll) if b > 1e-9]
            if verh and all(abs(v - 0.1) < 0.01 for v in verh):
                ursache = " Die Zeichnung ist 10× zu klein – vermutlich cm statt mm."
            elif verh and all(abs(v - 10) < 0.1 for v in verh):
                ursache = " Die Zeichnung ist 10× zu gross."
            else:
                ursache = ""
            probleme.append("Die DXF hat %.1f × %.1f mm, erwartet sind %.1f × %.1f mm (Toleranz %.1f mm).%s" % (masse[0], masse[1], soll[0], soll[1], toleranz_mm, ursache))
    # doppelte Linien (gleiche Endpunkte, Reihenfolge egal)
    gesehen, doppelte = set(), 0
    for el in elemente:
        if el["typ"] == "linie":
            k = tuple(sorted((_schluessel(el["p"][0]), _schluessel(el["p"][1]))))
            if k in gesehen:
                doppelte += 1
            gesehen.add(k)
    if doppelte:
        hinweise.append("%d doppelte Linie(n) in der DXF." % doppelte)
    # offene Konturen: Biegelinien ausgenommen; ein Endpunkt, der nur einmal vorkommt, ist ein offenes Ende
    zaehler = {}
    for el in elemente:
        if dxf_lesen.BIEGE.search(el.get("layer", "")):
            continue
        for p in _enden(el):
            zaehler[_schluessel(p)] = zaehler.get(_schluessel(p), 0) + 1
    offen = sum(1 for n in zaehler.values() if n % 2 == 1)
    if offen:
        hinweise.append("Die Kontur ist nicht geschlossen (%d offene Enden)." % offen)
    konturen = _konturen(elemente)
    if erwartete_konturen is not None and konturen != erwartete_konturen:
        hinweise.append("%d Kontur(en) statt %d – unerwartete Zusatzprofile oder fehlende Teile." % (konturen, erwartete_konturen))
    return {"ok": not probleme, "probleme": probleme, "hinweise": hinweise, "masse": masse, "elemente": len(elemente), "doppelte": doppelte, "offene_enden": offen, "einheit": e,
            "konturen": konturen}


def pruefe_datei(pfad, erwartet_breite=None, erwartet_laenge=None, toleranz_mm=1.0, erwartete_konturen=None):
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as ex:
        return {"ok": False, "probleme": ["Die DXF-Datei lässt sich nicht öffnen (%s)." % ex], "hinweise": [], "masse": None, "elemente": 0, "doppelte": 0, "offene_enden": 0, "einheit": None}
    return pruefe(text, erwartet_breite, erwartet_laenge, toleranz_mm, erwartete_konturen)


def zusammenfassung(r):
    """Eine Zeile für Berichte: Mass, Elemente, Probleme."""
    teile = []
    if r.get("masse"):
        teile.append("%.1f × %.1f mm, %d Elemente" % (r["masse"][0], r["masse"][1], r["elemente"]))
    return ", ".join(teile + r["probleme"] + r["hinweise"])

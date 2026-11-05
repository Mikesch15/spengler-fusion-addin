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


# ------------------------------------------------------------------ STRENGE Prüfung (nur interne Validierung, Restpunkt 1 Review 0.4.49)
def _kontur_rahmen(elemente):
    """Begrenzungsrahmen je zusammenhängender Kontur (ohne Biegelinien). → Liste (x0, y0, x1, y1)."""
    eltern, gruppen, einzeln = {}, {}, []

    def wurzel(k):
        eltern.setdefault(k, k)
        while eltern[k] != k:
            eltern[k] = eltern[eltern[k]]
            k = eltern[k]
        return k
    rest = []
    for el in elemente:
        if dxf_lesen.BIEGE.search(el.get("layer", "")):
            continue
        enden = [_schluessel(p) for p in _enden(el)]
        if not enden:
            einzeln.append(el)
            continue
        a = wurzel(enden[0])
        for b in enden[1:]:
            eltern[wurzel(b)] = a
        rest.append((el, enden[0]))
    for el, k in rest:
        gruppen.setdefault(wurzel(k), []).append(el)
    return [dxf_lesen._grenzen(g) for g in gruppen.values()] + [dxf_lesen._grenzen([e]) for e in einzeln]


def _ueberlappende_linien(linien, tol=1e-3):
    """Anzahl Linienpaare, die auf derselben Geraden liegen und sich auf einer Länge > tol überdecken (auch teilweise)."""
    n = 0
    for i in range(len(linien)):
        (ax, ay), (bx, by) = linien[i][0], linien[i][1]
        L = math.hypot(bx - ax, by - ay)
        if L < tol:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        for j in range(i + 1, len(linien)):
            (cx, cy), (dx, dy) = linien[j][0], linien[j][1]
            if abs((cx - ax) * uy - (cy - ay) * ux) > tol or abs((dx - ax) * uy - (dy - ay) * ux) > tol:
                continue                                   # nicht auf derselben Geraden
            t0, t1 = sorted(((cx - ax) * ux + (cy - ay) * uy, (dx - ax) * ux + (dy - ay) * uy))
            if min(L, t1) - max(0.0, t0) > tol:
                n += 1
    return n


def _polylinie(el, sehne=0.005):
    """Element → Punktfolge (Bögen/Kreise adaptiv: Sehnenfehler ≤ sehne mm)."""
    if el["typ"] == "linie":
        return list(el["p"])
    if el["typ"] == "poly":
        pts = list(el["p"])
        return pts + [pts[0]] if el.get("zu") else pts
    c, r = el["c"], el["r"]
    if el["typ"] == "kreis":
        a0, a1 = 0.0, 2 * math.pi
    else:
        a0, a1 = math.radians(el["a0"]), math.radians(el["a1"])
        if a1 <= a0:
            a1 += 2 * math.pi
    schritt = 2.0 * math.acos(max(-1.0, 1.0 - sehne / r)) if r > sehne else math.radians(10)
    n = max(2, int(math.ceil((a1 - a0) / max(schritt, 1e-6))))
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n), c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _kreuz(o, p, q):
    return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])


def _strecken_treffen(a, b, c, d, tol):
    """Schneiden oder berühren sich zwei Strecken (innerhalb tol)? → Treffpunkt oder None."""
    d1, d2, d3, d4 = _kreuz(c, d, a), _kreuz(c, d, b), _kreuz(a, b, c), _kreuz(a, b, d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and abs(d1 - d2) > 1e-15:
        t = d1 / (d1 - d2)
        return "kreuz", (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    for p_, s0, s1 in ((a, c, d), (b, c, d), (c, a, b), (d, a, b)):
        dx, dy = s1[0] - s0[0], s1[1] - s0[1]
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 < 1e-24 else max(0.0, min(1.0, ((p_[0] - s0[0]) * dx + (p_[1] - s0[1]) * dy) / L2))
        if math.hypot(p_[0] - s0[0] - u * dx, p_[1] - s0[1] - u * dy) <= tol:
            return "nah", p_
    return None


def _kreuzungen(elemente, tol=0.005):
    """Anzahl Elementpaare (ohne Biegelinien), die sich schneiden oder berühren, ausser an einem GEMEINSAMEN Endpunkt (dort hängen Konturen
    regulär zusammen). Bögen/Kreise werden fein polygonisiert (Sehnenfehler ≤ 5 µm)."""
    els = [e for e in elemente if not dxf_lesen.BIEGE.search(e.get("layer", ""))]
    polys = [_polylinie(e) for e in els]
    enden = [[tuple(p) for p in _enden(e)] for e in els]
    rahmen = [(min(p[0] for p in pl) - tol, min(p[1] for p in pl) - tol, max(p[0] for p in pl) + tol, max(p[1] for p in pl) + tol) for pl in polys]
    n = 0
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            ri, rj = rahmen[i], rahmen[j]
            if ri[2] < rj[0] or rj[2] < ri[0] or ri[3] < rj[1] or rj[3] < ri[1]:
                continue
            gemeinsam = [p for p in enden[i] if any(math.hypot(p[0] - q[0], p[1] - q[1]) <= 2 * tol for q in enden[j])]
            gefunden = False
            for a, b in zip(polys[i], polys[i][1:]):
                for c, d in zip(polys[j], polys[j][1:]):
                    t = _strecken_treffen(a, b, c, d, tol)
                    if t is None:
                        continue
                    art, q = t
                    # echte Kreuzung: nur am gemeinsamen Endpunkt selbst erlaubt; blosse Annäherung: erst ab 1 mm vom gemeinsamen Endpunkt
                    # (ein tangential anschliessender Bogen liegt nahe der Ecke zwangsläufig dicht an der Linie)
                    frei = 5 * tol if art == "kreuz" else 1.0
                    if not any(math.hypot(q[0] - g[0], q[1] - g[1]) <= frei for g in gemeinsam):
                        gefunden = True
                        break
                if gefunden:
                    break
            n += gefunden
    return n


def _gleiche_boegen(elemente, tol=1e-3):
    """Doppelte oder überlappende Bögen/Kreise: gleiches Zentrum und gleicher Radius und überlappender Winkelbereich."""
    kreise = [e for e in elemente if e["typ"] in ("bogen", "kreis") and not dxf_lesen.BIEGE.search(e.get("layer", ""))]

    def bereich(e):
        if e["typ"] == "kreis":
            return 0.0, 360.0
        a0, a1 = e["a0"] % 360.0, e["a1"] % 360.0
        return (a0, a1) if a1 > a0 else (a0, a1 + 360.0)
    n = 0
    for i in range(len(kreise)):
        for j in range(i + 1, len(kreise)):
            a, b = kreise[i], kreise[j]
            if math.hypot(a["c"][0] - b["c"][0], a["c"][1] - b["c"][1]) > tol or abs(a["r"] - b["r"]) > tol:
                continue
            (s0, s1), (t0, t1) = bereich(a), bereich(b)
            if any(min(s1, t1 + k) - max(s0, t0 + k) > 1e-6 for k in (-360.0, 0.0, 360.0)):
                n += 1
    return n


def pruefe_streng(text, erwartet_breite, erwartet_laenge, toleranz_mm=1.0):
    """Strenge Freigabeprüfung für die INTERNE Validierung neu erzeugter Geometrie (nicht für normale Exporte – die nutzen pruefe()).
    Zwingend: lesbar, Elemente vorhanden, Aussenmasse = erwartet (± toleranz_mm), Einheit mm – FEHLT die Einheitenangabe, gilt mm nur, weil die
    Aussenmasse in mm übereinstimmen (ein cm-/Zoll-Export fiele durch den Massvergleich); keine offenen Enden, keine doppelten Linien, keine
    ungeprüften Kurven (Spline/Ellipse → «nicht sicher prüfbar»); genau EINE Aussenkontur mit dem Gesamtrahmen, weitere Konturen nur vollständig
    innerhalb (als Löcher gewertet, nur ihre Lage wird geprüft); keine doppelten/überlappenden Bögen oder Kreise; keine Elemente, die sich kreuzen oder
    berühren, ohne einen gemeinsamen Endpunkt zu haben. Biegelinien werden über den Ebenennamen erkannt (bend/bieg/fold) – liegen sie
    auf einer anders benannten Ebene, erscheinen sie als offene Kontur und die Prüfung lehnt ab (keine falsche Sicherheit).
    → dict wie pruefe() mit 'streng': True; 'ok' nur, wenn ALLE Kriterien erfüllt sind."""
    if erwartet_breite is None or erwartet_laenge is None:
        r = pruefe(text)
        r.update(ok=False, streng=True)
        r["probleme"] = r["probleme"] + ["Strenge Prüfung braucht die erwarteten Aussenmasse."]
        return r
    r = pruefe(text, erwartet_breite, erwartet_laenge, toleranz_mm)
    r["streng"] = True
    probleme, hinweise = list(r["probleme"]), []
    if r["elemente"]:
        if r["doppelte"]:
            probleme.append("%d doppelte Linie(n)." % r["doppelte"])
        if r["offene_enden"]:
            probleme.append("Kontur nicht geschlossen (%d offene Enden)." % r["offene_enden"])
        if any("Spline/Ellipse" in h for h in r["hinweise"]):
            probleme.append("Kurven (Spline/Ellipse) sind nicht sicher prüfbar.")
        if r["einheit"] is None:
            hinweise.append("Keine Einheitenangabe – mm durch den Vergleich der Aussenmasse bestätigt.")
        try:
            elemente, _ = dxf_lesen.lesen(text)
            rahmen = _kontur_rahmen(elemente)
        except Exception as ex:
            elemente, rahmen = [], None
            probleme.append("Konturen nicht bestimmbar (%s)." % ex)
        # Einfache Konturen: jeder Endpunkt gehört zu genau zwei Elementen (mehr = Verzweigung), keine teilweise überlappenden Linien
        zaehler = {}
        linien = []
        for el in elemente:
            if dxf_lesen.BIEGE.search(el.get("layer", "")):
                continue
            for p_ in _enden(el):
                zaehler[_schluessel(p_)] = zaehler.get(_schluessel(p_), 0) + 1
            if el["typ"] == "linie":
                linien.append(el["p"])
        verzweigt = sum(1 for n in zaehler.values() if n > 2)
        if verzweigt:
            probleme.append("Kontur verzweigt (%d Punkt(e) mit mehr als zwei Enden)." % verzweigt)
        ueberlapp = _ueberlappende_linien(linien)
        if ueberlapp:
            probleme.append("%d Paar(e) teilweise überlappender Linien." % ueberlapp)
        boegen = _gleiche_boegen(elemente)
        if boegen:
            probleme.append("%d Paar(e) doppelter oder überlappender Bögen/Kreise." % boegen)
        kreuz = _kreuzungen(elemente)
        if kreuz:
            probleme.append("%d Paar(e) von Elementen kreuzen oder berühren sich ohne gemeinsamen Endpunkt." % kreuz)
        if rahmen is not None:
            if not rahmen:
                probleme.append("Keine Kontur ausser Biegelinien.")
            else:
                gx0, gy0, gx1, gy1 = (min(b[0] for b in rahmen), min(b[1] for b in rahmen), max(b[2] for b in rahmen), max(b[3] for b in rahmen))
                t = 1e-3
                aussen = [b for b in rahmen if abs(b[0] - gx0) < t and abs(b[1] - gy0) < t and abs(b[2] - gx1) < t and abs(b[3] - gy1) < t]
                innen = [b for b in rahmen if b not in aussen]
                if len(aussen) != 1:
                    probleme.append("%d Konturen bilden den Aussenrahmen (erwartet genau 1)." % len(aussen))
                fremd = [b for b in innen if not (b[0] > gx0 + t and b[1] > gy0 + t and b[2] < gx1 - t and b[3] < gy1 - t)]
                if fremd:
                    probleme.append("%d Zusatzkontur(en) berühren oder überragen die Aussenkontur." % len(fremd))
                elif innen:
                    hinweise.append("%d Innenkontur(en) als Löcher gewertet (nur Lage geprüft)." % len(innen))
                r["konturen"] = len(rahmen)
    r["probleme"], r["hinweise"] = probleme, hinweise
    r["ok"] = not probleme
    return r


def pruefe_datei_streng(pfad, erwartet_breite, erwartet_laenge, toleranz_mm=1.0):
    try:
        with open(pfad, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError as ex:
        return {"ok": False, "streng": True, "probleme": ["Die DXF-Datei lässt sich nicht öffnen (%s)." % ex], "hinweise": [], "masse": None,
                "elemente": 0, "doppelte": 0, "offene_enden": 0, "einheit": None}
    return pruefe_streng(text, erwartet_breite, erwartet_laenge, toleranz_mm)

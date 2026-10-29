"""Zeichnungen als SVG – Port von profilSvg/abwicklungSvg aus kern/zeichnung.js, dazu die Vorlagen-Vorschau.

profil_svg:     Querschnitt (Blechmitte) mit Schenkelmassen, Biegungen B1… und Kante A/B
abwicklung_svg: Blechstreifen mit Biegelinien und Anschlagmass ab Kante A
vorlagen_vorschau: Querschnitt einer Kantenvorlage mit ihren Standardwerten (für die Palette)
Alle Masse sind theoretisch (Blechmitte, Biegerechnung aus der App).
"""
import html
import math

from ..core import short_syntax
from ..core.bend_geometry import ProfilFehler, berechne, polylinie, rueckversatz

_STIL_PROFIL = (".mass{font-family:Barlow,'Segoe UI',Arial,sans-serif;fill:currentColor}.biegung{font-family:Barlow,'Segoe UI',Arial,sans-serif;"
                "font-weight:600;fill:#c4352b}.kante-a{fill:#2e9b4f}.kante-a-text{fill:#2e9b4f;font-weight:600}.kante-b{fill:#8a969e}"
                ".kante-b-text{fill:#8a969e;font-weight:600}.basis{stroke:#8a969e}")
_STIL_ABW = (".streifen{fill:none;stroke:currentColor;stroke-width:1.5}.rundung{fill:#c4352b;opacity:.15}.biegelinie{stroke:#c4352b;"
             "stroke-width:1.5;stroke-dasharray:4 2}.mass{font-family:Barlow,'Segoe UI',Arial,sans-serif;fill:currentColor}"
             ".biegung{font-family:Barlow,'Segoe UI',Arial,sans-serif;font-weight:600;fill:#c4352b}.kante-a{fill:#2e9b4f}"
             ".kante-a-text{fill:#2e9b4f;font-weight:600}.kante-b-text{fill:#8a969e;font-weight:600}")


def _z(v):
    return "%g" % round(v, 1)


def _esc(s):
    return html.escape(str(s), quote=True)


def _grenzen(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def profil_svg(res, breite=300, hoehe=220, rand=34, schrift=12, dicke=0.0, basis_segment=False, kante_a="A", kante_b=True):
    """basis_segment=True: das erste gerade Stück ist das bestehende Blech (grau, ohne Mass), Kante A sitzt an seinem Ende."""
    pts = polylinie(res["pfad"], 3)
    if len(pts) < 2:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d"></svg>' % (breite, hoehe)
    x0, y0, x1, y1 = _grenzen(pts)
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    s = min((breite - 2 * rand) / w, (hoehe - 2 * rand) / h)
    ox, oy = (breite - w * s) / 2 - x0 * s, (hoehe + h * s) / 2 + y0 * s

    def P(p):
        return (ox + p[0] * s, oy - p[1] * s)
    mitte = P(((x0 + x1) / 2, (y0 + y1) / 2))
    teile, marken = [], []
    sw = max(2, dicke * s)
    if basis_segment and res["pfad"] and res["pfad"][0]["typ"] == "linie":
        a, b = P(res["pfad"][0]["p1"]), P(res["pfad"][0]["p2"])
        teile.append('<path d="M%s %sL%s %s" class="basis" stroke-width="%s" stroke-dasharray="6 3" fill="none"/>' % (_z(a[0]), _z(a[1]), _z(b[0]), _z(b[1]), _z(sw)))
        rest = polylinie(res["pfad"][1:], 3)
    else:
        rest = pts
    if len(rest) >= 2:
        d = "".join(("L" if i else "M") + "%s %s" % (_z(P(p)[0]), _z(P(p)[1])) for i, p in enumerate(rest))
        teile.append('<path d="%s" fill="none" stroke="currentColor" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>' % (d, _z(sw)))

    def marke(p, richtung, text, klasse, abstand):
        marken.append((p, richtung, str(text), klasse, abstand))

    for b in res.get("beschriftungen", []):
        if basis_segment and b["nr"] == 1:
            continue
        p = P((b["x"], b["y"]))
        nx, ny = math.sin(b["richtung"]), math.cos(b["richtung"])
        if (p[0] - mitte[0]) * nx + (p[1] - mitte[1]) * ny < 0:
            nx, ny = -nx, -ny
        marke(p, (nx, ny), "%g" % round(b["mass"], 1), "mass", schrift * 0.6 + 4)

    def von_mitte(p):
        dx, dy = p[0] - mitte[0], p[1] - mitte[1]
        L = math.hypot(dx, dy) or 1
        return (dx / L, dy / L)
    nr = 0
    for el in res["pfad"]:
        if el["typ"] != "bogen":
            continue
        nr += 1
        mw = el["start"] + math.radians(el["winkel"]) / 2
        pm = P((el["zentrum"][0] + el["rm"] * math.cos(mw), el["zentrum"][1] + el["rm"] * math.sin(mw)))
        c = P(el["zentrum"])
        dx, dy = pm[0] - c[0], pm[1] - c[1]
        L = math.hypot(dx, dy)
        marke(pm, (dx / L, dy / L) if L > 0.5 else von_mitte(pm), "B%d" % nr, "biegung", schrift * 0.6 + 6)
    a = P(rest[0])
    teile.append('<circle cx="%s" cy="%s" r="%s" class="kante-a"/>' % (_z(a[0]), _z(a[1]), _z(schrift * 0.4)))
    marke(a, von_mitte(a), kante_a, "kante-a-text", schrift * 0.6 + 4)
    e = P(pts[-1])
    teile.append('<circle cx="%s" cy="%s" r="%s" class="kante-b"/>' % (_z(e[0]), _z(e[1]), _z(schrift * 0.3)))
    if kante_b:
        marke(e, von_mitte(e), "B", "kante-b-text", schrift * 0.6 + 4)

    belegt = []
    for p, (dx, dy), text, klasse, abstand in marken:
        kb = len(text) * schrift * 0.62
        k = None
        for i in range(6):
            d = abstand + i * schrift * 0.8
            x = min(max(p[0] + dx * d, kb / 2 + 2), breite - kb / 2 - 2)
            y = min(max(p[1] + dy * d, schrift / 2 + 2), hoehe - schrift / 2 - 2)
            k = (x, y, kb)
            if not any(abs(o[0] - x) < (o[2] + kb) / 2 + 2 and abs(o[1] - y) < schrift + 1 for o in belegt):
                break
        belegt.append(k)
        teile.append('<text x="%s" y="%s" class="%s">%s</text>' % (_z(k[0]), _z(k[1]), klasse, _esc(text)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-size="%d" text-anchor="middle" '
            'dominant-baseline="middle"><style>%s</style>\n%s\n</svg>' % (breite, hoehe, breite, hoehe, schrift, _STIL_PROFIL, "\n".join(teile)))


def abwicklung_svg(res, breite=300, schrift=11, ab=0.0):
    """Streifen mit Biegelinien. ab: Länge am Streifenanfang, die nicht gezeichnet wird (bestehendes Blech)."""
    rand, streifen = 18, 22
    gesamt = max(res["zuschnitt"] - ab, 1)
    s = (breite - 2 * rand) / gesamt

    def X(v):
        return rand + (v - ab) * s
    y0 = schrift * 2 + 10
    teile = ['<rect x="%s" y="%s" width="%s" height="%s" class="streifen"/>' % (_z(X(ab)), _z(y0), _z(gesamt * s), streifen)]
    belegt = []
    for b in res["biegungen"]:
        if b["art"] == "Rundung":
            teile.append('<rect x="%s" y="%s" width="%s" height="%s" class="rundung"/>' % (_z(X(b["von"])), _z(y0), _z((b["bis"] - b["von"]) * s), streifen))
        else:
            teile.append('<line x1="%s" y1="%s" x2="%s" y2="%s" class="biegelinie"/>' % (_z(X(b["pos"])), _z(y0 - 3), _z(X(b["pos"])), _z(y0 + streifen + 3)))
        x = X(b["pos"])
        zeile = len([o for o in belegt if abs(o - x) < schrift * 3.2]) % 2
        belegt.append(x)
        teile.append('<text x="%s" y="%s" class="biegung">B%d</text>' % (_z(x), _z(y0 - 6 - zeile * (schrift + 2)), b["nr"]))
        txt = "%.0f–%.0f" % (b["von"] - ab, b["bis"] - ab) if b["art"] == "Rundung" else "%.1f" % (b["pos"] - ab)
        teile.append('<text x="%s" y="%s" class="mass">%s</text>' % (_z(x), _z(y0 + streifen + schrift + 2 + zeile * (schrift + 2)), txt))
    teile.append('<circle cx="%s" cy="%s" r="%s" class="kante-a"/>' % (_z(X(ab)), _z(y0 + streifen / 2), _z(schrift * 0.4)))
    ym = _z(y0 + streifen / 2 + schrift * 0.35)
    teile.append('<text x="%s" y="%s" class="kante-a-text">A</text><text x="%s" y="%s" class="kante-b-text">B</text>' % (_z(rand / 2 - 1), ym, _z(breite - rand / 2 + 1), ym))
    h = y0 + streifen + (schrift + 2) * 2 + 6
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %s" width="%d" height="%s" font-size="%d" text-anchor="middle"><style>%s</style>\n%s\n</svg>'
            % (breite, _z(h), breite, _z(h), schrift, _STIL_ABW, "\n".join(teile)))


def kanten_profil(ops, t, ri, k):
    """Operationen ab der Kante → (res, ab): Profil mit kurzem Basisstück, dessen gerader Teil 0 ist.
    ab = Länge bis zum Beginn der ersten Biegung (für die Abwicklung «ab Kante»)."""
    from ..core.bend_geometry import profil_aus_operationen
    if not ops:
        raise ProfilFehler("Keine Operationen")
    erste = {"typ": "biegung", "winkel": ops[0]["winkel"], "ri": ops[0].get("radius"), "modus": "hem" if ops[0]["typ"] == "umschlag" else "sharp"}
    basis = rueckversatz(erste, t, ri)
    # sichtbares Stück Blech vor der Kante (nur Zeichnung): halbe erste Schenkellänge
    zeichen_basis = basis + max(5.0, 0.5 * float(ops[0]["laenge"]))
    res = berechne(0.0, profil_aus_operationen(zeichen_basis, ops, t), t, ri, k)
    return res, zeichen_basis - basis


def vorlagen_vorschau(vorlage, material=None, breite=260, hoehe=170, schrift=11):
    """→ (svg, None) oder (None, grund). Ohne Materialprofil: Skizze mit t = 1 mm, ri = t (nur Darstellung)."""
    from ..core import template_engine
    try:
        m = dict(material) if material else {"name": "Skizze", "thickness": 1.0}
        m.setdefault("innerRadius", None)
        if m.get("innerRadius") is None:
            m["innerRadius"] = m["thickness"]
        m.setdefault("kFactor", None)
        if m.get("kFactor") is None:
            m["kFactor"] = 0.5   # wirkt nur auf die Abwicklung, nicht auf den Querschnitt
        ops, _ = template_engine.aufloesen(vorlage, {}, m)
        res, _ = kanten_profil(ops, m["thickness"], m["innerRadius"], m["kFactor"])
    except (template_engine.VorlagenFehler, short_syntax.KurzschriftFehler, ProfilFehler, KeyError, TypeError, ValueError) as e:
        return None, str(e).splitlines()[-1] if str(e) else "keine Vorschau"
    return profil_svg(res, breite, hoehe, rand=26, schrift=schrift, basis_segment=True, kante_a="Kante", kante_b=False), None

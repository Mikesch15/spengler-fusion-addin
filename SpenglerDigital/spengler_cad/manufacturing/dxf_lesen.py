"""DXF lesen und als SVG zeichnen – für die Abwicklung im Werkstattblatt.

Gelesen wird die von Fusion erzeugte DXF der Abwicklung (Abschnitt ENTITIES: LINE, CIRCLE, ARC, LWPOLYLINE, POLYLINE; Kurven wie SPLINE
werden gezählt, aber nicht gezeichnet). Ebenen, deren Name «bend», «biege», «fold» oder «kante» enthält, werden gestrichelt (Biegelinien).
Reine Rechnung ohne Fusion; der Aufbau der Fusion-DXF (Ebenennamen) ist nicht live geprüft."""
import math
import re

BIEGE = re.compile(r"bend|biege|fold|kante", re.I)


def _paare(text):
    z = [x.strip() for x in text.splitlines()]
    return [(z[i], z[i + 1]) for i in range(0, len(z) - 1, 2)]


def _f(w):
    return float(w.replace(",", "."))


def lesen(text):
    """→ (Elemente, Anzahl nicht darstellbarer Elemente). Element: {"typ","layer", ...} (alles in DXF-Einheiten)."""
    paare = _paare(text)
    start = next((i for i, (c, v) in enumerate(paare) if c == "2" and v == "ENTITIES"), None)
    if start is None:
        return [], 0
    ents, aktuell = [], None
    for c, v in paare[start + 1:]:
        if c == "0":
            if aktuell is not None:
                ents.append(aktuell)
            if v == "ENDSEC":
                aktuell = None
                break
            aktuell = {"typ": v, "daten": []}
        elif aktuell is not None:
            aktuell["daten"].append((c, v))
    elemente, ignoriert = [], 0
    poly = None
    for e in ents:
        d = e["daten"]
        layer = next((v for c, v in d if c == "8"), "0")
        werte = lambda code: [_f(v) for c, v in d if c == code]
        t = e["typ"]
        if t == "LINE":
            x1, y1, x2, y2 = (werte(k)[0] for k in ("10", "20", "11", "21"))
            elemente.append({"typ": "linie", "layer": layer, "p": [(x1, y1), (x2, y2)]})
        elif t == "CIRCLE":
            elemente.append({"typ": "kreis", "layer": layer, "c": (werte("10")[0], werte("20")[0]), "r": werte("40")[0]})
        elif t == "ARC":
            elemente.append({"typ": "bogen", "layer": layer, "c": (werte("10")[0], werte("20")[0]), "r": werte("40")[0],
                             "a0": werte("50")[0], "a1": werte("51")[0]})
        elif t == "LWPOLYLINE":
            pts, bul = [], []
            for c, v in d:
                if c == "10":
                    pts.append([_f(v), 0.0])
                    bul.append(0.0)
                elif c == "20" and pts:
                    pts[-1][1] = _f(v)
                elif c == "42" and bul:
                    bul[-1] = _f(v)
            geschlossen = any(c == "70" and int(float(v)) & 1 for c, v in d)
            elemente.append({"typ": "poly", "layer": layer, "p": [tuple(p) for p in pts], "b": bul, "zu": geschlossen})
        elif t == "POLYLINE":
            poly = {"typ": "poly", "layer": layer, "p": [], "b": [], "zu": any(c == "70" and int(float(v)) & 1 for c, v in d)}
        elif t == "VERTEX" and poly is not None:
            poly["p"].append((werte("10")[0], werte("20")[0]))
            poly["b"].append(werte("42")[0] if werte("42") else 0.0)
        elif t == "SEQEND" and poly is not None:
            elemente.append(poly)
            poly = None
        elif t in ("SPLINE", "ELLIPSE", "POINT", "TEXT", "MTEXT", "INSERT", "HATCH", "DIMENSION"):
            ignoriert += 1 if t in ("SPLINE", "ELLIPSE") else 0
    return [x for x in elemente if x["typ"] != "poly" or len(x["p"]) >= 2], ignoriert


def _segment(p, q, b):
    """Strecke bzw. Bogen (Ausbuchtung b) von p nach q als SVG-Pfadstück (nach «L/A», Koordinaten wie DXF)."""
    if abs(b) < 1e-9:
        return "L %.4f %.4f" % q
    sehne = math.hypot(q[0] - p[0], q[1] - p[1])
    r = sehne / (2 * math.sin(2 * math.atan(abs(b))))
    return "A %.4f %.4f 0 %d %d %.4f %.4f" % (abs(r), abs(r), 1 if abs(b) > 1 else 0, 1 if b > 0 else 0, q[0], q[1])


def _grenzen(elemente):
    xs, ys = [], []
    for e in elemente:
        if e["typ"] in ("linie", "poly"):
            xs += [p[0] for p in e["p"]]
            ys += [p[1] for p in e["p"]]
        else:
            r = e["r"]
            xs += [e["c"][0] - r, e["c"][0] + r]
            ys += [e["c"][1] - r, e["c"][1] + r]
    return min(xs), min(ys), max(xs), max(ys)


def svg(elemente, breite=640):
    """Elemente → SVG (y nach oben wie in der DXF, Biegelinien gestrichelt)."""
    if not elemente:
        return ""
    x0, y0, x1, y1 = _grenzen(elemente)
    w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    rand = 0.04 * max(w, h)
    hoehe = breite * (h + 2 * rand) / (w + 2 * rand)
    teile = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.3f %.3f %.3f %.3f" width="%d" height="%d" style="border:1px solid #ccc;background:#fff">'
             % (x0 - rand, -(y1 + rand), w + 2 * rand, h + 2 * rand, breite, hoehe),
             '<g transform="scale(1,-1)" fill="none" stroke-linecap="round">']
    for e in elemente:
        biege = bool(BIEGE.search(e["layer"]))
        stil = 'stroke="%s" stroke-width="1.4" vector-effect="non-scaling-stroke"%s' % ("#b00020" if biege else "#111", ' stroke-dasharray="6 4"' if biege else "")
        if e["typ"] == "linie":
            (a, b), (c, d) = e["p"]
            teile.append('<path d="M %.4f %.4f L %.4f %.4f" %s/>' % (a, b, c, d, stil))
        elif e["typ"] == "kreis":
            teile.append('<circle cx="%.4f" cy="%.4f" r="%.4f" %s/>' % (e["c"][0], e["c"][1], e["r"], stil))
        elif e["typ"] == "bogen":
            a0, a1 = math.radians(e["a0"]), math.radians(e["a1"])
            c, r = e["c"], e["r"]
            gross = ((e["a1"] - e["a0"]) % 360.0) > 180.0
            teile.append('<path d="M %.4f %.4f A %.4f %.4f 0 %d 1 %.4f %.4f" %s/>' % (
                c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), r, r, 1 if gross else 0, c[0] + r * math.cos(a1), c[1] + r * math.sin(a1), stil))
        else:
            p, b = e["p"], e["b"]
            d = "M %.4f %.4f " % p[0]
            for i in range(1, len(p)):
                d += _segment(p[i - 1], p[i], b[i - 1]) + " "
            if e["zu"]:
                d += _segment(p[-1], p[0], b[-1]) + " Z"
            teile.append('<path d="%s" %s/>' % (d.strip(), stil))
    teile.append("</g></svg>")
    return "".join(teile)


def svg_aus_datei(pfad, breite=640):
    """→ (svg, Anzahl nicht gezeichneter Kurven). Wirft bei unlesbarer Datei."""
    with open(pfad, encoding="utf-8", errors="replace") as f:
        elemente, ignoriert = lesen(f.read())
    return svg(elemente, breite), ignoriert

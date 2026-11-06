"""Quetschfalte an der Ecke zweier Aufkantungen – reine Rechnung (ohne Fusion testbar).

Geometrie (aus dem Falten selbst hergeleitet, nicht geraten):
  Basisfläche B in z = 0, Ecke O im Ursprung, Kante e1 = (1, 0, 0), Kante e2 = (cos β, sin β, 0); B liegt zwischen e1 und e2.
  Aufkantung 1 steht an e1, Aufkantung 2 an e2, mit dem Aufkantungswinkel φ (90° = senkrecht zur Basisfläche).
  Die beiden Wände schneiden sich in der Ecklinie ε. Im ebenen Zuschnitt haben die Flansche an O die Sektorwinkel γ1 = ∠(e1, ε), γ2 = ∠(e2, ε);
  B hat β. Der Rest ψ = 360° − β − γ1 − γ2 ist ÜBERSCHUSS (bei β = 90°, φ = 90°: 90°). Er wird nicht abgeschnitten, sondern an seiner Winkelhalbierenden
  um 180° gefaltet: die beiden Seiten des Überschusses (beide ℓ lang) fallen aufeinander und liegen beide an ε – das ist die Quetschfalte.
  Voraussetzung (= «A0 und C0 gleich lang» der Unterlagen): beide Seiten gleich lang (ℓ1 = ℓ2) und die Spitzen C1, C2 liegen auf der
  Winkelhalbierenden (symmetrische Ecke). Sonst: Fehler «nicht unterstützt» – nichts wird geraten.
Masse sind Aussenmasse bis zu den virtuellen Kanten; Biegezugaben der Kanten e1/e2 und die Dicke der Lagen sind NICHT eingerechnet (ideale Faltlinien)."""
import math

TOL = 1e-6


class QuetschfalteFehler(ValueError):
    pass


def _sk(a, b):
    return sum(x * y for x, y in zip(a, b))


def _kreuz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_sk(a, a))
    if n < 1e-12:
        raise QuetschfalteFehler("Entartete Richtung.")
    return tuple(x / n for x in a)


def _winkel(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, _sk(_norm(a), _norm(b))))))


def _rot(p, achse, grad):
    """Punkt p um die Achse durch den Ursprung (Einheitsvektor) um grad drehen (Rechte-Hand-Regel, Rodrigues)."""
    a = math.radians(grad)
    c, s = math.cos(a), math.sin(a)
    k = _kreuz(achse, p)
    d = _sk(achse, p)
    return tuple(p[i] * c + k[i] * s + achse[i] * d * (1 - c) for i in range(3))


def ecke_geometrie(beta, phi1=90.0, phi2=90.0):
    """3D-Ecke aus Kantenwinkel β (in der Basisfläche) und den Aufkantungswinkeln φ1, φ2 (90° = senkrecht). → dict:
    e1, e2, d1, d2 (Flanschrichtungen), eps (Ecklinie, aufwärts), gamma1, gamma2, psi (Überschuss), alle Winkel in Grad."""
    if not (10.0 <= beta <= 170.0):
        raise QuetschfalteFehler("Der Winkel zwischen den Kanten (%.1f°) muss zwischen 10° und 170° liegen." % beta)
    for p in (phi1, phi2):
        if not (20.0 <= p <= 160.0):
            raise QuetschfalteFehler("Aufkantungswinkel %.1f° unplausibel (erlaubt 20°–160°)." % p)
    b = math.radians(beta)
    z = (0.0, 0.0, 1.0)
    e1 = (1.0, 0.0, 0.0)
    e2 = (math.cos(b), math.sin(b), 0.0)
    f1 = (0.0, -1.0, 0.0)
    f2 = (-math.sin(b), math.cos(b), 0.0)
    c1, s1 = math.cos(math.radians(phi1)), math.sin(math.radians(phi1))
    c2, s2 = math.cos(math.radians(phi2)), math.sin(math.radians(phi2))
    d1 = tuple(c1 * f1[i] + s1 * z[i] for i in range(3))
    d2 = tuple(c2 * f2[i] + s2 * z[i] for i in range(3))
    n1, n2 = _kreuz(e1, d1), _kreuz(e2, d2)
    eps = _kreuz(n1, n2)
    if math.sqrt(_sk(eps, eps)) < 1e-9:
        raise QuetschfalteFehler("Die Wände der beiden Aufkantungen sind parallel – keine Ecke.")
    eps = _norm(eps)
    if eps[2] < 0:
        eps = tuple(-x for x in eps)
    if eps[2] < 0.05:
        raise QuetschfalteFehler("Die Ecklinie verläuft fast parallel zur Basisfläche – keine sinnvolle Ecke.")
    # ε muss in den Halbebenen der Flansche liegen (Anteil in Flanschrichtung > 0)
    for e, d, name in ((e1, d1, "1"), (e2, d2, "2")):
        anteil = _sk(eps, d) - _sk(eps, e) * _sk(e, d)
        if anteil <= 1e-9:
            raise QuetschfalteFehler("Aufkantung %s: die Ecklinie liegt nicht auf der Flanschseite (Winkel unplausibel)." % name)
    g1, g2 = _winkel(e1, eps), _winkel(e2, eps)
    psi = 360.0 - beta - g1 - g2
    return {"beta": beta, "phi1": phi1, "phi2": phi2, "e1": e1, "e2": e2, "d1": d1, "d2": d2, "eps": eps, "gamma1": g1, "gamma2": g2, "psi": psi}


def zuschnitt(beta, hoehe, phi1=90.0, phi2=90.0, laenge=None):
    """Ebener Zuschnitt der Ecke (mm, Ursprung = Ecke O, Aussenmass bis zu den virtuellen Kanten). hoehe = Aufkantungshöhe von Flansch 1 (Abstand der
    Oberkante von der Biegelinie in der Flanschebene); Flansch 2 wird so hoch, dass beide Oberkanten an ε zusammentreffen (sonst gäbe es keine
    gemeinsame Ecklinie). → dict mit Punkten, Faltlinien und Prüfwerten."""
    g = ecke_geometrie(beta, phi1, phi2)
    g1, g2, psi = g["gamma1"], g["gamma2"], g["psi"]
    if not (hoehe > 0):
        raise QuetschfalteFehler("Die Aufkantungshöhe muss grösser als 0 sein.")
    if not (5.0 <= psi <= 175.0):
        raise QuetschfalteFehler("Der Überschuss ψ = %.1f° liegt ausserhalb von 5°…175° – keine Quetschfalte möglich." % psi)
    ell = hoehe / math.sin(math.radians(g1))                       # Länge der Ecklinie ε bis zur Oberkante
    h2 = ell * math.sin(math.radians(g2))                         # Höhe Flansch 2, damit die Oberkanten an ε zusammentreffen
    L = laenge if laenge else 2.5 * max(hoehe, h2) + 10.0
    a1, a2 = math.radians(360.0 - g1), math.radians(beta + g2)       # Richtungen der Seitenkanten von Flansch 1 / 2 im Zuschnitt
    P1 = (ell * math.cos(a1), ell * math.sin(a1))
    P2 = (ell * math.cos(a2), ell * math.sin(a2))
    mid = a2 + math.radians(psi) / 2.0                               # Winkelhalbierende des Überschusses
    d = (math.cos(mid), math.sin(mid))
    # Spitze: Schnitt der Winkelhalbierenden mit der Oberkante von Flansch 1 (y = −hoehe) und von Flansch 2 (Abstand h2 von e2 auf der f2-Seite)
    f2 = (-math.sin(math.radians(beta)), math.cos(math.radians(beta)))
    if abs(d[1]) < 1e-9 or abs(d[0] * f2[0] + d[1] * f2[1]) < 1e-9:
        raise QuetschfalteFehler("Die Winkelhalbierende verläuft parallel zu einer Oberkante – keine Spitze.")
    t1 = -hoehe / d[1]
    t2 = h2 / (d[0] * f2[0] + d[1] * f2[1])
    if t1 <= ell or t2 <= ell:
        raise QuetschfalteFehler("Die Spitze der Quetschfalte liegt vor der Ecklinie (Überschuss zu klein für diese Höhe).")
    if abs(t1 - t2) > 1e-6 * max(t1, t2):
        raise QuetschfalteFehler("Asymmetrische Ecke (Spitzen %.3f / %.3f mm): die Quetschfalte wäre nicht deckungsgleich – noch nicht unterstützt." % (t1, t2))
    C = (t1 * d[0], t1 * d[1])
    m = math.hypot(C[0] - P1[0], C[1] - P1[1])                       # Länge der Oberkante im Überschuss (P → C)
    # Kontur der Ecke (Ausschnitt): entlang der Oberkante Flansch 1 → P1 → C → P2 → entlang der Oberkante Flansch 2
    e2d = (math.cos(math.radians(beta)), math.sin(math.radians(beta)))
    ende1 = (L, -hoehe)
    ende2 = tuple(h2 * f2[i] + L * e2d[i] for i in range(2))
    kontur = [ende1, P1, C, P2, ende2]
    falten = {
        "e1": ((0.0, 0.0), (L, 0.0)),
        "e2": ((0.0, 0.0), (L * e2d[0], L * e2d[1])),
        "eps1": ((0.0, 0.0), P1),                                    # Seitenkante Flansch 1 (wird zur Ecklinie)
        "eps2": ((0.0, 0.0), P2),                                    # Seitenkante Flansch 2 (wird zur Ecklinie)
        "quetsch": ((0.0, 0.0), C),                                  # Faltlinie der Quetschfalte (180°)
    }
    return {"geometrie": g, "hoehe1": hoehe, "hoehe2": h2, "ell": ell, "P1": P1, "P2": P2, "C": C, "m": m, "t_spitze": t1, "kontur": kontur,
            "faltlinien": falten, "laenge": L, "beta": beta, "psi": psi, "gamma1": g1, "gamma2": g2}


def falten_pruefen(z):
    """Zuschnitt rechnerisch falten: Flansch 1 um e1 (−φ1), Flansch 2 um e2 (+φ2) aufstellen. Kontrolle: die Seitenkanten beider Flansche (P1, P2) landen
    auf DERSELBEN Ecklinie ε, gleich lang (A0 = C0), und die Faltung der Quetschfalte (Spiegelung an der Winkelhalbierenden) legt die Seiten aufeinander.
    → dict {ok, abweichung_mm, ...}."""
    g = z["geometrie"]
    e1, e2 = g["e1"], g["e2"]
    P1, P2 = z["P1"], z["P2"]
    p1 = _rot((P1[0], P1[1], 0.0), e1, -g["phi1"])
    p2 = _rot((P2[0], P2[1], 0.0), e2, g["phi2"])
    soll = tuple(z["ell"] * x for x in g["eps"])
    abw1 = math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, soll)))
    abw2 = math.sqrt(sum((a - b) ** 2 for a, b in zip(p2, soll)))
    abw12 = math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
    # Spiegelung von P2 an der Winkelhalbierenden muss P1 ergeben (Seiten decken sich)
    d = _norm((z["C"][0], z["C"][1], 0.0))
    sp = _rot((P2[0], P2[1], 0.0), (0.0, 0.0, 1.0), 0.0)
    # Spiegelung in der Zuschnittsebene: v' = 2 (v·d) d − v
    k = 2 * (sp[0] * d[0] + sp[1] * d[1])
    spiegel = (k * d[0] - sp[0], k * d[1] - sp[1])
    abw_sp = math.hypot(spiegel[0] - P1[0], spiegel[1] - P1[1])
    streck = abs(math.hypot(*P1) - math.hypot(*P2))
    worst = max(abw1, abw2, abw12, abw_sp, streck)
    return {"ok": worst < 1e-6, "abweichung_mm": worst, "ecklinie_flansch1_mm": abw1, "ecklinie_flansch2_mm": abw2, "seitenkanten_mm": abw12,
            "spiegelung_mm": abw_sp, "laengenunterschied_mm": streck, "ell": z["ell"]}


def quetschfalte_3d(z, seite="wand1"):
    """Die gefaltete Quetschfalte als Dreieck (O, P, C') in der Wandebene, auf Wand 1 oder Wand 2 gedrückt (lokale Koordinaten der Ecke, mm):
    O = Fuss der Ecklinie, P = Kopf der Ecklinie, C' = Spitze. → dict mit den Dreieckspunkten und der Wandebene."""
    if seite not in ("wand1", "wand2"):
        raise QuetschfalteFehler("Seite muss «wand1» oder «wand2» sein.")
    g = z["geometrie"]
    P = tuple(z["ell"] * x for x in g["eps"])
    e = g["e1"] if seite == "wand1" else g["e2"]
    C = tuple(P[i] + z["m"] * e[i] for i in range(3))
    return {"O": (0.0, 0.0, 0.0), "P": P, "C": C, "wand": seite, "richtung": e}


def richtung_zu_wand(richtung):
    """«hinten links»/«hinten rechts» (von der Sichtseite aus gesehen, Anwender 6. 11. 2026) → Wand, auf die die Falte gelegt wird.
    Von der Sichtseite (vom Ende der Ecklinie ε aus auf die Ecke blickend, Basisfläche unten) liegt Wand 1 (an e1) rechts, Wand 2 (an e2) links,
    wenn e1 nach rechts zeigt und e2 gegen den Uhrzeigersinn folgt (so ist die Ecke aufgebaut)."""
    r = (richtung or "").strip().lower()
    if r in ("hinten rechts", "rechts"):
        return "wand1"
    if r in ("hinten links", "links"):
        return "wand2"
    raise QuetschfalteFehler("Richtung muss «hinten links» oder «hinten rechts» sein.")


def svg_zuschnitt(z, titel="Quetschfalte – Ecke zweier Aufkantungen (Zuschnitt)", masse=True):
    """SVG des Zuschnitts mit allen Faltlinien (Biegelinien gestrichelt, Quetschfalte rot) – zum Vergleich mit der Zeichnung der Unterlagen."""
    pts = list(z["kontur"]) + [(0.0, 0.0), z["faltlinien"]["e1"][1], z["faltlinien"]["e2"][1]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 12.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    s = 3.2

    def P(p):
        return "%.1f,%.1f" % ((p[0] - x0) * s, (y1 - p[1]) * s)

    def linie(a, b, stil, farbe):
        return '<line x1="%s" y1="%s" x2="%s" y2="%s" %s stroke="%s"/>' % (P(a).split(",")[0], P(a).split(",")[1], P(b).split(",")[0], P(b).split(",")[1], stil, farbe)
    f = z["faltlinien"]
    W, H = max((x1 - x0) * s, 760), (y1 - y0) * s + 66
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI,Arial" font-size="11">' % (W, H, W, H),
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<text x="8" y="16" font-size="13" font-weight="600">%s</text>' % titel]
    out.append('<g transform="translate(0,24)">')
    kontur = [z["kontur"][0]] + [z["kontur"][1], z["kontur"][2], z["kontur"][3], z["kontur"][4]]
    out.append('<polyline points="%s" fill="none" stroke="#111" stroke-width="1.6"/>' % " ".join(P(p) for p in kontur))
    out.append(linie(*f["e1"], 'stroke-width="1.1" stroke-dasharray="9,3,2,3"', "#1f6fb2"))
    out.append(linie(*f["e2"], 'stroke-width="1.1" stroke-dasharray="9,3,2,3"', "#1f6fb2"))
    out.append(linie(*f["eps1"], 'stroke-width="1.1" stroke-dasharray="6,3"', "#555"))
    out.append(linie(*f["eps2"], 'stroke-width="1.1" stroke-dasharray="6,3"', "#555"))
    out.append(linie(*f["quetsch"], 'stroke-width="1.6" stroke-dasharray="5,3"', "#c0392b"))
    for name, p, dx, dy in (("O", (0.0, 0.0), -10, 14), ("P1", z["P1"], 4, 14), ("P2", z["P2"], -22, -4), ("C", z["C"], 4, -4)):
        q = P(p).split(",")
        out.append('<circle cx="%s" cy="%s" r="2.5" fill="#111"/><text x="%.1f" y="%.1f">%s</text>' % (q[0], q[1], float(q[0]) + dx, float(q[1]) + dy, name))
    if masse:
        zeilen = ["β %.1f° · γ1 %.1f° · γ2 %.1f° · Überschuss ψ %.1f° · Ecklinie ℓ %.2f mm" % (z["beta"], z["gamma1"], z["gamma2"], z["psi"], z["ell"]),
                  "Höhe Aufkantung 1/2: %.2f / %.2f mm · Spitze C: %.2f mm von O · Länge der Oberkante im Überschuss: %.2f mm" % (
                      z["hoehe1"], z["hoehe2"], z["t_spitze"], z["m"]),
                  "blau: Biegelinien der Aufkantungen · rot: Faltlinie der Quetschfalte (180°) · grau: Seitenkanten, werden zur Ecklinie ε",
                  "Aussenmass bis zu den virtuellen Kanten – Biegezugaben noch nicht eingerechnet"]
        for i, zl in enumerate(zeilen):
            out.append('<text x="8" y="%.0f" fill="#333">%s</text>' % ((y1 - y0) * s + 10 + 14 * i, zl))
    out.append("</g></svg>")
    return "\n".join(out)


def svg_gefaltet(z, seite="wand1", titel="Quetschfalte – gefaltete Ecke (Ansicht von innen-oben, Falte liegt HINTER der Aufkantung)"):
    """Isometrische SVG der gefalteten Ecke: Basisfläche, beide Aufkantungen und die Quetschfalte (rot) auf der gewählten Wand."""
    g = z["geometrie"]
    L = z["laenge"] * 0.8
    e1, e2, d1, d2, eps = g["e1"], g["e2"], g["d1"], g["d2"], g["eps"]
    ell = z["ell"]

    def add(*vs):
        return tuple(sum(v[i] for v in vs) for i in range(3))

    def mul(v, k):
        return tuple(k * x for x in v)
    O = (0.0, 0.0, 0.0)
    Pk = mul(eps, ell)
    basis = [O, mul(e1, L), add(mul(e1, L), mul(e2, L)), mul(e2, L)]
    f1 = [O, mul(e1, L), add(mul(e1, L), mul(d1, z["hoehe1"])), Pk]
    f2 = [O, mul(e2, L), add(mul(e2, L), mul(d2, z["hoehe2"])), Pk]
    t = quetschfalte_3d(z, seite)
    wand_e, wand_d = (e1, d1) if seite == "wand1" else (e2, d2)
    n = _norm(_kreuz(wand_e, wand_d))
    c = (math.cos(math.radians(g["beta"] / 2.0)), math.sin(math.radians(g["beta"] / 2.0)), 0.0)
    if _sk(n, c) > 0:
        n = mul(n, -1.0)                                           # nach aussen (von der Basisfläche weg)
    versatz = 1.2
    tri = [add(t["O"], mul(n, versatz)), add(t["P"], mul(n, versatz)), add(t["C"], mul(n, versatz))]
    ca, sa = math.cos(math.radians(30)), math.sin(math.radians(30))

    def proj(p):
        return ((p[0] - p[1]) * ca, -(p[2] - (p[0] + p[1]) * sa))
    alle = [proj(p) for fl in (basis, f1, f2, tri) for p in fl]
    xs, ys = [a[0] for a in alle], [a[1] for a in alle]
    pad, sc = 14.0, 4.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    W, H = max((x1 - x0) * sc, 820), (y1 - y0) * sc + 44

    def pts(fl):
        return " ".join("%.1f,%.1f" % ((proj(p)[0] - x0) * sc, (proj(p)[1] - y0) * sc + 24) for p in fl)
    # Blickrichtung: von aussen (−x,−y,+z); weiter hinten liegende Flächen zuerst
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI,Arial" font-size="11">' % (W, H, W, H),
           '<rect width="100%" height="100%" fill="#fff"/>', '<text x="8" y="16" font-size="13" font-weight="600">%s</text>' % titel,
           '<polygon points="%s" fill="#e8756a" fill-opacity="0.95" stroke="#c0392b" stroke-width="1.6"/>' % pts(tri),
           '<polygon points="%s" fill="#cfe3f5" stroke="#1f6fb2" stroke-width="1.2"/>' % pts(basis),
           '<polygon points="%s" fill="#dfe6ec" stroke="#555" stroke-width="1.2" fill-opacity="0.82"/>' % pts(f1),
           '<polygon points="%s" fill="#e9eef2" stroke="#555" stroke-width="1.2" fill-opacity="0.82"/>' % pts(f2),
           '<text x="8" y="%d" fill="#333">Quetschfalte (rot, durch die Wand sichtbar) liegt flach auf der Aussenseite von %s – %s.</text>' % (
               H - 20, "Aufkantung 1 (an Kante 1)" if seite == "wand1" else "Aufkantung 2 (an Kante 2)",
               "hinten rechts" if seite == "wand1" else "hinten links"),
           '<text x="8" y="%d" fill="#333">Ecklinie ε %.2f mm · «rechts/links» von der Sichtseite aus gesehen · Lagen und Biegezonen nicht dargestellt.</text>' % (H - 6, ell),
           "</svg>"]
    return "\n".join(out)

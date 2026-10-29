"""Biege- und Abwicklungsrechnung – Python-Port von kern/geometrie.js (berechne, polylinie, kontur).

Ein Profil ist eine Folge von Operationen:
  {"typ": "schenkel", "L": mm}
  {"typ": "biegung", "winkel": Grad (+ links/oben, - rechts/unten), "ri": mm|None, "modus": "sharp"|"hem"|"tangent"}
Gemessen wird auf der Blechmitte bis zur virtuellen Kante. Bogenlänge = (ri + k·t)·|α|.

Die Werte (ri, k) kommen aus dem benutzerdefinierten Materialprofil. Das Ergebnis ist
eine THEORETISCHE Abwicklung – die verbindliche Abwicklung macht Fusion (Blechregel).
Gegen die Referenzwerte der JavaScript-Fassung getestet (tests/fixtures/referenz_geometrie.json).
"""
import math


class ProfilFehler(ValueError):
    pass


def _rueckversatz(op, t, ri_std):
    ri = op.get("ri") if op.get("ri") is not None else ri_std
    rm = ri + t / 2.0
    if op.get("modus") == "tangent":
        return 0.0
    if op.get("modus") == "hem" or abs(op["winkel"]) >= 175:
        return rm + t / 2.0
    return rm * math.tan(math.radians(abs(op["winkel"])) / 2.0)


def berechne(start_winkel, ops, t, ri_std, k):
    if not (t > 0):
        raise ProfilFehler("Blechdicke muss grösser als 0 sein")
    gerade = {}
    for i, op in enumerate(ops):
        if op["typ"] != "schenkel":
            continue
        sb = 0.0
        if i > 0 and ops[i - 1]["typ"] == "biegung":
            sb += _rueckversatz(ops[i - 1], t, ri_std)
        if i + 1 < len(ops) and ops[i + 1]["typ"] == "biegung":
            sb += _rueckversatz(ops[i + 1], t, ri_std)
        s = op["L"] - sb
        if s < -1e-6:
            nr = len([o for o in ops[: i + 1] if o["typ"] == "schenkel"])
            raise ProfilFehler("Schenkel %d (%s mm) ist zu kurz für die Biegeradien" % (nr, op["L"]))
        gerade[i] = max(s, 0.0)

    x = y = 0.0
    th = math.radians(start_winkel)
    pfad, biegungen, schenkel, beschriftungen = [], [], [], []
    pos = 0.0
    for i, op in enumerate(ops):
        if op["typ"] == "schenkel":
            s = gerade[i]
            schenkel.append(op["L"])
            if s > 1e-6:
                x2, y2 = x + s * math.cos(th), y + s * math.sin(th)
                pfad.append({"typ": "linie", "p1": (x, y), "p2": (x2, y2)})
                beschriftungen.append({"x": (x + x2) / 2, "y": (y + y2) / 2, "richtung": th, "mass": op["L"], "nr": len(schenkel)})
                x, y = x2, y2
            pos += s
        elif op["typ"] == "biegung":
            ri = op.get("ri") if op.get("ri") is not None else ri_std
            a = math.radians(op["winkel"])
            rm = ri + t / 2.0
            sg = 1 if a > 0 else -1
            cx, cy = x - sg * rm * math.sin(th), y + sg * rm * math.cos(th)
            a0 = math.atan2(y - cy, x - cx)
            p2 = (cx + rm * math.cos(a0 + a), cy + rm * math.sin(a0 + a))
            pfad.append({"typ": "bogen", "p1": (x, y), "p2": p2, "zentrum": (cx, cy), "rm": rm, "start": a0, "winkel": op["winkel"]})
            bogen = (ri + k * t) * abs(a)
            biegungen.append({
                "nr": len(biegungen) + 1, "pos": pos + bogen / 2.0, "von": pos, "bis": pos + bogen,
                "winkel": op["winkel"], "ri": ri,
                "art": {"sharp": "Abkanten", "hem": "Umschlag", "tangent": "Rundung"}.get(op.get("modus", "sharp")),
                "richtung": "oben" if op["winkel"] > 0 else "unten",
            })
            pos += bogen
            x, y = p2
            th += a
        else:
            raise ProfilFehler("Unbekannte Operation %r" % (op,))
    return {"pfad": pfad, "zuschnitt": pos, "summe_schenkel": sum(schenkel), "biegungen": biegungen, "schenkel": schenkel,
            "beschriftungen": beschriftungen}


def polylinie(pfad, schritt_grad=4):
    pts = []

    def add(p):
        if not pts or math.hypot(pts[-1][0] - p[0], pts[-1][1] - p[1]) > 1e-6:
            pts.append(p)

    for el in pfad:
        if el["typ"] == "linie":
            add(el["p1"])
            add(el["p2"])
            continue
        n = max(4, int(math.ceil(abs(el["winkel"]) / schritt_grad)))
        a = math.radians(el["winkel"])
        for i in range(n + 1):
            w = el["start"] + a * i / n
            add((el["zentrum"][0] + el["rm"] * math.cos(w), el["zentrum"][1] + el["rm"] * math.sin(w)))
    return pts


def kontur(pfad, t, schritt_grad=4):
    """Geschlossene Querschnittskontur mit Blechdicke (für Rundblech-Drehkörper und Werkstattblatt)."""
    h = t / 2.0

    def seite(vz):
        pts = []

        def add(p):
            if not pts or math.hypot(pts[-1][0] - p[0], pts[-1][1] - p[1]) > 1e-6:
                pts.append(p)

        for el in pfad:
            if el["typ"] == "linie":
                dx, dy = el["p2"][0] - el["p1"][0], el["p2"][1] - el["p1"][1]
                L = math.hypot(dx, dy)
                nx, ny = -dy / L * h * vz, dx / L * h * vz
                add((el["p1"][0] + nx, el["p1"][1] + ny))
                add((el["p2"][0] + nx, el["p2"][1] + ny))
            else:
                links = el["winkel"] > 0
                r = el["rm"] + (-h if (vz > 0) == links else h)
                n = max(4, int(math.ceil(abs(el["winkel"]) / schritt_grad)))
                a = math.radians(el["winkel"])
                for i in range(n + 1):
                    w = el["start"] + a * i / n
                    add((el["zentrum"][0] + r * math.cos(w), el["zentrum"][1] + r * math.sin(w)))
        return pts

    links, rechts = seite(1), seite(-1)
    return links + list(reversed(rechts))


def rueckversatz(op, t, ri_std):
    """Öffentlich für Zeichnungen: Abstand Tangentenpunkt ↔ virtuelle Kante einer Biegung."""
    return _rueckversatz(op, t, ri_std)


def profil_aus_operationen(basis_mm, ops, t):
    """Kantenoperationen (ab der Kante) → Profiloperationen mit einem Basisschenkel davor.

    basis_mm: Länge des bestehenden Blechs bis zur (virtuellen) Kante, nur für Rechnung/Zeichnung.
    """
    prof = [{"typ": "schenkel", "L": float(basis_mm)}]
    for op in ops:
        modus = "hem" if op["typ"] == "umschlag" else "sharp"
        prof.append({"typ": "biegung", "winkel": float(op["winkel"]), "ri": op.get("radius"), "modus": modus})
        prof.append({"typ": "schenkel", "L": float(op["laenge"])})
    return prof


def zugabe_abwicklung(ops, t, ri, k, basis_mm=100.0):
    """Theoretische Abwicklungslänge, die die Operationen an der Kante zusätzlich brauchen (mm, Blechmitte)."""
    res = berechne(0.0, profil_aus_operationen(basis_mm, ops, t), t, ri, k)
    return res["zuschnitt"] - basis_mm, res


def grenzen_von(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def k_faktor_aus_probe(zuschnitt, a, b, t, ri):
    """K-Faktor aus einer Probebiegung – Port von kFaktorAusProbe (kern/materialien.js).

    Streifen mit Zuschnitt z, EINE 90°-Biegung mit Innenradius ri, danach beide Schenkel AUSSEN gemessen (a, b).
    Masse auf Blechmitte = aussen − t/2. → {"k", "verkuerzung", "plausibel", "hinweis"}; ValueError bei unmöglichen Werten.
    """
    for name, v in (("Zuschnitt", zuschnitt), ("a", a), ("b", b), ("Dicke", t)):
        if not (isinstance(v, (int, float)) and v > 0):
            raise ValueError("%s muss grösser als 0 sein." % name)
    if not (isinstance(ri, (int, float)) and ri >= 0):
        raise ValueError("Innenradius fehlt (im Materialprofil oder bei der Probe eingeben).")
    verkuerzung = a + b - zuschnitt
    if verkuerzung <= 0:
        raise ValueError("a + b (%.1f) ist nicht grösser als der Zuschnitt (%.1f). Wurde aussen gemessen, und stimmt der Zuschnitt?" % (a + b, zuschnitt))
    rm = ri + t / 2.0
    l1, l2 = a - t / 2.0, b - t / 2.0
    bogen = zuschnitt - (l1 - rm) - (l2 - rm)   # Länge der neutralen Faser im Bogen
    k = (bogen / (math.pi / 2) - ri) / t
    plausibel = 0.1 < k < 0.6
    return {"k": k, "verkuerzung": verkuerzung, "plausibel": plausibel,
            "hinweis": "" if plausibel else "Unplausibel – üblich sind 0.3 bis 0.5. Prüfen: genau 90° gebogen? Aussen gemessen? Dicke und Innenradius richtig?"}

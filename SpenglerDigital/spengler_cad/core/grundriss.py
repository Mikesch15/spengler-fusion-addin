"""Grundrissverlauf: eine Linie in der Draufsicht (Folge von Strecken mit Richtungswechseln, offen oder als Ring) wird zu einem Band der Breite b.
Auf dieser Fläche entsteht das Grundblech; die Kanten am Verlauf bzw. an der Gegenkante bekommen die Kantenfolgen des Bauteils (Gehrung an den Ecken
übernimmt Fusion, weil zusammenhängende Kanten gemeinsam gebaut werden). Reine Geometrie ohne Fusion, alle Masse in mm.

Schreibweise des Verlaufs: «2500 L90 1800 R45 2500» – Zahl = Länge einer Strecke, «L90»/«R45» = Richtungswechsel am Ende dieser Strecke
(L = links, R = rechts, ohne Zahl 90°). Ein Ring (geschlossen) ist ein Verlauf, der am Ende wieder am Anfang ankommt, z. B. «3000 L90 2000 L90 3000 L90 2000 L90»."""
import math
import re

MAX_DREHUNG = 150.0       # schärfere Richtungswechsel lassen sich nicht sauber auf Gehrung bauen
TOL = 0.5                 # mm Abweichung beim Schliessen


class VerlaufFehler(ValueError):
    pass


_RICHTUNG = re.compile(r"^([LRlr])(\d+(?:[.,]\d+)?)?$")
_ZAHL = re.compile(r"^\d+(?:[.,]\d+)?$")


def parse(text):
    """Text → [{'laenge', 'drehung'}] (drehung am Ende der Strecke in Grad, + = links)."""
    teile = [t for t in re.split(r"[\s;]+", (text or "").strip()) if t]
    if not teile:
        raise VerlaufFehler("Der Verlauf ist leer. Beispiel: 2500 L90 1800")
    segs = []
    for t in teile:
        if _ZAHL.match(t):
            L = float(t.replace(",", "."))
            if L <= 0:
                raise VerlaufFehler("Eine Streckenlänge muss grösser als 0 sein.")
            segs.append({"laenge": L, "drehung": 0.0})
            continue
        m = _RICHTUNG.match(t)
        if not m:
            raise VerlaufFehler("«%s» ist nicht lesbar. Erlaubt: Längen (2500) und Richtungswechsel (L90, R45)." % t)
        if not segs:
            raise VerlaufFehler("Der Verlauf beginnt mit einer Länge, nicht mit «%s»." % t)
        w = float((m.group(2) or "90").replace(",", "."))
        if w <= 0 or w > MAX_DREHUNG:
            raise VerlaufFehler("Richtungswechsel «%s»: erlaubt sind 1° bis %g°." % (t, MAX_DREHUNG))
        segs[-1]["drehung"] += w if m.group(1).upper() == "L" else -w
    return segs


def als_text(segs):
    out = []
    for s in segs:
        out.append("%g" % s["laenge"])
        d = s.get("drehung") or 0
        if abs(d) > 1e-9:
            out.append("%s%g" % ("L" if d > 0 else "R", abs(d)))
    return " ".join(out)


def zusammenfassen(segs, geschlossen=False):
    """Strecken ohne Richtungswechsel dazwischen werden zu einer Strecke (sonst entstehen unnötig geteilte Kanten)."""
    out = []
    for s in segs:
        if out and abs(out[-1]["drehung"]) < TOL:
            out[-1] = {"laenge": out[-1]["laenge"] + s["laenge"], "drehung": s["drehung"]}
        else:
            out.append(dict(s))
    return out


def punkte(segs, geschlossen=False):
    """Eckpunkte der Verlaufslinie (Start im Ursprung, erste Strecke entlang +X). Ring: der letzte Punkt entfällt (= Start)."""
    segs = zusammenfassen(segs, geschlossen)
    x = y = 0.0
    kurs = 0.0
    pts = [(0.0, 0.0)]
    for s in segs:
        x += s["laenge"] * math.cos(math.radians(kurs))
        y += s["laenge"] * math.sin(math.radians(kurs))
        pts.append((x, y))
        kurs += s["drehung"]
    if geschlossen:
        if len(segs) < 3:
            raise VerlaufFehler("Ein Ring braucht mindestens 3 Strecken.")
        if math.hypot(pts[-1][0], pts[-1][1]) > TOL:
            raise VerlaufFehler("Der Verlauf schliesst nicht: Das Ende liegt %.0f mm vom Anfang entfernt. Prüfe Längen und Winkel (bei einem Rechteck: 4 Strecken mit 4 × L90 bzw. R90)." % math.hypot(pts[-1][0], pts[-1][1]))
        if abs(abs(sum(s["drehung"] for s in segs)) - 360.0) > 0.5:
            raise VerlaufFehler("Der Verlauf schliesst, kreuzt sich aber selbst (Summe der Richtungswechsel %.0f° statt ±360°)." % sum(s["drehung"] for s in segs))
        pts = pts[:-1]
    return pts


def _norm(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    return (dx / n, dy / n)


def versetzen(pts, breite, links=True, geschlossen=False):
    """Parallele Linie im Abstand `breite` (links/rechts der Laufrichtung) mit Gehrungsecken. → Punkte (gleiche Anzahl)."""
    s = 1.0 if links else -1.0
    n = len(pts)
    nsg = n if geschlossen else n - 1
    nrm = []
    for i in range(nsg):
        dx, dy = _norm(pts[i], pts[(i + 1) % n])
        nrm.append((-dy, dx))
    out = []
    for i in range(n):
        if not geschlossen and i == 0:
            v = nrm[0]
            k = 1.0
        elif not geschlossen and i == n - 1:
            v = nrm[-1]
            k = 1.0
        else:
            a, b = nrm[(i - 1) % nsg], nrm[i % nsg]
            dot = a[0] * b[0] + a[1] * b[1]
            if 1.0 + dot < 0.07:
                raise VerlaufFehler("Der Richtungswechsel an Punkt %d ist zu spitz für eine Gehrung." % (i + 1))
            k = 1.0 / (1.0 + dot)
            v = (a[0] + b[0], a[1] + b[1])
        out.append((pts[i][0] + s * breite * k * v[0], pts[i][1] + s * breite * k * v[1]))
    return out


def _kreuzt(p1, p2, p3, p4):
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p3, p4, p1), o(p3, p4, p2), o(p1, p2, p3), o(p1, p2, p4)
    return d1 * d2 < -1e-9 and d3 * d4 < -1e-9


def _selbst_kreuzung(segmente):
    """segmente: [(a, b)] → (i, j) des ersten sich kreuzenden Paars (ohne Nachbarn) oder None."""
    n = len(segmente)
    for i in range(n):
        for j in range(i + 2, n):
            if _kreuzt(segmente[i][0], segmente[i][1], segmente[j][0], segmente[j][1]):
                return i, j
    return None


def flaeche(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2.0


def band(segs, breite, links=True, geschlossen=False):
    """→ {'verlauf': Punkte, 'gegen': Punkte, 'schleifen': [Polygon,…] (für die Skizze: offen 1, Ring 2), 'ketten': {name: [(a, b),…]}, 'flaeche', 'laenge', 'text'}."""
    if breite <= 0:
        raise VerlaufFehler("Die Breite muss grösser als 0 sein.")
    segs = zusammenfassen(segs, geschlossen)
    if not geschlossen:
        segs = segs[:-1] + [dict(segs[-1], drehung=0.0)]       # am offenen Ende gibt es keinen Richtungswechsel
    pts = punkte(segs, geschlossen)
    gegen = versetzen(pts, breite, links, geschlossen)
    n = len(pts)
    nsg = n if geschlossen else n - 1
    ketten = {"verlauf": [(pts[i], pts[(i + 1) % n]) for i in range(nsg)], "gegen": [(gegen[i], gegen[(i + 1) % n]) for i in range(nsg)]}
    # Versatz darf Strecken nicht umkehren (Breite grösser als die kurze Strecke bei Innenecken)
    for i in range(nsg):
        a, b = ketten["verlauf"][i], ketten["gegen"][i]
        if (b[1][0] - b[0][0]) * (a[1][0] - a[0][0]) + (b[1][1] - b[0][1]) * (a[1][1] - a[0][1]) <= 0:
            raise VerlaufFehler("Die Breite %g mm ist zu gross für Strecke %d (die Gegenkante würde umklappen)." % (breite, i + 1))
    if geschlossen:
        schleifen = [list(pts), list(gegen)]
        for k in ("verlauf", "gegen"):
            if _selbst_kreuzung(ketten[k]):
                raise VerlaufFehler("Das Band überschneidet sich selbst – Breite verkleinern oder den Verlauf ändern.")
        if any(_kreuzt(a[0], a[1], b[0], b[1]) for a in ketten["verlauf"] for b in ketten["gegen"]):
            raise VerlaufFehler("Verlaufskante und Gegenkante kreuzen sich – die Breite ist für diesen Ring zu gross.")
        fl = abs(flaeche(pts) - flaeche(gegen))
    else:
        schleifen = [list(pts) + list(reversed(gegen))]
        ketten["start"] = [(pts[0], gegen[0])]
        ketten["ende"] = [(pts[-1], gegen[-1])]
        rand = [(schleifen[0][i], schleifen[0][(i + 1) % len(schleifen[0])]) for i in range(len(schleifen[0]))]
        if _selbst_kreuzung(rand):
            raise VerlaufFehler("Das Band überschneidet sich selbst – Breite verkleinern oder den Verlauf ändern.")
        fl = flaeche(schleifen[0])
    laenge = sum(math.hypot(a[1][0] - a[0][0], a[1][1] - a[0][1]) for a in ketten["verlauf"])
    text = "%d Strecke%s%s, Länge am Verlauf %.2f m, Fläche %.2f m²" % (nsg, "" if nsg == 1 else "n", " (Ring)" if geschlossen else "", laenge / 1000.0, fl / 1e6)
    return {"verlauf": pts, "gegen": gegen, "schleifen": schleifen, "ketten": ketten, "flaeche": fl, "laenge": laenge, "text": text, "geschlossen": bool(geschlossen)}


def svg(b, breite_px=300, hoehe_px=220, schrift=11):
    """Draufsicht des Bandes: Fläche hellblau, Kante am Verlauf blau, Gegenkante orange."""
    alle = [p for s in b["schleifen"] for p in s]
    xs, ys = [p[0] for p in alle], [p[1] for p in alle]
    rand = 24
    spanne_x, spanne_y = max(xs) - min(xs) or 1.0, max(ys) - min(ys) or 1.0
    m = min((breite_px - 2 * rand) / spanne_x, (hoehe_px - 2 * rand) / spanne_y)

    def pt(p):
        return "%.1f,%.1f" % (rand + (p[0] - min(xs)) * m, hoehe_px - rand - (p[1] - min(ys)) * m)

    def linie(punkte_, farbe, geschl):
        return '<polyline points="%s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="miter"/>' % (
            " ".join(pt(p) for p in (list(punkte_) + ([punkte_[0]] if geschl else []))), farbe)
    teile = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Segoe UI,Arial" font-size="%d">' % (breite_px, hoehe_px, breite_px, hoehe_px, schrift)]
    if b["geschlossen"]:
        teile.append('<path fill="#cfe5f7" fill-rule="evenodd" d="%s"/>' % " ".join("M" + " L".join(pt(p) for p in s) + " Z" for s in b["schleifen"]))
    else:
        teile.append('<polygon points="%s" fill="#cfe5f7"/>' % " ".join(pt(p) for p in b["schleifen"][0]))
    teile.append(linie(b["verlauf"], "#1f78c1", b["geschlossen"]))
    teile.append(linie(b["gegen"], "#f28c28", b["geschlossen"]))
    p0 = b["verlauf"][0]
    teile.append('<circle cx="%s" cy="%s" r="4" fill="#1f78c1"/>' % tuple(pt(p0).split(",")))
    teile.append('<text x="6" y="%d" fill="#1f78c1">▬ Kante am Verlauf</text><text x="%d" y="%d" fill="#f28c28">▬ Gegenkante</text>' % (hoehe_px - 6, breite_px // 2, hoehe_px - 6))
    teile.append("</svg>")
    return "".join(teile)

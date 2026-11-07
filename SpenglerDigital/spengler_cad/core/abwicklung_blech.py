"""Eigene Abwicklung eines Rechteck-Blechs mit geraden Aufkantungen und Quetschfalten an Ecken – unabhängig von Fusions Flat Pattern.

Modell (mm, Aussenmass): Grundfläche = Rechteck [0,lx]×[0,ly] bis zu den VIRTUELLEN Aussenkanten; je Seite optional eine Aufkantung (Winkel, Höhe aussen h).
Biegung: Rückversatz rv = (ri+t)·tan(α/2), Bogen = (ri + k·t)·α. Abgewickelt reicht die Aufkantung über die virtuelle Kante hinaus um E = h − 2·rv + Bogen
(Biegelinien: Beginn der Biegezone bei rv innerhalb der Grundfläche, Ende bei rv − Bogen). Ecken: ohne Quetschfalte offen (Stossecke, Streifen laufen durch);
mit Quetschfalte (zwei benachbarte Aufkantungen gleicher Höhe, 90°) ein Eckquadrat E×E mit Faltlinie (Diagonale), Ecklinien und Kontur.
Nur 90°-Ecken; Lagendicke und Biegezugabe der Falte selbst sind NICHT eingerechnet (ideale Faltlinien, wie core/quetschfalte)."""
import math


class AbwicklungFehler(ValueError):
    pass


SEITEN = ("unten", "rechts", "oben", "links")            # unten: y=0, rechts: x=lx, oben: y=ly, links: x=0
ECKEN = {"unten-links": ("unten", "links"), "unten-rechts": ("unten", "rechts"), "oben-rechts": ("oben", "rechts"), "oben-links": ("oben", "links")}


def biegung(h, t, ri, k, winkel=90.0):
    """→ dict rv, bogen, ausdehnung (E über die virtuelle Kante hinaus)."""
    if h <= 0 or t <= 0 or ri < 0:
        raise AbwicklungFehler("Höhe, Dicke und Innenradius müssen sinnvoll sein.")
    a = math.radians(winkel)
    rv = (ri + t) * math.tan(a / 2.0)
    bogen = (ri + k * t) * a
    E = h - 2.0 * rv + bogen
    if h < 2.0 * rv:
        raise AbwicklungFehler("Aufkantung %.1f mm ist niedriger als zwei Rückversätze (%.1f mm) – so nicht biegbar." % (h, 2 * rv))
    return {"rv": rv, "bogen": bogen, "E": E}


def abwicklung(lx, ly, aufkantungen, dicke, ri, k, quetschfalten=()):
    """aufkantungen: {seite: höhe_aussen}; quetschfalten: Eckennamen. → dict kontur, biegelinien, ecklinien, quetschlinien (Listen von ('linie',x1,y1,x2,y2)),
    breite, hoehe, bbox, flaeche, hinweise."""
    if lx <= 0 or ly <= 0:
        raise AbwicklungFehler("Länge und Breite müssen grösser als 0 sein.")
    b = {}
    for s, h in aufkantungen.items():
        if s not in SEITEN:
            raise AbwicklungFehler("Unbekannte Seite «%s»." % s)
        b[s] = biegung(h, dicke, ri, k)
    for e in quetschfalten:
        if e not in ECKEN:
            raise AbwicklungFehler("Unbekannte Ecke «%s»." % e)
        s1, s2 = ECKEN[e]
        if s1 not in b or s2 not in b:
            raise AbwicklungFehler("Quetschfalte an Ecke «%s» braucht Aufkantungen an «%s» und «%s»." % (e, s1, s2))
        if abs(aufkantungen[s1] - aufkantungen[s2]) > 1e-6:
            raise AbwicklungFehler("Quetschfalte «%s»: die beiden Aufkantungen müssen gleich hoch sein (%.1f / %.1f mm)." % (e, aufkantungen[s1], aufkantungen[s2]))
    rechtecke = [(0.0, 0.0, lx, ly)]                                  # (x0, y0, x1, y1)
    bl, ecklinien, quetsch = [], [], []
    for s, v in b.items():
        E, rv, bo = v["E"], v["rv"], v["bogen"]
        if s == "unten":
            rechtecke.append((0.0, -E, lx, 0.0))
            bl += [("linie", 0.0, rv, lx, rv), ("linie", 0.0, rv - bo, lx, rv - bo)]
        elif s == "oben":
            rechtecke.append((0.0, ly, lx, ly + E))
            bl += [("linie", 0.0, ly - rv, lx, ly - rv), ("linie", 0.0, ly - rv + bo, lx, ly - rv + bo)]
        elif s == "links":
            rechtecke.append((-E, 0.0, 0.0, ly))
            bl += [("linie", rv, 0.0, rv, ly), ("linie", rv - bo, 0.0, rv - bo, ly)]
        else:
            rechtecke.append((lx, 0.0, lx + E, ly))
            bl += [("linie", lx - rv, 0.0, lx - rv, ly), ("linie", lx - rv + bo, 0.0, lx - rv + bo, ly)]
    for e in quetschfalten:
        s1, s2 = ECKEN[e]
        E = b[s1]["E"]
        sx = -1.0 if e.endswith("links") else 1.0
        sy = -1.0 if e.startswith("unten") else 1.0
        ox = 0.0 if sx < 0 else lx
        oy = 0.0 if sy < 0 else ly
        x0, x1 = sorted((ox, ox + sx * E))
        y0, y1 = sorted((oy, oy + sy * E))
        rechtecke.append((x0, y0, x1, y1))
        ecklinien += [("linie", ox, oy, ox, oy + sy * E), ("linie", ox, oy, ox + sx * E, oy)]
        quetsch.append(("linie", ox, oy, ox + sx * E, oy + sy * E))
    # die Biegelinien enden an einer Quetschfalten-Ecke NICHT im Eckquadrat (dort gilt die Faltlinie) – sie laufen bis zur Ecklinie
    kontur = _umriss(rechtecke)
    xs = [p for r in rechtecke for p in (r[0], r[2])]
    ys = [p for r in rechtecke for p in (r[1], r[3])]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    flaeche = _flaeche(rechtecke)
    return {"kontur": kontur, "biegelinien": bl, "ecklinien": ecklinien, "quetschlinien": quetsch, "bbox": bbox,
            "breite": bbox[2] - bbox[0], "hoehe": bbox[3] - bbox[1], "flaeche": flaeche,
            "hinweise": ["Ideale Faltlinien; Lagendicke und Biegezugabe der Quetschfalte selbst nicht eingerechnet."] if quetschfalten else []}


def _flaeche(rechtecke):
    xs = sorted({p for r in rechtecke for p in (r[0], r[2])})
    ys = sorted({p for r in rechtecke for p in (r[1], r[3])})
    a = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if _belegt(rechtecke, (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2):
                a += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return a


def _belegt(rechtecke, x, y):
    return any(r[0] < x < r[2] and r[1] < y < r[3] for r in rechtecke)


def _umriss(rechtecke):
    """Aussenkontur der Vereinigung achsparalleler Rechtecke → Liste ('linie', x1, y1, x2, y2) mit zusammengefassten Strecken."""
    xs = sorted({round(p, 9) for r in rechtecke for p in (r[0], r[2])})
    ys = sorted({round(p, 9) for r in rechtecke for p in (r[1], r[3])})
    nx, ny = len(xs) - 1, len(ys) - 1
    zelle = [[_belegt(rechtecke, (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2) for j in range(ny)] for i in range(nx)]

    def voll(i, j):
        return 0 <= i < nx and 0 <= j < ny and zelle[i][j]
    horiz, vert = {}, {}              # horizontale Kanten: y-Index → Liste (i); vertikale: x-Index → Liste (j)
    for i in range(nx):
        for j in range(ny):
            if not zelle[i][j]:
                continue
            if not voll(i, j - 1):
                horiz.setdefault(j, []).append(i)
            if not voll(i, j + 1):
                horiz.setdefault(j + 1, []).append(i)
            if not voll(i - 1, j):
                vert.setdefault(i, []).append(j)
            if not voll(i + 1, j):
                vert.setdefault(i + 1, []).append(j)
    out = []
    for j, liste in sorted(horiz.items()):
        for a, z in _laeufe(sorted(liste)):
            out.append(("linie", xs[a], ys[j], xs[z + 1], ys[j]))
    for i, liste in sorted(vert.items()):
        for a, z in _laeufe(sorted(liste)):
            out.append(("linie", xs[i], ys[a], xs[i], ys[z + 1]))
    return out


def _laeufe(indizes):
    lauf = []
    for n in indizes:
        if lauf and n == lauf[-1][1] + 1:
            lauf[-1][1] = n
        else:
            lauf.append([n, n])
    return [tuple(x) for x in lauf]

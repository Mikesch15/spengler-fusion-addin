"""Allgemeine eigene Abwicklung von Blechteilen (unabhängig von Fusions Flat Pattern).

Modell (mm): Blech = ebene Flächen («Flächen», alle auf DERSELBEN Blechseite, Normale nach aussen) + Biegungen zwischen je zwei Flächen. Eine Biegung hat je Fläche
die Tangentenkante (gerade Strecke, 3D) und die Länge der neutralen Faser (Bogen = (ri + k·t)·α). Beliebig viele Flächen, beliebige Biegewinkel (auch > 90° und
gegensinnig), beliebige Konturen mit Löchern und Ausschnitten (Kurven als Polygonzug), schräge Biegeenden (Gehrung → Trapez), Verzweigungen (Baum). Zusatzstücke
(«Flicken», z. B. Quetschfalte an einer Ecke) werden in der Ebene einer Fläche angefügt. Ergebnis = Vereinigung aller Teile: Aussenkontur, Löcher, Biegelinien,
Faltlinien. Nur Biegungen entlang gerader Achsen; Kegel/Kugel/Doppelkrümmung werden nicht abgewickelt (gehören nicht in dieses Modell)."""
import math


class AbwicklungFehler(ValueError):
    pass


# ------------------------------------------------------------------ Vektoren
def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _mul(a, s):
    return tuple(x * s for x in a)


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _len(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _len(a)
    if n < 1e-12:
        raise AbwicklungFehler("Nullvektor (entartete Fläche oder Kante).")
    return _mul(a, 1.0 / n)


# ------------------------------------------------------------------ Flächen
class _Flaeche(object):
    def __init__(self, d):
        self.id = d["id"]
        self.n = _unit(d["n"])
        ref = (1.0, 0.0, 0.0) if abs(self.n[0]) < 0.9 else (0.0, 1.0, 0.0)          # u = Welt-X in der Fläche (stabile Lage der Abwicklung)
        self.u = _unit(_sub(ref, _mul(self.n, _dot(ref, self.n))))
        self.v = _cross(self.n, self.u)
        self.o = tuple(d["loops"][0][0])
        self.loops = [[self.lokal(p) for p in loop] for loop in d["loops"]]
        if len(self.loops[0]) < 3:
            raise AbwicklungFehler("Fläche «%s» hat keine Kontur." % self.id)
        self.abstand = {}                         # nur Plausibilität
        for loop in d["loops"]:
            for p in loop:
                if abs(_dot(_sub(p, self.o), self.n)) > 0.05:
                    raise AbwicklungFehler("Fläche «%s» ist nicht eben (Abweichung %.3f mm)." % (self.id, abs(_dot(_sub(p, self.o), self.n))))
        self.pose = None                           # (theta, tx, ty): lokal → Abwicklung

    def lokal(self, p):
        q = _sub(p, self.o)
        return (_dot(q, self.u), _dot(q, self.v))

    def platzieren(self, p2):
        th, tx, ty = self.pose
        c, s = math.cos(th), math.sin(th)
        return (c * p2[0] - s * p2[1] + tx, s * p2[0] + c * p2[1] + ty)

    def schwerpunkt_aussen(self):
        L = self.loops[0]
        return (sum(p[0] for p in L) / len(L), sum(p[1] for p in L) / len(L))


def abwickeln(flaechen, biegungen, flicken=(), wurzel=None, toleranz=1e-4):
    """flaechen: [{id, n, loops: [[(x,y,z)…] aussen, [..] Loch …]}]; biegungen: [{a, b, ea: (P0,P1), eb: (Q0,Q1), bogen}];
    flicken: [{flaeche, o (3D), e1 (3D), e2 (3D), polygon [(x,y) im Flickenrahmen: e1 = (1,0), e2 = Winkel β gegen e1], linien: {name: ((x,y),(x,y))}}].
    → dict kontur (Liste von Schleifen [(x,y)…], aussen gegen den Uhrzeigersinn, Löcher im Uhrzeigersinn), biegelinien, faltlinien {name: [...]}, flaeche, bbox, hinweise."""
    F = {}
    for d in flaechen:
        f = _Flaeche(d)
        if f.id in F:
            raise AbwicklungFehler("Flächen-ID «%s» doppelt." % f.id)
        F[f.id] = f
    if not F:
        raise AbwicklungFehler("Keine Flächen.")
    nach = {i: [] for i in F}
    for b in biegungen:
        if b["a"] not in F or b["b"] not in F:
            raise AbwicklungFehler("Biegung verweist auf eine unbekannte Fläche.")
        if b["bogen"] < 0:
            raise AbwicklungFehler("Negative Bogenlänge.")
        nach[b["a"]].append((b, True))
        nach[b["b"]].append((b, False))
    wurzel = wurzel if wurzel is not None else max(F.values(), key=lambda f: _flaeche_loops(f.loops)).id
    F[wurzel].pose = (0.0, 0.0, 0.0)
    biegelinien, streifen = [], []
    todo = [wurzel]
    benutzt = set()
    while todo:
        a = F[todo.pop(0)]
        for b, vorwaerts in nach[a.id]:
            if id(b) in benutzt:
                continue
            ziel = F[b["b"] if vorwaerts else b["a"]]
            ea, eb = (b["ea"], b["eb"]) if vorwaerts else (b["eb"], b["ea"])
            if ziel.pose is not None:
                raise AbwicklungFehler("Die Biegungen bilden eine Schleife (Fläche «%s» doppelt erreicht) – ein geschlossener Ring ist nicht abwickelbar." % ziel.id)
            benutzt.add(id(b))
            _anlegen(a, ziel, ea, eb, b["bogen"], biegelinien, streifen)
            todo.append(ziel.id)
    for f in F.values():
        if f.pose is None:
            raise AbwicklungFehler("Fläche «%s» hängt über keine Biegung am Rest des Blechs." % f.id)
    teile = []
    for f in F.values():
        teile.append([[f.platzieren(p) for p in loop] for loop in f.loops])
    for s in streifen:
        teile.append([s])
    falt = {}
    hinweise = []
    for k in flicken:
        f = F[k["flaeche"]]
        loops, lin = _flicken_platzieren(f, k)
        teile.append(loops)
        for name, seg in lin.items():
            falt.setdefault(name, []).append(seg)
    schleifen = vereinigung(teile, toleranz)
    xs = [p[0] for s in schleifen for p in s]
    ys = [p[1] for s in schleifen for p in s]
    flaeche = sum(_schnuer(s) for s in schleifen)
    return {"kontur": schleifen, "biegelinien": biegelinien, "faltlinien": falt, "flaeche": flaeche, "bbox": (min(xs), min(ys), max(xs), max(ys)),
            "breite": max(xs) - min(xs), "hoehe": max(ys) - min(ys), "hinweise": hinweise}


def _flaeche_loops(loops):
    return abs(_schnuer(loops[0])) - sum(abs(_schnuer(l)) for l in loops[1:])


def _schnuer(s):
    return sum(s[i][0] * s[(i + 1) % len(s)][1] - s[(i + 1) % len(s)][0] * s[i][1] for i in range(len(s))) / 2.0


def _anlegen(a, ziel, ea, eb, bogen, biegelinien, streifen):
    d = _unit(_sub(ea[1], ea[0]))
    if abs(_dot(d, _unit(_sub(eb[1], eb[0])))) < 0.999:
        raise AbwicklungFehler("Die Tangentenkanten der Biegung zwischen «%s» und «%s» sind nicht parallel (Kegel/Doppelkrümmung?) – nicht abwickelbar." % (a.id, ziel.id))
    # Achskoordinate s entlang d, geordnet
    sa = sorted((_dot(p, d), p) for p in ea)
    sb = sorted((_dot(p, d), p) for p in eb)
    pa = [a.platzieren(a.lokal(p)) for _, p in sa]
    u2 = _sub(pa[1], pa[0])
    if math.hypot(*u2) < 1e-9:
        raise AbwicklungFehler("Biegekante der Länge 0 zwischen «%s» und «%s»." % (a.id, ziel.id))
    u2 = _mul(u2, 1.0 / math.hypot(*u2))
    # weg von der Fläche a
    sx, sy = a.schwerpunkt_aussen()
    cx, cy = a.platzieren((sx, sy))
    w = (-u2[1], u2[0])
    if (cx - pa[0][0]) * w[0] + (cy - pa[0][1]) * w[1] > 0:
        w = (-w[0], -w[1])
    qa = [(pa[0][0] + w[0] * bogen + u2[0] * (s - sa[0][0]), pa[0][1] + w[1] * bogen + u2[1] * (s - sa[0][0])) for s, _ in sb]
    # Pose der Zielfläche: lokal (sb[0]) → qa[0], Richtung sb[0]→sb[1] → u2
    l0, l1 = ziel.lokal(sb[0][1]), ziel.lokal(sb[1][1])
    dl = (l1[0] - l0[0], l1[1] - l0[1])
    if math.hypot(*dl) < 1e-9:
        raise AbwicklungFehler("Biegekante der Länge 0 an «%s»." % ziel.id)
    th = math.atan2(u2[1], u2[0]) - math.atan2(dl[1], dl[0])
    c, s_ = math.cos(th), math.sin(th)
    tx = qa[0][0] - (c * l0[0] - s_ * l0[1])
    ty = qa[0][1] - (s_ * l0[0] + c * l0[1])
    ziel.pose = (th, tx, ty)
    sx2, sy2 = ziel.schwerpunkt_aussen()
    zx, zy = ziel.platzieren((sx2, sy2))
    if (zx - qa[0][0]) * w[0] + (zy - qa[0][1]) * w[1] < 0:
        raise AbwicklungFehler("Die Flächen «%s» und «%s» liegen nach dem Abwickeln auf derselben Seite der Biegung – die Normalen zeigen nicht auf dieselbe "
                               "Blechseite." % (a.id, ziel.id))
    biegelinien.append((pa[0], pa[1]))
    biegelinien.append((qa[0], qa[1]))
    streifen.append([pa[0], pa[1], qa[1], qa[0]])


def _flicken_platzieren(f, k):
    o2 = f.platzieren(f.lokal(k["o"]))
    e1 = f.platzieren(f.lokal(_add(k["o"], k["e1"])))
    e2 = f.platzieren(f.lokal(_add(k["o"], k["e2"])))
    r1 = (e1[0] - o2[0], e1[1] - o2[1])
    r2 = (e2[0] - o2[0], e2[1] - o2[1])
    th = math.atan2(r1[1], r1[0])
    spiegel = (r1[0] * r2[1] - r1[1] * r2[0]) < 0               # e2 liegt im Uhrzeigersinn von e1 → Flickenrahmen spiegeln
    c, s = math.cos(th), math.sin(th)

    def abb(p):
        x, y = p[0], (-p[1] if spiegel else p[1])
        return (c * x - s * y + o2[0], s * x + c * y + o2[1])
    poly = [abb(p) for p in k["polygon"]]
    lin = {n: (abb(a), abb(b)) for n, (a, b) in k.get("linien", {}).items()}
    return [poly], lin


# ------------------------------------------------------------------ Vereinigung ebener Vielecke (mit Löchern)
def _im_loop(p, loop):
    x, y = p
    innen = False
    n = len(loop)
    for i in range(n):
        x1, y1 = loop[i]
        x2, y2 = loop[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                innen = not innen
    return innen


def _im_teil(p, teil):
    return _im_loop(p, teil[0]) and not any(_im_loop(p, h) for h in teil[1:])


def vereinigung(teile, tol=1e-4):
    """teile: [[aussen, loch…], …] (Vielecke als Punktlisten). → Schleifen der Vereinigung (Aussen gegen, Löcher mit dem Uhrzeigersinn)."""
    segs = []
    for t in teile:
        for loop in t:
            n = len(loop)
            for i in range(n):
                a, b = loop[i], loop[(i + 1) % n]
                if math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9:
                    segs.append((a, b))
    eps = max(tol, 1e-6)
    teile_bb = []
    for t in teile:
        xs = [p[0] for p in t[0]]
        ys = [p[1] for p in t[0]]
        teile_bb.append((min(xs) - eps, min(ys) - eps, max(xs) + eps, max(ys) + eps))

    def innen(p):
        for t, bb in zip(teile, teile_bb):
            if bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3] and _im_teil(p, t):
                return True
        return False
    teilstuecke = {}
    for i, (a, b) in enumerate(segs):
        ts = [0.0, 1.0]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        for j, (c, d) in enumerate(segs):
            if i == j:
                continue
            if max(c[0], d[0]) < min(a[0], b[0]) - tol or min(c[0], d[0]) > max(a[0], b[0]) + tol \
                    or max(c[1], d[1]) < min(a[1], b[1]) - tol or min(c[1], d[1]) > max(a[1], b[1]) + tol:
                continue
            ex, ey = d[0] - c[0], d[1] - c[1]
            den = dx * ey - dy * ex
            if abs(den) > 1e-12:
                t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
                u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
                if -1e-9 <= u <= 1 + 1e-9 and 0 < t < 1:
                    ts.append(t)
            else:
                for p in (c, d):                       # parallel/kollinear: Endpunkte des anderen Stücks als Teilpunkte
                    if abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / math.sqrt(L2) <= tol:
                        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
                        if 0 < t < 1:
                            ts.append(t)
        ts = sorted(set(round(t, 12) for t in ts))
        for t0, t1 in zip(ts, ts[1:]):
            p0 = (a[0] + dx * t0, a[1] + dy * t0)
            p1 = (a[0] + dx * t1, a[1] + dy * t1)
            l = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            if l < 1e-7:
                continue
            m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            nx, ny = -(p1[1] - p0[1]) / l, (p1[0] - p0[0]) / l
            links = innen((m[0] + nx * eps, m[1] + ny * eps))
            rechts = innen((m[0] - nx * eps, m[1] - ny * eps))
            if links == rechts:
                continue
            q0, q1 = (p0, p1) if links else (p1, p0)             # Inneres liegt links der Richtung
            teilstuecke[(round(q0[0] / tol), round(q0[1] / tol), round(q1[0] / tol), round(q1[1] / tol))] = (q0, q1)
    return _ketten(list(teilstuecke.values()), tol)


def _ketten(segs, tol):
    nach = {}
    for s in segs:
        nach.setdefault((round(s[0][0] / tol), round(s[0][1] / tol)), []).append(s)
    benutzt = set()
    schleifen = []
    for s in segs:
        if id(s) in benutzt:
            continue
        pts = [s[0]]
        cur = s
        benutzt.add(id(s))
        while True:
            pts.append(cur[1])
            k = (round(cur[1][0] / tol), round(cur[1][1] / tol))
            cand = [c for c in nach.get(k, []) if id(c) not in benutzt]
            if not cand:
                break
            cur = cand[0]
            benutzt.add(id(cur))
        if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 2 * tol:
            pts.pop()
        schleifen.append(_gerade_punkte_entfernen(pts))
    return schleifen


def _gerade_punkte_entfernen(pts, tol=1e-6):
    n = len(pts)
    out = []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) > tol * max(1.0, math.hypot(b[0] - a[0], b[1] - a[1])):
            out.append(b)
    return out if len(out) >= 3 else pts


# ------------------------------------------------------------------ echte Bögen aus dem Polygonzug zurückgewinnen
def _kreis3(a, b, c):
    d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-12:
        return None
    ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1]) + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
    uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0]) + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
    return (ux, uy), math.hypot(a[0] - ux, a[1] - uy)


def _dreh(a, b, c):
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])


def _bogen_ok(pts, tol, max_schritt=math.radians(46.0)):
    """Passt der Punktzug (≥ 4 Punkte) auf einen Kreis? Gleichmässige Sehnen/Knicke, gleicher Drehsinn. → (mitte, r) oder None."""
    if len(pts) < 4:
        return None
    k = _kreis3(pts[0], pts[len(pts) // 2], pts[-1])
    if not k or k[1] > 20000.0:
        return None
    (cx, cy), r = k
    if any(abs(math.hypot(p[0] - cx, p[1] - cy) - r) > tol for p in pts):
        return None
    seh = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    if max(seh) > 1.6 * min(seh):
        return None
    vz = [_dreh(pts[i], pts[i + 1], pts[i + 2]) for i in range(len(pts) - 2)]
    if not (all(v > 0 for v in vz) or all(v < 0 for v in vz)):
        return None
    if any(2.0 * math.asin(min(1.0, s / (2.0 * r))) > max_schritt for s in seh):
        return None
    return (cx, cy), r


def _kreis_ganz(p, tol):
    n = len(p)
    if n < 8:
        return None
    k = _kreis3(p[0], p[n // 3], p[2 * n // 3])
    if not k:
        return None
    (cx, cy), r = k
    if any(abs(math.hypot(q[0] - cx, q[1] - cy) - r) > tol for q in p):
        return None
    seh = [math.hypot(p[(i + 1) % n][0] - p[i][0], p[(i + 1) % n][1] - p[i][1]) for i in range(n)]
    if max(seh) > 1.6 * min(seh):
        return None
    vz = [_dreh(p[i - 1], p[i], p[(i + 1) % n]) for i in range(n)]
    if not (all(v > 0 for v in vz) or all(v < 0 for v in vz)):
        return None
    return (cx, cy), r


def kontur_elemente(schleife, tol=0.004):
    """Schleife (Polygonzug) → Elemente ('linie', x1, y1, x2, y2) / ('bogen', cx, cy, r, a0, a1) (gegen den Uhrzeigersinn, Grad) / ('kreis', cx, cy, r)."""
    n = len(schleife)
    if n < 3:
        return []
    voll = _kreis_ganz(schleife, tol)
    if voll:
        return [("kreis", voll[0][0], voll[0][1], voll[1])]
    # Start an einer Ecke, die sicher nicht mitten im Bogen liegt (grösster Knick)
    def knick(i):
        a, b, c = schleife[i - 1], schleife[i], schleife[(i + 1) % n]
        return abs(math.atan2(_dreh(a, b, c), (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])))
    s0 = max(range(n), key=knick)
    p = schleife[s0:] + schleife[:s0]
    p = p + [p[0]]
    out = []
    i = 0
    while i < len(p) - 1:
        best = None
        j = i + 3
        while j < len(p):
            k = _bogen_ok(p[i:j + 1], tol)
            if not k:
                break
            best = (j, k)
            j += 1
        if best:
            j, ((cx, cy), r) = best
            a0 = math.degrees(math.atan2(p[i][1] - cy, p[i][0] - cx))
            a1 = math.degrees(math.atan2(p[j][1] - cy, p[j][0] - cx))
            if _dreh(p[i], p[i + 1], p[i + 2]) < 0:                 # im Uhrzeigersinn durchlaufen → Start/Ende tauschen
                a0, a1 = a1, a0
            out.append(("bogen", cx, cy, r, a0 % 360.0, a1 % 360.0))
            i = j
        else:
            out.append(("linie", p[i][0], p[i][1], p[i + 1][0], p[i + 1][1]))
            i += 1
    return out

"""Profil-Engine der Bauweise «eigene Geometrie» (Auftrag Kantenwerkzeug, Prototyp 2) – reine Rechnung, ohne Fusion testbar.

Ein Spenglerprofil entlang einer GERADEN Kante ist ein prismatischer Körper: ein ebener Querschnitt (Blechmitte als Folge von Schenkeln und
Kreisbögen, Dicke t) wird senkrecht zur Kante extrudiert. Daraus folgt mathematisch:
- jede Fläche ist eine Ebene (Schenkel) oder ein Kreiszylinder (Biegung, Achse ∥ Kante) → Gausssche Krümmung 0 → mathematisch (verzerrungsfrei) abwickelbar;
- Abwicklung: Breite = Kantenlänge, Länge = Σ gerade Schenkelteile + Σ (ri + k·t)·|α| (Spengler-Modell mit K-Faktor, wie core/bend_geometry);
- Volumen des 3D-Körpers = Breite · t · (Länge der Blechmitte) exakt; die Abweichung zur Abwicklung ist rein das K-Faktor-Modell:
  ΔV = Breite · t · Σ (k − ½)·t·|α|  → Rückvergleich trennt numerischen Fehler und Modellannahme.
Masse: Schenkellängen auf der Blechmitte bis zur virtuellen Kante (wie Vorschau und Abwicklungsrechnung). 2D-Koordinaten: x = vom Blech weg
(lokale Tangente u an der Kante), y = Seite der Bezugsfläche (lokale Normale n); Winkel + = zur Bezugsfläche hin."""
import math

from . import bend_geometry as bg

RI_MIN = 0.05          # mm: kleinster Innenradius (0 wäre eine scharfe, degenerierte Biegung)


class ProfilFehler(ValueError):
    pass


def doppelfalz_stellen(ops):
    """Indizes i, an denen ein Umschlag direkt auf einen Umschlag GLEICHER Richtung folgt = Doppelfalz wie beim Stehfalz (Anwender 5. 11. 2026:
    das umgeschlagene Ende wird samt Umschlag nochmals um 180° umgelegt). Gegenrichtung bleibt ein Z-Profil."""
    def umschlag(o):
        return o.get("typ") == "umschlag"
    return [i for i in range(len(ops or []) - 1) if umschlag(ops[i]) and umschlag(ops[i + 1])
            and (float(ops[i].get("winkel", 180)) >= 0) == (float(ops[i + 1].get("winkel", 180)) >= 0)]


def _stehfalz(prof, h1, h2, t, ri_std):
    """Doppelfalz als Paket-Umlegung (Querschnitt eines Blechs, Mittellinie). Vorher: ... Aufkantung (prof[-1]), Umschlag h1 (Länge a, Radius rh).
    Dann wird das obere Stück der Aufkantung der Höhe b = Länge des 2. Umschlags SAMT dem Umschlag nach aussen um 180° umgelegt:
    Aufkantung bis zur Falzlinie → äussere Biegung um das Paket (Innenradius rh·2 + t + r2) → umgelegter Aufkantungsteil b (aussen) → Umschlagbogen
    → Umschlagschenkel zurück bis zur Falzlinie → innere Biegung r2 (konzentrisch, Gegenrichtung) → Rest des Umschlagschenkels (a − b) bleibt am
    alten Platz. Ist b ≥ Umschlagschenkel, liegt der ganze Umschlag im Paket (keine innere Biegung). Masse bis zur virtuellen Kante wie überall."""
    w = 180.0 if float(h1["winkel"]) >= 0 else -180.0
    rh = h1.get("radius") if h1.get("radius") is not None else ri_std
    r2 = h2.get("radius") if h2.get("radius") is not None else ri_std
    for r in (rh, r2):
        if r is None or r < RI_MIN:
            raise ProfilFehler("Innenradius %s mm zu klein (mindestens %.2f mm) – eine scharfe Biegung ist geometrisch degeneriert." % (r, RI_MIN))
    rh, r2 = float(rh), float(r2)
    a, b = float(h1["laenge"]), float(h2["laenge"])
    if not prof or prof[-1]["typ"] != "schenkel" or len(prof) < 3:
        raise ProfilFehler("Ein Doppelfalz braucht vorher eine Aufkantung (Flansch), deren oberes Stück umgelegt wird.")
    ro = 2 * rh + t + r2
    prof[-1]["L"] = prof[-1]["L"] - b + ro - rh
    prof.append({"typ": "biegung", "winkel": w, "ri": ro, "modus": "hem"})
    prof.append({"typ": "schenkel", "L": b + (ro + t) + (rh + t)})
    prof.append({"typ": "biegung", "winkel": w, "ri": rh, "modus": "hem"})
    if a - (rh + t) > b + 1e-6:
        prof.append({"typ": "schenkel", "L": b + (rh + t) + (r2 + t)})
        prof.append({"typ": "biegung", "winkel": -w, "ri": r2, "modus": "hem"})
        prof.append({"typ": "schenkel", "L": a - b + r2 - rh})
    else:
        prof.append({"typ": "schenkel", "L": a})


def ops_zu_profil(ops, t, ri_std):
    """Kantenoperationen (Vorlage: flansch/umschlag mit winkel, laenge, radius) → Profil für bend_geometry, Biegung beginnt AN der Kante.
    Umschlag + Umschlag gleicher Richtung = Doppelfalz wie beim Stehfalz (_stehfalz). Ein Versatz ist in der eigenen Bauweise noch nicht umgesetzt
    (→ ProfilFehler)."""
    if not ops:
        raise ProfilFehler("Keine Operationen.")
    prof = []
    doppel = set(doppelfalz_stellen(ops))
    ueberspringen = set()
    for i, op in enumerate(ops):
        if i in ueberspringen:
            continue
        if i in doppel:
            if any(o.get("versatz") for o in ops[i:i + 2]):
                raise ProfilFehler("Versatz ist in der Bauweise «eigene Geometrie» noch nicht umgesetzt (nur nativ).")
            _stehfalz(prof, op, ops[i + 1], t, ri_std)
            ueberspringen.add(i + 1)
            continue
        if op.get("versatz"):
            raise ProfilFehler("Versatz ist in der Bauweise «eigene Geometrie» noch nicht umgesetzt (nur nativ).")
        if op.get("typ") not in ("flansch", "umschlag"):
            raise ProfilFehler("Operation «%s» ist im Profil nicht vorgesehen." % op.get("typ"))
        w = float(op["winkel"])
        if op["typ"] == "umschlag":
            w = 180.0 if w >= 0 else -180.0
        ri = op.get("radius") if op.get("radius") is not None else ri_std
        if ri is None or ri < RI_MIN:
            raise ProfilFehler("Innenradius %s mm zu klein (mindestens %.2f mm) – eine scharfe Biegung ist geometrisch degeneriert." % (ri, RI_MIN))
        biegung = {"typ": "biegung", "winkel": w, "ri": float(ri), "modus": "hem" if op["typ"] == "umschlag" else "sharp", "mass": "aussen"}
        rv = bg.rueckversatz(biegung, t, ri_std)
        if i == 0:
            prof.append({"typ": "schenkel", "L": rv})                 # gerader Anteil 0: die Biegung beginnt an der Kante
        prof.append(biegung)
        prof.append({"typ": "schenkel", "L": float(op["laenge"])})
    return prof


def segment_profil(r_innen, winkel_grad, t, schenkel_a=0.0, schenkel_b=0.0):
    """Gerolltes Segment (Innenradius, Bogenwinkel) mit optionalen geraden Enden – als Profil. Gerade Enden 0 = reines Kreissegment."""
    b = {"typ": "biegung", "winkel": float(winkel_grad), "ri": float(r_innen), "modus": "sharp"}
    rv = bg.rueckversatz(b, t, r_innen)
    return [{"typ": "schenkel", "L": rv + schenkel_a}, b, {"typ": "schenkel", "L": rv + schenkel_b}]


def anhaengen(profil, ops, t, ri_std, vorzeichen=1.0):
    """Kantenoperationen an das ENDE eines bestehenden Profils anhängen (Grundkörper + Aufkantung = ein Profil, für die Abwicklung des ganzen Teils).
    vorzeichen −1: die Seite der Bezugsfläche liegt im Profil rechts (Winkel spiegeln)."""
    neu = [dict(x) for x in profil]
    for op_ in ops_zu_profil(ops, t, ri_std)[1:]:
        if op_["typ"] == "biegung":
            op_ = dict(op_, winkel=vorzeichen * op_["winkel"])
            neu[-1]["L"] += bg.rueckversatz(op_, t, ri_std)
        neu.append(dict(op_))
    return neu


def umgekehrt(profil):
    """Profil von hinten gelesen (Anhängen am Anfang): Reihenfolge umkehren, Biegerichtung spiegeln."""
    return [dict(x, winkel=-x["winkel"]) if x["typ"] == "biegung" else dict(x) for x in reversed(profil)]


def _pt(c, r, w):
    return (c[0] + r * math.cos(w), c[1] + r * math.sin(w))


def querschnitt(profil, t, ri_std, k):
    """→ dict: umriss (geschlossene Folge exakter Elemente ('linie', p0, p1) / ('bogen', p0, pm, p1, zentrum, r)), flaechen [(typ, radius)],
    mittellinie_mm, flaeche_mm2 (Querschnitt), zuschnitt (Abwicklungslänge mit k), biegungen, pfad."""
    if not (t > 0):
        raise ProfilFehler("Blechdicke muss grösser als 0 sein.")
    try:
        res = bg.berechne(0.0, profil, t, ri_std, k)
    except bg.ProfilFehler as e:
        raise ProfilFehler(str(e))
    h = t / 2.0
    pfad = res["pfad"]
    if not pfad:
        raise ProfilFehler("Das Profil hat keine Geometrie.")

    def seite(vz):
        out = []
        for el in pfad:
            if el["typ"] == "linie":
                (x1, y1), (x2, y2) = el["p1"], el["p2"]
                L = math.hypot(x2 - x1, y2 - y1)
                nx, ny = -(y2 - y1) / L * h * vz, (x2 - x1) / L * h * vz
                out.append(("linie", (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)))
            else:
                links = el["winkel"] > 0
                r = el["rm"] + (-h if (vz > 0) == links else h)
                a = math.radians(el["winkel"])
                c = el["zentrum"]
                out.append(("bogen", _pt(c, r, el["start"]), _pt(c, r, el["start"] + a / 2), _pt(c, r, el["start"] + a), c, r))
        return out

    links, rechts = seite(1), seite(-1)
    umriss = list(links)
    umriss.append(("linie", links[-1][-3] if links[-1][0] == "bogen" else links[-1][2], rechts[-1][-3] if rechts[-1][0] == "bogen" else rechts[-1][2]))
    for el in reversed(rechts):
        if el[0] == "linie":
            umriss.append(("linie", el[2], el[1]))
        else:
            umriss.append(("bogen", el[3], el[2], el[1], el[4], el[5]))
    umriss.append(("linie", rechts[0][1], links[0][1]))
    flaechen, mitte, flaeche = [], 0.0, 0.0
    for el in pfad:
        if el["typ"] == "linie":
            L = math.hypot(el["p2"][0] - el["p1"][0], el["p2"][1] - el["p1"][1])
            mitte += L
            flaechen.append(("eben", None))
        else:
            b = el["rm"] * abs(math.radians(el["winkel"]))
            mitte += b
            flaechen.append(("zylinder", el["rm"] - h))
            flaechen.append(("zylinder", el["rm"] + h))
    flaeche = mitte * t
    return {"umriss": umriss, "flaechen": flaechen, "mittellinie_mm": mitte, "flaeche_mm2": flaeche, "zuschnitt": res["zuschnitt"],
            "biegungen": res["biegungen"], "pfad": pfad, "t": t, "k": k}


KONTAKT_TOL = 0.01     # mm: kleinerer Abstand zweier nicht benachbarter Konturteile gilt als Berührung (Kollision)


def _polygon(umriss, schritt_grad=3.0, sehnenfehler=KONTAKT_TOL / 2.0):
    """Polygon des Umrisses. Bögen adaptiv geteilt: Sehnenabweichung ≤ sehnenfehler (sonst könnten grosse Radien eine Überlappung von bis zu
    r·(1 − cos 1.5°) – bei R 100 mm 0.03 mm – verdecken), höchstens schritt_grad je Segment."""
    pts = []
    for el in umriss:
        if el[0] == "linie":
            seg = [el[1], el[2]]
        else:
            c, r = el[4], el[5]
            w0, w1 = math.atan2(el[1][1] - c[1], el[1][0] - c[0]), math.atan2(el[3][1] - c[1], el[3][0] - c[0])
            wm = math.atan2(el[2][1] - c[1], el[2][0] - c[0])
            # Richtung über den Mittelpunkt bestimmen
            d = (w1 - w0) % (2 * math.pi)
            if not (0 <= (wm - w0) % (2 * math.pi) <= d):
                d -= 2 * math.pi
            schritt = math.radians(schritt_grad)
            if r > sehnenfehler:
                schritt = min(schritt, 2.0 * math.acos(1.0 - sehnenfehler / r))
            n = max(2, int(math.ceil(abs(d) / schritt)))
            seg = [_pt(c, r, w0 + d * i / n) for i in range(n + 1)]
        for p in seg:
            if not pts or math.hypot(pts[-1][0] - p[0], pts[-1][1] - p[1]) > 1e-9:
                pts.append(p)
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 1e-9:
        pts.pop()
    return pts


def _schneiden(a, b, c, d, tol=1e-7):
    def kreuz(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = kreuz(c, d, a), kreuz(c, d, b), kreuz(a, b, c), kreuz(a, b, d)
    return ((d1 > tol and d2 < -tol) or (d1 < -tol and d2 > tol)) and ((d3 > tol and d4 < -tol) or (d3 < -tol and d4 > tol))


def _abstand_punkt_strecke(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    u = 0.0 if L2 < 1e-24 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)


def _abstand_strecken(a, b, c, d):
    if _schneiden(a, b, c, d, 0.0):
        return 0.0
    return min(_abstand_punkt_strecke(a, c, d), _abstand_punkt_strecke(b, c, d), _abstand_punkt_strecke(c, a, b), _abstand_punkt_strecke(d, a, b))


def selbstschnitt(umriss, tol=KONTAKT_TOL):
    """Schneidet oder BERÜHRT sich der Querschnitt selbst (Falz läuft in den Schenkel, Lagen liegen aufeinander, kollineare Überlappung)?
    Geprüft: echte Kreuzungen und Abstand < tol zwischen Konturteilen, die entlang des Umrisses weiter als 10·tol auseinanderliegen (so zählen die
    Nachbarsegmente einer engen Biegung nicht als Kontakt). → Liste der Problemstellen (leer = frei)."""
    p = _polygon(umriss)
    n = len(p)
    weg = [0.0]
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        weg.append(weg[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    umfang = weg[-1]
    nah = 10.0 * tol
    treffer = []
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        for j in range(i + 1, n):
            # Weg entlang des Umrisses zwischen den Segmenten (beide Richtungen um den geschlossenen Umriss)
            zwischen = max(0.0, weg[j] - weg[i + 1])
            zwischen = min(zwischen, max(0.0, umfang - weg[j + 1] + weg[i]))
            if zwischen < nah:
                continue
            c, d = p[j], p[(j + 1) % n]
            if _schneiden(a, b, c, d) or _abstand_strecken(a, b, c, d) < tol:
                treffer.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    return treffer


def pruefen(q):
    """Fertigungs-/Geometrieprüfung des Querschnitts. → Liste der Probleme (leer = in Ordnung)."""
    probleme = []
    for b in q["biegungen"]:
        if b["ri"] < RI_MIN:
            probleme.append("Biegung %d: Innenradius %.2f mm < %.2f mm" % (b["nr"], b["ri"], RI_MIN))
    s = selbstschnitt(q["umriss"])
    if s:
        probleme.append("Der Querschnitt schneidet oder berührt sich selbst (%d Stelle(n), z. B. bei x %.1f / y %.1f mm; Mindestabstand %.2f mm) – "
                        "Falz/Schenkel kollidieren" % (len(s), s[0][0], s[0][1], KONTAKT_TOL))
    return probleme


def abwicklung(q, breite, titel="Abwicklung"):
    """Eigene 2D-Abwicklung eines Profilteils: Rechteck Länge × Breite, Biegelinien in Bogenmitte (Spengler-Modell mit K-Faktor).
    → zuschnitt-dict im Format von manufacturing/dxf_writer.elemente_dxf."""
    L, W = q["zuschnitt"], float(breite)
    kontur = [("linie", 0.0, 0.0, L, 0.0), ("linie", L, 0.0, L, W), ("linie", L, W, 0.0, W), ("linie", 0.0, W, 0.0, 0.0)]
    biege = [("linie", b["pos"], 0.0, b["pos"], W) for b in q["biegungen"]]
    return {"kontur": kontur, "biegelinien": biege, "grenzen": (0.0, 0.0, L, W), "laenge": L, "breite": W,
            "beschreibung": "THEORETISCHER Zuschnitt %.2f x %.2f mm (Modell L = Summe Schenkel + Summe (ri + k*t)*Winkel; t %.2f, k %.2f, ri %s mm), "
                            "%d Biegung(en); Geometrie mathematisch abwickelbar (nur Ebenen/Zylinder); NICHT praktisch verifiziert" % (
                                L, W, q["t"], q["k"], "/".join("%.2f" % b["ri"] for b in q["biegungen"]) or "-", len(q["biegungen"]))}


def rueckvergleich(q, breite, volumen_3d_mm3=None, radien_3d_mm=None, tol_rel=1e-5):
    """2D ↔ 3D: Volumen des 3D-Körpers gegen Mittellinie × t × Breite (exakt) und Abwicklung × t × Breite (K-Faktor-Modell).
    radien_3d_mm: gemessene Zylinderradien des 3D-Körpers – müssen den Innen-/Aussenradien der Biegungen entsprechen.
    → dict mit ok, Texten und Zahlen (numerischer Fehler getrennt von der Modellabweichung)."""
    W, t = float(breite), q["t"]
    v_mitte = q["mittellinie_mm"] * t * W
    v_flach = q["zuschnitt"] * t * W
    modell = sum((q["k"] - 0.5) * t * abs(math.radians(b["winkel"])) for b in q["biegungen"]) * t * W
    erg = {"v_mitte": v_mitte, "v_flach": v_flach, "modell_diff": modell, "ok": True, "texte": []}
    erg["texte"].append("Theoretischer Zuschnitt %.3f mm × %.3f mm (k %.2f, ri %s mm); Mittellinie %.3f mm; K-Faktor-Modell ΔV = %+.3f mm³ (flach − Mitte)" % (
        q["zuschnitt"], W, q["k"], "/".join("%.2f" % b["ri"] for b in q["biegungen"]) or "-", q["mittellinie_mm"], modell))
    if abs((v_flach - v_mitte) - modell) > max(1e-6, tol_rel * v_mitte):
        erg["ok"] = False
        erg["texte"].append("Innere Rechnung inkonsistent (Abwicklung passt nicht zum Querschnitt)")
    if volumen_3d_mm3 is not None:
        num = volumen_3d_mm3 - v_mitte
        erg["numerisch"] = num
        gut = abs(num) <= max(0.01, tol_rel * v_mitte)
        erg["ok"] = erg["ok"] and gut
        erg["texte"].append("3D-Volumen %.3f mm³ gegen Sollvolumen (Mittellinie × t × Breite) %.3f mm³: Abweichung %+.4f mm³ (%s)" % (
            volumen_3d_mm3, v_mitte, num, "numerisch" if gut else "ZU GROSS – 3D und 2D passen nicht zusammen"))
    if radien_3d_mm is not None:
        soll = sorted({round(b["ri"], 3) for b in q["biegungen"]} | {round(b["ri"] + t, 3) for b in q["biegungen"]})
        ist = sorted({round(r, 3) for r in radien_3d_mm})
        fehlt = [r for r in soll if not any(abs(r - x) < 0.005 for x in ist)]
        erg["ok"] = erg["ok"] and not fehlt
        erg["texte"].append("Zylinderradien 3D %s, Soll %s%s" % (ist, soll, (" – FEHLEN: %s" % fehlt) if fehlt else ""))
    return erg

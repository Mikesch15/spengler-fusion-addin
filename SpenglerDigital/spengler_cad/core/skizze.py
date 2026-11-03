"""Profil von Hand skizzieren: aus gezeichneten Punkten (mm, y nach oben) werden Schenkel und Winkel; Längen und Winkel rasten auf das gewählte Raster ein.
Der erste Strich ist das bestehende Blech (Anschluss), jeder weitere Strich ein Flansch (Drehung links = +, rechts = −); eine Drehung von ≥ 170° ist ein Umschlag.
Gleiche Konvention wie die Kantenvorlagen und die Vorschau (bend_geometry). Reine Logik ohne Fusion."""
import math

UMSCHLAG_AB = 170.0
MIN_LAENGE = 1.0


class SkizzenFehler(ValueError):
    pass


def _norm(w):
    """Winkel in (−180, 180]."""
    w = (w + 180.0) % 360.0 - 180.0
    return 180.0 if w == -180.0 else w


def _runden(x, raster):
    return x if not raster or raster <= 0 else round(x / raster) * raster


def aus_punkten(punkte, laengenraster=1.0, winkelraster=5.0):
    """punkte: [(x, y)] in mm → Schenkel [{'laenge', 'winkel'}] (winkel = Drehung gegenüber dem vorigen Strich, 0 beim ersten) und Startrichtung in Grad.
    Zu kurze Striche entfallen; fast gerade Fortsetzungen werden mit dem vorigen Strich verbunden."""
    pts = [(float(p[0]), float(p[1])) for p in punkte]
    roh = []
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L >= MIN_LAENGE:
            roh.append((L, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))))
    if not roh:
        raise SkizzenFehler("Es ist noch kein Strich gezeichnet.")
    start = _runden(roh[0][1], winkelraster)
    schenkel = []
    vorher = start
    for i, (L, richtung) in enumerate(roh):
        dreh = 0.0 if i == 0 else _runden(_norm(richtung - roh[i - 1][1]), winkelraster)
        L = max(_runden(L, laengenraster), laengenraster or MIN_LAENGE)
        if i and abs(dreh) < 0.5:                       # gerade weiter → derselbe Strich
            schenkel[-1]["laenge"] += L
            continue
        schenkel.append({"laenge": L, "winkel": dreh})
    for s in schenkel:
        s["laenge"] = round(s["laenge"], 2)
        s["winkel"] = round(s["winkel"], 2)
    return schenkel, start


def zu_punkten(schenkel, start=(0.0, 0.0), start_richtung=0.0):
    """Schenkel → Eckpunkte (mm). Die Drehung eines Schenkels wirkt VOR seiner Länge."""
    x, y = start
    richtung = start_richtung
    pts = [(x, y)]
    for i, s in enumerate(schenkel):
        if i:
            richtung += float(s.get("winkel") or 0)
        x += float(s["laenge"]) * math.cos(math.radians(richtung))
        y += float(s["laenge"]) * math.sin(math.radians(richtung))
        pts.append((x, y))
    return pts


def operationen(schenkel):
    """Schenkel 2… → Kantenoperationen (der erste Schenkel ist das bestehende Blech)."""
    ops, hinweise = [], []
    for i, s in enumerate(schenkel[1:], 2):
        w = float(s.get("winkel") or 0)
        if abs(w) >= UMSCHLAG_AB:
            ops.append({"typ": "umschlag", "winkel": 180.0 if w > 0 else -180.0, "laenge": float(s["laenge"]), "radius": None})
            if abs(abs(w) - 180.0) > 0.5:
                hinweise.append("Strich %d: Drehung %g° als Umschlag (180°) übernommen." % (i, w))
        elif abs(w) >= 0.5:
            ops.append({"typ": "flansch", "winkel": w, "laenge": float(s["laenge"]), "radius": None})
    return ops, hinweise


def zuschnitt(schenkel, dicke, ri, k):
    """Theoretische Abwicklungslänge des ganzen Profils (inkl. erstem Strich) → (mm, None) oder (None, Grund)."""
    from .bend_geometry import ProfilFehler, berechne
    prof = [{"typ": "schenkel", "L": float(schenkel[0]["laenge"])}]
    for s in schenkel[1:]:
        w = float(s.get("winkel") or 0)
        prof.append({"typ": "biegung", "winkel": w if abs(w) < UMSCHLAG_AB else (180.0 if w > 0 else -180.0), "ri": None,
                     "modus": "hem" if abs(w) >= UMSCHLAG_AB else "sharp"})
        prof.append({"typ": "schenkel", "L": float(s["laenge"])})
    try:
        return berechne(0.0, prof, dicke, ri, k)["zuschnitt"], None
    except ProfilFehler as e:
        return None, str(e)


def auswerten(schenkel, start, dicke=None, ri=None, k=None):
    """Alles für die Anzeige: Eckpunkte, Operationen, Kurzschrift, Zuschnitt, Hinweise."""
    from .lernen import kurzschrift
    ops, hinweise = operationen(schenkel)
    erg = {"schenkel": schenkel, "start": start, "punkte": [list(p) for p in zu_punkten(schenkel, (0.0, 0.0), start)], "operationen": ops,
           "kurz": kurzschrift(ops) if ops else "", "hinweise": hinweise, "zuschnitt": None, "zuschnitt_grund": None,
           "summe": round(sum(float(s["laenge"]) for s in schenkel), 2)}
    if len(schenkel) == 1:
        hinweise.append("Zeichne weitere Striche: jeder Strich nach dem ersten wird ein Flansch oder Umschlag.")
    if dicke:
        erg["zuschnitt"], erg["zuschnitt_grund"] = zuschnitt(schenkel, dicke, ri if ri is not None else dicke, k if k is not None else 0.4)
        if erg["zuschnitt"] is not None:
            erg["zuschnitt"] = round(erg["zuschnitt"], 2)
    return erg

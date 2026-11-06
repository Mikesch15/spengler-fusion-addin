"""DXF des Zuschnitt-Ausschnitts einer Ecke mit Quetschfalte (Rechnung: core/quetschfalte). Layer: AUSSCHNITT (Kontur), BIEGUNG_OBEN (Biegelinien der
Aufkantungen), BIEGUNG_QUETSCHFALTE (Faltlinie 180°), BIEGUNG_ECKLINIE (Seitenkanten, die zur Ecklinie werden). Aussenmass, ideale Faltlinien."""
import math

from .dxf_writer import Dxf


def ecke_dxf(z, titel="Quetschfalte"):
    f = z["faltlinien"]
    L = z["laenge"]
    e2 = f["e2"][1]
    kontur = [z["kontur"][0], z["kontur"][1], z["kontur"][2], z["kontur"][3], z["kontur"][4],          # Flansch 1 → P1 → C → P2 → Flansch 2 (Oberkante)
              (e2[0], e2[1]),                                                                          # Ende Biegelinie 2
              (e2[0] + L, e2[1]),                                                                      # ferne Ecke der Basis
              (L, 0.0)]                                                                                # Ende Biegelinie 1
    d = Dxf()
    n = len(kontur)
    for i in range(n):
        d.linie(kontur[i], kontur[(i + 1) % n], "AUSSCHNITT", 7)
    d.linie(*f["e1"], "BIEGUNG_OBEN", 5)
    d.linie(*f["e2"], "BIEGUNG_OBEN", 5)
    d.linie(*f["quetsch"], "BIEGUNG_QUETSCHFALTE", 1)
    d.linie(*f["eps1"], "BIEGUNG_ECKLINIE", 8)
    d.linie(*f["eps2"], "BIEGUNG_ECKLINIE", 8)
    d.text((2.0, -z["hoehe1"] - 8.0), 4.0, "%s | Kantenwinkel %.1f | Ueberschuss %.1f | Ecklinie %.2f mm | Spitze %.2f mm" % (
        titel, z["beta"], z["psi"], z["ell"], z["t_spitze"]), "TEXT")
    return d


def ecke_flaeche_mm2(z):
    pts = z["kontur"]
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))) / 2.0


def ecke_anhaengen(pfad, z, titel="Quetschfalte (Ecke, neben der Abwicklung)", abstand=30.0):
    """Zuschnitt-Ausschnitt der Quetschfalte NEBEN die DXF-Abwicklung des Blechs anhängen (rechts der Abwicklung, Unterkante bündig, eigene Layer).
    Fusions Abwicklung kennt die Falte nicht (sie liegt in eigener Komponente). Die Ecke ist NICHT in die Kontur des Blechs eingerechnet.
    → (ok, Text). Nie Ausnahme; bei unlesbarer Datei bleibt sie unverändert. Nicht live geprüft."""
    try:
        with open(pfad, "r", encoding="utf-8", errors="replace") as f:
            zeilen = f.read().replace("\r\n", "\n").split("\n")
    except OSError as e:
        return False, "DXF nicht lesbar (%s)" % e
    xs, ys = [], []
    for i in range(0, len(zeilen) - 1, 2):
        try:
            code, wert = zeilen[i].strip(), float(zeilen[i + 1])
        except ValueError:
            continue
        if code in ("10", "11"):
            xs.append(wert)
        elif code in ("20", "21"):
            ys.append(wert)
    idx = [i for i, t in enumerate(zeilen) if t.strip() == "ENDSEC"]
    ent = [i for i in range(len(zeilen) - 1) if zeilen[i].strip() == "ENTITIES" and zeilen[i - 1].strip() == "2"]
    if not xs or not ys or not ent:
        return False, "Aufbau der DXF-Datei nicht erkannt"
    ende = next((i for i in idx if i > ent[0]), None)
    if ende is None or ende < 1:
        return False, "Ende des ENTITIES-Abschnitts nicht gefunden"
    d = ecke_dxf(z, titel)
    lx = [float(d.ents[i + 1]) for i in range(len(d.ents) - 1) if d.ents[i] in ("10", "11")]
    ly = [float(d.ents[i + 1]) for i in range(len(d.ents) - 1) if d.ents[i] in ("20", "21")]
    dx, dy = max(xs) + abstand - min(lx), min(ys) - min(ly)
    neu = []
    i = 0
    e = d.ents
    while i < len(e) - 1:
        c, w = e[i], e[i + 1]
        if c in ("10", "11"):
            w = repr(float(w) + dx)
        elif c in ("20", "21"):
            w = repr(float(w) + dy)
        neu += [c, w]
        i += 2
    zeilen[ende:ende] = neu
    try:
        with open(pfad, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(zeilen))
    except OSError as e2:
        return False, "DXF nicht beschreibbar (%s)" % e2
    return True, "Ecke der Quetschfalte rechts neben die Abwicklung gesetzt (Layer AUSSCHNITT/BIEGUNG_*)"

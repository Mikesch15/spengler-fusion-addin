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

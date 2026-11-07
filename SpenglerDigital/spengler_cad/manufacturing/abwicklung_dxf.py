"""DXF der eigenen Abwicklung (core/abwicklung_blech): Layer KONTUR, BIEGUNG (Biegezonen-Grenzen), BIEGUNG_ECKLINIE, BIEGUNG_QUETSCHFALTE, TEXT. mm."""
from .dxf_writer import Dxf


def abwicklung_dxf(r, titel="Abwicklung"):
    d = Dxf()
    for e in r["kontur"]:
        d.linie((e[1], e[2]), (e[3], e[4]), "KONTUR", 7)
    for e in r["biegelinien"]:
        d.linie((e[1], e[2]), (e[3], e[4]), "BIEGUNG", 5)
    for e in r["ecklinien"]:
        d.linie((e[1], e[2]), (e[3], e[4]), "BIEGUNG_ECKLINIE", 8)
    for e in r["quetschlinien"]:
        d.linie((e[1], e[2]), (e[3], e[4]), "BIEGUNG_QUETSCHFALTE", 1)
    x0, y0, x1, y1 = r["bbox"]
    d.text((x0, y0 - 10.0), 4.0, "%s | %.1f x %.1f mm | Flaeche %.0f mm2" % (titel, r["breite"], r["hoehe"], r["flaeche"]), "TEXT")
    return d


def zuschnitt_fuer_koerper(r):
    """Format für fusion_adapter.abwicklung_koerper (Kontur + Linien, die die Oberseite teilen)."""
    return {"kontur": r["kontur"], "biegelinien": r["biegelinien"] + r["ecklinien"] + r["quetschlinien"]}

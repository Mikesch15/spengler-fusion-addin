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


def _linien(schleife):
    n = len(schleife)
    return [(schleife[i], schleife[(i + 1) % n]) for i in range(n)]


def allgemein_dxf(r, titel="Abwicklung"):
    """DXF zu core/abwicklung_allgemein: KONTUR (Aussenkontur und Ausschnitte), BIEGUNG, Faltlinien (BIEGUNG_<NAME>), TEXT."""
    d = Dxf()
    for s in r["kontur"]:
        for a, b in _linien(s):
            d.linie(a, b, "KONTUR", 7)
    for a, b in _paare(r["biegelinien"]):
        d.linie(a, b, "BIEGUNG", 5)
    for name, segs in r["faltlinien"].items():
        for a, b in segs:
            d.linie(a, b, "BIEGUNG_" + ("QUETSCHFALTE" if name == "quetsch" else "ECKLINIE"), 1 if name == "quetsch" else 8)
    x0, y0, x1, y1 = r["bbox"]
    d.text((x0, y0 - 10.0), 4.0, "%s | %.1f x %.1f mm | Flaeche %.0f mm2" % (titel, r["breite"], r["hoehe"], r["flaeche"]), "TEXT")
    return d


def _paare(biegelinien):
    return [tuple(x) for x in biegelinien]


def allgemein_zuschnitt(r):
    """Format für fusion_adapter.abwicklung_koerper."""
    kontur = [("linie", a[0], a[1], b[0], b[1]) for s in r["kontur"] for a, b in _linien(s)]
    inner = [("linie", a[0], a[1], b[0], b[1]) for a, b in _paare(r["biegelinien"])]
    for segs in r["faltlinien"].values():
        inner += [("linie", a[0], a[1], b[0], b[1]) for a, b in segs]
    return {"kontur": kontur, "biegelinien": inner}

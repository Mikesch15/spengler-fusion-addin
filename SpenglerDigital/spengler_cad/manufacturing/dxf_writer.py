"""DXF-Schreiber (R12, mm) ohne Fremdbibliothek – nach dem Vorbild von kern/dxf.js.

Wird verwendet für: Zuschnittplan (Tafeln/Rollen) und die Prüfung von Konturen. Die Abwicklung
eines Fusion-Bauteils exportiert Fusion selbst (geometry/fusion_adapter.py, exportManager).
"""
import math


class DxfFehler(ValueError):
    pass


def ascii_text(s):
    s = str(s)
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss"), ("×", "x")):
        s = s.replace(a, b)
    return "".join(c if 32 <= ord(c) < 127 else "?" for c in s)


def kontur_pruefen(segmente, geschlossen=True, tol=1e-4):
    """Segmente [((x1,y1),(x2,y2)), …] auf Nulllängen, Doppelte und offene Enden prüfen → Liste von Problemen."""
    probleme = []
    gesehen = set()
    enden = {}
    r = lambda p: (round(p[0] / tol), round(p[1] / tol))
    for i, (a, b) in enumerate(segmente, 1):
        if math.hypot(b[0] - a[0], b[1] - a[1]) < tol:
            probleme.append("Segment %d hat Länge 0." % i)
            continue
        k = tuple(sorted([r(a), r(b)]))
        if k in gesehen:
            probleme.append("Segment %d ist doppelt." % i)
        gesehen.add(k)
        for p in (r(a), r(b)):
            enden[p] = enden.get(p, 0) + 1
    if geschlossen:
        offen = [p for p, n in enden.items() if n % 2]
        if offen:
            probleme.append("Kontur ist nicht geschlossen (%d offene Enden)." % len(offen))
    return probleme


class Dxf(object):
    def __init__(self):
        self.ents = []
        self.layer = {}

    def _layer(self, name, farbe):
        self.layer.setdefault(name, farbe)

    def linie(self, a, b, layer="0", farbe=7):
        self._layer(layer, farbe)
        self.ents += ["0", "LINE", "8", layer, "10", _f(a[0]), "20", _f(a[1]), "30", "0", "11", _f(b[0]), "21", _f(b[1]), "31", "0"]

    def rechteck(self, x, y, w, h, layer="0", farbe=7):
        p = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        for i in range(4):
            self.linie(p[i], p[(i + 1) % 4], layer, farbe)

    def text(self, p, hoehe, s, layer="TEXT", farbe=7):
        self._layer(layer, farbe)
        self.ents += ["0", "TEXT", "8", layer, "10", _f(p[0]), "20", _f(p[1]), "30", "0", "40", _f(hoehe), "1", ascii_text(s)]

    def inhalt(self):
        tab = ["0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(self.layer))]
        for n, c in self.layer.items():
            tab += ["0", "LAYER", "2", ascii_text(n), "70", "0", "62", str(c), "6", "CONTINUOUS"]
        tab += ["0", "ENDTAB", "0", "ENDSEC"]
        kopf = ["0", "SECTION", "2", "HEADER", "9", "$INSUNITS", "70", "4", "0", "ENDSEC"]  # 4 = Millimeter
        return "\n".join(kopf + tab + ["0", "SECTION", "2", "ENTITIES"] + self.ents + ["0", "ENDSEC", "0", "EOF"]) + "\n"

    def speichern(self, pfad):
        with open(pfad, "w", encoding="ascii", newline="\n") as f:
            f.write(self.inhalt())


def _f(v):
    return "%.4f" % float(v)


def zuschnittplan_dxf(blaetter, titel, layer_kontur="ZUSCHNITT", layer_text="TEXT", abstand=100.0):
    """Blätter des Zuschnittplans nebeneinander: Blattumriss (Layer FORMAT), Teile (layer_kontur), Beschriftung."""
    d = Dxf()
    x0 = 0.0
    for b in blaetter:
        d.rechteck(x0, 0, b["breite"], b["laenge"], "FORMAT", 8)
        d.text((x0, -15), 8, "%s - Blatt %d (%g x %g mm)" % (titel, b["blatt"], b["breite"], b["laenge"]), layer_text)
        for r in b["rechtecke"]:
            d.rechteck(x0 + r["x"], r["y"], r["w"], r["h"], layer_kontur, 7)
            d.text((x0 + r["x"] + 2, r["y"] + 4), min(6.0, r["w"] / 4), "%s %s" % (r["nr"], r["name"]), layer_text)
        x0 += b["breite"] + abstand
    return d

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spengler_cad.core import abwicklung_allgemein as aa
from spengler_cad.core import quetschfalte as qf


def flach(i, n, pts):
    return {"id": i, "n": n, "loops": [pts]}


class Allgemein(unittest.TestCase):
    def winkel(self, h=40, bogen=2.0):
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        fl = flach("f", (0, -1, 0), [(0, 0, 0), (200, 0, 0), (200, 0, h), (0, 0, h)])
        return [boden, fl], [{"a": "b", "b": "f", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": bogen}]

    def test_winkelblech(self):
        f, b = self.winkel()
        r = aa.abwickeln(f, b)
        self.assertAlmostEqual(r["flaeche"], 200 * (100 + 2 + 40), 6)
        self.assertEqual(len(r["kontur"]), 1)
        self.assertEqual(len(r["kontur"][0]), 4)
        self.assertEqual(len(r["biegelinien"]), 2)
        self.assertAlmostEqual(max(r["breite"], r["hoehe"]), 200, 6)

    def test_wurzel_egal(self):
        f, b = self.winkel()
        r1 = aa.abwickeln(f, b, wurzel="b")
        r2 = aa.abwickeln(f, b, wurzel="f")
        self.assertAlmostEqual(r1["flaeche"], r2["flaeche"], 6)
        self.assertAlmostEqual(sorted((r1["breite"], r1["hoehe"]))[0], sorted((r2["breite"], r2["hoehe"]))[0], 6)

    def test_u_profil_und_z_profil(self):
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        links = flach("l", (0, -1, 0), [(0, 0, 0), (200, 0, 0), (200, 0, 30), (0, 0, 30)])
        rechts = flach("r", (0, 1, 0), [(0, 100, 0), (0, 100, 30), (200, 100, 30), (200, 100, 0)])
        bi = [{"a": "b", "b": "l", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": 2.0},
              {"a": "b", "b": "r", "ea": ((0, 100, 0), (200, 100, 0)), "eb": ((0, 100, 0), (200, 100, 0)), "bogen": 2.0}]
        r = aa.abwickeln([boden, links, rechts], bi)
        self.assertAlmostEqual(r["flaeche"], 200 * (100 + 4 + 60), 6)
        # Z-Profil: zweite Aufkantung nach UNTEN (gegensinnig)
        rechts_z = flach("r", (0, -1, 0), [(0, 100, 0), (200, 100, 0), (200, 100, -30), (0, 100, -30)])
        r2 = aa.abwickeln([boden, links, rechts_z], bi)
        self.assertAlmostEqual(r2["flaeche"], 200 * (100 + 4 + 60), 6)

    def test_schraege_aufkantung_45_grad(self):
        c = math.cos(math.radians(45))
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        fl = flach("f", (0, -c, -c), [(0, 0, 0), (200, 0, 0), (200, -40 * c, 40 * c), (0, -40 * c, 40 * c)])
        r = aa.abwickeln([boden, fl], [{"a": "b", "b": "f", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": 1.5}])
        self.assertAlmostEqual(r["flaeche"], 200 * (100 + 1.5 + 40), 6)

    def test_trapez_und_gehrung(self):
        # Flansch mit schrägem Ende (Gehrung): Trapez – Fläche = Mittelwert der Längen × Breite
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        fl = flach("f", (0, -1, 0), [(0, 0, 0), (200, 0, 0), (150, 0, 40), (0, 0, 40)])
        r = aa.abwickeln([boden, fl], [{"a": "b", "b": "f", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": 2.0}])
        self.assertAlmostEqual(r["flaeche"], 200 * 102 + (200 + 150) / 2 * 40, 6)
        self.assertEqual(len(r["kontur"][0]), 5)

    def test_loch(self):
        boden = {"id": "b", "n": (0, 0, -1), "loops": [[(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)],
                                                        [(50, 40, 0), (80, 40, 0), (80, 60, 0), (50, 60, 0)]]}
        r = aa.abwickeln([boden], [])
        self.assertAlmostEqual(r["flaeche"], 200 * 100 - 30 * 20, 6)
        self.assertEqual(len(r["kontur"]), 2)

    def test_fehler(self):
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        lose = flach("x", (0, 0, -1), [(300, 0, 0), (300, 10, 0), (310, 10, 0), (310, 0, 0)])
        with self.assertRaises(aa.AbwicklungFehler):
            aa.abwickeln([boden, lose], [])
        # falsche Seite: Normale des Flansches nach innen
        f, b = self.winkel()
        f[1]["n"] = (0, 1, 0)
        with self.assertRaises(aa.AbwicklungFehler):
            aa.abwickeln(f, b)
        schief = flach("s", (0, 0, -1), [(0, 0, 0), (1, 0, 0), (1, 1, 5)])
        with self.assertRaises(aa.AbwicklungFehler):
            aa.abwickeln([schief], [])

    def test_quetschfalte_flicken(self):
        # Ecke O = (0,0,0), Basis x,y >= 0; Flansch 1 an y=0 (Höhe 40), Flansch 2 an x=0 (Höhe 40); Ersatzhöhe E = 40 + 2
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        f1 = flach("f1", (0, -1, 0), [(0, 0, 0), (200, 0, 0), (200, 0, 40), (0, 0, 40)])
        f2 = flach("f2", (-1, 0, 0), [(0, 0, 0), (0, 0, 40), (0, 100, 40), (0, 100, 0)])
        bi = [{"a": "b", "b": "f1", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": 2.0},
              {"a": "b", "b": "f2", "ea": ((0, 0, 0), (0, 100, 0)), "eb": ((0, 0, 0), (0, 100, 0)), "bogen": 2.0}]
        oh = aa.abwickeln([boden, f1, f2], bi)
        z = qf.zuschnitt(90.0, 42.0)
        flicken = {"flaeche": "b", "o": (0, 0, 0), "e1": (1, 0, 0), "e2": (0, 1, 0), "polygon": [(0, 0), z["P1"], z["C"], z["P2"]],
                   "linien": {"quetsch": ((0, 0), z["C"]), "eps1": ((0, 0), z["P1"]), "eps2": ((0, 0), z["P2"])}}
        r = aa.abwickeln([boden, f1, f2], bi, [flicken])
        self.assertAlmostEqual(r["flaeche"] - oh["flaeche"], 42.0 * 42.0, 4)       # Eckquadrat füllt die Lücke
        self.assertIn("quetsch", r["faltlinien"])
        self.assertEqual(len(r["kontur"]), 1)
        self.assertEqual(len(r["kontur"][0]), 4)                                    # wieder ein Rechteck mit Ausbuchtung? Quadrat + Streifen → 6 Ecken weniger


if __name__ == "__main__":
    unittest.main()


class AllgemeinDxf(unittest.TestCase):
    def test_dxf_und_zuschnitt(self):
        import tempfile
        from spengler_cad.manufacturing import abwicklung_dxf as ad
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        fl = flach("f", (0, -1, 0), [(0, 0, 0), (200, 0, 0), (200, 0, 40), (0, 0, 40)])
        r = aa.abwickeln([boden, fl], [{"a": "b", "b": "f", "ea": ((0, 0, 0), (200, 0, 0)), "eb": ((0, 0, 0), (200, 0, 0)), "bogen": 2.0}],
                         [{"flaeche": "b", "o": (200, 0, 0), "e1": (-1, 0, 0), "e2": (0, 1, 0), "polygon": [(0, 0), (0, -5), (-5, -5), (-5, 0)],
                           "linien": {"quetsch": ((0, 0), (-5, -5))}}])
        d = ad.allgemein_dxf(r)
        p = os.path.join(tempfile.mkdtemp(), "x.dxf")
        d.speichern(p)
        with open(p, encoding="ascii") as f:
            t = f.read()
        for layer in ("KONTUR", "BIEGUNG", "BIEGUNG_QUETSCHFALTE"):
            self.assertIn(layer, t)
        z = ad.allgemein_zuschnitt(r)
        self.assertGreaterEqual(len(z["kontur"]), 4)
        self.assertEqual(len(z["biegelinien"]), 2 + 1)

    def test_flicken_gespiegelt_gleiche_flaeche(self):
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        f1 = {"flaeche": "b", "o": (0, 0, 0), "e1": (1, 0, 0), "e2": (0, 1, 0), "polygon": [(0, 0), (0, -5), (-5, -5), (-5, 0)]}
        f2 = {"flaeche": "b", "o": (0, 0, 0), "e1": (0, 1, 0), "e2": (1, 0, 0), "polygon": [(0, 0), (0, -5), (-5, -5), (-5, 0)]}
        a1 = aa.abwickeln([boden], [], [f1])["flaeche"]
        a2 = aa.abwickeln([boden], [], [f2])["flaeche"]
        self.assertAlmostEqual(a1, 200 * 100 + 25, 6)
        self.assertAlmostEqual(a2, 200 * 100 + 25, 6)


class Boegen(unittest.TestCase):
    def kreis_pts(self, cx, cy, r, n=48, a0=0.0, a1=360.0):
        return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n)]

    def test_loch_wird_kreis(self):
        el = aa.kontur_elemente(self.kreis_pts(50, 50, 10))
        self.assertEqual(len(el), 1)
        self.assertEqual(el[0][0], "kreis")
        self.assertAlmostEqual(el[0][3], 10.0, 6)

    def test_rechteck_bleibt_linien(self):
        el = aa.kontur_elemente([(0, 0), (100, 0), (100, 50), (0, 50)])
        self.assertEqual([e[0] for e in el], ["linie"] * 4)

    def test_abgerundete_ecke(self):
        # Rechteck 100x50 mit Eckenradius 8 unten rechts
        pts = [(0, 0)]
        pts += [(92 + 8 * math.cos(math.radians(a)), 8 + 8 * math.sin(math.radians(a))) for a in range(-90, 1, 10)]
        pts += [(100, 50), (0, 50)]
        el = aa.kontur_elemente(pts)
        arten = sorted(e[0] for e in el)
        self.assertEqual(arten.count("bogen"), 1)
        b = next(e for e in el if e[0] == "bogen")
        self.assertAlmostEqual(b[3], 8.0, 6)
        self.assertAlmostEqual(b[4], 270.0, 4)
        self.assertAlmostEqual(math.sin(math.radians(b[5])), 0.0, 6)
        self.assertAlmostEqual(math.cos(math.radians(b[5])), 1.0, 6)
        self.assertEqual(arten.count("linie"), 4)

    def test_dxf_hat_arc_und_circle(self):
        import tempfile
        from spengler_cad.manufacturing import abwicklung_dxf as ad
        boden = {"id": "b", "n": (0, 0, -1), "loops": [[(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)],
                                                        [(x, y, 0) for x, y in self.kreis_pts(100, 50, 12, 64)]]}
        r = aa.abwickeln([boden], [])
        p = os.path.join(tempfile.mkdtemp(), "k.dxf")
        ad.allgemein_dxf(r).speichern(p)
        with open(p, encoding="ascii") as f:
            t = f.read()
        self.assertIn("CIRCLE", t)
        z = ad.allgemein_zuschnitt(r)
        self.assertIn("kreis", [e[0] for e in z["kontur"]])


class Faltzone(unittest.TestCase):
    def test_breite(self):
        self.assertAlmostEqual(aa.faltzone_breite(1.0, 0.33), math.pi * 0.33, 9)
        self.assertAlmostEqual(aa.faltzone_breite(1.0, 0.33, 1.5), 1.5, 9)
        with self.assertRaises(aa.AbwicklungFehler):
            aa.faltzone_breite(0, 0.33)

    def test_linien_im_eckfeld(self):
        z = qf.zuschnitt(90.0, 42.0)
        poly = [(0.0, 0.0), z["P1"], z["C"], z["P2"]]
        l = aa.faltzonen_linien(poly, (0.0, 0.0), z["C"], 2.0)
        self.assertEqual(len(l), 2)
        for p, q in l:
            self.assertTrue(aa._im_loop(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), poly))
            # parallel zur Faltlinie (Diagonale), Abstand 1.0 zur Mitte
            self.assertAlmostEqual(abs((q[0] - p[0]) - (q[1] - p[1])) , 0.0, 6)
            dist = abs(p[0] - p[1]) / math.sqrt(2)
            self.assertAlmostEqual(dist, 1.0, 6)

    def test_in_dxf_ebene(self):
        import tempfile
        from spengler_cad.manufacturing import abwicklung_dxf as ad
        boden = flach("b", (0, 0, -1), [(0, 0, 0), (0, 100, 0), (200, 100, 0), (200, 0, 0)])
        z = qf.zuschnitt(90.0, 42.0)
        poly = [(0.0, 0.0), z["P1"], z["C"], z["P2"]]
        lin = {"quetsch": ((0.0, 0.0), z["C"])}
        for i, sg in enumerate(aa.faltzonen_linien(poly, (0.0, 0.0), z["C"], 1.0)):
            lin["zone%d" % i] = sg
        r = aa.abwickeln([boden], [], [{"flaeche": "b", "o": (0, 0, 0), "e1": (1, 0, 0), "e2": (0, 1, 0), "polygon": poly, "linien": lin}])
        p = os.path.join(tempfile.mkdtemp(), "z.dxf")
        ad.allgemein_dxf(r).speichern(p)
        with open(p, encoding="ascii") as f:
            t = f.read()
        self.assertIn("BIEGUNG_QUETSCHFALTE_ZONE", t)

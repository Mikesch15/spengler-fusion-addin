import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spengler_cad.core import abwicklung_blech as ab
from spengler_cad.manufacturing import abwicklung_dxf as ad


class Abwicklung(unittest.TestCase):
    def test_einfache_aufkantung_masse(self):
        # Standardformel: a + b - 2 rv + Bogen
        r = ab.abwicklung(200, 100, {"unten": 40}, 1.0, 1.0, 0.33)
        b = ab.biegung(40, 1.0, 1.0, 0.33)
        self.assertAlmostEqual(r["hoehe"], 100 + 40 - 2 * b["rv"] + b["bogen"], 6)
        self.assertAlmostEqual(r["breite"], 200, 6)
        self.assertEqual(len(r["biegelinien"]), 2)
        self.assertEqual(len(r["kontur"]), 4)

    def test_u_form_ohne_quetschfalte_flaeche(self):
        r = ab.abwicklung(200, 100, {"unten": 40, "oben": 40}, 1.0, 1.0, 0.33)
        E = ab.biegung(40, 1.0, 1.0, 0.33)["E"]
        self.assertAlmostEqual(r["flaeche"], 200 * (100 + 2 * E), 6)

    def test_quetschfalte_eckquadrat(self):
        r = ab.abwicklung(200, 100, {"unten": 40, "links": 40}, 1.0, 1.0, 0.33, ["unten-links"])
        E = ab.biegung(40, 1.0, 1.0, 0.33)["E"]
        self.assertAlmostEqual(r["flaeche"], 200 * 100 + 200 * E + 100 * E + E * E, 6)
        self.assertEqual(len(r["quetschlinien"]), 1)
        self.assertEqual(len(r["ecklinien"]), 2)
        q = r["quetschlinien"][0]
        self.assertAlmostEqual(math.hypot(q[3] - q[1], q[4] - q[2]), E * math.sqrt(2), 6)
        self.assertAlmostEqual(r["bbox"][0], -E, 6)
        self.assertAlmostEqual(r["bbox"][1], -E, 6)

    def test_alle_vier_ecken_geschlossen(self):
        r = ab.abwicklung(200, 100, {s: 30 for s in ab.SEITEN}, 1.0, 1.0, 0.33, list(ab.ECKEN))
        E = ab.biegung(30, 1.0, 1.0, 0.33)["E"]
        self.assertAlmostEqual(r["flaeche"], (200 + 2 * E) * (100 + 2 * E), 6)
        self.assertEqual(len(r["kontur"]), 4)

    def test_fehler(self):
        with self.assertRaises(ab.AbwicklungFehler):
            ab.abwicklung(200, 100, {"unten": 40, "links": 30}, 1.0, 1.0, 0.33, ["unten-links"])
        with self.assertRaises(ab.AbwicklungFehler):
            ab.abwicklung(200, 100, {"unten": 40}, 1.0, 1.0, 0.33, ["unten-links"])
        with self.assertRaises(ab.AbwicklungFehler):
            ab.abwicklung(200, 100, {"unten": 3}, 1.0, 1.0, 0.33)

    def test_dxf(self):
        r = ab.abwicklung(200, 100, {"unten": 40, "links": 40}, 1.0, 1.0, 0.33, ["unten-links"])
        d = ad.abwicklung_dxf(r)
        pfad = os.path.join(tempfile.mkdtemp(), "a.dxf")
        d.speichern(pfad)
        t = open(pfad, encoding="utf-8").read()
        for layer in ("KONTUR", "BIEGUNG", "BIEGUNG_ECKLINIE", "BIEGUNG_QUETSCHFALTE"):
            self.assertIn(layer, t)
        z = ad.zuschnitt_fuer_koerper(r)
        self.assertEqual(len(z["biegelinien"]), len(r["biegelinien"]) + 3)


if __name__ == "__main__":
    unittest.main()

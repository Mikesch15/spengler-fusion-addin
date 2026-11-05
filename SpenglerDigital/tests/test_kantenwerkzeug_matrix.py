"""Kantenwerkzeug: Matrix nativ/eigen/Klasse a–e und mathematische Machbarkeit – reine Logik, KEIN Fusion-Test."""
import math
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import machbarkeit_gekruemmt as mg
from spengler_cad.core import unterstuetzung as u


class Matrix(unittest.TestCase):
    def test_api_grenze_ist_keine_unmoeglichkeit(self):
        self.assertEqual(u.stand("flansch", "zylinder", "gerade")[0], "prototyp")
        s, grund, kl = u.eigen("flansch", "zylinder", "gerade")
        self.assertEqual((s, kl), ("prototyp", "b"), "eigene exakte Geometrie möglich")
        self.assertEqual(u.eigen("flansch", "eben", "bogen")[2], "d", "Bogenkante: Torus – mathematisch nicht exakt")
        self.assertEqual(u.eigen("flansch", "eben", "kette")[2], "c")
        self.assertEqual(u.eigen("flansch", "unbekannt", "gerade")[2], "e")
        self.assertEqual(u.klasse("flansch", "eben", "gerade"), "a")

    def test_pruefen_bauweise(self):
        self.assertIsNone(u.pruefen_bauweise("flansch", "eben", "gerade", "eigen"))
        self.assertIn("gesperrter Prototyp", u.pruefen_bauweise("umschlag", "zylinder", "gerade", "eigen"))
        self.assertIsNone(u.pruefen_bauweise("umschlag", "zylinder", "gerade", "eigen", prototyp_erlaubt=True))
        self.assertIn("Torus", u.pruefen_bauweise("flansch", "eben", "kreis", "eigen", True))
        self.assertIn("gesperrter Prototyp", u.pruefen_bauweise("flansch", "zylinder", "gerade", "nativ"))

    def test_kantentypen(self):
        self.assertEqual([u.kantentyp(k) for k in ("linie", "ellipse", "spline", "kette")], ["gerade", "ellipse", "kurve", "kette"])
        self.assertIn("| Flansch | Zylinder | gerade Kante | Prototyp (gesperrt) | Prototyp (gesperrt) | b |", u.kantenwerkzeug_markdown())


class Machbarkeit(unittest.TestCase):
    def test_gauss(self):
        self.assertEqual(mg.biegezone_max_gauss("gerade"), 0.0)
        k = mg.biegezone_max_gauss("kreis", 500.0, 1.0, 1.0)
        self.assertGreater(k, 1e6 * mg.K_TOL, "Torus-Biegezone ist klar doppelt gekrümmt, kein Rundungsfehler")
        self.assertAlmostEqual(mg.gauss_torus(100, 10, 0.0), 1 / (10 * 110))
        self.assertAlmostEqual(mg.gauss_torus(100, 10, math.pi / 2), 0.0)

    def test_prototypwahl(self):
        p = mg.erster_prototyp()
        self.assertEqual(p["nr"], 2)
        self.assertFalse(mg.KANDIDATEN[0]["entwickelbar"], "Bogenkante auf ebenem Blech wird nicht als Erfolg umgesetzt")
        self.assertIn("Erster Prototyp: Nr. 2", mg.als_markdown())


if __name__ == "__main__":
    unittest.main()

import json
import os
import unittest

from _basis import FIXTURES
from spengler_cad.core import short_syntax as ks


class KurzschriftTest(unittest.TestCase):
    def test_prototyp_kompatibel(self):
        s = ks.schritte("90 25 U+ 7")
        self.assertEqual(s[0], {"winkel": 90.0, "laenge": 25.0, "art": "abkanten", "ri": None})
        self.assertEqual((s[1]["art"], s[1]["winkel"], s[1]["laenge"]), ("umschlag", 180.0, 7.0))
        self.assertEqual(ks.schritte("U-r1.4 40")[0], {"winkel": -180.0, "laenge": 40.0, "art": "umschlag", "ri": 1.4})
        self.assertEqual(ks.schritte("−90 30 45 10")[1]["winkel"], 45)

    def test_fehler(self):
        for falsch in ["", "90", "x 25", "90 -3", "90 0", "Q 5"]:
            with self.assertRaises(ValueError, msg=falsch):
                ks.schritte(falsch)

    def test_parameter_und_ausdruecke(self):
        ops = ks.zerlege("90 H U+ u+4*t {w}r2*t 10")
        self.assertEqual(ops[0]["laenge"], "H")
        self.assertEqual(ops[1]["laenge"], "u+4*t")
        self.assertEqual(ops[2]["winkel"], "w")
        self.assertEqual(ops[2]["radius"], "2*t")
        werte = {"H": 25, "u": 7, "t": 0.7, "w": -45}
        aufg = ks.aufloesen(ops, werte)
        self.assertAlmostEqual(aufg[1]["laenge"], 9.8)
        self.assertEqual(aufg[2]["winkel"], -45)
        self.assertAlmostEqual(aufg[2]["radius"], 1.4)
        with self.assertRaises(ks.KurzschriftFehler):
            ks.aufloesen(ops, {"H": 25})

    def test_text_rueckwaerts(self):
        for t in ["90 25 U+ 7", "-90 30 45 10", "U-r1.4 40", "90 H U+ u+4*t", "{w} 12.5"]:
            self.assertEqual(ks.als_text(ks.zerlege(t)), t)

    def test_alte_prototyp_bausteine_als_testdaten(self):
        """Die Bausteine aus Prototyp 0.1 sind nur noch Testdaten (Fixture) und müssen weiter lesbar sein."""
        with open(os.path.join(FIXTURES, "prototyp_0_1_bausteine_TESTDATEN.json"), encoding="utf-8") as f:
            daten = json.load(f)
        for b in daten["bausteine"]:
            self.assertTrue(ks.schritte(b["folge"]), b["name"])


if __name__ == "__main__":
    unittest.main()

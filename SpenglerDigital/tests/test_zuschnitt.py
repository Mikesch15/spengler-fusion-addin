"""Zuschnitt (theoretisch) von Rundblechen: Geometrie und DXF – Live-Test 7.1 «müsste auch abwickelbar werden»."""
import math
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.forming import forming as fo
from spengler_cad.manufacturing import dxf_lesen, dxf_writer


class ZuschnittTest(unittest.TestCase):
    def test_scheibe(self):
        z = fo.zuschnitt(fo.scheibe_mit_rand(100, 20, 90))
        self.assertEqual(z["kontur"], [("kreis", 0.0, 0.0, 120.0)])
        self.assertEqual(z["biegelinien"], [("kreis", 0.0, 0.0, 100.0)])
        self.assertIn("Rohling D 240.0", z["beschreibung"])

    def test_kragen_nur_loch_und_biegekreis(self):
        z = fo.zuschnitt(fo.kragen(50, 10, 90))
        self.assertEqual((z["kontur"][0][3], z["biegelinien"][0][3]), (40.0, 50.0))
        self.assertFalse(z["geschlossen"], "ohne Aussenkontur kein Körper")
        with self.assertRaises(ValueError):
            fo.zuschnitt(fo.kragen(10, 20, 90))

    def test_kegel_sektor(self):
        z = fo.zuschnitt(fo.kegelstumpf(100, 50, 100))
        arten = sorted(e[0] for e in z["kontur"])
        self.assertEqual(arten, ["bogen", "bogen", "linie", "linie"])
        R1, R2, w = 111.8033988, 223.6067977, 161.0
        bogen = [e for e in z["kontur"] if e[0] == "bogen"]
        self.assertAlmostEqual(max(e[3] for e in bogen), R2, 4)
        self.assertAlmostEqual(min(e[3] for e in bogen), R1, 4)
        self.assertAlmostEqual(bogen[0][5], w, 0)
        self.assertEqual(z["biegelinien"], [])

    def test_zylinder_rechteck_und_mehrteilig(self):
        z = fo.zuschnitt(fo.kegelstumpf(50, 50, 80))
        self.assertAlmostEqual(z["grenzen"][2], 2 * math.pi * 50, 4)
        self.assertEqual(len(z["kontur"]), 4)
        with self.assertRaises(ValueError):
            fo.zuschnitt(dict(fo.kegelstumpf(100, 99.9, 1), mehrteilig_noetig=True))

    def test_dxf_roundtrip(self):
        z = fo.zuschnitt(fo.scheibe_mit_rand(100, 20, 90))
        text = dxf_writer.elemente_dxf(z, "Rundblech scheibe").inhalt()
        elemente, ignoriert = dxf_lesen.lesen(text)
        self.assertEqual([(e["typ"], e["layer"]) for e in elemente], [("kreis", "ZUSCHNITT"), ("kreis", "BIEGELINIE")])
        self.assertEqual(elemente[0]["r"], 120.0)
        self.assertIn("TEXT", text)
        self.assertIn("stroke-dasharray", dxf_lesen.svg(elemente), "Biegelinie gestrichelt")

    def test_kegel_dxf_hat_boegen_und_linien(self):
        elemente, _ = dxf_lesen.lesen(dxf_writer.elemente_dxf(fo.zuschnitt(fo.kegelstumpf(100, 50, 100)), "Kegel").inhalt())
        self.assertEqual(sorted(e["typ"] for e in elemente), ["bogen", "bogen", "linie", "linie"])


if __name__ == "__main__":
    unittest.main()

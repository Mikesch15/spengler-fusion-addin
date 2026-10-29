"""Rundblech/Umformung: Geometrie, Unterscheidung konstruierbar/abwickelbar/herstellbar, keine Einschnitte."""
import math
import unittest

from _basis import test_material
from spengler_cad.forming import forming as fo


class UmformTest(unittest.TestCase):
    def test_scheibe_stauchen(self):
        e = fo.scheibe_mit_rand(100, 20)
        self.assertEqual(e["art"], "stauchen")
        self.assertAlmostEqual(e["dehnung_rand"], -20 / 120)
        self.assertEqual(e["rohling_durchmesser"], 240)
        self.assertFalse(e["abwickelbar"])

    def test_kragen_strecken(self):
        e = fo.kragen(50, 10)
        self.assertEqual(e["art"], "strecken")
        self.assertAlmostEqual(e["dehnung_rand"], 10 / 40)
        self.assertIn("fehler", fo.kragen(10, 15))

    def test_kegel(self):
        e = fo.kegelstumpf(100, 50, 100)
        s = math.hypot(50, 100)
        self.assertAlmostEqual(e["R_aussen"] - e["R_innen"], s)
        self.assertAlmostEqual(e["oeffnungswinkel"] / 360 * 2 * math.pi * e["R_aussen"], 2 * math.pi * 100)
        self.assertTrue(e["abwickelbar"])
        self.assertTrue(fo.kegelstumpf(80, 80, 50)["zylinder"])

    def test_herstellbarkeit_nur_mit_eigenem_grenzwert(self):
        e = fo.scheibe_mit_rand(100, 20)
        ohne = fo.beurteilen(e, "auto", test_material())
        self.assertIsNone(ohne["herstellbar"])
        self.assertTrue(any("nicht beurteilbar" in h for h in ohne["hinweise"]))
        m = test_material(formingLimits={"shrinkMaxPercent": 20, "stretchMaxPercent": 10, "source": "Probe Werkstatt"})
        self.assertTrue(fo.beurteilen(e, "stauchen", m)["herstellbar"])
        m["formingLimits"]["shrinkMaxPercent"] = 10
        self.assertFalse(fo.beurteilen(e, "stauchen", m)["herstellbar"])
        self.assertFalse(fo.beurteilen(e, "strecken", m)["herstellbar"], "falsches Verfahren")
        self.assertIsNone(fo.beurteilen(e, "manuell", m)["herstellbar"])

    def test_keine_einschnitte_ohne_freigabe(self):
        r = fo.beurteilen(fo.kragen(10, 15), "auto", test_material())
        self.assertFalse(r["herstellbar"])
        self.assertTrue(any("nicht erlaubt" in h for h in r["hinweise"]))

    def test_drehprofil(self):
        k = fo.drehprofil_scheibe(100, 20, 0.7, 1.0)
        self.assertGreater(len(k), 8)
        xs = [p[0] for p in k]
        self.assertAlmostEqual(max(xs), 100 + 0.35, places=1)


class WerkstattblattTest(unittest.TestCase):
    def test_blatt(self):
        from spengler_cad.manufacturing import workshop_sheet
        h = workshop_sheet.erstelle({"bauteil": "Teil <1>", "material": "TEST", "dicke": 0.7, "vorlage": "V", "vorlagenVersion": 2,
                                     "operationen": [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None},
                                                     {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}],
                                     "ri": 1.0, "k": 0.4, "abwicklung": {"breite": 120.5, "laenge": 1000, "quelle": "Fusion"}, "datum": "heute"})
        self.assertIn("Teil &lt;1&gt;", h)
        self.assertIn('class="biegelinie"', h)
        self.assertEqual(h.count('class="biegung">B'), 4, "B1/B2 im Querschnitt und in der Abwicklung")
        self.assertIn(">25<", h, "Schenkelmass 25 im Querschnitt")
        self.assertIn("theoretisch", h)
        self.assertEqual(h.count("<tr><td>"), 2 + 2)


if __name__ == "__main__":
    unittest.main()

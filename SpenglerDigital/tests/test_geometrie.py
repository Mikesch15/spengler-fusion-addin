"""Biegerechnung gegen die Referenzwerte der JavaScript-Fassung (kern/geometrie.js)."""
import json
import os
import unittest

from _basis import FIXTURES
from spengler_cad.core import bend_geometry as bg
from spengler_cad.core import units


def _ops(js_ops):
    return [{"typ": o["typ"], "L": o.get("L"), "winkel": o.get("winkel"), "ri": o.get("ri"), "modus": o.get("modus")} for o in js_ops]


class GeometrieTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURES, "referenz_geometrie.json"), encoding="utf-8") as f:
            self.ref = json.load(f)

    def test_referenzfaelle(self):
        for fall in self.ref["faelle"]:
            r = bg.berechne(fall["start"], _ops(fall["ops"]), fall["t"], fall["ri"], fall["k"])
            e = fall["erg"]
            self.assertAlmostEqual(r["zuschnitt"], e["zuschnitt"], places=9)
            for b, rb in zip(r["biegungen"], e["biegungen"]):
                for k in ("pos", "von", "bis"):
                    self.assertAlmostEqual(b[k], rb[k], places=9)
            self.assertAlmostEqual(r["pfad"][-1]["p2"][0], e["endpunkt"][0], places=9)
            self.assertAlmostEqual(r["pfad"][-1]["p2"][1], e["endpunkt"][1], places=9)
            self.assertEqual(len(r["beschriftungen"]), len(e["beschriftungen"]))
            for a, b in zip(r["beschriftungen"], e["beschriftungen"]):
                for k in ("x", "y", "richtung", "mass", "nr"):
                    self.assertAlmostEqual(a[k], b[k], places=9)
            ko = bg.kontur(r["pfad"], fall["t"], 4)
            self.assertEqual(len(ko), e["konturPunkte"])
            for a, b in zip(ko[0] + ko[-1], e["konturErster"] + e["konturLetzter"]):
                self.assertAlmostEqual(a, b, places=9)

    def test_zu_kurzer_schenkel(self):
        f = self.ref["fehlerFall"]
        with self.assertRaises(bg.ProfilFehler) as cm:
            bg.berechne(0, _ops(f["ops"]), f["t"], f["ri"], f["k"])
        self.assertEqual(str(cm.exception), f["meldung"])

    def test_zugabe(self):
        z, res = bg.zugabe_abwicklung([{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}], 0.7, 1.0, 0.4)
        self.assertEqual(len(res["biegungen"]), 1)
        self.assertTrue(20 < z < 25, z)   # kleiner als 25: Biegeverkürzung

    def test_k_faktor_aus_probe(self):
        """Wie test/kern.test.js: mit bekanntem k rechnen und aus a/b wieder zurück."""
        for k in (0.33, 0.4, 0.45):
            probe = bg.berechne(0, [{"typ": "schenkel", "L": 49.65}, {"typ": "biegung", "winkel": 90, "ri": None, "modus": "sharp"},
                                    {"typ": "schenkel", "L": 79.65}], 0.7, 1, k)
            r = bg.k_faktor_aus_probe(probe["zuschnitt"], 50, 80, 0.7, 1)
            self.assertAlmostEqual(r["k"], k, places=9)
            self.assertTrue(r["plausibel"])
        self.assertFalse(bg.k_faktor_aus_probe(129.5, 50, 80, 0.7, 1)["plausibel"])
        for falsch in ((131, 50, 80, 0.7, 1), (0, 50, 80, 0.7, 1), (128, 50, 80, 0.7, None), (128, 50, 80, 0, 1)):
            with self.assertRaises(ValueError, msg=falsch):
                bg.k_faktor_aus_probe(*falsch)

    def test_einheiten(self):
        self.assertEqual(units.mm_zu_cm(25), 2.5)
        self.assertEqual(units.laenge_mm("2,5 cm"), 25)
        self.assertEqual(units.laenge_mm("0.025m"), 25)
        self.assertAlmostEqual(units.winkel_grad("1.5707963 rad"), 90, places=4)
        self.assertEqual(units.fusion_ausdruck_mm(25), "25 mm")
        self.assertEqual(units.fusion_ausdruck_mm(0.75), "0.75 mm")
        self.assertEqual(units.fusion_ausdruck_grad(-90), "-90 deg")
        self.assertEqual(units.anzeigen_mm(1234.5), "1'234.5 mm")
        for falsch in ("abc", "25 kg", ""):
            with self.assertRaises(units.EinheitFehler):
                units.laenge_mm(falsch)


if __name__ == "__main__":
    unittest.main()

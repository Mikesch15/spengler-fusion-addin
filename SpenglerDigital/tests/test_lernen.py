"""Vorlage aus vorhandenem Profil lernen: Werte → Operationen → Vorlage (ohne Fusion)."""
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import lernen


def fl(**k):
    return dict({"art": "flansch", "name": "Kantenflansch 1", "winkel_grad": 90.0, "laenge_mm": 25.0, "radius_mm": None, "gespiegelt": False}, **k)


class LernenTest(unittest.TestCase):
    def test_flansch_und_umschlag(self):
        ops, hin, fehler = lernen.schritte_aus_features([fl(), {"art": "umschlag", "name": "Falz 1", "laenge_mm": 7.0, "gespiegelt": False}])
        self.assertEqual(fehler, [])
        self.assertEqual(lernen.kurzschrift(ops), "90 25 U+ 7")
        self.assertTrue(any("Richtung" in h for h in hin))

    def test_gespiegelter_erster_schritt_gibt_allen_das_minus(self):
        ops, _, _ = lernen.schritte_aus_features([fl(gespiegelt=True), fl(winkel_grad=45.0, laenge_mm=10.0), {"art": "umschlag", "laenge_mm": 5.0}])
        self.assertEqual([o["winkel"] for o in ops], [-90.0, -45.0, -180.0])

    def test_radius_und_rundung(self):
        ops, _, _ = lernen.schritte_aus_features([fl(radius_mm=1.5, laenge_mm=24.99999, winkel_grad=88.0000001)])
        self.assertEqual((ops[0]["radius"], ops[0]["laenge"], ops[0]["winkel"]), (1.5, 25.0, 88.0))

    def test_fehlende_werte_sind_fehler(self):
        ops, _, fehler = lernen.schritte_aus_features([fl(laenge_mm=None), fl(winkel_grad=None), fl(winkel_grad=180.0), fl(winkel_grad=60.0)])
        self.assertEqual(len(ops), 1)
        self.assertEqual(len(fehler), 3)
        self.assertIn("Länge nicht lesbar", fehler[0])

    def test_vorlage(self):
        ops, _, _ = lernen.schritte_aus_features([fl(), fl(winkel_grad=90.0, laenge_mm=10.0)])
        v, f, w = lernen.vorlage_aus_schritten("Winkelfalz gelernt", ops, "Gelernt")
        self.assertEqual(f, [])
        self.assertEqual((v["name"], v["category"], len(v["operations"])), ("Winkelfalz gelernt", "Gelernt", 2))
        self.assertIsNone(lernen.vorlage_aus_schritten("", ops)[0])
        self.assertIsNone(lernen.vorlage_aus_schritten("x", [])[0], "ohne Schritte keine Vorlage")

    def test_rollen_und_text(self):
        self.assertEqual([lernen.feld_zu_rolle(t) for t in ("Flange Angle", "Höhe", "BendRadius", "d12")], ["winkel", "laenge", "radius", None])
        self.assertEqual(lernen.beschreibung(fl(radius_mm=1.5)), "Flansch 90°, 25 mm, Ri 1.5")
        self.assertIn("nicht lesbar", lernen.beschreibung({"art": "umschlag"}))


if __name__ == "__main__":
    unittest.main()

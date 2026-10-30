"""Massbezug/Lage in Kantenvorlagen: Prüfung, Auflösung, Bauplan-Text."""
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import operation_plan, short_syntax, validation


def op(**k):
    return dict({"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, **k)


class MassbezugTest(unittest.TestCase):
    def test_gueltige_werte(self):
        f, _ = validation.pruefe_operationen([op(bezug="innen", lage="aussen"), op(bezug="tangential", lage="kante")], [])
        self.assertEqual(f, [])

    def test_ungueltige_werte(self):
        f, _ = validation.pruefe_operationen([op(bezug="mitte", lage="oben")], [])
        self.assertIn("Massbezug «mitte» unbekannt", " ".join(f))
        self.assertIn("Lage «oben» unbekannt", " ".join(f))

    def test_umschlag_ohne_massbezug_aber_mit_lage(self):
        um = {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}
        f, _ = validation.pruefe_operationen([dict(um, bezug="innen")], [])
        self.assertIn("keinen Massbezug", " ".join(f))
        f, _ = validation.pruefe_operationen([dict(um, lage="innen")], [])
        self.assertEqual(f, [])

    def test_aufloesen_reicht_felder_durch_aber_nur_wenn_gesetzt(self):
        aufgeloest = short_syntax.aufloesen([op(bezug="innen", lage="aussen"), op()], {})
        self.assertEqual(aufgeloest[0]["bezug"], "innen")
        self.assertEqual(aufgeloest[0]["lage"], "aussen")
        self.assertEqual(aufgeloest[1], {"typ": "flansch", "winkel": 90.0, "laenge": 25.0, "radius": None}, "ohne Wahl bleibt alles wie bisher")

    def test_bauplantext(self):
        from _basis import test_material
        from test_templates import testvorlage
        v = testvorlage()
        v["operations"] = [op(bezug="innen", lage="aussen")]
        k = {"ref": 1, "text": "Kante 1", "kurve": "linie", "laenge": 500.0, "flaechen": 2, "blech": True, "dicke": 0.7, "frei": True}
        text = operation_plan.beschreibung(operation_plan.erstelle(v, {}, test_material(), [k]))
        self.assertIn("Mass innen, Lage aussen", text)

    def test_radius_standard_aus_material(self):
        from _basis import test_material
        from test_templates import testvorlage
        v = testvorlage()
        v["operations"] = [op(), op(radius=2.0), {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}]
        k = {"ref": 1, "text": "Kante 1", "kurve": "linie", "laenge": 500.0, "flaechen": 2, "blech": True, "dicke": 0.7, "frei": True}
        m = test_material()
        ops = operation_plan.erstelle(v, {}, m, [k])["operations"]
        self.assertEqual([o["radius"] for o in ops], [m["innerRadius"], 2.0, None], "Flansch: Materialradius, eigener Radius gilt, Umschlag unberührt")


if __name__ == "__main__":
    unittest.main()

"""Bauplan: Kanteneignung, Fehler, Theorie – ohne Fusion mit Kantenbeschreibungen."""
import unittest

from _basis import test_material
from spengler_cad.core import operation_plan as op
from test_templates import testvorlage


def kante(**k):
    d = {"ref": 1, "text": "Kante 1", "kurve": "linie", "laenge": 500.0, "flaechen": 2, "blech": True, "dicke": 0.7, "frei": True}
    d.update(k)
    return d


class BauplanTest(unittest.TestCase):
    def test_gueltiger_plan(self):
        p = op.erstelle(testvorlage(), {"H": 25}, test_material(), [kante(), kante(ref=2, text="Kante 2")])
        self.assertEqual(p["validation"]["errors"], [])
        self.assertTrue(op.ist_ausfuehrbar(p))
        self.assertEqual(len(p["operations"]), 2)
        self.assertIsNotNone(p["theory"]["zugabe"])
        self.assertEqual(p["templateVersion"], 1)
        text = op.beschreibung(p)
        self.assertIn("Kanten: 2 gewählt, 2 geeignet", text)

    def test_ungeeignete_kanten(self):
        faelle = [kante(kurve="spline"), kante(kurve="ellipse"), kante(blech=False), kante(flaechen=1), kante(frei=False), kante(dicke=1.0)]
        for k in faelle:
            p = op.erstelle(testvorlage(), {}, test_material(), [k])
            self.assertTrue(p["validation"]["errors"], k)
            self.assertFalse(op.ist_ausfuehrbar(p))

    def test_runde_kanten_sind_geeignet(self):
        for kurve in ("kreis", "bogen"):
            p = op.erstelle(testvorlage(), {}, test_material(), [kante(kurve=kurve)])
            self.assertFalse(p["validation"]["errors"], kurve)
            self.assertTrue(op.ist_ausfuehrbar(p))

    def test_dicken_und_laengenbereich(self):
        v = testvorlage()
        v["constraints"].update({"thicknessMin": 0.8, "edgeLengthMin": 1000})
        p = op.erstelle(v, {}, test_material(), [kante()])
        t = " ".join(p["validation"]["errors"])
        self.assertIn("Mindestlänge", t)
        self.assertIn("Vorlagenbereich", t)

    def test_ohne_material_und_ohne_kante(self):
        p = op.erstelle(testvorlage(), {}, None, [])
        self.assertTrue(any("Materialprofil" in e for e in p["validation"]["errors"]))
        self.assertTrue(any("Keine Kante" in e for e in p["validation"]["errors"]))

    def test_ohne_k_faktor_keine_theorie(self):
        m = test_material(kFactor=None)
        p = op.erstelle(testvorlage(), {}, m, [kante()])
        self.assertIsNone(p["theory"]["zugabe"])
        self.assertTrue(op.ist_ausfuehrbar(p))

    def test_zu_kurzer_schenkel_fuer_radius(self):
        from spengler_cad.core.template_engine import vorlage_aus_kurzschrift
        v = vorlage_aus_kurzschrift("kurz", "90r10 1")
        p = op.erstelle(v, {}, test_material(), [kante()])
        self.assertTrue(any("Biegeradien" in e for e in p["validation"]["errors"]))


if __name__ == "__main__":
    unittest.main()

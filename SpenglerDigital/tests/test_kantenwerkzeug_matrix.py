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


class BauplanEigeneGeometrie(unittest.TestCase):
    """«Kanten bearbeiten» mit Bauweise «eigene Geometrie»: Eignung und Analyse im Bauplan – reine Logik, KEIN Fusion-Test."""
    def plan(self, bauweise="eigen", prototyp=False, mat=None, **kante_):
        from spengler_cad.core import operation_plan as op
        from test_operation_plan import kante
        from test_templates import testvorlage
        from _basis import test_material
        m = mat if mat is not None else test_material(innerRadius=1.0, kFactor=0.44)
        return op, op.erstelle(testvorlage(), {"H": 25}, m, [kante(**kante_)], bauweise, prototyp)

    def test_eben_gerade_eigen_ausfuehrbar_mit_analyse(self):
        op, p = self.plan()
        self.assertTrue(op.ist_ausfuehrbar(p), p["validation"]["errors"])
        t = op.beschreibung(p)
        self.assertIn("Bauweise: eigene Geometrie", t)
        self.assertIn("gerade Kante auf eben Fläche", t)
        self.assertIn("Abwicklung: exakt", t)

    def test_zylinder_nur_mit_freigegebenen_prototypen(self):
        op, p = self.plan(flaeche="zylinder")
        self.assertFalse(op.ist_ausfuehrbar(p))
        self.assertIn("gesperrter Prototyp", " ".join(p["validation"]["errors"]))
        op, p = self.plan(prototyp=True, flaeche="zylinder")
        self.assertTrue(op.ist_ausfuehrbar(p), p["validation"]["errors"])

    def test_bogenkante_mit_begruendung_abgelehnt(self):
        op, p = self.plan(prototyp=True, kurve="bogen")
        self.assertFalse(op.ist_ausfuehrbar(p))
        self.assertIn("Torus", " ".join(p["validation"]["errors"]))
        self.assertIn("keine exakte Abwicklung", op.beschreibung(p))

    def test_ohne_k_faktor_oder_radius_keine_eigene_geometrie(self):
        from _basis import test_material
        op, p = self.plan(mat=test_material(innerRadius=1.0, kFactor=None))
        self.assertIn("K-Faktor", " ".join(p["validation"]["errors"]))
        op, p = self.plan(mat=test_material(innerRadius=0.0, kFactor=0.4))
        self.assertIn("Innenradius", " ".join(p["validation"]["errors"]))

    def test_profilteil_ohne_blech_und_regression_nativ(self):
        op, p = self.plan(blech=False, profilteil=True)
        self.assertTrue(op.ist_ausfuehrbar(p), "Profilteil der eigenen Geometrie braucht keinen Fusion-Blechkörper")
        op, p = self.plan(bauweise="nativ")
        self.assertTrue(op.ist_ausfuehrbar(p), "Regression: native Bauweise auf ebener gerader Kante unverändert")
        op, p = self.plan(bauweise="nativ", blech=False, profilteil=True)
        self.assertFalse(op.ist_ausfuehrbar(p))


class DokuSynchron(unittest.TestCase):
    def test_statusdokument_aktuell(self):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs"))
        import status_tabellen as st
        with open(st.PFAD, encoding="utf-8") as f:
            t = f.read()
        self.assertEqual(st.aktualisieren(t), t, "Matrix/Analyse geändert → python3 docs/status_tabellen.py ausführen")
        for name in st.BLOECKE:
            self.assertIn("<!-- AUTO:%s -->" % name, t)

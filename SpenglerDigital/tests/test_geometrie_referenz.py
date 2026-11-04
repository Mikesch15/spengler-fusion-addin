"""Zentrale Geometrie-Referenz und Unterstützungsmatrix – reine Rechnung, KEIN Fusion-Test."""
import math
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import geometrie_referenz as gr
from spengler_cad.core import unterstuetzung as u
from spengler_cad.details import frames


def nah(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


class Referenz(unittest.TestCase):
    def test_lokaler_rahmen_nicht_global_z(self):
        n = gr.zylinder_normale((0, 0, 0), (0, 0, 1), (100, 0, 50))     # Zylinder R100 um Z: Normale radial = +X
        self.assertTrue(nah(n, (1, 0, 0)))
        r = gr.referenz("zylinder", (100, 0, 50), n, (0, 0, 1))["rahmen"]
        self.assertTrue(nah(r["z"], (1, 0, 0)), "z = lokale Normale, nicht Welt-Z")
        self.assertTrue(nah(r["x"], (0, 0, 1)))
        self.assertTrue(nah(r["y"], frames.kreuz(r["z"], r["x"])))

    def test_seite_und_tangente_wird_orthogonalisiert(self):
        r = gr.referenz("eben", (0, 0, 0), (0, 0, 2), (1, 0, 0.5), seite=-1)["rahmen"]
        self.assertTrue(nah(r["x"], (1, 0, 0)))
        self.assertTrue(nah(r["z"], (0, 0, -1)), "Gegenseite")
        self.assertEqual(gr.referenz("eben", (0, 0, 0), (0, 0, 1))["rahmen"]["z"], [0.0, 0.0, 1.0], "ohne Tangente reproduzierbar")

    def test_kegel_normale(self):
        n = gr.kegel_normale((0, 0, 0), (0, 0, 1), 30, (0.5, 0, math.sqrt(3) / 2))   # Mantellinie unter 30° zur Achse
        self.assertAlmostEqual(gr.winkel_grad(n, (0.5, 0, math.sqrt(3) / 2)), 90.0, 6)
        self.assertGreater(n[0], 0)

    def test_klasse(self):
        self.assertEqual(gr.klasse(gr.referenz("eben", (0, 0, 0), (0, 0, 1), kurve_typ="linie")), "eben_gerade")
        self.assertEqual(gr.klasse(gr.referenz("eben", (0, 0, 0), (0, 0, 1), kurve_typ="bogen")), "gekruemmte_kante")
        self.assertEqual(gr.klasse(gr.referenz("kugel", (0, 0, 0), (0, 0, 1))), "freiform")
        with self.assertRaises(ValueError):
            gr.referenz("blob", (0, 0, 0), (0, 0, 1))

    def test_veraltete_auswahl(self):
        alt = gr.referenz("eben", (0, 0, 0), (0, 0, 1), kennung={"flaeche": "f1", "flaeche_mm2": 6000.0, "kante": "k1", "kante_mm": 100.0})
        self.assertEqual(gr.ist_veraltet(alt, alt), [])
        neu = gr.referenz("zylinder", (0, 0, 0), (0, 0, 1), kennung={"flaeche": "f2", "flaeche_mm2": 5000.0, "kante": "k1", "kante_mm": 100.0})
        g = " ".join(gr.ist_veraltet(alt, neu))
        self.assertIn("Fläche ist eine andere", g)
        self.assertIn("Flächentyp geändert", g)
        self.assertIn("Flächengrösse geändert", g)
        self.assertIn("existiert nicht mehr", gr.ist_veraltet(alt, None)[0])


class Abwickelbarkeit(unittest.TestCase):
    def test_einordnung(self):
        self.assertEqual(gr.abwickelbarkeit(["eben", "zylinder", "kegel"])[0], "exakt")
        self.assertEqual(gr.abwickelbarkeit(["eben", "kugel"])[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["torus"])[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["freiform"], 1e-10)[0], "naeherung")
        self.assertEqual(gr.abwickelbarkeit(["freiform"], 1e-3)[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["freiform"])[0], "nicht", "ohne Messung keine Aussage")
        self.assertEqual(gr.abwickelbarkeit(["unbekannt"])[0], "nicht")
        self.assertAlmostEqual(gr.gauss(0.01, 0.0), 0.0)                     # Zylinder: eine Hauptkrümmung 0


class Versatz(unittest.TestCase):
    def test_richtung_eindeutig(self):
        eben = gr.referenz("eben", (0, 0, 0), (0, 0, 1), (1, 0, 0), kurve_typ="linie")
        richtung, text = gr.versatz_definition(eben, 5, "tangential")
        self.assertTrue(nah(richtung, (0, 1, 0)))
        self.assertIn("lokale Richtung", text)
        self.assertIn("+5 mm", text)
        zyl = gr.referenz("zylinder", (100, 0, 0), (1, 0, 0), (0, 0, 1), kurve_typ="linie")
        with self.assertRaises(ValueError) as cm:
            gr.versatz_definition(zyl, 5, "tangential")
        self.assertIn("nur an Kanten EBENER", str(cm.exception))
        self.assertTrue(nah(gr.versatz_definition(zyl, 2, "radial")[0], (1, 0, 0)))
        with self.assertRaises(ValueError):
            gr.versatz_definition(eben, 2, "radial")


class Matrix(unittest.TestCase):
    def test_vollstaendig_und_pruefung(self):
        for op, felder in u.MATRIX.items():
            self.assertEqual(set(felder), set(u.KLASSEN), op)
            for k, (s, grund) in felder.items():
                self.assertIn(s, ("ja", "eingeschraenkt", "nein"))
                if s == "nein":
                    self.assertTrue(grund, "%s/%s: Ablehnung braucht einen Grund" % (op, k))
        self.assertIsNone(u.pruefen("flansch", "eben_gerade"))
        self.assertIn("nicht unterstützt", u.pruefen("flansch", "gekruemmte_kante"))
        self.assertIn("nicht ungefragt verformt", u.pruefen("detail_anpassen", "zylinder"))
        t = u.als_markdown()
        self.assertIn("| Versatz | implementiert | nicht unterstützt |", t)


if __name__ == "__main__":
    unittest.main()


class DokuSynchron(unittest.TestCase):
    def test_statusdokument_enthaelt_die_aktuelle_matrix(self):
        import os
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "ANFORDERUNGEN_STATUS.md")
        with open(pfad, encoding="utf-8") as f:
            self.assertIn(u.als_markdown(), f.read(), "Matrix geändert → Statusdokument neu erzeugen")

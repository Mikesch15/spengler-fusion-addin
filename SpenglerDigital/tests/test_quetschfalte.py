"""Quetschfalte an der Ecke zweier Aufkantungen: Rechnung und rechnerisches Falten (ohne Fusion)."""
import math
import unittest

from spengler_cad.core import quetschfalte as q


class Ecke90(unittest.TestCase):
    def test_klassische_ecke(self):
        z = q.zuschnitt(90.0, 30.0)
        self.assertAlmostEqual(z["gamma1"], 90.0)
        self.assertAlmostEqual(z["gamma2"], 90.0)
        self.assertAlmostEqual(z["psi"], 90.0, msg="Überschuss = 90° bei der rechtwinkligen Ecke")
        self.assertAlmostEqual(z["ell"], 30.0)
        self.assertAlmostEqual(z["hoehe2"], 30.0)
        self.assertAlmostEqual(z["P1"][0], 0.0, places=9)
        self.assertAlmostEqual(z["P1"][1], -30.0)
        self.assertAlmostEqual(z["P2"][0], -30.0)
        self.assertAlmostEqual(z["C"][0], -30.0)
        self.assertAlmostEqual(z["C"][1], -30.0, msg="Spitze im Quadrat h × h")
        self.assertAlmostEqual(z["m"], 30.0)

    def test_falten_geschlossen(self):
        r = q.falten_pruefen(q.zuschnitt(90.0, 30.0))
        self.assertTrue(r["ok"], r)
        self.assertLess(r["abweichung_mm"], 1e-9)

    def test_dreieck_auf_wand(self):
        z = q.zuschnitt(90.0, 30.0)
        t1 = q.quetschfalte_3d(z, "wand1")
        self.assertAlmostEqual(t1["P"][2], 30.0)
        self.assertAlmostEqual(t1["C"][0], 30.0, msg="auf Wand 1 (entlang e1) gedrückt")
        t2 = q.quetschfalte_3d(z, "wand2")
        self.assertAlmostEqual(t2["C"][1], 30.0)


class AndereWinkel(unittest.TestCase):
    def test_stumpfe_ecke_laeuft_symmetrisch(self):
        for beta in (60.0, 75.0, 105.0, 120.0, 135.0):
            z = q.zuschnitt(beta, 25.0)
            r = q.falten_pruefen(z)
            self.assertTrue(r["ok"], (beta, r))
            self.assertAlmostEqual(z["gamma1"], z["gamma2"], places=6, msg="Symmetrie bei gleichen Aufkantungswinkeln")
            self.assertAlmostEqual(z["hoehe1"], z["hoehe2"], places=6)
            self.assertAlmostEqual(z["gamma1"] + z["gamma2"] + z["beta"] + z["psi"], 360.0, places=6)

    def test_schraege_aufkantung_gleich_beidseitig(self):
        z = q.zuschnitt(90.0, 30.0, 100.0, 100.0)               # beide Aufkantungen 100° (leicht nach aussen geneigt)
        self.assertTrue(q.falten_pruefen(z)["ok"])
        self.assertAlmostEqual(z["gamma1"], z["gamma2"], places=6)

    def test_asymmetrisch_wird_abgelehnt_nicht_geraten(self):
        with self.assertRaises(q.QuetschfalteFehler) as cm:
            q.zuschnitt(90.0, 30.0, 90.0, 105.0)                # Dachneigung: eine Aufkantung 90°, die andere 105°
        self.assertIn("Asymmetrisch", str(cm.exception))


class Eingaben(unittest.TestCase):
    def test_ungueltig(self):
        for args in ((5.0, 30.0), (175.0, 30.0), (90.0, 0.0), (90.0, -3.0)):
            with self.assertRaises(q.QuetschfalteFehler):
                q.zuschnitt(*args)
        with self.assertRaises(q.QuetschfalteFehler):
            q.ecke_geometrie(90.0, 10.0, 90.0)

    def test_richtung_von_der_sichtseite(self):
        # Blick von der Sichtseite auf die Ecke: Wand 2 (an e2, gegen den Uhrzeigersinn nach e1) liegt rechts – per Vektorrechnung belegt
        self.assertEqual(q.richtung_zu_wand("hinten rechts"), "wand2")
        self.assertEqual(q.richtung_zu_wand("Hinten links"), "wand1")
        with self.assertRaises(q.QuetschfalteFehler):
            q.richtung_zu_wand("oben")

    def test_svg_enthaelt_faltlinien(self):
        s = q.svg_zuschnitt(q.zuschnitt(90.0, 30.0))
        self.assertIn("<svg", s)
        self.assertIn("#c0392b", s, "Faltlinie der Quetschfalte rot")
        self.assertIn("Überschuss ψ 90.0°", s)

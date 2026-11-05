"""Profil-Engine (eigene Geometrie, Prototyp 2): Querschnitt, Selbstschnitt, Abwicklung, Rückvergleich – reine Rechnung, KEIN Fusion-Test."""
import math
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import profil_engine as pe

T, RI, K = 1.0, 1.0, 0.5


def flansch(w=90.0, L=20.0, r=None):
    return {"typ": "flansch", "winkel": w, "laenge": L, "radius": r}


class Querschnitt(unittest.TestCase):
    def test_aufkantung_90_exakt(self):
        q = pe.querschnitt(pe.ops_zu_profil([flansch()], T, RI), T, RI, K)
        rm = RI + T / 2
        # Mittellinie: Bogen rm·π/2 + gerader Schenkel 20 − Rückversatz rm
        self.assertAlmostEqual(q["mittellinie_mm"], rm * math.pi / 2 + (20 - rm), 9)
        self.assertEqual([f[0] for f in q["flaechen"]], ["zylinder", "zylinder", "eben"])
        self.assertEqual(sorted(f[1] for f in q["flaechen"] if f[1]), [RI, RI + T])
        self.assertEqual(pe.pruefen(q), [])
        u = q["umriss"]
        for a, b in zip(u, u[1:] + u[:1]):          # geschlossen: jedes Element endet, wo das nächste beginnt
            ende = a[2] if a[0] == "linie" else a[3]
            self.assertLess(math.hypot(ende[0] - b[1][0], ende[1] - b[1][1]), 1e-9)

    def test_einfach_und_doppelfalz(self):
        einfach = [flansch(90, 25), {"typ": "umschlag", "winkel": 180, "laenge": 10, "radius": 0.5}]
        q = pe.querschnitt(pe.ops_zu_profil(einfach, T, RI), T, RI, K)
        self.assertEqual(pe.pruefen(q), [], "Falz mit Abstand 2 × 0.5 mm kollidiert nicht")
        doppel = einfach + [{"typ": "umschlag", "winkel": 180, "laenge": 8, "radius": 0.5}]
        q2 = pe.querschnitt(pe.ops_zu_profil(doppel, T, RI), T, RI, K)
        self.assertEqual(len(q2["biegungen"]), 3)
        self.assertGreater(q2["mittellinie_mm"], q["mittellinie_mm"])

    def test_selbstschnitt_wird_erkannt(self):
        ops = [flansch(90, 20), flansch(170, 30, 0.5), flansch(170, 30, 0.5)]
        q = pe.querschnitt(pe.ops_zu_profil(ops, T, RI), T, RI, K)
        self.assertTrue(pe.pruefen(q), "Zickzack, der in sich zurückläuft, schneidet sich")

    def test_ungueltig(self):
        with self.assertRaises(pe.ProfilFehler):
            pe.ops_zu_profil([flansch(90, 20, 0.0)], T, RI)
        with self.assertRaises(pe.ProfilFehler):
            pe.ops_zu_profil([dict(flansch(), versatz=5)], T, RI)
        with self.assertRaises(pe.ProfilFehler):
            pe.querschnitt(pe.ops_zu_profil([flansch(90, 0.5)], T, RI), T, RI, K)   # Schenkel kürzer als Biegeradius


class Prototyp2(unittest.TestCase):
    """Zylindersegment R 100 / 90° + Aufkantung 90° 20 mm: ein Profil, exakte Abwicklung, Rückvergleich."""
    def teil(self, k=K):
        p = pe.anhaengen(pe.segment_profil(100.0, 90.0, T), [flansch(90, 20)], T, RI)
        return pe.querschnitt(p, T, RI, k)

    def test_abwicklung_und_rueckvergleich(self):
        q = self.teil()
        soll = (100 + T / 2) * math.pi / 2 + (RI + T / 2) * math.pi / 2 + (20 - (RI + T / 2))
        self.assertAlmostEqual(q["zuschnitt"], soll, 9, "k = 0.5: Abwicklung = Mittellinie")
        z = pe.abwicklung(q, 80.0)
        self.assertEqual(z["grenzen"], (0.0, 0.0, q["zuschnitt"], 80.0))
        self.assertEqual(len(z["biegelinien"]), 2)
        v = q["mittellinie_mm"] * T * 80.0
        r = pe.rueckvergleich(q, 80.0, v + 0.001, [100.0, 101.0, 1.0, 2.0])
        self.assertTrue(r["ok"], r["texte"])
        self.assertFalse(pe.rueckvergleich(q, 80.0, v * 1.01)["ok"], "1 % Volumenabweichung ist kein Rundungsfehler")
        self.assertFalse(pe.rueckvergleich(q, 80.0, None, [100.0, 101.0])["ok"], "fehlende Biegeradien im 3D-Körper")

    def test_k_faktor_modell_getrennt(self):
        q = self.teil(k=0.33)
        r = pe.rueckvergleich(q, 80.0, q["mittellinie_mm"] * T * 80.0)
        self.assertTrue(r["ok"])
        self.assertLess(r["modell_diff"], 0, "k < 0.5: Abwicklung kürzer als Mittellinie – Modell, kein Fehler")

    def test_umgekehrt_und_vorzeichen(self):
        p = pe.segment_profil(100.0, 90.0, T)
        self.assertEqual([x.get("winkel") for x in pe.umgekehrt(p) if x["typ"] == "biegung"], [-90.0])
        a = pe.querschnitt(pe.anhaengen(p, [flansch(90, 20)], T, RI, -1.0), T, RI, K)
        self.assertEqual(a["biegungen"][1]["winkel"], -90.0)


if __name__ == "__main__":
    unittest.main()


class Begriffe(unittest.TestCase):
    """Korrektur 0.4.49 Phase 4: Zuschnitt ist THEORETISCH (Modell, k, ri angegeben), nicht «exakt», nicht praktisch verifiziert."""
    def test_beschreibung_und_rueckvergleich(self):
        q = pe.querschnitt(pe.ops_zu_profil([flansch()], T, RI), T, RI, 0.44)
        b = pe.abwicklung(q, 100.0)["beschreibung"]
        for wort in ("THEORETISCHER Zuschnitt", "k 0.44", "ri 1.00", "NICHT praktisch verifiziert", "mathematisch abwickelbar"):
            self.assertIn(wort, b)
        self.assertNotIn("exakt", b)
        self.assertIn("Theoretischer Zuschnitt", pe.rueckvergleich(q, 100.0)["texte"][0])


class Kontur(unittest.TestCase):
    """Korrektur 0.4.49 Phase 5: Berührung, kollineare Überlappung, knappe Abstände, grosse Radien."""
    def loop(self, pts):
        return [("linie", pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]

    def test_kollineare_ueberlappung(self):
        u = self.loop([(0, 0), (10, 0), (10, 2), (6, 2), (6, 0), (4, 0), (4, 2), (0, 2)])
        self.assertTrue(pe.selbstschnitt(u))

    def test_beruehrung_in_einem_punkt_und_toleranzgrenze(self):
        self.assertTrue(pe.selbstschnitt(self.loop([(0, 0), (10, 0), (10, 3), (6, 3), (5, 0.0), (4, 3), (0, 3)])), "Spitze berührt die Grundlinie")
        self.assertTrue(pe.selbstschnitt(self.loop([(0, 0), (10, 0), (10, 3), (6, 3), (5, 0.005), (4, 3), (0, 3)])), "0.005 mm < Toleranz")
        self.assertEqual(pe.selbstschnitt(self.loop([(0, 0), (10, 0), (10, 3), (6, 3), (5, 0.05), (4, 3), (0, 3)])), [], "0.05 mm Abstand ist frei")

    def test_enge_biegung_ist_kein_kontakt(self):
        ops = [flansch(90, 25), {"typ": "umschlag", "winkel": 180, "laenge": 10, "radius": pe.RI_MIN}]
        q = pe.querschnitt(pe.ops_zu_profil(ops, T, RI), T, RI, K)
        self.assertEqual(pe.selbstschnitt(q["umriss"]), [], "kleinster Radius: Lagen 0.1 mm auseinander, Nachbarsegmente der Biegung zählen nicht")

    def test_grosser_radius_fein_geteilt(self):
        u = pe.querschnitt(pe.segment_profil(100.0, 90.0, T), T, RI, K)["umriss"]
        p = pe._polygon(u)
        bogen = [el for el in u if el[0] == "bogen" and el[5] > 99]
        c, r = bogen[0][4], bogen[0][5]
        # grösste Abweichung der Polygonkante vom echten Kreis (Sehnenmitte)
        fehler = max(r - math.hypot((a[0] + b[0]) / 2 - c[0], (a[1] + b[1]) / 2 - c[1]) for a, b in zip(p, p[1:])
                     if abs(math.hypot(a[0] - c[0], a[1] - c[1]) - r) < 1e-6 and abs(math.hypot(b[0] - c[0], b[1] - c[1]) - r) < 1e-6)
        self.assertLessEqual(fehler, pe.KONTAKT_TOL / 2 + 1e-9)

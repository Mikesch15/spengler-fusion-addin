"""Bewertung der Live-Test-Messwerte (reine Zahlenlogik, ohne Fusion). Die Zahlen stammen aus einer Handrechnung am Test-Blech 100 × 60 × 1 mm."""
import unittest

from _basis import DatenTest  # noqa: F401

from spengler_cad.core import livetest_messung as m


def blech(vol=6000.0, lo=(0, 0, 0), hi=(100, 60, 1), flaechen=6):
    return {"vol": vol, "min": lo, "max": hi, "flaechen": flaechen, "kanten": 12}


class Flansch(unittest.TestCase):
    def test_guter_flansch_nach_oben(self):
        vor = blech()
        nach = blech(8050, (0, -1, 0), (100, 60, 20), 12)                      # +2050 mm³, Höhe 20 über dem Blech
        s, t = m.pruefe_flansch(vor, nach, 90, 20, 1.0, 100)
        self.assertEqual(s, "ok", t)

    def test_falsche_richtung_ist_fehler(self):
        vor = blech()
        nach = blech(8050, (0, -1, -19), (100, 60, 1), 12)                     # Flansch zeigt nach unten statt nach oben
        s, t = m.pruefe_flansch(vor, nach, 90, 20, 1.0, 100)
        self.assertEqual(s, "fehler")
        self.assertIn("Richtung", t)
        s, _ = m.pruefe_flansch(vor, nach, -90, 20, 1.0, 100)
        self.assertEqual(s, "ok", "mit Winkel −90 ist «nach unten» richtig")

    def test_dicke_verdoppelt_ist_fehler(self):
        vor = blech()
        nach = blech(6000 + 6000 + 2000, (0, 0, 0), (100, 60, 20), 12)       # zusätzlich die ganze Blechfläche doppelt
        s, t = m.pruefe_flansch(vor, nach, 90, 20, 1.0, 100)
        self.assertEqual(s, "fehler")
        self.assertIn("Volumen", t)

    def test_kein_flansch_ist_fehler(self):
        s, _ = m.pruefe_flansch(blech(), blech(), 90, 20, 1.0, 100)
        self.assertEqual(s, "fehler")

    def test_abweichung_ist_warnung(self):
        vor = blech()
        nach = blech(8050, (0, -1, 0), (100, 60, 12), 12)                       # Höhe 11 statt 20, Volumen stimmt
        s, _ = m.pruefe_flansch(vor, nach, 90, 20, 1.0, 100)
        self.assertEqual(s, "warnung")

    def test_winkel_45_hoehe_ist_sinus(self):
        vor = blech()
        nach = blech(7550, (0, -1, 0), (100, 60, 11.6), 12)                     # 15 mm schräg: Höhe 10.6 + Blech
        s, t = m.pruefe_flansch(vor, nach, 45, 15, 1.0, 100)
        self.assertEqual(s, "ok", t)


class Umschlag(unittest.TestCase):
    def test_guter_umschlag(self):
        vor = blech()
        nach = blech(7050, (0, -0.5, 0), (100, 60, 2.1), 14)                    # doppelt dick, +1050 mm³ (10 mm × 100 mm × 1 mm + Bogen)
        s, t = m.pruefe_umschlag(vor, nach, 10, 1.0, 100)
        self.assertEqual(s, "ok", t)

    def test_umschlag_fehlt_ist_fehler(self):
        s, _ = m.pruefe_umschlag(blech(), blech(6000, (0, 0, 0), (100, 60, 1)), 10, 1.0, 100)
        self.assertEqual(s, "fehler")

    def test_umschlag_ragt_weit_heraus_ist_warnung(self):
        vor = blech()
        nach = blech(7050, (0, -9.0, 0), (100, 60, 2.1), 14)                    # Saum steht 9 mm über die Kante (nicht umgeschlagen, nur verlängert)
        s, _ = m.pruefe_umschlag(vor, nach, 10, 1.0, 100)
        self.assertEqual(s, "warnung")


class Versatz(unittest.TestCase):
    def _bau(self, y_min, vol):
        vor = blech()
        return {"vor": vor, "nach": blech(vol, (0, y_min, 0), (100, 60, 20), 12)}

    def test_rueckversatz_plus5(self):
        ohne = self._bau(-1.0, 8050)
        mit = self._bau(4.0, 8050 - 5 * 100 * 1)                                # Kante 5 mm weiter innen, 500 mm³ weniger
        s, t = m.pruefe_versatz(ohne, mit, 5.0, 1.0, 100, 20)
        self.assertEqual(s, "ok", t)

    def test_vorversatz_minus5(self):
        ohne = self._bau(-1.0, 8050)
        mit = self._bau(-6.0, 8050 + 500)
        self.assertEqual(m.pruefe_versatz(ohne, mit, -5.0, 1.0, 100, 20)[0], "ok")

    def test_ohne_wirkung_und_falsche_richtung(self):
        ohne = self._bau(-1.0, 8050)
        self.assertEqual(m.pruefe_versatz(ohne, self._bau(-1.0, 8050), 5.0, 1.0, 100, 20)[0], "fehler")
        self.assertEqual(m.pruefe_versatz(ohne, self._bau(-6.0, 8550), 5.0, 1.0, 100, 20)[0], "fehler", "Richtung vertauscht")

    def test_dicke_verdoppelt(self):
        ohne = self._bau(-1.0, 8050)
        mit = self._bau(-6.0, 8050 + 6000)                                      # Vorversatz, aber das ganze Blech doppelt
        s, t = m.pruefe_versatz(ohne, mit, -5.0, 1.0, 100, 20)
        self.assertEqual(s, "fehler")
        self.assertIn("Dicke verdoppelt", t)


class RadiusGehrungAbwicklung(unittest.TestCase):
    def test_radius_muss_wirken(self):
        a = {"vor": blech(), "nach": blech(8050)}
        b = {"vor": blech(), "nach": blech(8066)}
        self.assertEqual(m.pruefe_radius(a, b, 3.0)[0], "ok")
        self.assertEqual(m.pruefe_radius(a, a, 3.0)[0], "warnung")

    def test_gehrung(self):
        einzeln = blech(8000, flaechen=18)
        self.assertEqual(m.pruefe_gehrung(einzeln, blech(7990, flaechen=20))[0], "ok")
        self.assertEqual(m.pruefe_gehrung(einzeln, blech(8000, flaechen=18))[0], "warnung")

    def test_abwicklung(self):
        s, t = m.pruefe_abwicklung(100.0, 78.6, 100.0, 60.0, 20.0, 1.0, 1.0, 0.44)
        self.assertEqual(s, "ok", t)
        self.assertEqual(m.pruefe_abwicklung(100.0, 60.0, 100.0, 60.0, 20.0, 1.0)[0], "fehler", "Flansch fehlt in der Abwicklung")
        self.assertEqual(m.pruefe_abwicklung(100.0, 74.0, 100.0, 60.0, 20.0, 1.0)[0], "warnung")

    def test_text(self):
        self.assertIn("Volumen 6000 mm³, Ausdehnung 100.0 × 60.0 × 1.0 mm", m.text(blech()))


if __name__ == "__main__":
    unittest.main()

"""Live-Test: Auswertung (ohne Fusion) und – mit der Attrappe – dass jeder Schritt einen Fehler abfängt, statt den Test abzubrechen."""
import unittest

import _basis  # noqa: F401
from spengler_cad.core import livetest_bericht as b


class Bericht(unittest.TestCase):
    erg = [{"name": "A", "status": "ok", "detail": "fein", "dauer": 0.5},
           {"name": "B", "status": "warnung", "detail": "Gehrung nicht geschnitten\nzweite Zeile", "dauer": 1.0},
           {"name": "C", "status": "uebersprungen", "detail": "", "dauer": None}]

    def test_status_warnung_ist_kein_fehler(self):
        self.assertEqual(b.gesamtstatus(self.erg), "ok")
        self.assertEqual(b.gesamtstatus(self.erg + [{"name": "D", "status": "fehler", "detail": "x"}]), "fehler")

    def test_unbekannter_status_zaehlt_als_fehler(self):
        self.assertEqual(b.zaehlen([{"name": "X", "status": "komisch"}])["fehler"], 1)

    def test_text_und_meldung(self):
        t = b.text(self.erg, "Kopf")
        self.assertIn("Kopf", t)
        self.assertIn("⚠ 2. B", t)
        self.assertIn("zweite Zeile", t)
        self.assertEqual(b.kurz(self.erg), "1 ok, 1 Warnungen, 0 Fehler, 1 übersprungen")
        self.assertIn("Gehrung nicht geschnitten", b.meldung(self.erg))
        self.assertIn("Alle 1", b.meldung([self.erg[0]]))


class FusionAttrappe(unittest.TestCase):
    def test_schritte_fangen_fehler_ab(self):
        from spengler_cad.diagnostics import live_test
        self.assertGreaterEqual(len(live_test.SCHRITTE), 12)
        self.assertEqual(len({n for n, _, _ in live_test.SCHRITTE}), len(live_test.SCHRITTE))
        self.assertFalse(live_test.SCHRITTE[0][2])     # das Test-Blech selbst braucht kein Blech


if __name__ == "__main__":
    unittest.main()

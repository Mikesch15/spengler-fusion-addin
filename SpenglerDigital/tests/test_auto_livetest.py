"""Automatischer Live-Test: Auslöser-Logik (ohne Fusion)."""
import tempfile
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.diagnostics import auto_livetest as al


class AutoLivetest(unittest.TestCase):
    def test_einmal_je_version(self):
        d = tempfile.mkdtemp()
        self.assertTrue(al.noetig_nach_update(d))
        al.gelaufen(d, "update")
        self.assertFalse(al.noetig_nach_update(d))

    def test_anfrage_nur_bei_offen(self):
        self.assertTrue(al.anfrage_offen([{"test_id": "97.900", "status": "offen"}, {"test_id": "97.002", "status": "fehler"}]))
        self.assertFalse(al.anfrage_offen([{"test_id": "97.900", "status": "ok"}]))
        self.assertFalse(al.anfrage_offen(None))

    def test_nur_bei_leerlauf(self):
        self.assertTrue(al.untaetig(0, 600, "SelectCommand"))
        self.assertFalse(al.untaetig(0, 599, None), "weniger als 10 Minuten")
        self.assertFalse(al.untaetig(0, 9999, "SpenglerKantenBearbeiten"), "ein Befehl läuft")

    def test_erledigt_zeile(self):
        z = al.erledigt_zeile("40 ok, 1 Fehler")
        self.assertEqual((z["test_id"], z["status"]), ("97.900", "ok"))
        self.assertIn("40 ok", z["notiz"])

    def test_einstellungen_standard_an(self):
        from spengler_cad.core import models
        import inspect
        self.assertIn('"livetestNachUpdate": True, "livetestFern": True', inspect.getsource(models))

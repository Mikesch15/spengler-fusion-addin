"""Auftragsordner: Namenszerlegung, Einstellungen, Plan und Anlegen (mit Nachbau der Fusion-Ordner – NICHT die echte Daten-API)."""
import os
import shutil
import sys
import tempfile
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import auftrag

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
import adsk.core  # noqa: E402,F401
from spengler_cad.geometry import fusion_adapter as fa  # noqa: E402
from spengler_cad.storage.settings_service import EinstellungsFehler, Einstellungen  # noqa: E402


class Ordner(object):
    def __init__(self, name, eltern=None):
        self.name, self.parentFolder, self.kinder = name, eltern, []
        self.dataFolders = self

    def __iter__(self):
        return iter(self.kinder)

    def add(self, name):
        o = Ordner(name, self)
        self.kinder.append(o)
        return o


class NamenTest(unittest.TestCase):
    def test_zerlegen_wie_die_ordner_des_betriebs(self):
        self.assertEqual(auftrag.zerlegen("17642 Nägeligasse 1a, Bern"), ("17642", "Nägeligasse 1a, Bern"))
        self.assertEqual(auftrag.zerlegen("17990 Sonnhalde 1, 3063 Ittigen"), ("17990", "Sonnhalde 1, 3063 Ittigen"))
        for n in ("2026", "Modelle", "17642", "", None, "12 Zu kurz"):
            self.assertIsNone(auftrag.zerlegen(n), n)

    def test_aus_pfad_nimmt_den_innersten_auftragsordner(self):
        self.assertEqual(auftrag.aus_pfad(["Projekte", "2026", "18162 Sonneggweg 9, Bern", "Modelle"]), ("18162", "Sonneggweg 9, Bern"))
        self.assertIsNone(auftrag.aus_pfad(["Projekte", "2026"]))
        self.assertIsNone(auftrag.aus_pfad([]))

    def test_ordnername_pruefung(self):
        self.assertEqual(auftrag.ordnername("17999", " Testweg 1, Bern "), "17999 Testweg 1, Bern")
        for nr, obj in (("", "x"), ("12", "x"), ("abc", "x"), ("17999", ""), ("17999", "a/b"), ("17999", 'a:"b')):
            with self.assertRaises(auftrag.AuftragsFehler):
                auftrag.ordnername(nr, obj)

    def test_plan_mit_und_ohne_jahr(self):
        p = auftrag.plan(None, "17999", "Testweg 1, Bern", 2026)
        self.assertEqual((p["wurzel"], p["pfad"], p["unterordner"]), ("Projekte", ["2026", "17999 Testweg 1, Bern"], ["Modelle", "Pläne", "Export"]))
        p = auftrag.plan({"jahresordner": False, "unterordner": "A, B"}, "17999", "X", 2026)
        self.assertEqual((p["pfad"], p["unterordner"]), (["17999 X"], ["A", "B"]))
        with self.assertRaises(auftrag.AuftragsFehler):
            auftrag.pruefe_einstellung({"unterordner": ["A", "a"]})


class AnlegenTest(unittest.TestCase):
    def fusion(self, projektname="Projekte", mit_wurzel=False):
        wurzel = Ordner("root")
        projekt = type("P", (), {"name": projektname, "rootFolder": wurzel})()
        if mit_wurzel:
            wurzel.add("Projekte")
        app = type("App", (), {"data": type("D", (), {"activeProject": projekt})()})()
        self.alt = adsk.core.Application
        adsk.core.Application = type("A", (), {"get": staticmethod(lambda: app)})
        self.addCleanup(setattr, adsk.core.Application, "get", self.alt.get) if hasattr(self.alt, "get") else self.addCleanup(setattr, adsk.core, "Application", self.alt)
        return wurzel

    def test_projekt_ist_der_stamm(self):
        w = self.fusion("Projekte")
        pfad, hinweise = fa.auftrag_ordner_anlegen(auftrag.plan(None, "17999", "Testweg 1, Bern", 2026))
        self.assertEqual(pfad, "Projekte/2026/17999 Testweg 1, Bern")
        auftragsordner = w.kinder[0].kinder[0]
        self.assertEqual([k.name for k in auftragsordner.kinder], ["Modelle", "Pläne", "Export"])
        self.assertEqual(hinweise, [])

    def test_ordner_im_projekt_und_wiederverwendung(self):
        w = self.fusion("Betrieb", mit_wurzel=True)
        p = auftrag.plan(None, "17999", "Testweg 1, Bern", 2026)
        fa.auftrag_ordner_anlegen(p)
        pfad, hinweise = fa.auftrag_ordner_anlegen(p)
        self.assertEqual(len(w.kinder[0].kinder), 1, "Jahresordner nicht doppelt")
        self.assertEqual(len(w.kinder[0].kinder[0].kinder), 1, "Auftragsordner nicht doppelt")
        self.assertIn("gab es schon", hinweise[0])

    def test_stamm_fehlt(self):
        self.fusion("Betrieb")
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.auftrag_ordner_anlegen(auftrag.plan(None, "17999", "X", 2026))
        self.assertIn("nicht gefunden", str(cm.exception))


class EinstellungTest(unittest.TestCase):
    def test_standard_und_ungueltig(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        s = Einstellungen(tmp)
        e = s.laden()
        self.assertEqual(e["auftrag"]["unterordner"], ["Modelle", "Pläne", "Export"])
        e["auftrag"]["unterordner"] = ["a/b"]
        with self.assertRaises(EinstellungsFehler):
            s.speichern(e)
        e["auftrag"] = {"wurzelOrdner": "Aufträge", "jahresordner": False, "unterordner": ["Modelle"]}
        s.speichern(e)
        self.assertEqual(s.laden()["auftrag"]["wurzelOrdner"], "Aufträge")


if __name__ == "__main__":
    unittest.main()

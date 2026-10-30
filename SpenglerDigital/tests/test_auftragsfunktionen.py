"""Prüfung vor dem Export, Abkantliste, Bestellliste, Teilenummer-Label, lokaler Exportpfad (alles ohne Fusion)."""
import os
import shutil
import tempfile
import unittest

from _basis import DatenTest, test_material  # noqa: F401
from spengler_cad.core import auftrag
from spengler_cad.manufacturing import bend_list, bestellung, pruefung

OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "umschlag", "winkel": 180, "laenge": 6, "radius": 0.3}]


class PruefungTest(unittest.TestCase):
    def test_warnungen(self):
        teile = [{"name": "A", "nr": 1, "material": {"name": "m"}, "dicke": 0.7, "abwicklung": True, "operationen": OPS, "ri": 1.5},
                 {"name": "B", "nr": 1, "material": None, "dicke": 0.7, "abwicklung": False, "operationen": None, "ri": None},
                 {"name": "C", "nr": "", "material": {"name": "m"}, "dicke": 0.7, "abwicklung": True, "operationen": [], "ri": None}]
        w = " | ".join(pruefung.pruefe_teile(teile))
        self.assertIn("A, Schritt 2 (Umschlag): Schenkel 6.0 mm", w)
        self.assertIn("A, Schritt 2 (Umschlag): Innenradius 0.30 mm", w)
        self.assertNotIn("A, Schritt 1", w)
        self.assertIn("B: kein Materialprofil", w)
        self.assertIn("B: keine Fusion-Abwicklung", w)
        self.assertIn("C: keine Teilenummer", w)
        self.assertIn("Teilenummer 1 mehrfach vergeben: A, B", w)

    def test_schwellen_aus_einstellung(self):
        t = [{"name": "A", "nr": 1, "material": {"n": 1}, "dicke": 0.7, "abwicklung": True, "operationen": OPS[:1], "ri": 1.5}]
        self.assertEqual(pruefung.pruefe_teile(t, {"minSchenkel": 30}).__len__(), 1)
        self.assertEqual(pruefung.pruefe_teile(t, {"minSchenkel": 5}), [])


class AbkantlisteTest(unittest.TestCase):
    def test_html(self):
        h = bend_list.abkantliste_html([{"nr": 3, "name": "Ortgang <1>", "material": "Alu", "dicke": 0.7, "operationen": OPS, "ri": 1.5, "stueck": 4},
                                        {"nr": 4, "name": "Roh", "operationen": None}], "Testweg 1", "17999", "2026-10-30", "0.4")
        self.assertIn("Ortgang &lt;1&gt;", h)
        self.assertIn("<td>1</td><td>Abkanten</td><td>90°</td><td>25.0</td><td>1.50</td>", h)
        self.assertIn("<td>2</td><td>Umschlag</td><td>180°</td><td>6.0</td><td>0.30</td>", h)
        self.assertIn("Ohne Biegefolge", h)


class BestellungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.m = test_material()

    def teile(self, n):
        return [{"nr": i, "name": "T%d" % i, "materialId": self.m["id"], "flaeche": 200000.0, "breite": 400.0, "laenge": 500.0, "stueck": 2} for i in range(1, n + 1)]

    def test_mehrere_dokumente_zusammenfuehren(self):
        self.assertFalse(bestellung.teile_merken("", "Dok", self.teile(1), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Dach", self.teile(2), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Wand", self.teile(1), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Dach", self.teile(1), self.tmp))   # ersetzt den alten Stand von «Dach»
        b = bestellung.bestellung("17999", [self.m], None, self.tmp)
        self.assertEqual(b["dokumente"], ["Dach", "Wand"])
        self.assertEqual(len(b["teile"]), 2)
        self.assertEqual(b["erg"]["materialien"][0]["teile"], 4)
        self.assertIn("Wand – Stand", b["text"])

    def test_ohne_daten(self):
        b = bestellung.bestellung("555", [self.m], None, self.tmp)
        self.assertIsNone(b["erg"])
        self.assertIn("noch keine gespeicherten Teile", b["text"])


class LabelTest(unittest.TestCase):
    def test_teil_label(self):
        self.assertEqual(auftrag.teil_label("17642", 3), "17642-03")
        self.assertEqual(auftrag.teil_label("17642", 12, False), "12")
        self.assertEqual(auftrag.teil_label("", 3), "3")
        self.assertEqual(auftrag.teil_label("17642", ""), "")

    def test_lokaler_exportpfad(self):
        a = {"lokalBasis": os.path.join("C:", "Auftraege"), "jahresordner": True}
        p = auftrag.lokaler_exportpfad(a, "17642", "Nägeligasse 1a, Bern", 2026)
        self.assertEqual(p, os.path.join("C:", "Auftraege", "2026", "17642 Nägeligasse 1a, Bern", "Export"))
        self.assertEqual(auftrag.lokaler_exportpfad(dict(a, jahresordner=False), "17642", "X", 2026), os.path.join("C:", "Auftraege", "17642 X", "Export"))
        self.assertIsNone(auftrag.lokaler_exportpfad({}, "17642", "X", 2026), "ohne Basis kein eigener Pfad")
        self.assertIsNone(auftrag.lokaler_exportpfad(a, "", "", 2026))


if __name__ == "__main__":
    unittest.main()

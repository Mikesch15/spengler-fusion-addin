"""Vorlagen-Vorschau, Zeichnungen (Port kern/zeichnung.js), Stückliste (Port kern/auftrag.js) und Etiketten."""
import unittest

from _basis import DatenTest, test_material
from spengler_cad.core.bend_geometry import berechne
from spengler_cad.manufacturing import drawing, parts_list
from spengler_cad.storage.settings_service import Einstellungen, EinstellungsFehler
from test_templates import testvorlage


def teile():
    m = test_material()
    ohne_dichte = test_material(density=None, name="TEST ohne Dichte")
    return [{"nr": 1, "name": "Ortblech", "material": m, "breite": 333.3, "laenge": 2000, "stueck": 2, "flaeche": None},
            {"nr": 2, "name": "Rinne; links", "material": m, "breite": 250, "laenge": 1000, "stueck": 1, "flaeche": 240000.0, "notiz": "Muster"},
            {"nr": 3, "name": "Kappe", "material": ohne_dichte, "breite": 100, "laenge": 500, "stueck": 3, "flaeche": None}]


class ZeichnungTest(unittest.TestCase):
    def test_profil_und_abwicklung(self):
        S = lambda L: {"typ": "schenkel", "L": L}
        res = berechne(0, [S(100), {"typ": "biegung", "winkel": 90, "ri": None, "modus": "sharp"}, S(25),
                           {"typ": "biegung", "winkel": 180, "ri": None, "modus": "hem"}, S(7)], 0.7, 1, 0.4)
        svg = drawing.profil_svg(res)
        for teil in (">100<", ">25<", ">7<", ">B1<", ">B2<", ">A<", ">B<"):
            self.assertIn(teil, svg)
        a = drawing.abwicklung_svg(res)
        self.assertEqual(a.count('class="biegelinie"'), 2)
        self.assertIn("%.1f" % res["biegungen"][0]["pos"], a)

    def test_vorschau(self):
        svg, grund = drawing.vorlagen_vorschau(testvorlage(), test_material())
        self.assertIsNone(grund)
        self.assertIn(">25<", svg)
        self.assertIn(">Kante<", svg)
        self.assertNotIn(">100<", svg, "bestehendes Blech ohne Mass")
        svg, grund = drawing.vorlagen_vorschau(testvorlage())   # ohne Material: Skizze
        self.assertIsNotNone(svg)
        from spengler_cad.core.template_engine import vorlage_aus_kurzschrift
        svg, grund = drawing.vorlagen_vorschau(vorlage_aus_kurzschrift("ohne Wert", "90 H"))
        self.assertIsNone(svg)
        self.assertIn("H", grund)

    def test_kanten_profil_abwicklung_ab_kante(self):
        res, ab = drawing.kanten_profil([{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}], 0.7, 1, 0.4)
        self.assertGreater(ab, 0)
        b = res["biegungen"][0]
        self.assertAlmostEqual(b["von"], ab)   # Biegung beginnt genau am Ende des bestehenden Blechs


class StuecklisteTest(unittest.TestCase):
    def test_rechnung(self):
        sl = parts_list.stueckliste(teile())
        z = sl["zeilen"]
        self.assertAlmostEqual(z[0]["flaeche"], 1.3332)   # wie test/kern.test.js
        self.assertAlmostEqual(z[0]["gewicht"], 333.3 * 2000 * 2 / 1e6 * 0.7 * 7.2)   # wie kern/auftrag.js
        self.assertEqual(z[1]["flaecheQuelle"], "Abwicklung")
        self.assertAlmostEqual(z[1]["flaeche"], 0.24)
        self.assertIsNone(z[2]["gewicht"])
        self.assertEqual(len(sl["jeMaterial"]), 2)
        self.assertEqual(sl["jeMaterial"][0]["stueck"], 3)
        self.assertAlmostEqual(sl["jeMaterial"][0]["laufmeter"], 5)
        self.assertFalse(sl["summe"]["gewichtVollstaendig"])
        self.assertEqual(sl["summe"]["stueck"], 6)

    def test_csv_und_html(self):
        sl = parts_list.stueckliste(teile())
        csv = parts_list.stueckliste_csv(sl, [["Objekt", "Muster; Bern"]])
        self.assertTrue(csv.startswith('﻿Objekt;"Muster; Bern"'))
        self.assertIn('"Rinne; links"', csv)
        self.assertIn("1;Ortblech;TEST Blech 0.7;0.7;333.3;2000;2;4;1.333;Rechteck;", csv)
        h = parts_list.stueckliste_html(sl, "Objekt <x>", "A-1")
        self.assertIn("Objekt &lt;x&gt;", h)
        self.assertIn("Dichte fehlt", h)


class EtikettenTest(DatenTest):
    def test_bogen(self):
        e = Einstellungen().laden()["labels"]
        self.assertEqual(parts_list.etiketten_pruefen(e)[0], [])
        self.assertIn("24 Etiketten pro Bogen", parts_list.etiketten_pruefen(e)[1])
        seite, n = parts_list.etiketten_html(parts_list.stueckliste(teile()), e, "Muster", "A-1")
        self.assertEqual(n, 6)
        self.assertEqual(seite.count('class="etikett"'), 6)
        self.assertIn("1 · Ortblech <small>2/2</small>", seite)
        self.assertEqual(seite.count('class="bogen"'), 1)
        e2 = dict(e, spalten=1, zeilen=4)
        self.assertEqual(parts_list.etiketten_html(parts_list.stueckliste(teile()), e2)[0].count('class="bogen"'), 2)

    def test_ungueltig(self):
        e = Einstellungen().laden()
        for k, v in (("spalten", 0), ("spalten", 2.5), ("breite", -1), ("oben", -2), ("breite", 100)):
            x = dict(e["labels"], **{k: v})
            self.assertTrue(parts_list.etiketten_pruefen(x)[0], (k, v))
            e2 = dict(e, labels=x)
            with self.assertRaises(EinstellungsFehler):
                Einstellungen().speichern(e2)
            with self.assertRaises(ValueError):
                parts_list.etiketten_html(parts_list.stueckliste(teile()), x)

    def test_alte_einstellungen_bekommen_etiketten(self):
        s = Einstellungen()
        e = s.laden()
        del e["labels"], e["order"]
        from spengler_cad.storage import json_store
        json_store.schreiben(s.pfad, e)
        e = s.laden()
        self.assertEqual(e["labels"]["spalten"], 3)
        self.assertEqual(e["order"], {"objekt": "", "auftrag": ""})


if __name__ == "__main__":
    unittest.main()

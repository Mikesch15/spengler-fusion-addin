"""Zuschnittoptimierung: Python-Port gegen Referenzfälle aus dem echten App-JavaScript (js/29, v3.416)."""
import json
import os
import unittest

from _basis import FIXTURES, test_material
from spengler_cad.manufacturing import dxf_writer, material_calculator, nesting


def bl(laengen):
    return [{"nr": i + 1, "laenge": float(l)} for i, l in enumerate(laengen)]


class ReferenzTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "referenz_zuschnitt.json"), encoding="utf-8") as f:
            cls.ref = json.load(f)["faelle"]

    def test_packe_in_streifen(self):
        faelle = [f for f in self.ref if f["art"] == "packe"]
        self.assertGreaterEqual(len(faelle), 6)
        for f in faelle:
            r = nesting.packe_in_streifen(bl(f["laengen"]), f["L"], f["fuge"])
            e = f["erg"]
            self.assertEqual(r["optimal"], e["optimal"])
            if e["streifen"] is None:
                self.assertIsNone(r["streifen"])
                self.assertEqual([s["nr"] for s in r["zuLang"]], e["zuLang"])
                continue
            self.assertEqual([[s["nr"] for s in st["stuecke"]] for st in r["streifen"]], [st["nr"] for st in e["streifen"]], f)
            for a, b in zip(r["streifen"], e["streifen"]):
                self.assertAlmostEqual(a["rest"], b["rest"], places=9)

    def test_mehrere_abschnitte(self):
        for f in [x for x in self.ref if x["art"] == "mehrfach"]:
            r = nesting.packe_mehrere_abschnitte(bl(f["laengen"]), f["je"], f["fuge"])
            self.assertEqual([(a["laenge"], [[s["nr"] for s in st["stuecke"]] for st in a["streifen"]]) for a in r["abschnitte"]],
                             [(a["laenge"], [s["nr"] for s in a["streifen"]]) for a in f["erg"]["abschnitte"]])

    def test_mauerabdeckung_rueckmeldung(self):
        """Fall aus der App (11.09.2026): 4×4020 + 4×2510 auf 1000er Rolle, je Abschnitt 2 → 13'060 mm statt 16'080 mm."""
        r = nesting.packe_mehrere_abschnitte(bl([4020] * 4 + [2510] * 4), 2)
        self.assertEqual(sum(a["laenge"] for a in r["abschnitte"]), 13060)

    def test_quer(self):
        for f in [x for x in self.ref if x["art"] == "quer"]:
            n = nesting.streifen_je_abschnitt(f["B"], f["A"], f["fuge"])
            self.assertEqual(n, f["n"], f)
            self.assertAlmostEqual(nesting.rest_breite(f["B"], f["A"], n, f["fuge"]), f["rest"])


class PlanTest(unittest.TestCase):
    def test_format_plan_waehlt_kleinste_flaeche(self):
        gruppen = [{"breite": 330.0, "stuecke": bl([2000, 1800, 1500, 900, 600])}]
        formate = [{"breite": 1000, "laenge": 2000, "text": "Tafel 1000×2000"}, {"breite": 1250, "laenge": 2500, "text": "Tafel 1250×2500"},
                   {"breite": 670, "laenge": None, "text": "Rolle 670"}]
        p = nesting.format_plan(gruppen, formate)
        flaechen = [m["flaeche"] for m in p["moeglich"]]
        self.assertEqual(flaechen, sorted(flaechen))
        self.assertAlmostEqual(p["netto"], 330 * 6800 / 1e6)
        for m in p["moeglich"]:
            self.assertGreaterEqual(m["flaeche"], p["netto"] - 1e-9)
            blaetter = nesting.lage(m)
            self.assertEqual(nesting.kollisionen(blaetter), [], m["format"]["text"])
            self.assertEqual(sum(len(b["rechtecke"]) for b in blaetter), 5)

    def test_zu_breit_zu_lang(self):
        p = nesting.format_plan([{"breite": 1100.0, "stuecke": bl([500])}], [{"breite": 1000, "laenge": 2000}])
        self.assertIsNone(p["bestes"])
        self.assertEqual(len(p["zuSchmal"]), 1)
        p = nesting.format_plan([{"breite": 300.0, "stuecke": bl([2500])}], [{"breite": 1000, "laenge": 2000}])
        self.assertEqual(len(p["zuKurz"]), 1)

    def test_rand_und_fuge_ohne_kollision(self):
        m = test_material(sheets=[[1000, 2000]])
        formate = nesting.formate_aus_material(m, rand=10)
        self.assertEqual((formate[0]["breite"], formate[0]["laenge"]), (980, 1980))
        gruppen, _ = nesting.teile_gruppieren([{"name": "A", "breite": 240, "laenge": 900, "stueck": 7}])
        p = nesting.format_plan(gruppen, formate, fuge=3)
        blaetter = nesting.lage(p["bestes"], fuge=3, rand=10)
        self.assertEqual(nesting.kollisionen(blaetter, fuge=3, rand=10), [])
        # absichtliche Überlappung wird erkannt
        blaetter[0]["rechtecke"].append(dict(blaetter[0]["rechtecke"][0], nr=99))
        self.assertTrue(nesting.kollisionen(blaetter, fuge=3, rand=10))

    def test_drehen_nur_wenn_erlaubt(self):
        t = [{"name": "lang", "breite": 300, "laenge": 2600, "stueck": 1}]
        g, h = nesting.teile_gruppieren(t, False, [2000])
        self.assertEqual(g[0]["breite"], 300)
        g, h = nesting.teile_gruppieren(t, True, [2000])
        self.assertEqual(g[0]["breite"], 2600)
        self.assertTrue(h)

    def test_ausgabe(self):
        p = nesting.format_plan([{"breite": 250.0, "stuecke": bl([1000, 800])}], [{"breite": 1000, "laenge": 2000, "text": "T"}])
        b = nesting.lage(p["bestes"])
        svg = nesting.als_svg(b)
        self.assertTrue(svg.startswith("<svg") and svg.count("<rect") == 3)
        self.assertEqual(len(nesting.als_csv(p["bestes"]).strip().splitlines()), 3)
        d = dxf_writer.zuschnittplan_dxf(b, "Test äöü").inhalt()
        self.assertIn("$INSUNITS", d)
        self.assertIn("Test aeoeue", d)
        self.assertTrue(d.endswith("EOF\n"))


class MaterialTest(unittest.TestCase):
    def test_berechnung(self):
        m = test_material(sheets=[[1000, 2000]], coils=[670])
        teile = [{"name": "A", "materialId": m["id"], "flaeche": 250 * 1000 * 0.95, "breite": 250, "laenge": 1000, "stueck": 4},
                 {"name": "B", "materialId": m["id"], "flaeche": None, "breite": 250, "laenge": 500, "stueck": 2}]
        e = material_calculator.berechne(teile, [m], {"nesting": {"kerf": 0, "margin": 0}})
        x = e["materialien"][0]
        self.assertEqual(x["teile"], 6)
        self.assertAlmostEqual(x["flaeche_netto_m2"], 0.95 + 0.25)
        self.assertAlmostEqual(x["gewicht_kg"], 1.2 * 0.7 * 7.2)
        self.assertTrue(x["gewicht_ist_schaetzung"])
        self.assertEqual(x["flaeche_quelle"], "teilweise umschliessendes Rechteck")
        self.assertIsNotNone(x["verbrauch_m2"])
        self.assertTrue(0 < x["ausnutzung_prozent"] <= 100)
        self.assertIn("Schätz", material_calculator.bericht_text(e))

    def test_ohne_dichte_kein_gewicht(self):
        m = test_material(density=None)
        e = material_calculator.berechne([{"name": "A", "materialId": m["id"], "flaeche": 1e6, "breite": 1000, "laenge": 1000, "stueck": 1}], [m])
        self.assertIsNone(e["materialien"][0]["gewicht_kg"])


class DxfTest(unittest.TestCase):
    def test_dxf_mit_unabhaengigem_leser(self):
        """Zuschnittplan-DXF mit ezdxf (unabhängige Bibliothek) lesen und prüfen – nur wenn installiert."""
        try:
            from ezdxf import recover
        except ImportError:
            self.skipTest("ezdxf nicht installiert")
        import tempfile
        p = nesting.format_plan([{"breite": 250.0, "stuecke": bl([1000, 800])}], [{"breite": 1000, "laenge": 2000, "text": "T"}])
        pfad = os.path.join(tempfile.mkdtemp(), "plan.dxf")
        dxf_writer.zuschnittplan_dxf(nesting.lage(p["bestes"]), "Test äöü").speichern(pfad)
        doc, auditor = recover.readfile(pfad)
        self.assertEqual((doc.dxfversion, len(auditor.errors)), ("AC1009", 0))
        msp = doc.modelspace()
        self.assertEqual(len(msp.query("LINE")), 4 + 2 * 4)
        self.assertEqual({l.dxf.name for l in doc.layers} >= {"FORMAT", "ZUSCHNITT", "TEXT"}, True)
        xs = [e.dxf.end.x for e in msp.query('LINE[layer=="ZUSCHNITT"]')]
        self.assertAlmostEqual(max(xs), 250.0, msg="Massstab 1:1 in mm")

    def test_konturpruefung(self):
        q = [((0, 0), (10, 0)), ((10, 0), (10, 10)), ((10, 10), (0, 10)), ((0, 10), (0, 0))]
        self.assertEqual(dxf_writer.kontur_pruefen(q), [])
        self.assertTrue(dxf_writer.kontur_pruefen(q[:3]))
        self.assertTrue(dxf_writer.kontur_pruefen(q + [q[0]]))
        self.assertTrue(dxf_writer.kontur_pruefen(q + [((5, 5), (5, 5))]))


if __name__ == "__main__":
    unittest.main()

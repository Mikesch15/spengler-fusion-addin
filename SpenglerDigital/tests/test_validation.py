"""Prüfungen: Materialprofile, Einstellungen, Detailvorlagen, Ausrichtung, ungültige Eingaben."""
import unittest

from _basis import DatenTest, test_material
from spengler_cad.core import models
from spengler_cad.details import detail_validation as dv, frames
from spengler_cad.storage.material_library import MaterialBibliothek, MaterialFehler, pruefe_material
from spengler_cad.storage.settings_service import Einstellungen, EinstellungsFehler


class MaterialTest(DatenTest):
    def test_leer_und_speichern(self):
        b = MaterialBibliothek()
        self.assertEqual(b.liste(), [], "Materialbibliothek beginnt leer")
        m = b.speichern(test_material(sheets=[[1000, 2000]]))
        self.assertEqual(b.holen(m["id"])["name"], "TEST Blech 0.7")
        with self.assertRaises(MaterialFehler):
            b.loeschen(m["id"])
        b.loeschen(m["id"], bestaetigt=True)
        self.assertEqual(b.liste(), [])

    def test_ungueltig(self):
        for k, v in (("thickness", 0), ("thickness", "x"), ("kFactor", 2), ("density", 0), ("sheets", [[1000]]), ("coils", [-1]), ("name", "")):
            m = test_material()
            m[k] = v
            self.assertTrue(pruefe_material(m), (k, v))
        self.assertEqual(pruefe_material(models.neues_materialprofil("nur Dicke", 0.6)), [])


class EinstellungenTest(DatenTest):
    def test_standard_und_unbekannte_felder(self):
        s = Einstellungen()
        e = s.laden()
        self.assertIsNone(e["defaultMaterialId"], "kein vorgegebenes Material")
        e["eigen"] = {"a": 1}
        e["nesting"]["kerf"] = 2
        s.speichern(e)
        e2 = s.laden()
        self.assertEqual((e2["eigen"], e2["nesting"]["kerf"]), ({"a": 1}, 2))
        e2["nesting"]["kerf"] = -1
        with self.assertRaises(EinstellungsFehler):
            s.speichern(e2)
        e2["nesting"]["kerf"] = 0
        e2["ui"]["mode"] = "x"
        with self.assertRaises(EinstellungsFehler):
            s.speichern(e2)


def gueltige_detailvorlage():
    v = models.neue_detailvorlage("TEST Detail")
    v["source"]["file"] = "geometrie/x.f3d"
    v["anchor"]["frame"] = frames.rahmen_aus_kante([0, 0, 0], [100, 0, 0], [0, 0, 1])
    v["anchor"]["edgeLength"] = 100.0
    v["parameters"] = [dict(models.parameter("H", "Höhe", "mm", 20, 10, 40), fusionName="SD_H")]
    v["compatibility"].update({"thickness": 0.7, "edgeLengthMin": 50, "edgeLengthMax": 300})
    return v


class DetailTest(unittest.TestCase):
    def test_vorlage(self):
        self.assertEqual(dv.pruefe_detailvorlage(gueltige_detailvorlage())[0], [])
        v = gueltige_detailvorlage()
        v["parameters"][0]["fusionName"] = ""
        v["anchor"]["frame"]["x"] = [1, 1, 0]
        f, _ = dv.pruefe_detailvorlage(v)
        self.assertEqual(len(f), 2)

    def test_passung(self):
        v = gueltige_detailvorlage()
        k = {"kurve": "linie", "laenge": 200, "dicke": 0.7, "blech": True}
        self.assertTrue(dv.passung(v, k)[0])
        for aenderung in ({"kurve": "kreis"}, {"laenge": 20}, {"laenge": 400}, {"dicke": 1.0}):
            kk = dict(k, **aenderung)
            self.assertFalse(dv.passung(v, kk)[0], aenderung)

    def test_parameter_zuordnen(self):
        """Live-Test 29.10.2026: Fusion benennt importierte Parameter um (SD_H → SD_H_1); nur NEUE dürfen gesetzt werden."""
        self.assertEqual(dv.parameter_zuordnen(["SD_H"], ["SD_H_1"]), ({"SD_H": "SD_H_1"}, []))
        self.assertEqual(dv.parameter_zuordnen(["SD_H"], ["SD_H"]), ({"SD_H": "SD_H"}, []))
        self.assertEqual(dv.parameter_zuordnen(["SD_H", "B"], ["SD_H_1", "SD_H_2"]), ({}, ["SD_H", "B"]), "mehrdeutig/fehlend → nicht raten")
        self.assertEqual(dv.parameter_zuordnen(["SD_H"], ["SD_HX_1"]), ({}, ["SD_H"]))

    def test_palette_url(self):
        """Live-Test 29.10.2026: Windows-Pfad mit Backslashes ergab file:///C:/%5CUsers… – als URI übergeben."""
        import pathlib
        u = pathlib.PureWindowsPath(r"C:\Users\Mike\Downloads\SpenglerDigital\palette\vorlagen.html").as_uri()
        self.assertEqual(u, "file:///C:/Users/Mike/Downloads/SpenglerDigital/palette/vorlagen.html")
        import os, sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.commands import settings_command
        self.assertTrue(settings_command.html_url().startswith("file:///"))
        self.assertNotIn("\\", settings_command.html_url())

    def test_ausrichtung(self):
        anker = frames.rahmen_aus_kante([10, 0, 0], [10, 50, 0], [0, 0, 1])
        ziel = frames.rahmen_aus_kante([0, 0, 100], [0, 0, 300], [1, 0, 0])
        T = frames.ausrichtung(anker, ziel)
        for a, b in ((frames.anwenden(T, [10, 0, 0]), [0, 0, 100]), (frames.anwenden(T, [10, 50, 0]), [0, 0, 150])):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y)
        # Normale wird mitgedreht: Punkt 1 über der Ankerfläche liegt 1 vor der Zielfläche
        p = frames.anwenden(T, [10, 0, 1])
        for x, y in zip(p, [1, 0, 100]):
            self.assertAlmostEqual(x, y)


if __name__ == "__main__":
    unittest.main()

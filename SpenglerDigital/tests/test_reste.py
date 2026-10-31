"""Reststücke: speichern/prüfen/löschen und Vorschläge (ohne Fusion)."""
import shutil
import tempfile
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.storage import reste

M = {"name": "Alu 0.7", "material": "Aluminium", "thickness": 0.7}


class ResteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def rest(self, **k):
        return reste.speichern(dict({"material_name": "Alu 0.7", "staerke_mm": 0.7, "breite_mm": 500, "laenge_mm": 800, "anzahl": 1}, **k), self.tmp)

    def test_speichern_aendern_loeschen_pruefen(self):
        r = self.rest()
        self.assertTrue(r["id"].startswith("rest-"))
        self.rest(id=r["id"], anzahl=3)
        self.assertEqual([x["anzahl"] for x in reste.liste(self.tmp)], [3])
        for schlecht in ({"breite_mm": 0}, {"anzahl": 0}, {"staerke_mm": "x"}, {"laenge_mm": None}):
            with self.assertRaises(reste.RestFehler):
                self.rest(**schlecht)
        self.assertEqual(reste.loeschen(r["id"], self.tmp), 1)
        self.assertEqual(reste.liste(self.tmp), [])

    def test_vorschlaege(self):
        gross = self.rest(breite_mm=600, laenge_mm=900)
        klein = self.rest(breite_mm=300, laenge_mm=500)
        andere_dicke = self.rest(staerke_mm=1.0, breite_mm=310, laenge_mm=510)
        fremdes_material = self.rest(material_name="Zink", breite_mm=310, laenge_mm=510)
        verbraucht = self.rest(breite_mm=305, laenge_mm=505, verbraucht=True)
        teile = [{"nr": 1, "name": "A", "breite": 280.0, "laenge": 480.0, "stueck": 1, "material": M},
                 {"nr": 2, "name": "B", "breite": 480.0, "laenge": 280.0, "stueck": 1, "material": M},      # gedreht passt
                 {"nr": 3, "name": "C", "breite": 700.0, "laenge": 1000.0, "stueck": 1, "material": M},     # zu gross
                 {"nr": 4, "name": "D", "breite": 100.0, "laenge": 100.0, "stueck": 5, "material": M}]      # zu wenig Stück
        v = reste.vorschlaege(teile, reste.liste(self.tmp), drehen=True)
        self.assertEqual([r["id"] if r else None for _, r in v], [klein["id"], klein["id"], None, None], "kleinster passender, richtiges Material/Dicke")
        v = reste.vorschlaege(teile, reste.liste(self.tmp), drehen=False)
        self.assertEqual(v[1][1]["id"], gross["id"], "ohne Drehen: B (480 × 280) passt nur in den grossen Rest 600 × 900")
        leer = self.rest(material_name="", breite_mm=290, laenge_mm=490)
        self.assertEqual(reste.vorschlaege(teile[:1], reste.liste(self.tmp))[0][1]["id"], leer["id"], "Rest ohne Materialangabe passt zu jedem Material")


if __name__ == "__main__":
    unittest.main()

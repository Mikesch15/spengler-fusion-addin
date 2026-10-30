"""DXF der Fusion-Abwicklung lesen und als SVG im Werkstattblatt zeigen (Live-Test 8.3: «keine Abwicklung zu sehen»).
Geprüft mit selbst erzeugten DXF-Texten – wie Fusions Ebenennamen tatsächlich heissen, zeigt nur der Live-Test."""
import os
import tempfile
import unittest

from _basis import DatenTest  # noqa: F401  (stellt den Importpfad her)
from spengler_cad.manufacturing import dxf_lesen, workshop_sheet

DXF = ("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n"
       "0\nLINE\n8\nCONTOUR\n10\n0.0\n20\n0.0\n30\n0.0\n11\n150.0\n21\n0.0\n31\n0.0\n"
       "0\nLINE\n8\nBEND_LINES\n10\n0\n20\n30\n11\n150\n21\n30\n"
       "0\nARC\n8\n0\n10\n150\n20\n20\n40\n20\n50\n270\n51\n90\n"
       "0\nCIRCLE\n8\n0\n10\n75\n20\n50\n40\n5\n"
       "0\nLWPOLYLINE\n8\n0\n70\n1\n10\n0\n20\n0\n10\n50\n20\n0\n42\n0.5\n10\n50\n20\n98.3\n"
       "0\nSPLINE\n8\n0\n"
       "0\nENDSEC\n0\nEOF\n")


class LesenTest(unittest.TestCase):
    def test_elemente(self):
        e, ignoriert = dxf_lesen.lesen(DXF)
        self.assertEqual([x["typ"] for x in e], ["linie", "linie", "bogen", "kreis", "poly"])
        self.assertEqual(ignoriert, 1, "Spline wird gezählt, nicht gezeichnet")
        self.assertEqual(e[0]["p"], [(0.0, 0.0), (150.0, 0.0)])
        self.assertEqual((e[2]["a0"], e[2]["a1"]), (270.0, 90.0))
        self.assertTrue(e[4]["zu"])
        self.assertEqual(e[4]["b"], [0.0, 0.5, 0.0])

    def test_svg_biegelinien_gestrichelt(self):
        e, _ = dxf_lesen.lesen(DXF)
        s = dxf_lesen.svg(e)
        self.assertTrue(s.startswith("<svg") and s.endswith("</svg>"))
        self.assertEqual(s.count("stroke-dasharray"), 1, "nur die Ebene BEND_LINES ist gestrichelt")
        self.assertIn("<circle", s)
        self.assertIn(" A ", s, "Bogen und Ausbuchtung als SVG-Bogen")

    def test_leer_und_kaputt(self):
        self.assertEqual(dxf_lesen.lesen(""), ([], 0))
        self.assertEqual(dxf_lesen.svg([]), "")

    def test_datei(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.dxf")
            with open(p, "w", encoding="utf-8") as f:
                f.write(DXF)
            s, ign = dxf_lesen.svg_aus_datei(p)
            self.assertIn("<path", s)
            self.assertEqual(ign, 1)

    def test_werkstattblatt_zeigt_die_abwicklung(self):
        e, _ = dxf_lesen.lesen(DXF)
        basis = {"bauteil": "Körper1", "material": "Kupfer", "dicke": 0.6, "vorlage": "–", "vorlagenVersion": "–", "datum": "2026-10-30",
                 "abwicklung": {"breite": 98.3, "laenge": 150.0, "quelle": "Fusion-Abwicklung"}}
        html = workshop_sheet.erstelle(dict(basis, abwicklungSvg=dxf_lesen.svg(e)))
        self.assertIn("<svg", html)
        self.assertIn("Zeichnung aus der Fusion-DXF", html)
        html = workshop_sheet.erstelle(dict(basis, abwicklungHinweis="DXF leer"))
        self.assertNotIn("<svg", html)
        self.assertIn("Abwicklung nicht gezeichnet: DXF leer", html)


if __name__ == "__main__":
    unittest.main()

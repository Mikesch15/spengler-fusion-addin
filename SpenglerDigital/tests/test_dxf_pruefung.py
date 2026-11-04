"""DXF-Prüfung der Abwicklung (Logik ohne Fusion, mit selbst gebauten DXF-Texten – KEINE echte Fusion-DXF)."""
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.manufacturing import dxf_pruefung as dp


def dxf(entities, insunits=4):
    kopf = "0\nSECTION\n2\nHEADER\n" + ("9\n$INSUNITS\n70\n%d\n" % insunits if insunits is not None else "") + "0\nENDSEC\n"
    return kopf + "0\nSECTION\n2\nENTITIES\n" + "".join(entities) + "0\nENDSEC\n0\nEOF\n"


def linie(x1, y1, x2, y2, layer="0"):
    return "0\nLINE\n8\n%s\n10\n%s\n20\n%s\n11\n%s\n21\n%s\n" % (layer, x1, y1, x2, y2)


def kreis(x, y, r, layer="0"):
    return "0\nCIRCLE\n8\n%s\n10\n%s\n20\n%s\n40\n%s\n" % (layer, x, y, r)


def rechteck(b, h, layer="0"):
    return [linie(0, 0, b, 0, layer), linie(b, 0, b, h, layer), linie(b, h, 0, h, layer), linie(0, h, 0, 0, layer)]


class DxfPruefung(unittest.TestCase):
    def test_gueltige_abwicklung(self):
        r = dp.pruefe(dxf(rechteck(100, 60) + [linie(0, 20, 100, 20, "BEND_UP"), kreis(50, 40, 5)]), 100, 60)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["masse"], (60.0, 100.0))
        self.assertEqual((r["doppelte"], r["offene_enden"], r["probleme"]), (0, 0, []), "Biegelinie und Loch sind keine offene Kontur")
        self.assertEqual(r["einheit"], 4)

    def test_masse_weichen_ab_ist_schwer(self):
        r = dp.pruefe(dxf(rechteck(100, 60)), 100, 80)
        self.assertFalse(r["ok"])
        self.assertIn("60.0 × 100.0 mm, erwartet sind 80.0 × 100.0 mm", r["probleme"][0])
        r = dp.pruefe(dxf(rechteck(100, 60)), 100.8, 60.2)
        self.assertTrue(r["ok"], "innerhalb der Toleranz")

    def test_zehnfach_zu_klein_wird_benannt(self):
        r = dp.pruefe(dxf(rechteck(10, 6)), 100, 60)
        self.assertFalse(r["ok"])
        self.assertIn("cm statt mm", r["probleme"][0])
        self.assertIn("10× zu gross", dp.pruefe(dxf(rechteck(1000, 600)), 100, 60)["probleme"][0])

    def test_einheit(self):
        self.assertFalse(dp.pruefe(dxf(rechteck(100, 60), insunits=1), 100, 60)["ok"])
        r = dp.pruefe(dxf(rechteck(100, 60), insunits=None), 100, 60)
        self.assertTrue(r["ok"])
        self.assertTrue(any("keine Einheitenangabe" in h for h in r["hinweise"]), "fehlende Einheit ist nur ein Hinweis")

    def test_leer_und_kaputt(self):
        self.assertFalse(dp.pruefe(dxf([]), 100, 60)["ok"])
        self.assertIn("keine zeichenbaren Elemente", dp.pruefe(dxf([]), 100, 60)["probleme"][0])
        self.assertFalse(dp.pruefe("", 100, 60)["ok"])
        r = dp.pruefe_datei("/gibt/es/nicht.dxf")
        self.assertFalse(r["ok"])
        self.assertIn("nicht öffnen", r["probleme"][0])

    def test_offene_kontur_und_doppelte_sind_hinweise(self):
        offen = rechteck(100, 60)[:3]                                          # vierte Seite fehlt
        r = dp.pruefe(dxf(offen), 100, 60)
        self.assertTrue(r["ok"], "offene Kontur ist ein Hinweis, kein Abbruch")
        self.assertEqual(r["offene_enden"], 2)
        self.assertTrue(any("nicht geschlossen" in h for h in r["hinweise"]))
        r = dp.pruefe(dxf(rechteck(100, 60) + [linie(100, 0, 0, 0)]), 100, 60)      # dieselbe Linie rückwärts
        self.assertEqual(r["doppelte"], 1)
        self.assertTrue(any("doppelte Linie" in h for h in r["hinweise"]))

    def test_geschlossene_polylinie(self):
        poly = "0\nLWPOLYLINE\n8\n0\n70\n1\n10\n0\n20\n0\n10\n100\n20\n0\n10\n100\n20\n60\n10\n0\n20\n60\n"
        r = dp.pruefe(dxf([poly]), 100, 60)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["offene_enden"], 0)

    def test_zusammenfassung(self):
        r = dp.pruefe(dxf(rechteck(100, 60)[:3]), 100, 60)
        self.assertIn("60.0 × 100.0 mm, 3 Elemente", dp.zusammenfassung(r))


if __name__ == "__main__":
    unittest.main()


class ExportKontrolle(DatenTest):
    """Der Export meldet eine fehlerhafte DXF nicht als Erfolg (Hilfsfunktion des Befehls «Abwicklung & DXF»)."""

    def _datei(self, inhalt):
        import os
        p = os.path.join(os.environ["SPENGLER_CAD_DATEN"], "t.dxf")
        with open(p, "w", encoding="utf-8") as f:
            f.write(inhalt)
        return p

    def test_gut_mit_und_ohne_hinweis(self):
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.commands import export_command as ex
        self.assertEqual(ex.dxf_kontrolle(self._datei(dxf(rechteck(100, 60))), {"breite": 60, "laenge": 100}), "✓")
        t = ex.dxf_kontrolle(self._datei(dxf(rechteck(100, 60)[:3])), {"breite": 60, "laenge": 100})
        self.assertTrue(t.startswith("✓ ⚠") and "nicht geschlossen" in t)

    def test_schwere_probleme_werden_zum_fehler(self):
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.commands import export_command as ex
        fa = ex.fa
        for inhalt, soll in ((dxf(rechteck(100, 60)), {"breite": 60, "laenge": 120}), (dxf([]), {"breite": 60, "laenge": 100}), (dxf(rechteck(100, 60), insunits=1), {"breite": 60, "laenge": 100})):
            with self.assertRaises(fa.AdapterFehler) as cm:
                ex.dxf_kontrolle(self._datei(inhalt), soll)
            self.assertIn("DXF fehlerhaft", str(cm.exception))
            self.assertIn("t.dxf", str(cm.exception), "die Datei wird zur Kontrolle genannt")

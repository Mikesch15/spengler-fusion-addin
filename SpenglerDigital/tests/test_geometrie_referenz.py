"""Zentrale Geometrie-Referenz und Unterstützungsmatrix – reine Rechnung, KEIN Fusion-Test."""
import math
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import geometrie_referenz as gr
from spengler_cad.core import unterstuetzung as u
from spengler_cad.details import frames


def nah(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


class Referenz(unittest.TestCase):
    def test_lokaler_rahmen_nicht_global_z(self):
        n = gr.zylinder_normale((0, 0, 0), (0, 0, 1), (100, 0, 50))     # Zylinder R100 um Z: Normale radial = +X
        self.assertTrue(nah(n, (1, 0, 0)))
        r = gr.referenz("zylinder", (100, 0, 50), n, (0, 0, 1))["rahmen"]
        self.assertTrue(nah(r["z"], (1, 0, 0)), "z = lokale Normale, nicht Welt-Z")
        self.assertTrue(nah(r["x"], (0, 0, 1)))
        self.assertTrue(nah(r["y"], frames.kreuz(r["z"], r["x"])))

    def test_seite_und_tangente_wird_orthogonalisiert(self):
        r = gr.referenz("eben", (0, 0, 0), (0, 0, 2), (1, 0, 0.5), seite=-1)["rahmen"]
        self.assertTrue(nah(r["x"], (1, 0, 0)))
        self.assertTrue(nah(r["z"], (0, 0, -1)), "Gegenseite")
        self.assertEqual(gr.referenz("eben", (0, 0, 0), (0, 0, 1))["rahmen"]["z"], [0.0, 0.0, 1.0], "ohne Tangente reproduzierbar")

    def test_kegel_normale(self):
        n = gr.kegel_normale((0, 0, 0), (0, 0, 1), 30, (0.5, 0, math.sqrt(3) / 2))   # Mantellinie unter 30° zur Achse
        self.assertAlmostEqual(gr.winkel_grad(n, (0.5, 0, math.sqrt(3) / 2)), 90.0, 6)
        self.assertGreater(n[0], 0)

    def test_klasse(self):
        self.assertEqual(gr.klasse(gr.referenz("eben", (0, 0, 0), (0, 0, 1), kurve_typ="linie")), ("eben", "gerade"))
        self.assertEqual(gr.klasse(gr.referenz("eben", (0, 0, 0), (0, 0, 1), kurve_typ="bogen")), ("eben", "bogen"))
        self.assertEqual(gr.klasse(gr.referenz("zylinder", (0, 0, 0), (0, 0, 1), kurve_typ="linie")), ("zylinder", "gerade"),
                         "gerade Kante auf Zylinder ist KEIN ebener Fall")
        self.assertEqual(gr.klasse(gr.referenz("kugel", (0, 0, 0), (0, 0, 1))), ("doppelt_gekruemmt", "gerade"))
        with self.assertRaises(ValueError):
            gr.referenz("blob", (0, 0, 0), (0, 0, 1))

    def test_veraltete_auswahl(self):
        alt = gr.referenz("eben", (0, 0, 0), (0, 0, 1), kennung={"flaeche": "f1", "flaeche_mm2": 6000.0, "kante": "k1", "kante_mm": 100.0})
        self.assertEqual(gr.ist_veraltet(alt, alt), [])
        neu = gr.referenz("zylinder", (0, 0, 0), (0, 0, 1), kennung={"flaeche": "f2", "flaeche_mm2": 5000.0, "kante": "k1", "kante_mm": 100.0})
        g = " ".join(gr.ist_veraltet(alt, neu))
        self.assertIn("Fläche ist eine andere", g)
        self.assertIn("Flächentyp geändert", g)
        self.assertIn("Flächengrösse geändert", g)
        self.assertIn("existiert nicht mehr", gr.ist_veraltet(alt, None)[0])


class Abwickelbarkeit(unittest.TestCase):
    def test_einordnung(self):
        self.assertEqual(gr.abwickelbarkeit(["eben", "zylinder", "kegel"])[0], "exakt")
        self.assertEqual(gr.abwickelbarkeit(["eben", "kugel"])[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["torus"])[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["freiform"], 1e-10)[0], "naeherung")
        self.assertEqual(gr.abwickelbarkeit(["freiform"], 1e-3)[0], "nicht")
        self.assertEqual(gr.abwickelbarkeit(["freiform"])[0], "nicht", "ohne Messung keine Aussage")
        self.assertEqual(gr.abwickelbarkeit(["freiform"], 1e-10, stichprobe_unsicher=True)[0], "unsicher", "ausgefallene Stichproben = unsicher")
        self.assertEqual(gr.abwickelbarkeit(["unbekannt"])[0], "unsicher", "fehlende Erkennung ist nie «exakt»")
        self.assertEqual(gr.abwickelbarkeit(["eben", "unbekannt"])[0], "unsicher")
        self.assertEqual(gr.abwickelbarkeit([])[0], "unsicher")
        self.assertEqual(gr.abwickelbarkeit(["einfach_gekruemmt", "eben"])[0], "exakt")
        self.assertAlmostEqual(gr.gauss(0.01, 0.0), 0.0)                     # Zylinder: eine Hauptkrümmung 0


class Versatz(unittest.TestCase):
    def test_richtung_eindeutig(self):
        eben = gr.referenz("eben", (0, 0, 0), (0, 0, 1), (1, 0, 0), kurve_typ="linie")
        richtung, text = gr.versatz_definition(eben, 5, "tangential")
        self.assertTrue(nah(richtung, (0, 1, 0)))
        self.assertIn("lokale Richtung", text)
        self.assertIn("+5 mm", text)
        zyl = gr.referenz("zylinder", (100, 0, 0), (1, 0, 0), (0, 0, 1), kurve_typ="linie")
        with self.assertRaises(ValueError) as cm:
            gr.versatz_definition(zyl, 5, "tangential")
        self.assertIn("nur an Kanten EBENER", str(cm.exception))
        self.assertTrue(nah(gr.versatz_definition(zyl, 2, "radial")[0], (1, 0, 0)))
        with self.assertRaises(ValueError):
            gr.versatz_definition(eben, 2, "radial")


class Matrix(unittest.TestCase):
    def test_vollstaendig_und_pruefung(self):
        for op in u.OPS:
            for f in u.FLAECHEN:
                for k in u.KANTEN:
                    s, grund = u.stand(op, f, k)
                    self.assertIn(s, ("ja", "eingeschraenkt", "prototyp", "nein"))
                    if s != "ja":
                        self.assertTrue(grund, "%s/%s/%s: Einschränkung braucht einen Grund" % (op, f, k))
        self.assertIsNone(u.pruefen("flansch", "eben", "gerade"))
        self.assertIn("nicht unterstützt", u.pruefen("flansch", "eben", "bogen"))
        self.assertIn("nicht ungefragt verformt", u.pruefen("detail_anpassen", "kegel", "gerade"))

    def test_gerade_kante_auf_zylinder_ist_kein_ebener_fall(self):
        self.assertIn("Live 0.4.60", u.pruefen("flansch", "zylinder", "gerade"), "nativ von Fusion abgelehnt")
        self.assertIn("gesperrter Prototyp", u.pruefen("versatz", "zylinder", "gerade"))
        self.assertIsNone(u.pruefen("versatz", "zylinder", "gerade", prototyp_erlaubt=True), "nur im Live-Test")
        self.assertIn("schon die Einzelkante", u.pruefen("mehrkant_gehrung", "zylinder", "gerade", True))
        self.assertIn("Versatz als Bogenlänge", u.hinweis("versatz", "zylinder", "gerade"))

    def test_unbekannt_wird_nie_bearbeitet(self):
        for op in u.OPS:
            self.assertIn("unbekannt", u.pruefen(op, "unbekannt", "gerade", True))
        self.assertEqual(u.flaechenklasse("torus"), "doppelt_gekruemmt")
        self.assertEqual(u.flaechenklasse("blob"), "unbekannt")
        self.assertEqual((u.kantentyp("linie"), u.kantentyp("spline"), u.kantentyp(None)), ("gerade", "kurve", "gerade"))

    def test_eignung_im_bauplan(self):
        from spengler_cad.core import operation_plan as op
        from test_operation_plan import kante
        from test_templates import testvorlage
        from _basis import test_material
        p = op.erstelle(testvorlage(), {}, test_material(), [kante(flaeche="zylinder")])
        self.assertFalse(op.ist_ausfuehrbar(p), "gerade Kante auf Zylinder rutscht nicht durch")
        self.assertIn("Zylinder", " ".join(p["validation"]["errors"]))
        p = op.erstelle(testvorlage(), {}, test_material(), [kante(flaeche="unbekannt")])
        self.assertFalse(op.ist_ausfuehrbar(p), "unbekannte Fläche nie wie eben")
        self.assertTrue(op.ist_ausfuehrbar(op.erstelle(testvorlage(), {}, test_material(), [kante(flaeche="eben")])), "Regression eben")

    def test_markdown(self):
        t = u.als_markdown()
        self.assertIn("| Versatz | Zylinder | Prototyp (gesperrt) | nicht unterstützt |", t)
        self.assertIn("Grenzen und Gründe", t)


class DokuSynchron(unittest.TestCase):
    def test_statusdokument_enthaelt_die_aktuelle_matrix(self):
        import os
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "ANFORDERUNGEN_STATUS.md")
        with open(pfad, encoding="utf-8") as f:
            self.assertIn(u.als_markdown(), f.read(), "Matrix geändert → Statusdokument neu erzeugen")


class Orientierung(unittest.TestCase):
    def test_mantellinie_und_kreiskante(self):
        # Mantellinie eines Zylinders (Achse Z, R 100): Normale überall +X
        mantel = [gr.referenz("zylinder", (100, 0, z), (1, 0, 0), (0, 0, 1))["rahmen"] for z in (0, 40, 80)]
        ok, t, d = gr.orientierung_entlang(mantel)
        self.assertAlmostEqual(d, 0.0)
        # Kreiskante über 90°: Normale dreht sich um 90°; Flansch muss überall der LOKALEN Normale folgen
        kreis = [gr.referenz("zylinder", (100 * math.cos(math.radians(w)), 100 * math.sin(math.radians(w)), 0),
                             gr.zylinder_normale((0, 0, 0), (0, 0, 1), (math.cos(math.radians(w)), math.sin(math.radians(w)), 0)), (0, 0, 1))["rahmen"]
                 for w in (0, 45, 90)]
        ok, t, d = gr.orientierung_entlang(kreis, soll=lambda i, r: r["z"])
        self.assertTrue(ok)
        self.assertAlmostEqual(d, 90.0, 6)
        ok, t, _ = gr.orientierung_entlang(kreis, soll=lambda i, r: (1, 0, 0))
        self.assertFalse(ok, "eine feste globale Richtung folgt der Kurve nicht")
        self.assertFalse(gr.orientierung_entlang(kreis[:1])[0])

    def test_machbarkeit_im_statusdokument(self):
        import os
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "ANFORDERUNGEN_STATUS.md")
        with open(pfad, encoding="utf-8") as f:
            self.assertIn(u.machbarkeit_markdown(), f.read())

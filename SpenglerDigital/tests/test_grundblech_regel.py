"""Grundblech: Blechregel mit Soll-Dicke, Aktivierung der Zielkomponente, Ergebnisprüfung und Rückbau – sowie der zentrale Rückbau (deleteMe-Ergebnis)
und der Versatz-Rückbau. Mit Attrappen (tests/fake_fusion_blech.py) – KEIN echter Fusion-Test; ob Fusion so rechnet, zeigt erst der Live-Test."""
import unittest

import fake_fusion_blech as ff
from test_fusion_logik import ebene
from _basis import DatenTest  # noqa: F401

RECHTECK = [[(0, 0), (100, 0), (100, 60), (0, 60)]]


def _fa():
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class _Patch(unittest.TestCase):
    def patche(self, **attrs):
        fa = _fa()
        for name, wert in attrs.items():
            original = getattr(fa, name)
            self.addCleanup(setattr, fa, name, original)
            setattr(fa, name, wert)

    def design(self, **kw):
        d = ff.Design(**kw)
        self.patche(design=lambda: d, _oberseite=lambda b: object())
        return d


class Grundblech(_Patch):
    def test_07mm_neue_regel_als_kopie_in_zielkomponente(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Blech A")
        body = fa.blech_aus_profil(c, RECHTECK, 0.7)
        self.assertIs(body.parentComponent, c)
        self.assertEqual(d.rootComponent.bRepBodies.count, 0, "nichts in Root")
        self.assertAlmostEqual(c.activeSheetMetalRule.thickness.value * 10, 0.7)
        self.assertEqual(c.activeSheetMetalRule.name, "Spengler 0.70 mm")
        self.assertEqual(d.designSheetMetalRules.kopien, [("Stahl 1 mm (Bibliothek)", "Spengler 0.70 mm")])
        self.assertAlmostEqual(d.librarySheetMetalRules.item(0).thickness.value * 10, 1.0, msg="Bibliotheksregel bleibt unverändert")
        self.assertEqual(d.aktivierungen, ["Blech A", "Root"], "Zielkomponente aktiviert, danach wieder Root")
        self.assertEqual(c.features.flangeFeatures.aufrufe[0][0].__class__.__name__, "Profil", "dokumentierte Form createBaseFlangeInput(profil)")
        self.assertEqual(len(c.features.flangeFeatures.aufrufe[0]), 1, "kein Distanzparameter")

    def test_10mm_vorhandene_regel_wird_wiederverwendet(self):
        fa = _fa()
        d = self.design(design_regeln=[ff.Regel("Alu 1.0", 1.0)])
        c = d.neue_komponente("Blech B")
        body = fa.blech_aus_profil(c, RECHTECK, 1.0)
        self.assertEqual(d.designSheetMetalRules.kopien, [])
        self.assertEqual(c.activeSheetMetalRule.name, "Alu 1.0")
        self.assertAlmostEqual(body.boundingBox.maxPoint.z * 10, 1.0)

    def test_mit_vorhandenen_komponenten_und_koerpern(self):
        fa = _fa()
        d = self.design()
        d.rootComponent.bRepBodies.elemente.append(ff.Koerper(d.rootComponent, 2.0, d.rootComponent.bRepBodies))
        alt = d.neue_komponente("Bestand", koerper=2)
        c = d.neue_komponente("Neu")
        andere = d.neue_komponente("Aktiv")
        d.activeOccurrence = d.occs[2]
        fa.blech_aus_profil(c, RECHTECK, 0.7)
        self.assertEqual((d.rootComponent.bRepBodies.count, alt.bRepBodies.count, c.bRepBodies.count, andere.bRepBodies.count), (1, 2, 1, 0))
        self.assertIs(d.activeOccurrence, d.occs[2], "vorherige Aktivierung wiederhergestellt")

    def test_koerper_in_root_bricht_ab_und_baut_zurueck(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Ziel")
        c.features.flangeFeatures.ziel = d.rootComponent
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.blech_aus_profil(c, RECHTECK, 1.0)
        self.assertIn("nicht in der Zielkomponente", str(cm.exception))
        self.assertIn("wieder entfernt", str(cm.exception))
        self.assertEqual((d.rootComponent.bRepBodies.count, c.skizzen.count), (0, 0), "keine Teilgeometrie")
        self.assertIsNone(d.activeOccurrence, "Aktivierung auch nach dem Fehler zurückgestellt")

    def test_falsche_dicke_bricht_ab(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Ziel")
        c.features.flangeFeatures.dicke_mm = 1.0                     # Fusion baut (angenommen) mit 1 mm trotz Regel 0.7
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.blech_aus_profil(c, RECHTECK, 0.7)
        self.assertIn("Gemessene Blechdicke 1.000 mm statt 0.7 mm", str(cm.exception))
        self.assertEqual((c.bRepBodies.count, c.skizzen.count), (0, 0))

    def test_ungueltige_eingaben_vor_dem_modellieren(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Ziel")
        for dicke in (None, 0, 0.05, 50):
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.blech_aus_profil(c, RECHTECK, dicke)
            self.assertIn("Ungültige Blechdicke", str(cm.exception))
        for schleifen, text in (([[(0, 0), (10, 0)]], "nur 2 Punkte"), ([[(0, 0), (10, 0), (20, 0)]], "keine Fläche"), ([], "Umriss")):
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.blech_aus_profil(c, schleifen, 1.0)
            self.assertIn(text, str(cm.exception))
        self.assertEqual((c.skizzen.count, d.aktivierungen, d.designSheetMetalRules.kopien), (0, [], []), "nichts angefasst")

    def test_dicke_der_regel_nicht_setzbar(self):
        fa = _fa()
        d = self.design(setzbar=False)
        c = d.neue_komponente("Ziel")
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.blech_aus_profil(c, RECHTECK, 0.7)
        self.assertIn("hat 1.000 mm statt 0.7 mm", str(cm.exception))
        self.assertEqual(c.skizzen.count, 0)

    def test_nicht_aktivierbar(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Ziel", aktivierbar=False)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.blech_aus_profil(c, RECHTECK, 1.0)
        self.assertIn("nicht aktivieren", str(cm.exception))
        self.assertEqual(c.skizzen.count, 0)

    def test_testfehler_nach_feature_baut_zurueck_und_stellt_regel_zurueck(self):
        fa = _fa()
        d = self.design()
        alt = ff.Regel("Vorher", 2.0)
        c = d.neue_komponente("Ziel", regel=alt)
        fa.TESTFEHLER.add("grundblech_feature")
        self.addCleanup(fa.TESTFEHLER.clear)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.blech_aus_profil(c, RECHTECK, 0.7)
        self.assertIn("Testfehler", str(cm.exception))
        self.assertTrue(cm.exception.rueckbau_ok)
        self.assertEqual((c.bRepBodies.count, c.skizzen.count), (0, 0))
        self.assertIs(c.activeSheetMetalRule, alt)


class Rueckbau(_Patch):
    def test_umgekehrte_reihenfolge_und_ergebnis(self):
        fa = _fa()
        reihe = []
        a, b = ff.Objekt("Skizze"), ff.Objekt("Extrusion")
        for o in (a, b):
            o.deleteMe = (lambda o_=o, f=o.deleteMe: reihe.append(o_.name) or f())
        self.assertTrue(fa.entfernen([a, b]))
        self.assertEqual(reihe, ["Extrusion", "Skizze"])

    def test_false_und_ausnahme_sind_fehlschlag(self):
        fa = _fa()
        weg = ff.Objekt("schon weg")
        weg.isValid = False
        self.assertTrue(fa.entfernen([weg, None]), "bereits gelöschte Objekte gelten als entfernt")
        p = fa.entfernen_bericht([ff.Objekt("Flansch", ergebnis=False), ff.Objekt("Skizze", ergebnis=RuntimeError("gesperrt"))])
        self.assertEqual(len(p), 2)
        self.assertIn("Objekt «Flansch»: deleteMe() meldet False", p[1])
        self.assertIn("Objekt «Skizze»: Löschen fehlgeschlagen (gesperrt)", p[0])
        self.assertFalse(fa.entfernen([ff.Objekt("x", ergebnis=False)]))

    def test_transaktion_meldet_unvollstaendigen_rueckbau(self):
        fa = _fa()
        rb = fa.Rueckbau("Versatz")
        rb.merke(ff.Objekt("Skizze"))
        rb.merke(ff.Objekt("Extrusion", ergebnis=False))
        with self.assertRaises(fa.AdapterFehler) as cm:
            rb.abbrechen(RuntimeError("Fusion: kaputt"))
        self.assertFalse(cm.exception.rueckbau_ok)
        self.assertIn("ACHTUNG: Rückbau unvollständig", str(cm.exception))
        self.assertIn("Extrusion", str(cm.exception))


class VersatzRueckbau(_Patch):
    """Fehler nach dem Anlegen der Versatz-Skizze: die Funktion entfernt ihre Skizze selbst (früher blieb sie zurück)."""

    def _kante(self, comp):
        class Flaeche(object):
            area = 60.0
            geometry = ebene()

        class Geo(object):
            startPoint, endPoint = ff.Punkt(0, 0, 0.1), ff.Punkt(10, 0, 0.1)

        class Kante(object):
            geometry, faces = Geo(), [Flaeche()]
        k = Kante()
        k.body = ff.Koerper(comp, 1.0, comp.bRepBodies)
        return k

    def test_fehler_nach_skizze_hinterlaesst_nichts(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Blech")
        self.patche(_kurventyp=lambda e: "linie", _kantenrahmen_quer=lambda e: ((1.0, 0, 0), (0, 1.0, 0)))
        fa.TESTFEHLER.add("versatz_skizze")
        self.addCleanup(fa.TESTFEHLER.clear)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa._versatz_gruppe([self._kante(c)], 5.0, 1.0)
        self.assertIn("wieder entfernt", str(cm.exception))
        self.assertTrue(cm.exception.rueckbau_ok)
        self.assertEqual(c.skizzen.count, 0, "keine Skizze bleibt zurück")


if __name__ == "__main__":
    unittest.main()


class Abwicklung(_Patch):
    """Voraussetzungen vor createFlatPattern und echter DXF-Export – Attrappen, KEIN Fusion-Test."""
    def _flaeche(self, body, area, nz, x=0.0):
        import adsk.core
        f = type("F", (), {})()
        f.geometry, f.area, f.body, f.nz = adsk.core.Plane(), area, body, nz
        f.pointOnFace = ff.Punkt(x, 0, 0)
        return f

    def _aufbau(self, n_bleche=1, blech=True):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Teil")
        for _ in range(n_bleche):
            k = ff.Koerper(c, 1.0, c.bRepBodies)
            k.isSheetMetal = blech
            k.faces = [self._flaeche(k, 60.0, -1.0), self._flaeche(k, 60.0, 1.0), self._flaeche(k, 2.0, 0.0)]
            c.bRepBodies.elemente.append(k)
        c.flatPattern = None
        c.erzeugt = []
        c.createFlatPattern = lambda f: c.erzeugt.append(f) or "FP"
        self.patche(flaechennormale=lambda f, p=None: (0, 0, f.nz))
        return fa, d, c

    def test_feste_auswahlregel(self):
        fa, d, c = self._aufbau()
        self.assertEqual(fa.abwicklung(c), ("FP", True))
        self.assertEqual(c.erzeugt[0].nz, 1.0, "grösste ebene Fläche, Normale +Z zuerst")

    def test_vorhandene_abwicklung_wird_verwendet(self):
        fa, d, c = self._aufbau()
        c.flatPattern = "ALT"
        self.assertEqual(fa.abwicklung(c), ("ALT", False))

    def test_ungueltiges_wird_abgelehnt(self):
        fa, d, c = self._aufbau(blech=False)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(c)
        self.assertIn("Kein gültiger Blechkörper", str(cm.exception))
        fa, d, c = self._aufbau(n_bleche=2)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(c)
        self.assertIn("2 Blechkörper", str(cm.exception))
        fremd = ff.Koerper(d.neue_komponente("Anderes"), 1.0, ff.Liste())
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(c, self._flaeche(c.bRepBodies.item(0), 60, 1.0), fremd)
        self.assertIn("gehört nicht zur Komponente", str(cm.exception))
        rund = self._flaeche(c.bRepBodies.item(0), 60, 1.0)
        rund.geometry = object()
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(c, rund, c.bRepBodies.item(0))
        self.assertIn("nicht eben", str(cm.exception))
        self.assertEqual(c.erzeugt, [], "nichts abgewickelt")

    def test_dxf_export_wird_wirklich_geprueft(self):
        import os
        import tempfile
        fa, d, c = self._aufbau()
        ordner = tempfile.mkdtemp(prefix="spengler_dxf_")
        pfad = os.path.join(ordner, "teil.dxf")
        with open(pfad, "w") as f:
            f.write("ALT")                                           # alte Datei darf nie als neuer Export gelten

        class EM(object):
            schreiben = False

            def createDXFFlatPatternExportOptions(self, p, fp):
                return type("O", (), {"isSplineConvertedToPolyline": True, "p": p})()

            def execute(self, opt):
                if self.schreiben:
                    with open(opt.p, "w") as f:
                        f.write("0\nEOF\n")
                return True
        d.exportManager = EM()
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.dxf_abwicklung("FP", pfad)                            # execute meldet True, schreibt aber nichts
        self.assertIn("nicht erzeugt", str(cm.exception))
        d.exportManager.schreiben = True
        self.assertEqual(fa.dxf_abwicklung("FP", pfad), pfad)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.dxf_abwicklung("FP", os.path.join(ordner, "fehlt", "x.dxf"))
        self.assertIn("Exportordner fehlt", str(cm.exception))


class GekruemmteKantenUndGrenzen(_Patch):
    """Bögen im Grundriss, Versatz nur auf ebener Fläche, Mindestlänge des Umschlags – Attrappen, KEIN Fusion-Test."""
    def test_grundblech_mit_bogen(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Rund")
        body = fa.blech_aus_profil(c, [[(0, 0), (100, 0, 130, 30), (100, 60), (0, 60)]], 1.0)   # rechte Seite als Bogen
        self.assertIs(body.parentComponent, c)
        self.assertEqual(c.skizzen.count, 1)
        self.assertIsNone(fa.schleifen_pruefen([[(0, 0, 50, 20), (100, 0, 50, -20)]]), "zwei Bögen ergeben eine Fläche (Linse)")

    def test_versatz_auf_zylinder_wird_erklaert_abgelehnt(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Rohr")
        self.patche(_kurventyp=lambda e: "linie", _kantenrahmen_quer=lambda e: ((1.0, 0, 0), (0, 1.0, 0)), flaechentyp=lambda f: "zylinder")
        k = VersatzRueckbau._kante(None, c)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa._versatz_gruppe([k], 5.0, 1.0)
        self.assertIn("nur an Kanten EBENER Blechflächen", str(cm.exception))
        self.assertEqual(c.skizzen.count, 0, "nichts angelegt")

    def test_umschlag_zu_kurz(self):
        fa = _fa()
        self.patche(_kurventyp=lambda e: "linie")
        k = type("K", (), {})()
        k.body = object()
        k.faces = [type("F", (), {"area": 1.0, "geometry": ebene()})()]
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.umschlag(k, 1.5, False, None, None, 1.0)
        self.assertIn("mindestens 2 × Blechdicke", str(cm.exception))

    def test_versatz_text_nennt_lokale_richtung(self):
        self.assertIn("nicht global", _fa().versatz_text(-5))


class AbwickelbarkeitUndKollision(_Patch):
    """Nicht exakt abwickelbare Körper werden abgelehnt; Kollision: echte Volumenprüfung oder ausdrücklich grob – Attrappen, KEIN Fusion-Test."""
    def test_kugelflaeche_wird_nicht_abgewickelt(self):
        fa = _fa()
        d = self.design()
        c = d.neue_komponente("Kuppel")
        k = ff.Koerper(c, 1.0, c.bRepBodies)
        k.faces = ["a", "b"]
        c.bRepBodies.elemente.append(k)
        c.flatPattern = None
        c.createFlatPattern = lambda f: self.fail("darf nicht abwickeln")
        self.patche(flaechentyp=lambda f: {"a": "eben", "b": "kugel"}[f])
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(c)
        self.assertIn("Nicht exakt abwickelbar", str(cm.exception))
        self.assertIn("kugel", str(cm.exception))

    def test_zylinder_und_kegel_sind_exakt(self):
        fa = _fa()
        k = type("K", (), {"faces": ["a", "z", "k"]})()
        self.patche(flaechentyp=lambda f: {"a": "eben", "z": "zylinder", "k": "kegel"}[f])
        self.assertEqual(fa.abwickelbarkeit_koerper(k)[0], "exakt")

    def test_kollision_ohne_volumenpruefung_ist_grob(self):
        fa = _fa()
        d = self.design()                                     # Attrappe ohne createInterferenceInput → Rückfall
        self.patche(kollision=lambda occ, andere: ["Blech"])
        r = fa.kollision_pruefen(object(), [])
        self.assertEqual(r, {"art": "grob", "treffer": [("Blech", None)]})
        self.assertIsNotNone(d)

    def test_neue_abwicklung_wird_nach_fehler_entfernt(self):
        from spengler_cad.commands import export_command as ex
        fp = ff.Objekt("Abwicklung")
        self.assertIn("wieder entfernt", ex._abwicklung_zuruecknehmen(fp, True))
        self.assertFalse(fp.isValid)
        alt = ff.Objekt("vorhanden")
        self.assertEqual(ex._abwicklung_zuruecknehmen(alt, False), "")
        self.assertTrue(alt.isValid, "eine vorhandene Abwicklung bleibt")

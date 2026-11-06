"""Quetschfalte: Analyse der Ecke aus zwei Aufkantungsflächen mit Attrappen (KEIN Fusion-Test – ob Fusion so rechnet, zeigt erst der Live-Test)."""
import unittest

from _basis import DatenTest  # noqa: F401
from test_fusion_logik import ebene


def _fa():
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class P(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class Ev(object):
    def __init__(self, n):
        self.n = n

    def getNormalAtPoint(self, p):
        return True, P(*self.n)


class Ecke(object):
    def __init__(self, p):
        self.geometry = P(*p)


class Flaeche(object):
    _nr = 0

    def __init__(self, body, n, punkt, area, ecken):
        Flaeche._nr += 1
        self.body, self.entityToken, self.geometry = body, "F%d" % Flaeche._nr, ebene()
        self.pointOnFace, self.centroid, self.area = P(*punkt), P(*punkt), area
        self.evaluator = Ev(n)
        self.vertices = [Ecke(p) for p in ecken]


class Koerper(object):
    entityToken = "K1"

    def __init__(self, hoehe2=3.0):
        self.faces = []
        f = self.faces.append
        # Aussenmass-Schale (cm): Basis z 0…0.1, Wand 1 (y 0…0.1, an e1 = +x), Wand 2 (x 0…0.1, an e2 = +y); Höhe 30 mm, Biegungs-Tangente bei z = 0.2
        f(Flaeche(self, (0, 0, 1), (5, 5, 0.1), 100.0, [(0, 0, 0.1), (10, 0, 0.1)]))        # Basis innen
        f(Flaeche(self, (0, 0, -1), (5, 5, 0.0), 100.0, [(0, 0, 0), (10, 0, 0)]))           # Basis aussen
        f(Flaeche(self, (0, 1, 0), (5, 0.1, 1.5), 30.0, [(0, 0.1, 0.2), (10, 0.1, 3.0)]))   # Wand 1 innen
        self.w1 = Flaeche(self, (0, -1, 0), (5, 0.0, 1.5), 30.0, [(0, 0, 0.2), (10, 0, 3.0)])   # Wand 1 aussen
        f(self.w1)
        f(Flaeche(self, (1, 0, 0), (0.1, 5, 1.5), 30.0, [(0.1, 0, 0.2), (0.1, 10, hoehe2)]))   # Wand 2 innen
        self.w2 = Flaeche(self, (-1, 0, 0), (0.0, 5, 1.5), 30.0, [(0, 0, 0.2), (0, 10, hoehe2)])   # Wand 2 aussen
        f(self.w2)
        self.faces[2].body = self.faces[4].body = self


class Analyse(unittest.TestCase):
    def setUp(self):
        fa = _fa()
        orig = fa.blechdicke_mm
        fa.blechdicke_mm = lambda b: 1.0
        self.addCleanup(setattr, fa, "blechdicke_mm", orig)

    def test_rechtwinklige_ecke_hinten_rechts(self):
        fa = _fa()
        k = Koerper()
        a = fa.quetschfalte_analysieren(k.w1, k.w2, "hinten rechts")
        self.assertAlmostEqual(a["beta"], 90.0, places=6)
        self.assertAlmostEqual(a["phi1"], 90.0, places=6)
        self.assertAlmostEqual(a["h1"], 30.0, places=6)
        self.assertFalse(a["getauscht"])
        self.assertEqual(a["wand"], "wand2", "hinten rechts = Wand 2 (Blick von der Sichtseite)")
        O, P_, C = a["dreieck_mm"]
        self.assertLess(max(abs(c) for c in O), 1e-6)
        self.assertEqual([round(c, 6) for c in P_], [0.0, 0.0, 30.0])
        self.assertEqual([round(c, 6) for c in C], [0.0, 30.0, 30.0], "Spitze auf Wand 2 (entlang e2 = +y)")
        self.assertTrue(a["geprueft"]["ok"])
        self.assertIn("Überschuss in der Ecke 90.0°", fa.quetschfalte_text(a))

    def test_hinten_links_liegt_auf_der_anderen_wand(self):
        fa = _fa()
        k = Koerper()
        a = fa.quetschfalte_analysieren(k.w1, k.w2, "hinten links")
        self.assertEqual(a["wand"], "wand1")
        C = a["dreieck_mm"][2]
        self.assertEqual([round(c, 6) for c in C], [30.0, 0.0, 30.0], "Spitze auf Wand 1 (entlang e1 = +x)")

    def test_reihenfolge_der_auswahl_egal(self):
        fa = _fa()
        k = Koerper()
        a = fa.quetschfalte_analysieren(k.w2, k.w1, "hinten rechts")      # Wand 2 zuerst gewählt → intern getauscht
        self.assertTrue(a["getauscht"])
        self.assertEqual([round(c, 6) for c in a["dreieck_mm"][2]], [0.0, 30.0, 30.0])

    def test_innenflaechen_gewaehlt_gleiches_ergebnis(self):
        fa = _fa()
        k = Koerper()
        a = fa.quetschfalte_analysieren(k.faces[2], k.faces[4], "hinten rechts")      # Wand-Innenseiten
        self.assertEqual([round(c, 6) for c in a["dreieck_mm"][2]], [0.0, 30.0, 30.0], "Falte immer auf der AUSSENseite")

    def test_unterschiedliche_hoehen_abgelehnt(self):
        fa = _fa()
        k = Koerper(hoehe2=2.0)                                    # Wand 2 nur 20 mm hoch
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.quetschfalte_analysieren(k.w1, k.w2, "hinten rechts")
        self.assertIn("unterschiedlich hoch", str(cm.exception))

    def test_gleiche_flaeche_und_falsche_koerper(self):
        fa = _fa()
        k = Koerper()
        with self.assertRaises(fa.AdapterFehler):
            fa.quetschfalte_analysieren(k.w1, k.w1, "hinten rechts")
        k2 = Koerper()
        k2.w2.body = type("B", (), {"entityToken": "K2"})()
        with self.assertRaises(fa.AdapterFehler):
            fa.quetschfalte_analysieren(k.w1, k2.w2, "hinten rechts")

    def test_abwicklung_gesperrt_bei_quetschfalte(self):
        fa = _fa()
        comp = type("C", (), {"bRepBodies": [type("B", (), {"attributes": type("A", (), {"itemByName": lambda s, g, n: type("At", (), {"value": '{"x": 1}'})()})()})()],
                              "name": "T"})()
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abwicklung(comp)
        self.assertIn("Quetschfalte", str(cm.exception))


class DxfEcke(unittest.TestCase):
    def test_dxf_layer_und_kontur(self):
        from spengler_cad.core import quetschfalte as qf
        from spengler_cad.manufacturing import quetschfalte_dxf as qd
        z = qf.zuschnitt(90.0, 30.0)
        txt = qd.ecke_dxf(z, "Test").inhalt()
        for layer in ("AUSSCHNITT", "BIEGUNG_OBEN", "BIEGUNG_QUETSCHFALTE", "BIEGUNG_ECKLINIE"):
            self.assertIn(layer, txt)
        self.assertGreater(qd.ecke_flaeche_mm2(z), 0)

    def test_befehl_registriert(self):
        import inspect
        from spengler_cad.commands import command_registry, quetschfalte_command
        self.assertIn("quetschfalte_command.registrieren()", inspect.getsource(command_registry))
        self.assertEqual(quetschfalte_command.BID, "spenglerQuetschfalte")


class SkizzeUndProfil(unittest.TestCase):
    def test_profil_fehler_nennt_gefundene_flaechen(self):
        fa = _fa()

        class Pr(object):
            def __init__(self, a):
                self._a = a

            def areaProperties(self):
                return type("A", (), {"area": self._a / 100.0})()

        class Skizze(object):
            sketchCurves = type("C", (), {"count": 3})()
            profiles = type("L", (), {"count": 2, "item": lambda s, i: (Pr(120.0), Pr(80.0))[i]})()
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa._profil_waehlen(Skizze(), 200.0)
        t = str(cm.exception)
        self.assertIn("3 Kurven", t)
        self.assertIn("120.00, 80.00", t, "Live 0.4.71: ohne diese Angabe war die Ursache nicht erkennbar")

    def test_skizze_ueber_konstruktionsebene_mit_rueckfall(self):
        fa = _fa()
        rb = fa.Rueckbau("t")
        aufrufe = []

        class Ebenen(object):
            def createInput(self):
                return type("I", (), {"setByPlane": lambda s, g: aufrufe.append(("plane", g))})()

            def add(self, i):
                return object()

        class Skizzen(object):
            def add(self, ziel):
                aufrufe.append(("skizze", ziel))
                return object()
        comp = type("C", (), {"constructionPlanes": Ebenen(), "sketches": Skizzen()})()
        flaeche = type("F", (), {"geometry": "GEOM"})()
        fa._skizze_in_ebene(comp, flaeche, rb)
        self.assertEqual(aufrufe[0], ("plane", "GEOM"))
        self.assertNotEqual(aufrufe[1][1], flaeche, "Skizze auf der Konstruktionsebene, nicht auf der Fläche (keine Auto-Projektion)")
        # Rückfall, wenn die Ebene nicht anlegbar ist
        aufrufe.clear()
        Ebenen.createInput = lambda s: (_ for _ in ()).throw(RuntimeError("keine Ebene"))
        fa._skizze_in_ebene(comp, flaeche, fa.Rueckbau("t"))
        self.assertEqual(aufrufe[-1], ("skizze", flaeche))


class ZerschnittenesDreieck(unittest.TestCase):
    """Live 0.4.71/0.4.72: 3 Profile mit 855.07 / 179.46 / 20.54 bzw. 882.00 / 167.27 / 32.73 mm² – das 200-mm²-Dreieck ist in zwei Teile zerschnitten."""
    def _skizze(self, flaechen):
        class Pr(object):
            def __init__(self, a):
                self.a = a

            def areaProperties(self):
                return type("A", (), {"area": self.a / 100.0})()
        profile = [Pr(a) for a in flaechen]
        return type("S", (), {"profiles": type("L", (), {"count": len(profile), "item": lambda s, i: profile[i]})(),
                              "sketchCurves": type("C", (), {"count": 8})()})(), profile

    def test_zwei_teile_ergeben_das_dreieck(self):
        fa = _fa()

        class Sammlung(object):
            def __init__(self):
                self.teile = []

            @staticmethod
            def create():
                return Sammlung()

            def add(self, p):
                self.teile.append(p)
        orig = fa.adsk.core.ObjectCollection
        fa.adsk.core.ObjectCollection = Sammlung
        self.addCleanup(setattr, fa.adsk.core, "ObjectCollection", orig)
        for flaechen in ((855.07, 179.46, 20.54), (882.00, 167.27, 32.73)):
            sk, profile = self._skizze(flaechen)
            r = fa._profile_summe_waehlen(sk, 200.0)
            self.assertIsInstance(r, Sammlung, "mehrere Teilprofile werden zusammen extrudiert")
            self.assertEqual(len(r.teile), 2)
            self.assertAlmostEqual(sum(p.a for p in r.teile), 200.0, delta=0.05, msg=str(flaechen))
            self.assertNotIn(profile[0], r.teile, "das grosse Aussenprofil (855/882 mm²) gehört nicht dazu")

    def test_einzelnes_profil_hat_vorrang(self):
        fa = _fa()
        sk, profile = self._skizze((855.07, 200.0, 20.54))
        self.assertIs(fa._profile_summe_waehlen(sk, 200.0), profile[1])

    def test_nichts_passend_wirft_mit_angaben(self):
        fa = _fa()
        sk, _ = self._skizze((855.07, 100.0))
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa._profile_summe_waehlen(sk, 200.0)
        self.assertIn("8 Kurven", str(cm.exception))


class ZweiteLageEbene(unittest.TestCase):
    def test_ebene_direkt_aus_geometrie_ohne_flaeche(self):
        fa = _fa()
        gesetzt = []

        class Ebenen(object):
            def createInput(self):
                return type("I", (), {"setByPlane": lambda s, g: gesetzt.append(g)})()

            def add(self, i):
                return object()
        comp = type("C", (), {"constructionPlanes": Ebenen(), "sketches": type("S", (), {"add": lambda s, e: object()})()})()
        fa._skizze_in_ebene(comp, None, fa.Rueckbau("t"), "EBENE")
        self.assertEqual(gesetzt, ["EBENE"], "zweite Lage: Ebene aus Wandebene + Blechdicke, keine Flächensuche")

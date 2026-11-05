"""Rückbau-Analyse 0.4.59 (Auftrag «Fehleranalyse und Stabilisierung ab 0.4.58»): Nachweis des Löschens von Blechregeln über die Design-Regel-Liste,
alle Rückbau-Proben laufen durch, Live-Bericht in der Cloud vollständig. Attrappen – KEIN Fusion-Test."""
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import livetest_bericht as lb


def _fa():
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class SheetMetalRule(object):
    """Attrappe mit dem echten Klassennamen; deleteMe-Ergebnis und Verbleib in der Liste getrennt steuerbar."""
    def __init__(self, name, liste, meldet=True, entfernt=True, gueltig_danach=True):
        self.name, self._liste, self._meldet, self._entfernt, self._gueltig = name, liste, meldet, entfernt, gueltig_danach
        self.isValid, self.isUsed, self.thickness = True, False, None

    def deleteMe(self):
        if self._entfernt:
            self._liste.remove(self)
        self.isValid = self._gueltig            # bewusst: isValid bleibt wahr, obwohl die Regel weg ist
        return self._meldet


class _Regeln(object):
    def __init__(self):
        self.l = []

    @property
    def count(self):
        return len(self.l)

    def item(self, i):
        return self.l[i]

    def remove(self, r):
        self.l.remove(r)


class RegelLoeschen(unittest.TestCase):
    def setUp(self):
        fa = _fa()
        self.regeln = _Regeln()
        d = type("D", (), {"designSheetMetalRules": self.regeln})()
        orig = fa.design
        fa.design = lambda: d
        self.addCleanup(setattr, fa, "design", orig)

    def regel(self, **kw):
        r = SheetMetalRule("Spengler 0.65 mm", self.regeln, **kw)
        self.regeln.l.append(r)
        return r

    def test_weg_obwohl_isvalid_wahr(self):
        self.assertIsNone(_fa()._loeschen(self.regel()), "Nachweis über die Regel-Liste, nicht über isValid")

    def test_deleteme_false_aber_weg(self):
        self.assertIsNone(_fa()._loeschen(self.regel(meldet=False)))

    def test_noch_da_wird_mit_namen_gemeldet(self):
        r = self.regel(entfernt=False, meldet=False)
        r.isUsed = True
        p = _fa()._loeschen(r)
        self.assertIn("Spengler 0.65 mm", p)
        self.assertIn("noch in den Design-Regeln", p)
        self.assertIn("noch verwendet", p)


class ProbenSammeln(unittest.TestCase):
    def test_alle_proben_laufen_auch_nach_fehler(self):
        from spengler_cad.diagnostics import live_test as lt
        gelaufen = []

        def ok(n):
            gelaufen.append(n)
            return n + ": ok"

        def falsch():
            gelaufen.append("b")
            raise lt._Falsch("b: UNVOLLSTÄNDIG")
        with self.assertRaises(lt._Falsch) as cm:
            lt.proben_sammeln([("a", lambda: ok("a")), ("b", falsch), ("c", lambda: ok("c"))])
        self.assertEqual(gelaufen, ["a", "b", "c"], "Probe c läuft trotz Fehler bei b")
        self.assertIn("c: ok", str(cm.exception))
        self.assertIn("✗ b: UNVOLLSTÄNDIG", str(cm.exception))


class CloudBericht(unittest.TestCase):
    E = [{"name": "Gerollt %d" % i, "status": "fehler", "detail": "x" * 3000} for i in range(4)] + \
        [{"name": "Rückbau", "status": "fehler", "detail": "Zeile 1\nRest: Skizze «S1»: deleteMe() meldet False"},
         {"name": "Flansch", "status": "ok", "detail": "gut"}]

    def test_notiz_enthaelt_jeden_auffaelligen_schritt(self):
        n = lb.cloud_notiz(self.E)
        self.assertLessEqual(len(n), lb.NOTIZ_MAX)
        self.assertIn("Rückbau: Zeile 1 / Rest: Skizze", n, "auch nach langen Schritten, inkl. Folgezeilen")

    def test_protokoll_bericht_zuerst_log_hinten_gekuerzt(self):
        p = lb.cloud_protokoll(self.E, "Kopf", "LOG" * 20000)
        self.assertLessEqual(len(p), lb.PROTOKOLL_MAX)
        self.assertTrue(p.startswith("Kopf"))
        self.assertIn("Rest: Skizze «S1»: deleteMe() meldet False", p)
        self.assertIn("=== Alle Schritte ===", p)
        self.assertTrue(p.endswith("LOG"), "vom Protokoll bleibt das Ende")


class ZustandErweitert(unittest.TestCase):
    def test_neue_schluessel_im_vergleich(self):
        from spengler_cad.diagnostics import live_test as lt
        for k in ("konstruktionspunkte", "abwicklungen", "blechregel_namen"):
            self.assertIn(k, lt.ZUSTAND_GLEICH)
        from spengler_cad.core import livetest_messung as m
        abw, offen = m.zustand_vergleich({"blechregel_namen": ("A",), "vol": 1.0}, {"blechregel_namen": ("A", "Spengler 0.65 mm"), "vol": 1.0},
                                         ("blechregel_namen",))
        self.assertEqual(abw[0][0], "blechregel_namen")
        abw, offen = m.zustand_vergleich({"abwicklungen": 0, "vol": 1.0}, {"abwicklungen": None, "vol": 1.0}, ("abwicklungen",))
        self.assertEqual(offen, ["abwicklungen"], "beschädigte Abwicklung = nicht messbar, nie «unverändert»")


class GehrungDiagnose(unittest.TestCase):
    def test_diagnose_nennt_winkel_und_abstand(self):
        from spengler_cad.core import gehrung
        e1, e2, nb, ecke = (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)
        k = [(0, (1, 0, 0), (0.5, 5, 10)), (1, (0.7071, -0.7071, 0), (1, 1, 10)), (2, (0, 0, 1), (50, 50, 1))]
        t = gehrung.diagnose(k, e1, e2, nb, ecke)
        self.assertIn("e1 1.00, e2 0.00", t, "stumpfe Stirnfläche ⟂ Kante 1")
        self.assertIn("e1 0.71, e2 0.71", t)
        self.assertEqual(gehrung.gehrungsflaechen(k, e1, e2, nb, ecke), [1])
        self.assertEqual(gehrung.gehrungsflaechen(k, e1, e2, nb, ecke, reichweite_mm=1.0), [], "Reichweite in denselben Einheiten wie die Ecke")


class GerolltFixture(unittest.TestCase):
    def test_abhaengige_tests_nicht_getestet_statt_fehler(self):
        from spengler_cad.diagnostics import live_test as lt, live_test_gekruemmt as gk
        gk.FIXTURE_GEROLLT.clear()
        gk.FIXTURE_GEROLLT.update(ok=False, grund="Konturflansch: Signatur (entities, distance)")
        self.addCleanup(gk.FIXTURE_GEROLLT.clear)
        with self.assertRaises(lt._Uebersprungen) as cm:
            gk._segment("x")
        self.assertIn("Testkörper gerolltes Blech", str(cm.exception))
        self.assertIn("Signatur", str(cm.exception))

    def test_signatur_wird_gelesen(self):
        def createContourFlangeInput(entities, distance):
            """Creates a contour flange input."""
        s = _fa()._signatur(createContourFlangeInput)
        self.assertIn("(entities, distance)", s)
        self.assertIn("contour flange", s)


class AbstandMessung(unittest.TestCase):
    """Live 0.4.57: «Abstand Detail↔Fläche nicht messbar» – der MeasureManager bekam eine Occurrence. Jetzt: Körper der Occurrence gegen die Fläche."""
    def setUp(self):
        fa = _fa()
        self.aufrufe = []
        testfall = self

        class MM(object):
            def measureMinimumDistance(self, a, b):
                testfall.aufrufe.append((type(a).__name__, type(b).__name__))
                if type(a).__name__ == "Occ":
                    raise RuntimeError("3 : invalid argument geometry")
                return type("R", (), {"value": 0.2})()
        orig = fa.app
        fa.app = lambda: type("A", (), {"measureManager": MM()})()
        self.addCleanup(setattr, fa, "app", orig)

    def test_occurrence_wird_in_koerper_aufgeloest(self):
        fa = _fa()

        class Body(object):
            pass

        class Bodies(object):
            count = 1

            def item(self, i):
                return Body()

        class Occ(object):
            transform, component, bRepBodies = None, None, Bodies()

        class Face(object):
            assemblyContext = "root"
        gruende = []
        self.assertAlmostEqual(fa.abstand_mm(Occ(), Face(), gruende), 2.0)
        self.assertEqual(self.aufrufe, [("Body", "Face")])
        self.assertEqual(gruende, [])

    def test_nicht_messbar_mit_grund(self):
        fa = _fa()

        class Occ(object):
            pass
        gruende = []
        self.assertIsNone(fa.abstand_mm(Occ(), Occ(), gruende))
        self.assertIn("invalid argument", gruende[0])

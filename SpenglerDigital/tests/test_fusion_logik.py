"""Logik des Geometrieadapters mit NACHGEBAUTEN Fusion-Objekten (Vektoren, Kanten, Features, Eingabeobjekte).

WICHTIG: Das prüft nur die Entscheidungslogik des Add-ins (welche Kante, wann Abbruch, Rückbau, Einheiten, welche
Eigenschaft gesetzt wird). Ob Fusion die Eigenschaften so nennt und so ausführt, zeigt NUR der Live-Test in Fusion.
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
import adsk  # noqa: E402  Attrappe
import adsk.core  # noqa: E402
import adsk.fusion  # noqa: E402

from _basis import DatenTest  # noqa: E402

# Konstanten und statische Methoden der Attrappe festlegen, damit Vergleiche funktionieren
adsk.core.Curve3DTypes.Line3DCurveType = "LINIE"
adsk.core.Curve3DTypes.Arc3DCurveType = "BOGEN"
adsk.core.Curve3DTypes.Circle3DCurveType = "KREIS"
adsk.core.Curve3DTypes.Ellipse3DCurveType = "ELLIPSE"
adsk.core.Curve3DTypes.EllipticalArc3DCurveType = "ELLBOGEN"
adsk.core.Curve3DTypes.NurbsCurve3DCurveType = "NURBS"
adsk.core.ValueInput.createByString = staticmethod(lambda s: s)
adsk.core.ObjectCollection.createWithArray = staticmethod(lambda a: ("Sammlung", tuple(a)))
adsk.fusion.BRepEdge.cast = staticmethod(lambda x: x)

from spengler_cad.geometry import edge_resolver, fusion_adapter as fa  # noqa: E402


class V(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def vectorTo(self, p):
        return V(p.x - self.x, p.y - self.y, p.z - self.z)

    @property
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalize(self):
        L = self.length
        self.x, self.y, self.z = self.x / L, self.y / L, self.z / L

    def dotProduct(self, o):
        return self.x * o.x + self.y * o.y + self.z * o.z

    def crossProduct(self, o):
        return V(self.y * o.z - self.z * o.y, self.z * o.x - self.x * o.z, self.x * o.y - self.y * o.x)


class Geo(object):
    def __init__(self, a, b, typ="LINIE"):
        self.startPoint, self.endPoint, self.curveType = a, b, typ


_nr = [0]


class Kante(object):
    def __init__(self, a, b, typ="LINIE", flaechen=None, body=None):
        _nr[0] += 1
        self.tempId = _nr[0]
        self.isValid = True
        self.geometry = Geo(V(*a), V(*b), typ)
        self.length = V(*a).vectorTo(V(*b)).length
        self.faces = Liste(flaechen or [])
        self.body = body
        self.startVertex = type("P", (), {"geometry": V(*a)})()
        self.endVertex = type("P", (), {"geometry": V(*b)})()


class Liste(list):
    @property
    def count(self):
        return len(self)

    def item(self, i):
        return self[i]


class Flaeche(object):
    def __init__(self, kanten=(), area=1.0):
        self.edges = list(kanten)
        self.area = area


class Feature(object):
    def __init__(self, flaechen, name="F"):
        self.faces = flaechen
        self.name = name
        self.isValid = True
        self.geloescht = False
        self.attribute = []
        self.attributes = type("A", (), {"add": lambda s, g, n, w: self.attribute.append((g, n, w))})()

    def deleteMe(self):
        self.geloescht = True
        self.isValid = False


def flansch_feature(L_cm=50.0, H_mm=25.0, t_mm=0.7, extra=()):
    """Flansch 90° an einer Kante entlang x: Ende des Flansches bei z = H, zwei Endkanten (Abstand t), Biegekanten nahe 0."""
    H, t = H_mm / 10, t_mm / 10
    k_oben = Kante((0, 0, H), (L_cm, 0, H))
    k_unten = Kante((0, t, H), (L_cm, t, H))
    biege = Kante((0, 0.05, 0.1), (L_cm, 0.05, 0.1))
    quer = Kante((0, 0, 0), (0, 0, H))   # nicht parallel
    kurz = Kante((0, 0, H * 0.9), (L_cm / 2, 0, H * 0.9))   # parallel, aber nicht über die ganze Länge
    ext = [Kante((0, 0, h / 10), (L_cm, 0, h / 10)) for h in extra]
    return Feature([Flaeche([k_oben, biege, quer]), Flaeche([k_unten, kurz] + ext)]), k_oben, k_unten


class AussenkanteTest(unittest.TestCase):
    def setUp(self):
        self.vorher = Kante((0, 0, 0), (50, 0, 0))

    def test_findet_flanschende(self):
        feat, oben, unten = flansch_feature()
        self.assertIs(fa.neue_aussenkante(feat, self.vorher, 25.0, 0.7), unten)  # weiter entfernte des Paars (wie Prototyp)

    def test_nicht_gefunden(self):
        feat, _, _ = flansch_feature(H_mm=5.0)        # erwartet 25 mm, Ende liegt bei 5 mm → unplausibel
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.neue_aussenkante(feat, self.vorher, 25.0, 0.7)
        self.assertIn("nicht gefunden", str(cm.exception))

    def test_mehrdeutig_bricht_ab(self):
        feat, _, _ = flansch_feature(extra=(18.0,))   # dritte parallele, volle Kante in plausibler Entfernung
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.neue_aussenkante(feat, self.vorher, 25.0, 0.7)
        self.assertIn("mehrdeutig", str(cm.exception))

    def test_ohne_flaechen(self):
        with self.assertRaises(fa.AdapterFehler):
            fa.neue_aussenkante(object(), self.vorher, 25.0, 0.7)


class Eingabe(object):
    """Nachgebautes EdgeFlangeInput/HemFeatureInput: nur die übergebenen Eigenschaften existieren."""
    def __init__(self, *eigenschaften):
        object.__setattr__(self, "_erlaubt", set(eigenschaften))
        object.__setattr__(self, "werte", {})

    def __getattr__(self, n):
        if n in self._erlaubt:
            return self.werte.get(n)
        raise AttributeError(n)

    def __setattr__(self, n, v):
        if n not in self._erlaubt:
            raise AttributeError(n)
        self.werte[n] = v


class Sammlung(object):
    def __init__(self, inp, fehler_ohne_args=False):
        self.inp, self.hinzu, self.fehler_ohne_args = inp, [], fehler_ohne_args
        self.aufrufe = []

    def createEdgeFlangeInput(self, kanten, hoehe):
        self.aufrufe.append((kanten, hoehe))
        return self.inp

    def createHemFeatureInput(self, *args):
        self.aufrufe.append(args)
        if not args and self.fehler_ohne_args:
            raise TypeError("createHemFeatureInput() missing argument")
        return self.inp

    def add(self, inp):
        self.hinzu.append(inp)
        return Feature([], "neu")


def kante_mit(flange=None, hem=None):
    feats = type("Feats", (), {})()
    if flange is not None:
        feats.flangeFeatures = flange
    if hem is not None:
        feats.hemFeatures = hem
    comp = type("Comp", (), {"features": feats})()
    k = Kante((0, 0, 0), (50, 0, 0))
    k.body = type("Body", (), {"parentComponent": comp})()
    return k


class FlanschTest(unittest.TestCase):
    def test_werte_und_einheiten(self):
        inp = Eingabe("flangeAngle", "isFlipped", "bendRadiusOverride")
        ff = Sammlung(inp)
        fa.flansch(kante_mit(ff), -45, 25, 5)
        self.assertEqual(ff.aufrufe[0][1], "25 mm")
        self.assertEqual(inp.werte, {"flangeAngle": "45 deg", "isFlipped": True, "bendRadiusOverride": "5 mm"})
        self.assertEqual(len(ff.hinzu), 1)

    def test_kein_stilles_ersetzen(self):
        for eig, args, text in ((("isFlipped",), (45, 20), "Flanschwinkel"), (("flangeAngle",), (-90, 20), "Flanschrichtung"),
                                (("flangeAngle",), (90, 20, 3), "Biegeradius")):
            ff = Sammlung(Eingabe(*eig))
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.flansch(kante_mit(ff), *args)
            self.assertIn(text, str(cm.exception))
            self.assertEqual(ff.hinzu, [], "bei fehlender Einstellung wird NICHT gebaut")

    def test_90_grad_ohne_winkeleigenschaft(self):
        ff = Sammlung(Eingabe())
        fa.flansch(kante_mit(ff), 90, 20)
        self.assertEqual(len(ff.hinzu), 1)

    def test_ohne_api(self):
        with self.assertRaises(fa.AdapterFehler):
            fa.flansch(kante_mit(), 90, 20)


class UmschlagTest(unittest.TestCase):
    def test_ohne_argumente_dann_kante(self):
        inp = Eingabe("edges", "length", "gap", "isFlipped")
        hf = Sammlung(inp)
        k = kante_mit(hem=hf)
        fa.umschlag(k, 7, True)
        self.assertEqual(hf.aufrufe[0], ())
        self.assertEqual(inp.werte["edges"], [k])
        self.assertEqual((inp.werte["length"], inp.werte["gap"], inp.werte["isFlipped"]), ("7 mm", "0 mm", True))

    def test_aeltere_aufrufform(self):
        inp = Eingabe("length")
        hf = Sammlung(inp, fehler_ohne_args=True)
        fa.umschlag(kante_mit(hem=hf), 10, False, radius_mm=1.5)
        self.assertEqual(len(hf.aufrufe[1]), 1, "Rückfall auf createHemFeatureInput([kante])")
        self.assertEqual(len(hf.hinzu), 1)

    def test_laenge_nicht_setzbar(self):
        hf = Sammlung(Eingabe("edges"))
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.umschlag(kante_mit(hem=hf), 7, False)
        self.assertIn("Umschlaglänge", str(cm.exception))
        self.assertEqual(hf.hinzu, [])


class RueckbauTest(unittest.TestCase):
    def setUp(self):
        self.alt = (fa.flansch, fa.umschlag, fa.neue_aussenkante)
        self.feats = []

    def tearDown(self):
        fa.flansch, fa.umschlag, fa.neue_aussenkante = self.alt

    def _bauen(self, fehler_bei=None, kante_fehlt=False, loeschen_klappt=True):
        def flansch(k, w, L, r=None):
            if fehler_bei == len(self.feats) + 1:
                raise RuntimeError("Fusion: Flansch fehlgeschlagen\nInternal error 42")
            f = Feature([], "F%d" % (len(self.feats) + 1))
            if not loeschen_klappt:
                f.deleteMe = lambda: (_ for _ in ()).throw(RuntimeError("gesperrt"))
            self.feats.append(f)
            return f

        def kante(feat, vorher, L, t):
            if kante_fehlt:
                raise fa.AdapterFehler("Neue Aussenkante nicht gefunden")
            return vorher
        fa.flansch, fa.umschlag, fa.neue_aussenkante = flansch, flansch, kante
        ops = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None},
               {"typ": "flansch", "winkel": -45, "laenge": 10, "radius": None}]
        return fa.folge_anbringen(Kante((0, 0, 0), (50, 0, 0)), ops, 0.7, {"vorlageId": "kv-x", "vorlageVersion": 3})

    def test_erfolg_markiert(self):
        f = self._bauen()
        self.assertEqual(len(f), 3)
        self.assertIn('"vorlageVersion": 3', f[0].attribute[0][2])
        self.assertIn('"schritt": 1', f[0].attribute[0][2])

    def test_fehler_baut_zurueck(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            self._bauen(fehler_bei=3)
        self.assertTrue(all(f.geloescht for f in self.feats), "Schritte 1 und 2 wieder entfernt")
        self.assertIn("Schritt 3", str(cm.exception))
        self.assertIn("Internal error 42", str(cm.exception))
        self.assertIn("wieder entfernt", str(cm.exception))
        self.assertTrue(cm.exception.rueckbau_ok)

    def test_kante_nicht_gefunden(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            self._bauen(kante_fehlt=True)
        self.assertIn("Nach Schritt 1", str(cm.exception))
        self.assertTrue(self.feats[0].geloescht)

    def test_rueckbau_unvollstaendig_wird_gemeldet(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            self._bauen(fehler_bei=2, loeschen_klappt=False)
        self.assertFalse(cm.exception.rueckbau_ok)
        self.assertIn("Strg+Z", str(cm.exception))


def _schreibe(p):
    with open(p, "w") as f:
        f.write("0\nEOF\n")
    return True


class Box(object):
    def __init__(self, a, b):
        self.minPoint, self.maxPoint = V(*a), V(*b)


class AbwicklungTest(unittest.TestCase):
    def test_masse_unabhaengig_von_lage(self):
        for bb in (Box((0, 0, 0), (12, 100, 0.07)), Box((0, 0, 0), (12, 0.07, 100)), Box((-5, 3, 0), (-4.93, 15, 100))):
            body = type("B", (), {"boundingBox": bb, "faces": [Flaeche(area=1100.0), Flaeche(area=7.0)]})()
            m = fa.abwicklung_masse(type("FP", (), {"flatBody": body})())
            self.assertAlmostEqual(m["laenge"], 1000.0)
            self.assertAlmostEqual(m["breite"], 120.0)
            self.assertAlmostEqual(m["flaeche"], 110000.0)

    def test_ohne_koerper(self):
        with self.assertRaises(fa.AdapterFehler):
            fa.abwicklung_masse(type("FP", (), {"flatBody": None, "body": None, "bodies": None})())

    def test_dxf_nur_wenn_datei_existiert(self):
        import tempfile
        pfad = os.path.join(tempfile.mkdtemp(), "a.dxf")
        em = type("EM", (), {"createDXFFlatPatternExportOptions": lambda s, p, fp: p, "execute": lambda s, o: True})()
        alt = fa.design
        fa.design = lambda: type("D", (), {"exportManager": em})()
        try:
            with self.assertRaises(fa.AdapterFehler, msg="Fusion meldet Erfolg, aber keine Datei"):
                fa.dxf_abwicklung(object(), pfad)
            em.execute = lambda o: _schreibe(o)
            self.assertEqual(fa.dxf_abwicklung(object(), pfad), pfad)
        finally:
            fa.design = alt


class KantenTest(unittest.TestCase):
    def test_beschreibung_und_aussenkante(self):
        regel = type("R", (), {"thickness": type("T", (), {"value": 0.07})()})()
        body = type("B", (), {"isSheetMetal": True, "parentComponent": type("C", (), {"activeSheetMetalRule": regel})()})()
        aussen = Kante((0, 0, 0), (50, 0, 0), flaechen=[Flaeche(area=50 * 20.0), Flaeche(area=50 * 0.07)], body=body)
        d = fa.kante_beschreiben(aussen)
        self.assertEqual((d["kurve"], d["laenge"], round(d["dicke"], 6), d["frei"], d["blech"]), ("linie", 500.0, 0.7, True, True))
        innen = Kante((0, 0, 0), (50, 0, 0), flaechen=[Flaeche(area=50 * 20.0), Flaeche(area=50 * 3.0)], body=body)
        self.assertFalse(fa.kante_beschreiben(innen)["frei"], "Biegezone/innen: keine Stirnfläche")
        bogen = Kante((0, 0, 0), (50, 0, 0), typ="KREIS", flaechen=[Flaeche(), Flaeche()], body=body)
        self.assertEqual(fa.kante_beschreiben(bogen)["kurve"], "kreis")

    def test_aufloesen_nicht_raten(self):
        alt = fa.design
        try:
            for treffer, ok in (([], False), ([Kante((0, 0, 0), (1, 0, 0)), Kante((0, 0, 0), (1, 0, 0))], False)):
                fa.design = lambda t=treffer: type("D", (), {"findEntityByToken": lambda s, tok: t})()
                edge_resolver.design = fa.design
                with self.assertRaises(fa.AdapterFehler):
                    edge_resolver.aufloesen("tok")
            k = Kante((0, 0, 0), (1, 0, 0))
            k.isValid = True
            fa.design = lambda: type("D", (), {"findEntityByToken": lambda s, tok: [k]})()
            edge_resolver.design = fa.design
            self.assertIs(edge_resolver.aufloesen("tok"), k)
        finally:
            fa.design = alt
            edge_resolver.design = alt


class TeilnummerTest(DatenTest):
    def test_naechste_freie_nummer(self):
        class Attr(object):
            def __init__(self):
                self.d = {}

            def itemByName(self, g, n):
                return type("A", (), {"value": self.d[n]})() if n in self.d else None

            def add(self, g, n, w):
                self.d[n] = w
        vorhanden = [type("A", (), {"value": "3"})(), type("A", (), {"value": "kaputt"})(), type("A", (), {"value": "7"})()]
        alt = fa.design
        fa.design = lambda: type("D", (), {"findAttributes": lambda s, g, n: vorhanden})()
        try:
            b = type("B", (), {"nativeObject": None, "attributes": Attr()})()
            self.assertIsNone(fa.teilnummer(b, vergeben=False))
            self.assertEqual(fa.teilnummer(b), 8)
            self.assertEqual(fa.teilnummer(b), 8, "einmal vergeben bleibt die Nummer")
        finally:
            fa.design = alt


if __name__ == "__main__":
    unittest.main()

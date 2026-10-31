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


class Radiusueberschreibung(object):
    """Nachbau BendRadiusOverride (echte API: setOverride(ValueInput) → bool)."""
    def __init__(self, klappt=True):
        self.klappt, self.wert = klappt, None

    def setOverride(self, v):
        self.wert = v
        return self.klappt


class FlanschTest(unittest.TestCase):
    """Nach der echten API (EdgeFlangeInput: angle, isFlipped, bendRadiusOverride.setOverride) – ohne Fusion nachgebaut."""
    def test_werte_und_einheiten(self):
        inp = Eingabe("angle", "isFlipped", "bendRadiusOverride")
        inp.werte["bendRadiusOverride"] = ov = Radiusueberschreibung()
        ff = Sammlung(inp)
        fa.flansch(kante_mit(ff), -45, 25, 5)
        self.assertEqual(ff.aufrufe[0][1], "25 mm")
        self.assertEqual((inp.werte["angle"], inp.werte["isFlipped"], ov.wert), ("45 deg", True, "5 mm"))
        self.assertEqual(len(ff.hinzu), 1)

    def test_kein_stilles_ersetzen(self):
        def mit_radius(klappt):
            e = Eingabe("angle", "bendRadiusOverride")
            e.werte["bendRadiusOverride"] = Radiusueberschreibung(klappt)
            return e
        for inp, args, text in ((Eingabe("isFlipped"), (45, 20), "Flanschwinkel"), (Eingabe("angle"), (-90, 20), "Flanschrichtung"),
                                (Eingabe("angle"), (90, 20, 3), "Biegeradius"), (mit_radius(False), (90, 20, 3), "Biegeradius")):
            ff = Sammlung(inp)
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.flansch(kante_mit(ff), *args)
            self.assertIn(text, str(cm.exception))
            self.assertEqual(ff.hinzu, [], "bei fehlender Einstellung wird NICHT gebaut")

    def test_90_grad_ohne_winkeleigenschaft(self):
        ff = Sammlung(Eingabe())
        fa.flansch(kante_mit(ff), 90, 20)
        self.assertEqual(len(ff.hinzu), 1)

    def test_mit_dicke_kommen_radius_und_offener_saum_dazu(self):
        inp = HemEingabe(ergebnis=False)
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.umschlag(kante_mit(hem=Sammlung(inp)), 12, False, None, None, 0.6)
        self.assertIn("16 Varianten", str(cm.exception), "Regel, 2 Radien (hier nicht einstellbar), offener Saum")
        self.assertEqual(sum(1 for a in inp.aufrufe if a[0] == "open"), 4)

    def test_ohne_api(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(kante_mit(), 90, 20)
        self.assertIn("Oktober 2026", str(cm.exception))

    def test_runde_kante_wird_versucht_und_fusions_antwort_gemeldet(self):
        class Wirft(Sammlung):
            def createEdgeFlangeInput(self, kanten, hoehe):
                raise RuntimeError("Edges must be linear")
        k = kante_mit(Wirft(Eingabe("angle")))
        k.geometry.curveType = "KREIS"
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(k, 90, 20)
        self.assertIn("Edges must be linear", str(cm.exception))
        self.assertIn("nur an geraden Kanten", str(cm.exception))
        ff = Sammlung(Eingabe("angle"))
        ff.createEdgeFlangeInput = lambda kanten, hoehe: None     # Fusion liefert null
        k2 = kante_mit(ff)
        k2.geometry.curveType = "BOGEN"
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(k2, 90, 20)
        self.assertIn("lehnt den Flansch an dieser runden Kante ab", str(cm.exception))

    def test_runde_kante_klappt_wenn_fusion_sie_nimmt(self):
        ff = Sammlung(Eingabe("angle"))
        k = kante_mit(ff)
        k.geometry.curveType = "KREIS"
        fa.flansch(k, 90, 20)
        self.assertEqual(len(ff.hinzu), 1)

    def test_mehrere_kanten_in_einem_feature_mit_gehrung(self):
        inp = Eingabe("angle", "isMiteredCorners")
        ff = Sammlung(inp)
        k1 = kante_mit(ff)
        k2 = Kante((0, 0, 0), (0, 30, 0))
        k2.body = k1.body
        fa.flansch([k1, k2], 90, 20)
        self.assertEqual(ff.aufrufe[0][0], [k1, k2], "beide Kanten in einer Eingabe")
        self.assertEqual(len(ff.hinzu), 1)
        self.assertTrue(inp.werte["isMiteredCorners"])


class HemEingabe(object):
    """Nachbau HemFeatureInput: setFlatHem/setOpenHem merken die Argumente und liefern True/False."""
    def __init__(self, ergebnis=True, wirft=None):
        self.aufrufe, self.ergebnis, self.wirft = [], ergebnis, wirft

    def _set(self, name, *a):
        if self.wirft:
            raise RuntimeError(self.wirft)
        self.aufrufe.append((name,) + a)
        return self.ergebnis

    def setFlatHem(self, *a):
        return self._set("flat", *a)

    def setOpenHem(self, *a):
        return self._set("open", *a)


class UmschlagTest(unittest.TestCase):
    """Nach der echten API: createHemFeatureInput() ohne Argumente, dann setFlatHem/setOpenHem (Fusion 2025-09, help.autodesk.com)."""
    def test_geschlossener_saum_ohne_radius(self):
        inp = HemEingabe()
        hf = Sammlung(inp)
        k = kante_mit(hem=hf)
        fa.umschlag(k, 7, True)
        self.assertEqual(hf.aufrufe[0], ())
        name, kante, laenge, geflippt, position = inp.aufrufe[0]
        self.assertEqual((name, kante, laenge, geflippt), ("flat", k, "7 mm", True))
        self.assertEqual(len(hf.hinzu), 1)

    def test_radius_der_vorlage_macht_keinen_offenen_saum(self):
        inp = HemEingabe()
        fa.umschlag(kante_mit(hem=Sammlung(inp)), 10, False, radius_mm=1.5)
        self.assertEqual(inp.aufrufe[0][0], "flat", "Live-Test: offener Saum scheiterte, Radius kommt aus der Blechregel")

    def test_fusion_lehnt_ab_oder_wirft(self):
        for inp, text in ((HemEingabe(ergebnis=False), "abgelehnt"), (HemEingabe(wirft="Kante ungültig"), "Kante ungültig")):
            hf = Sammlung(inp)
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.umschlag(kante_mit(hem=hf), 7, False)
            self.assertIn(text, str(cm.exception))
            self.assertIn("4 Varianten", str(cm.exception), "Lage kante/tangential × beide Richtungen wurden versucht")
            self.assertEqual(hf.hinzu, [], "bei abgelehnter Definition wird NICHT gebaut")

    def test_berechnung_scheitert_naechste_variante(self):
        """Live-Test 30.10.: Fusion nahm die Definition an, hf.add scheiterte («SM_MODELING_ERROR») → andere Lage versuchen."""
        inp = HemEingabe()
        hf = Sammlung(inp)
        echte_add = hf.add
        zaehler = []

        def add(i):
            zaehler.append(1)
            if len(zaehler) < 3:
                raise RuntimeError("3 : Failed to create Hem: SM_MODELING_ERROR")
            return echte_add(i)
        hf.add = add
        fa.umschlag(kante_mit(hem=hf), 12, False)
        self.assertEqual(len(inp.aufrufe), 3, "dritte Lage hat funktioniert")
        self.assertEqual(len(hf.hinzu), 1)

    def test_ausdrueckliche_lage_zuerst_dann_die_uebrigen(self):
        """Live 0.4.9: eingestellte Lage «tangential» scheiterte allein – sie wird zuerst versucht, dann geht es mit den anderen weiter."""
        inp = HemEingabe()
        hf = Sammlung(inp)
        zaehler = []
        echte_add = hf.add

        def add(i):
            zaehler.append(1)
            if len(zaehler) < 2:
                raise RuntimeError("3 : Failed to create Hem: SM_MODELING_ERROR")
            return echte_add(i)
        hf.add = add
        fa.umschlag(kante_mit(hem=hf), 12, False, None, "tangential")
        self.assertEqual(len(inp.aufrufe), 2)

    def test_ohne_api(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(kante_mit(), 90, 20)
        self.assertIn("Oktober 2026", str(cm.exception))

    def test_runde_kante_wird_versucht_und_fusions_antwort_gemeldet(self):
        class Wirft(Sammlung):
            def createEdgeFlangeInput(self, kanten, hoehe):
                raise RuntimeError("Edges must be linear")
        k = kante_mit(Wirft(Eingabe("angle")))
        k.geometry.curveType = "KREIS"
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(k, 90, 20)
        self.assertIn("Edges must be linear", str(cm.exception))
        self.assertIn("nur an geraden Kanten", str(cm.exception))
        ff = Sammlung(Eingabe("angle"))
        ff.createEdgeFlangeInput = lambda kanten, hoehe: None     # Fusion liefert null
        k2 = kante_mit(ff)
        k2.geometry.curveType = "BOGEN"
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.flansch(k2, 90, 20)
        self.assertIn("lehnt den Flansch an dieser runden Kante ab", str(cm.exception))

    def test_runde_kante_klappt_wenn_fusion_sie_nimmt(self):
        ff = Sammlung(Eingabe("angle"))
        k = kante_mit(ff)
        k.geometry.curveType = "KREIS"
        fa.flansch(k, 90, 20)
        self.assertEqual(len(ff.hinzu), 1)

    def test_mehrere_kanten_in_einem_feature_mit_gehrung(self):
        inp = Eingabe("angle", "isMiteredCorners")
        ff = Sammlung(inp)
        k1 = kante_mit(ff)
        k2 = Kante((0, 0, 0), (0, 30, 0))
        k2.body = k1.body
        fa.flansch([k1, k2], 90, 20)
        self.assertEqual(ff.aufrufe[0][0], [k1, k2], "beide Kanten in einer Eingabe")
        self.assertEqual(len(ff.hinzu), 1)
        self.assertTrue(inp.werte["isMiteredCorners"])


class HemEingabe(object):
    """Nachbau HemFeatureInput: setFlatHem/setOpenHem merken die Argumente und liefern True/False."""
    def __init__(self, ergebnis=True, wirft=None):
        self.aufrufe, self.ergebnis, self.wirft = [], ergebnis, wirft

    def _set(self, name, *a):
        if self.wirft:
            raise RuntimeError(self.wirft)
        self.aufrufe.append((name,) + a)
        return self.ergebnis

    def setFlatHem(self, *a):
        return self._set("flat", *a)

    def setOpenHem(self, *a):
        return self._set("open", *a)


class UmschlagTest(unittest.TestCase):
    """Nach der echten API: createHemFeatureInput() ohne Argumente, dann setFlatHem/setOpenHem (Fusion 2025-09, help.autodesk.com)."""
    def test_geschlossener_saum_ohne_radius(self):
        inp = HemEingabe()
        hf = Sammlung(inp)
        k = kante_mit(hem=hf)
        fa.umschlag(k, 7, True)
        self.assertEqual(hf.aufrufe[0], ())
        name, kante, laenge, geflippt, position = inp.aufrufe[0]
        self.assertEqual((name, kante, laenge, geflippt), ("flat", k, "7 mm", True))
        self.assertEqual(len(hf.hinzu), 1)

    def test_radius_der_vorlage_macht_keinen_offenen_saum(self):
        inp = HemEingabe()
        fa.umschlag(kante_mit(hem=Sammlung(inp)), 10, False, radius_mm=1.5)
        self.assertEqual(inp.aufrufe[0][0], "flat", "Live-Test: offener Saum scheiterte, Radius kommt aus der Blechregel")

    def test_fusion_lehnt_ab_oder_wirft(self):
        for inp, text in ((HemEingabe(ergebnis=False), "abgelehnt"), (HemEingabe(wirft="Kante ungültig"), "Kante ungültig")):
            hf = Sammlung(inp)
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.umschlag(kante_mit(hem=hf), 7, False)
            self.assertIn(text, str(cm.exception))
            self.assertIn("4 Varianten", str(cm.exception), "Lage kante/tangential × beide Richtungen wurden versucht")
            self.assertEqual(hf.hinzu, [], "bei abgelehnter Definition wird NICHT gebaut")

    def test_berechnung_scheitert_naechste_variante(self):
        """Live-Test 30.10.: Fusion nahm die Definition an, hf.add scheiterte («SM_MODELING_ERROR») → andere Lage versuchen."""
        inp = HemEingabe()
        hf = Sammlung(inp)
        echte_add = hf.add
        zaehler = []

        def add(i):
            zaehler.append(1)
            if len(zaehler) < 3:
                raise RuntimeError("3 : Failed to create Hem: SM_MODELING_ERROR")
            return echte_add(i)
        hf.add = add
        fa.umschlag(kante_mit(hem=hf), 12, False)
        self.assertEqual(len(inp.aufrufe), 3, "dritte Lage hat funktioniert")
        self.assertEqual(len(hf.hinzu), 1)

    def test_ohne_api(self):
        with self.assertRaises(fa.AdapterFehler):
            fa.umschlag(kante_mit(), 7, False)


class RueckbauTest(unittest.TestCase):
    def setUp(self):
        self.alt = (fa.flansch, fa.umschlag, fa.neue_aussenkante)
        self.feats = []

    def tearDown(self):
        fa.flansch, fa.umschlag, fa.neue_aussenkante = self.alt

    def _bauen(self, fehler_bei=None, kante_fehlt=False, loeschen_klappt=True):
        def flansch(k, w, L, r=None, g=None, b=None, l=None):
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


# ---------------------------------------------------------------- Runde Kanten (Nachbau – NICHT live in Fusion)
class RundGeo(object):
    def __init__(self, c, r, n=(0, 0, 1), typ="KREIS"):
        self.center, self.radius, self.curveType = V(*c), r, typ
        self.normal = type("N", (V,), {"copy": lambda s: V(s.x, s.y, s.z)})(*n)


class Rundkante(object):
    """Kreis/Bogen um die z-Achse in Höhe z, Radius r (cm), Öffnungswinkel w (rad)."""
    def __init__(self, r, z=0.0, w=2 * math.pi, typ="KREIS"):
        _nr[0] += 1
        self.tempId = _nr[0]
        self.isValid = True
        self.geometry = RundGeo((0, 0, z), r, typ=typ)
        self.length = r * w
        self.pointOnEdge = V(r, 0, z)


class RundKanteTest(unittest.TestCase):
    def feature(self, *kanten):
        return Feature([Flaeche(list(kanten))])

    def test_kreisflansch_findet_ende(self):
        vorher = Rundkante(10.0)                         # R = 100 mm
        oben, unten = Rundkante(10.0, 2.5), Rundkante(10.07, 2.5)   # Flansch 25 mm hoch, Ende = 2 Kanten (t = 0.7 mm)
        biege = Rundkante(10.0, 0.05)                     # Biegezone nahe der Basis – unplausibel
        k = fa.neue_aussenkante(self.feature(oben, unten, biege), vorher, 25.0, 0.7)
        self.assertIn(k, (oben, unten))

    def test_andere_achse_wird_ignoriert(self):
        vorher = Rundkante(10.0)
        fremd = Rundkante(10.0, 2.5)
        fremd.geometry.center = V(5, 0, 2.5)              # nicht koaxial
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.neue_aussenkante(self.feature(fremd), vorher, 25.0, 0.7)
        self.assertIn("nicht gefunden", str(cm.exception))

    def test_bogen_braucht_gleichen_winkel(self):
        w = math.pi / 2
        vorher = Rundkante(10.0, 0, w, "BOGEN")
        gut, falsch = Rundkante(10.0, 2.5, w, "BOGEN"), Rundkante(10.0, 2.5, w / 2, "BOGEN")
        k = fa.neue_aussenkante(self.feature(gut, falsch), vorher, 25.0, 0.7)
        self.assertIs(k, gut)

    def test_rund_mehrdeutig(self):
        vorher = Rundkante(10.0)
        feat = self.feature(Rundkante(10.0, 2.5), Rundkante(10.07, 2.5), Rundkante(10.0, 1.8))
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.neue_aussenkante(feat, vorher, 25.0, 0.7)
        self.assertIn("mehrdeutig", str(cm.exception))

    def test_schlitzhinweis(self):
        def flaeche(breiten):
            f = Flaeche([type("E", (), {"length": b / 10.0})() for b in breiten])
            f.geometry = type("G", (), {"surfaceType": adsk.core.SurfaceTypes.PlaneSurfaceType})()
            return f
        adsk.core.SurfaceTypes.PlaneSurfaceType = "EBENE"
        kreis = Rundkante(10.0)
        self.assertEqual(fa.schlitze_pruefen(Feature([flaeche([0.7, 25])]), kreis, 0.7)[0][:20], "Der Flansch an der r")
        self.assertEqual(fa.schlitze_pruefen(Feature([flaeche([30, 25])]), kreis, 0.7), [])
        self.assertEqual(fa.schlitze_pruefen(Feature([flaeche([0.7, 25])]), Kante((0, 0, 0), (5, 0, 0)), 0.7), [])
        bogen = Rundkante(10.0, 0, 1.0, "BOGEN")
        self.assertEqual(fa.schlitze_pruefen(Feature([flaeche([0.7, 25]), flaeche([0.7, 25])]), bogen, 0.7), [])


# ---------------------------------------------------------------- Detail ins Modell integrieren (Nachbau – NICHT live in Fusion)
class IntegrationTest(unittest.TestCase):
    def aufbau(self, volumen_nachher=2.0, combine_fehler=None, blech=True):
        log = []

        class Koerper(object):
            isValid, isSolid, assemblyContext, entityToken = True, True, None, "tok"
            def __init__(s, v):
                s.volume = v
        ziel, danach = Koerper(1.0), Koerper(volumen_nachher)
        feats = []

        class Feat(object):
            isValid = True
            bodies = [object()]
            def __init__(s, n):
                s.n = n
            def startEdit(s): log.append("start")
            def finishEdit(s): log.append("fertig")
            def deleteMe(s):
                s.isValid = False
                log.append("del " + s.n)

        class CF(object):
            def createInput(s, z, t):
                return type("I", (), {})()

            def add(s, i):
                if combine_fehler:
                    raise RuntimeError(combine_fehler)
                f = Feat("combine"); feats.append(f); return f
        comp = type("C", (), {})()
        comp.features = type("F", (), {"baseFeatures": type("B", (), {"add": lambda s: (feats.append(Feat("basis")) or feats[-1])})(),
                                       "combineFeatures": CF()})()
        comp.bRepBodies = type("BB", (), {"add": lambda s, k, bf: log.append("add")})()
        ziel.parentComponent = comp
        occ = type("O", (), {"name": "Detail1", "bRepBodies": [object()], "deleteMe": lambda s: log.append("occ weg")})()
        return ziel, danach, occ, log, feats

    def lauf(self, **kw):
        ziel, danach, occ, log, feats = self.aufbau(**kw)
        alt = (fa.koerper_neu, fa.ist_blech, fa.design, adsk.fusion.TemporaryBRepManager, adsk.core.ObjectCollection, adsk.fusion.FeatureOperations)
        fa.koerper_neu = lambda t: danach
        fa.ist_blech = lambda b: kw.get("blech", False)
        fa.design = lambda: type("D", (), {"userParameters": type("U", (), {"itemByName": lambda s, n: None})()})()
        adsk.fusion.TemporaryBRepManager = type("T", (), {"get": staticmethod(lambda: type("M", (), {"copy": lambda s, b: b})())})
        adsk.core.ObjectCollection = type("OC", (), {"create": staticmethod(lambda: type("L", (), {"n": 0, "add": lambda s, b: setattr(s, "n", s.n + 1), "count": property(lambda s: s.n)})())})
        adsk.fusion.FeatureOperations.JoinFeatureOperation = "JOIN"
        try:
            return fa.detail_integrieren(occ, ziel, ["SD_H_1"]), log, feats
        finally:
            (fa.koerper_neu, fa.ist_blech, fa.design, adsk.fusion.TemporaryBRepManager, adsk.core.ObjectCollection, adsk.fusion.FeatureOperations) = alt

    def test_erfolg_ohne_restkomponente(self):
        (cf, warn), log, feats = self.lauf()
        self.assertEqual([f.n for f in feats], ["basis", "combine"])
        self.assertIn("occ weg", log)
        self.assertEqual(warn, [])

    def test_blechhinweis(self):
        (cf, warn), _, _ = self.lauf(blech=True)
        self.assertTrue(any("Blechkörper" in w for w in warn))

    def test_keine_beruehrung_baut_zurueck(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.aufbau_fehler(combine_fehler="No intersection")
        self.assertIn("berührt", str(cm.exception))
        self.assertIn("del basis", self.rest[0])   # Basis-Feature wurde zurückgebaut
        self.assertNotIn("occ weg", self.rest[0])

    def aufbau_fehler(self, **kw):
        ziel, danach, occ, log, feats = self.aufbau(**kw)
        alt = (fa.koerper_neu, adsk.fusion.TemporaryBRepManager, adsk.core.ObjectCollection)
        adsk.fusion.TemporaryBRepManager = type("T", (), {"get": staticmethod(lambda: type("M", (), {"copy": lambda s, b: b})())})
        adsk.core.ObjectCollection = type("OC", (), {"create": staticmethod(lambda: type("L", (), {"n": 0, "add": lambda s, b: setattr(s, "n", s.n + 1), "count": property(lambda s: s.n)})())})
        try:
            fa.detail_integrieren(occ, ziel)
        finally:
            self.rest = (log, feats)
            (fa.koerper_neu, adsk.fusion.TemporaryBRepManager, adsk.core.ObjectCollection) = alt

    def test_kein_volumenzuwachs_baut_zurueck(self):
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf(volumen_nachher=1.0)
        self.assertIn("nicht verändert", str(cm.exception))

    def test_unterkomponente_abgelehnt(self):
        ziel, _, occ, _, _ = self.aufbau()
        ziel.assemblyContext = object()
        with self.assertRaises(fa.AdapterFehler):
            fa.detail_integrieren(occ, ziel)


class RichtungTest(unittest.TestCase):
    """Richtung jedes Schritts wie in der Vorschau: Winkel + = nach links, − = nach rechts, relativ zur bisherigen Laufrichtung.
    Rechnung rein mathematisch; Fusion wird nur in den Einbau-Tests (mit Messwerten aus dem Nachbau) nachgespielt."""
    U, V = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)

    def test_flansch_relativ_zur_laufrichtung(self):
        # nach «90» (Lauf 90° = nach oben): gleiches Vorzeichen biegt wieder nach links = zurück (−u), umgekehrtes nach rechts = vorwärts (+u)
        self.assertTrue(fa.richtung_stimmt(90, 90, (-1, 0, 0), self.U, self.V))
        self.assertFalse(fa.richtung_stimmt(90, 90, (1, 0, 0), self.U, self.V))
        self.assertTrue(fa.richtung_stimmt(90, -90, (1, 0, 0), self.U, self.V))
        self.assertFalse(fa.richtung_stimmt(90, -90, (-1, 0, 0), self.U, self.V))

    def test_umschlag_seite(self):
        # nach «90»: Umschlag + faltet nach links (−u). Gemessen wird nur die seitliche Lage; der Rücklauf (−v) darf überwiegen
        self.assertTrue(fa.richtung_stimmt(90, 180, (-0.2, -5.0, 0), self.U, self.V))
        self.assertFalse(fa.richtung_stimmt(90, 180, (0.2, -5.0, 0), self.U, self.V))
        self.assertTrue(fa.richtung_stimmt(90, -180, (0.2, -5.0, 0), self.U, self.V))

    def test_nicht_entscheidbar(self):
        self.assertIsNone(fa.richtung_stimmt(90, 180, (0.0, -5.0, 0), self.U, self.V))

    def test_hilfen(self):
        self.assertEqual(fa._ohne_komponente((3, 4, 0), (1, 0, 0)), (0.0, 4.0, 0.0))
        self.assertIsNone(fa._einheit((0, 0, 0)))
        r = fa.richtung_in_ebene(180, self.U, self.V)
        self.assertAlmostEqual(r[0], -1.0)


class FolgeRichtungTest(unittest.TestCase):
    """folge_anbringen mit nachgespielten Messwerten: weicht Fusions Richtung von der Vorlage ab, wird der Schritt gespiegelt neu gebaut."""
    def setUp(self):
        self.alt = (fa.flansch, fa.umschlag, fa.neue_aussenkante, fa._kantenrahmen_quer, fa._gemessen)
        self.aufrufe, self.feats, self.messungen = [], [], []
        fa._kantenrahmen_quer = lambda edge: ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))        # e = z, u = x
        fa._gemessen = lambda vorher, neu, e: self.messungen.pop(0)
        fa.neue_aussenkante = lambda feat, vorher, L, t: Kante((0, 0, 0), (0, 0, 50))

        def bauen(kante, w, L, r=None, g=None, b=None, l=None):
            f = Feature([], "F%d" % (len(self.feats) + 1))
            self.feats.append(f)
            self.aufrufe.append((w, g))
            return f
        fa.flansch = fa.umschlag = bauen

    def tearDown(self):
        fa.flansch, fa.umschlag, fa.neue_aussenkante, fa._kantenrahmen_quer, fa._gemessen = self.alt

    OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "flansch", "winkel": 90, "laenge": 10, "radius": None}]

    def lauf(self, ops=None):
        h = []
        r = fa.folge_anbringen(Kante((0, 0, 0), (0, 0, 50)), ops or self.OPS, 0.7, {}, h)
        return r, h

    def test_richtige_richtung_bleibt(self):
        self.messungen = [(0, 1.0, 0), (-1.0, 0, 0)]       # Schritt 1 nach «oben» (+v); Schritt 2 zurück (−u) = wie die Vorschau
        r, h = self.lauf()
        self.assertEqual(len(r), 2)
        self.assertEqual(self.aufrufe, [(90, False), (90, False)])
        self.assertFalse([x for x in h if "umgekehrt" in x])

    def test_falsche_richtung_wird_gespiegelt_neu_gebaut(self):
        self.messungen = [(0, 1.0, 0), (1.0, 0, 0), (-1.0, 0, 0), (-1.0, 0, 0)]   # Fusion baut Schritt 2 zuerst nach +u (falsch)
        r, h = self.lauf()
        self.assertEqual(len(r), 2, "falscher Schritt 2 wurde ersetzt, nicht zusätzlich gebaut")
        self.assertTrue(self.feats[1].geloescht)
        self.assertEqual(self.aufrufe, [(90, False), (90, False), (90, True)])
        self.assertTrue(any("automatisch umgekehrt" in x for x in h))

    def test_bleibt_falsch_baut_alles_zurueck(self):
        self.messungen = [(0, 1.0, 0), (1.0, 0, 0), (1.0, 0, 0), (1.0, 0, 0)]
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf()
        self.assertIn("gespiegelt nicht herstellen", str(cm.exception))
        self.assertTrue(all(f.geloescht for f in self.feats))

    def test_negativer_erster_winkel_definiert_oben_richtig(self):
        # Schritt 1 mit −90 (nach rechts): Fusion baut mit isFlipped nach −v; «oben» bleibt +v. Lauf −90° (nach unten);
        # Schritt 2 mit −90 biegt wieder nach rechts → Laufrichtung −180° = −u (zurück)
        ops = [dict(self.OPS[0], winkel=-90), dict(self.OPS[1], winkel=-90)]
        self.messungen = [(0, -1.0, 0), (-1.0, 0, 0)]
        r, h = self.lauf(ops)
        self.assertEqual(self.aufrufe, [(-90, True), (-90, False)])
        self.assertFalse([x for x in h if "umgekehrt" in x])


class GruppeTest(unittest.TestCase):
    """Zusammenhängende Kanten: ein gemeinsamer Flansch (Gehrung), weitere Schritte je Kante – mit nachgespielten Messwerten."""
    def kanten(self):
        body = type("B", (), {"entityToken": "tok-body", "name": "Körper1"})()
        k1, k2, k3 = Kante((0, 0, 0), (10, 0, 0), body=body), Kante((10, 0, 0), (10, 10, 0), body=body), Kante((50, 50, 0), (60, 50, 0), body=body)
        return k1, k2, k3

    def test_gruppen_bilden(self):
        k1, k2, k3 = self.kanten()
        self.assertEqual(fa.gruppen_bilden([k1, k2, k3]), [[0, 1], [2]])
        self.assertEqual(fa.gruppen_bilden([k3, k1]), [[0], [1]])
        k2.body = type("B", (), {"entityToken": "anderer"})()
        self.assertEqual(fa.gruppen_bilden([k1, k2]), [[0], [1]], "andere Körper werden nie zusammengefasst")

    def setUp(self):
        self.alt = (fa.flansch, fa.neue_aussenkante, fa._kantenrahmen_quer, fa._gemessen)
        self.aufrufe, self.feats = [], []
        fa._kantenrahmen_quer = lambda edge: ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
        fa._gemessen = lambda vorher, neu, e: (0, 1.0, 0) if neu is not None and getattr(neu, "erste", False) else (-1.0, 0, 0)
        fa.neue_aussenkante = lambda feat, vorher, L, t: self._neu(feat)

        def bauen(kanten, w, L, r=None, g=None, b=None, l=None):
            f = Feature([], "F%d" % (len(self.feats) + 1))
            self.feats.append(f)
            self.aufrufe.append((kanten, w, g))
            if self.fehler_bei == len(self.feats):
                raise fa.AdapterFehler("Fusion lehnt ab")
            return f
        fa.flansch = bauen
        self.fehler_bei = None

    def _neu(self, feat):
        k = Kante((0, 0, 0), (0, 0, 50))
        k.erste = feat is self.feats[0]
        return k

    def tearDown(self):
        fa.flansch, fa.neue_aussenkante, fa._kantenrahmen_quer, fa._gemessen = self.alt

    OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "flansch", "winkel": 90, "laenge": 10, "radius": None}]

    def test_ein_gemeinsamer_flansch_dann_je_kante(self):
        k1, k2, _ = self.kanten()
        r = fa.folge_anbringen_gruppe([k1, k2], self.OPS, 0.7, {}, [])
        self.assertEqual(len(r), 3, "1 gemeinsamer Flansch + je Kante der zweite Schritt")
        self.assertEqual(self.aufrufe[0][0], [k1, k2], "Schritt 1: beide Kanten in EINEM Feature")
        self.assertTrue(all(not isinstance(a[0], list) for a in self.aufrufe[1:]), "weitere Schritte einzeln")
        self.assertEqual([a[2] for a in self.aufrufe], [False, False, False])

    def test_nur_ein_schritt(self):
        k1, k2, _ = self.kanten()
        r = fa.folge_anbringen_gruppe([k1, k2], self.OPS[:1], 0.7, {}, [])
        self.assertEqual(len(r), 1)

    def test_fehler_baut_alles_zurueck(self):
        k1, k2, _ = self.kanten()
        self.fehler_bei = 3        # Schritt 2 der zweiten Kante schlägt fehl
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.folge_anbringen_gruppe([k1, k2], self.OPS, 0.7, {}, [])
        self.assertIn("Fusion lehnt ab", str(cm.exception))
        self.assertTrue(all(f.geloescht for f in self.feats[:2]), "gemeinsamer Flansch und Schritt der ersten Kante wieder entfernt")

    def test_nicht_moeglich(self):
        k1, k2, _ = self.kanten()
        with self.assertRaises(fa.AdapterFehler):
            fa.folge_anbringen_gruppe([k1], self.OPS, 0.7, {}, [])
        with self.assertRaises(fa.AdapterFehler):
            fa.folge_anbringen_gruppe([k1, k2], [{"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}, {"typ": "flansch", "winkel": 90, "laenge": 5}], 0.7, {}, [])


class PlanMerkenTest(unittest.TestCase):
    """OK-Knopf bei eingeschalteter Vorschau (Live-Test 5.4): ist der Bauplan während der Vorschau nicht neu berechenbar, gilt der letzte Stand."""
    def setUp(self):
        from spengler_cad.commands import edge_apply_command as ec
        self.ec = ec
        self.alt = (ec._plan, ec._schluessel, ec._ausfuehrbar)
        ec.Z.clear()
        self.plan_aufrufe = []
        ec._plan = lambda inp: (self.plan_aufrufe.append(1) or ({"ok": True}, None))

    def tearDown(self):
        self.ec._plan, self.ec._schluessel, self.ec._ausfuehrbar = self.alt
        self.ec.Z.clear()

    def test_gleicher_stand_wird_nicht_neu_berechnet(self):
        self.ec._schluessel = lambda inp: ("a",)
        self.assertEqual(self.ec._plan_gemerkt(None), ({"ok": True}, None))
        self.ec._plan_gemerkt(None)
        self.assertEqual(len(self.plan_aufrufe), 1)

    def test_neuer_stand_wird_berechnet(self):
        self.ec._schluessel = lambda inp: ("a",)
        self.ec._plan_gemerkt(None)
        self.ec._schluessel = lambda inp: ("b",)
        self.ec._plan_gemerkt(None)
        self.assertEqual(len(self.plan_aufrufe), 2)

    def test_vorschau_macht_kanten_ungueltig_letzter_stand_gilt(self):
        self.ec._schluessel = lambda inp: ("a",)
        erster = self.ec._plan_gemerkt(None)

        def kaputt(inp):
            raise RuntimeError("invalid edge")
        self.ec._schluessel = kaputt           # Auswahl nicht mehr lesbar → kein Treffer im Merker
        self.ec._plan = kaputt                 # Neuberechnung scheitert ebenfalls
        self.assertEqual(self.ec._plan_gemerkt(None), erster, "OK bleibt möglich")

    def test_vorschau_hat_kante_veraendert_ausfuehrbarer_stand_gilt(self):
        """Live: mit Vorschau ist die Kante schon umgebaut → neuer Plan «nicht ausführbar»; gleiche Eingaben → letzter ausführbarer Plan."""
        ec = self.ec
        guter = {"ok": "gut"}
        plaene = [(guter, None), ({"ok": "schlecht"}, None)]
        ec._plan = lambda inp: plaene.pop(0)
        ec._ausfuehrbar = lambda plan, fehler: plan["ok"] == "gut"
        zustand = {"tok": "t1"}

        def schluessel(inp, mit_kanten=True):
            return ("a", zustand["tok"]) if mit_kanten else ("a",)
        ec._schluessel = schluessel
        self.assertEqual(ec._plan_gemerkt(None)[0], guter)
        zustand["tok"] = "t2"            # Vorschau hat die Kantenverweise verändert
        self.assertEqual(ec._plan_gemerkt(None)[0], guter, "OK bleibt möglich")
        schluessel_aus = lambda inp, mit_kanten=True: ("b", "t2") if mit_kanten else ("b",)
        ec._schluessel = schluessel_aus
        plaene.append(({"ok": "schlecht"}, None))
        self.assertEqual(ec._plan_gemerkt(None)[0], {"ok": "schlecht"}, "andere Eingaben: kein Ersatz")

    def test_ohne_vorherigen_stand_wird_der_fehler_nicht_verschluckt(self):
        def kaputt(inp):
            raise RuntimeError("invalid edge")
        self.ec._schluessel = kaputt
        self.ec._plan = kaputt
        with self.assertRaises(RuntimeError):
            self.ec._plan_gemerkt(None)


class MassUndLageTest(unittest.TestCase):
    """Massbezug (Höhe von aussen/innen/tangential) und Lage der Biegung → Fusion-Aufzählungen (FlangeHeightDatumTypes, BendPositionTypes)."""
    def setUp(self):
        adsk.fusion.FlangeHeightDatumTypes.InnerFacesFlangeHeightDatumType = "H-INNEN"
        adsk.fusion.FlangeHeightDatumTypes.OuterFacesFlangeHeightDatumType = "H-AUSSEN"
        adsk.fusion.FlangeHeightDatumTypes.TangentToBendFlangeHeightDatumType = "H-TANGENT"
        adsk.fusion.BendPositionTypes.StartEdgeBendPositionType = "B-KANTE"
        adsk.fusion.BendPositionTypes.InsideBendPositionType = "B-INNEN"
        adsk.fusion.BendPositionTypes.OutsideBendPositionType = "B-AUSSEN"
        adsk.fusion.BendPositionTypes.TangentToSideBendPositionType = "B-TANGENT"

    def test_flansch_setzt_bezug_und_lage(self):
        for bezug, lage, h, b in (("innen", "aussen", "H-INNEN", "B-AUSSEN"), ("tangential", "tangential", "H-TANGENT", "B-TANGENT"),
                                  ("aussen", "kante", "H-AUSSEN", "B-KANTE")):
            inp = Eingabe("angle", "heightDatumType", "bendPositionType")
            fa.flansch(kante_mit(Sammlung(inp)), 90, 20, None, None, bezug, lage)
            self.assertEqual((inp.werte["heightDatumType"], inp.werte["bendPositionType"]), (h, b))

    def test_ohne_angabe_bleibt_fusion_standard(self):
        inp = Eingabe("angle", "heightDatumType", "bendPositionType")
        fa.flansch(kante_mit(Sammlung(inp)), 90, 20)
        self.assertNotIn("heightDatumType", inp.werte)
        self.assertNotIn("bendPositionType", inp.werte)

    def test_nicht_einstellbar_bricht_ab(self):
        for eig, text in (("bendPositionType", "Massbezug"), ("heightDatumType", "Lage")):
            ff = Sammlung(Eingabe("angle", eig))
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.flansch(kante_mit(ff), 90, 20, None, None, "innen", "aussen")
            self.assertIn(text, str(cm.exception))
            self.assertEqual(ff.hinzu, [])

    def test_umschlag_lage(self):
        inp = HemEingabe()
        fa.umschlag(kante_mit(hem=Sammlung(inp)), 12, False, None, "aussen")
        self.assertEqual(inp.aufrufe[0][-1], "B-AUSSEN")


class ZuschnittKoerperTest(unittest.TestCase):
    """Flacher Körper aus dem Zuschnitt (Rundblech): Aufruffolge mit nachgebauten Fusion-Objekten – NICHT die echte Geometrie."""
    def fusion(self, split_fehler=False, flaechen_z=(0.0, -0.06)):
        log = []

        class Kurve(object):
            pass

        def kurvenfabrik(name):
            return type(name, (), {k: (lambda self, *a, _k=k: (log.append((name, _k)) or Kurve())) for k in ("addByCenterRadius", "addByCenterStartSweep", "addByTwoPoints")})()

        class Skizze(object):
            def __init__(s):
                s.name, s.sketchCurves = "", type("SC", (), {"sketchCircles": kurvenfabrik("kreis"), "sketchArcs": kurvenfabrik("bogen"), "sketchLines": kurvenfabrik("linie")})()
                s.profiles = Liste([type("Prof", (), {"areaProperties": lambda self: type("A", (), {"area": 5.0})()})()])

        class Flaeche(object):
            def __init__(s, z):
                s.boundingBox = type("BB", (), {"minPoint": type("P", (), {"z": z})()})()

        body = type("Body", (), {"name": "", "faces": [Flaeche(z) for z in flaechen_z]})()
        feat = type("F", (), {"bodies": Liste([body])})()
        ext = type("Ext", (), {"createInput": lambda s, p, op: type("EI", (), {"setDistanceExtent": lambda s2, sym, d: log.append(("extrude", sym))})(),
                               "add": lambda s, i: feat})()

        class Split(object):
            def createInput(s, f, w, erweitert):
                log.append(("split", len(f.liste), len(w.liste)))
                return object()

            def add(s, i):
                if split_fehler:
                    raise RuntimeError("Split failed")
        comp = type("Comp", (), {"xYConstructionPlane": object(), "sketches": type("Sk", (), {"add": lambda s, ebene: Skizze()})(),
                                 "features": type("Fe", (), {"extrudeFeatures": ext, "splitFaceFeatures": Split()})()})()
        return comp, body, log

    def lauf(self, comp, zs):
        class Sammlung2(object):
            def __init__(s):
                s.liste = []

            def add(s, x):
                s.liste.append(x)
        alt = adsk.core.ObjectCollection
        adsk.core.ObjectCollection = type("OC", (), {"create": staticmethod(lambda: Sammlung2())})
        try:
            return fa.abwicklung_koerper(comp, zs, 0.6, "Abwicklung Test")
        finally:
            adsk.core.ObjectCollection = alt

    def test_scheibe_mit_biegelinie(self):
        from spengler_cad.forming import forming as fo
        zs = fo.zuschnitt(fo.scheibe_mit_rand(100, 20, 90))
        comp, body, log = self.fusion()
        koerper, hinweise = self.lauf(comp, zs)
        self.assertIs(koerper, body)
        self.assertEqual(body.name, "Abwicklung Test")
        self.assertEqual(hinweise, [])
        self.assertIn(("split", 1, 1), log, "Oberseite (z = 0) wird mit dem Biegekreis geteilt")
        self.assertEqual([x for x in log if x[0] == "kreis"], [("kreis", "addByCenterRadius")] * 2, "Kontur- und Biegekreis")

    def test_split_scheitert_koerper_bleibt(self):
        from spengler_cad.forming import forming as fo
        zs = fo.zuschnitt(fo.scheibe_mit_rand(100, 20, 90))
        comp, body, log = self.fusion(split_fehler=True)
        koerper, hinweise = self.lauf(comp, zs)
        self.assertIs(koerper, body)
        self.assertIn("Skizze «Abwicklung Test Biegelinien»", hinweise[0])

    def test_kegel_ohne_biegelinien_kein_split(self):
        from spengler_cad.forming import forming as fo
        comp, body, log = self.fusion()
        self.lauf(comp, fo.zuschnitt(fo.kegelstumpf(100, 50, 100)))
        self.assertFalse([x for x in log if x[0] == "split"])
        self.assertIn(("bogen", "addByCenterStartSweep"), log)
        self.assertIn(("linie", "addByTwoPoints"), log)


class GruppeUmschlagTest(unittest.TestCase):
    """Umschlag als einziger Schritt an zusammenhängenden Kanten: gemeinsamer 179°-Flansch mit Gehrung (Live 31.10.: setFlatHem/setOpenHem nehmen nur
    EINE Kante, «U+ 12» an 2 Kanten wurde einzeln gebaut)."""
    def setUp(self):
        self.alt = fa.flansch
        self.aufrufe = []
        self.ablehnen = 0

        def flansch(kanten, winkel, laenge, radius=None, gespiegelt=None, bezug=None, lage=None):
            self.aufrufe.append((list(kanten), winkel, laenge, radius, gespiegelt))
            if self.ablehnen:
                self.ablehnen -= 1
                raise fa.AdapterFehler("Fusion lehnt ab")
            return Feature([], "saum")
        fa.flansch = flansch
        self.addCleanup(setattr, fa, "flansch", self.alt)

    def test_ein_feature_fuer_beide_kanten(self):
        k1, k2 = kante_mit(), kante_mit()
        hinweise = []
        erzeugt = fa.folge_anbringen_gruppe([k1, k2], [{"typ": "umschlag", "winkel": 180, "laenge": 12, "radius": None}], 0.6, {}, hinweise)
        self.assertEqual(len(erzeugt), 1)
        kanten, winkel, laenge, radius, gespiegelt = self.aufrufe[0]
        self.assertEqual((kanten, winkel, laenge, gespiegelt), ([k1, k2], 179.0, 12, False))
        self.assertAlmostEqual(radius, 0.3, msg="Innenradius = halbe Dicke (Spalt ≈ Dicke wie beim offenen Saum)")
        self.assertIn("179°-Flansch", hinweise[0])

    def test_nach_hinten_und_rueckfall_auf_kleineren_winkel(self):
        self.ablehnen = 1
        fa.folge_anbringen_gruppe([kante_mit(), kante_mit()], [{"typ": "umschlag", "winkel": -180, "laenge": 12, "radius": 1.0}], 0.6, {}, [])
        self.assertEqual([(a[1], a[3], a[4]) for a in self.aufrufe], [(-179.0, 1.0, True), (-178.0, 1.0, True)])

    def test_alles_abgelehnt_gibt_fehler_fuer_den_rueckfall_je_kante(self):
        self.ablehnen = 9
        with self.assertRaises(fa.AdapterFehler):
            fa.folge_anbringen_gruppe([kante_mit(), kante_mit()], [{"typ": "umschlag", "winkel": 180, "laenge": 12}], 0.6, {}, [])

    def test_umschlag_mit_weiteren_schritten_bleibt_einzeln(self):
        with self.assertRaises(fa.AdapterFehler):
            fa.folge_anbringen_gruppe([kante_mit(), kante_mit()], [{"typ": "umschlag", "winkel": 180, "laenge": 12}, {"typ": "flansch", "winkel": 90, "laenge": 5}], 0.6, {}, [])


class GemeinsamerUmschlagTest(unittest.TestCase):
    """Umschlag als zweiter Schritt an mehreren Kanten (gemeinsamer Flansch mit Gehrung) – Ablauf mit ausgetauschten Bausteinen."""
    OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25}, {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}]

    def setUp(self):
        self.alt = (fa._umschlag_gruppe, fa.neue_aussenkante, fa._gemessen, fa.richtung_stimmt)
        self.aufrufe, self.antworten = [], []
        fa._umschlag_gruppe = lambda kanten, op, dicke, flip: (self.aufrufe.append(flip) or Feature([], "saum%d" % len(self.aufrufe)))
        fa.neue_aussenkante = lambda *a: "neu"
        fa._gemessen = lambda *a: (1.0, 0.0, 0.0)
        fa.richtung_stimmt = lambda *a: self.antworten.pop(0)
        self.addCleanup(lambda: setattr(fa, "_umschlag_gruppe", self.alt[0]) or setattr(fa, "neue_aussenkante", self.alt[1])
                        or setattr(fa, "_gemessen", self.alt[2]) or setattr(fa, "richtung_stimmt", self.alt[3]))

    def test_richtung_stimmt_gleich_beim_ersten(self):
        self.antworten = [True]
        f = fa._gemeinsamer_umschlag(["k1", "k2"], self.OPS, 0.7, [((1, 0, 0), (0, 1, 0))], (0, 0, 1))
        self.assertEqual(self.aufrufe, [False])
        self.assertFalse(f.geloescht)

    def test_falsche_richtung_wird_gespiegelt_neu_gebaut(self):
        self.antworten = [False, True]
        f = fa._gemeinsamer_umschlag(["k1", "k2"], self.OPS, 0.7, [((1, 0, 0), (0, 1, 0))], (0, 0, 1))
        self.assertEqual(self.aufrufe, [False, True])
        self.assertEqual(f.name, "saum2")

    def test_fehler_ergibt_none_fuer_den_rueckfall(self):
        def kaputt(*a):
            raise fa.AdapterFehler("Fusion nimmt mehrere Kanten nicht an")
        fa._umschlag_gruppe = kaputt
        self.assertIsNone(fa._gemeinsamer_umschlag(["k1", "k2"], self.OPS, 0.7, [((1, 0, 0), (0, 1, 0))], (0, 0, 1)))

    def test_saum_werkzeug_nimmt_nur_die_erste_kante(self):
        inp = HemEingabe()
        hf = Sammlung(inp)
        k1, k2 = kante_mit(hem=hf), kante_mit(hem=hf)
        fa.umschlag([k1, k2], 7, False)
        self.assertIs(inp.aufrufe[0][1], k1, "setFlatHem(edge, …) bekommt EINE Kante (Live: eine Auswahl wird abgelehnt)")


class VersatzTest(unittest.TestCase):
    """Versatz der Biegung (Streifen abschneiden/anfügen) mit Nachbau von Skizze/Extrusion – NICHT die echte Geometrie."""
    def aufbau(self, volumen_nach, wirft_erste=False, mit_zielkante=True):
        t, L = 0.07, 50.0
        gross = Flaeche(area=100.0)
        gross.pointOnFace = V(25.0, -10.0, 0.0)          # Blech liegt bei y < 0, Kante bei y = 0
        kante = Kante((0, 0, 0), (L, 0, 0), flaechen=[gross])
        log = []
        body = type("Body", (), {"volume": 100.0})()
        body.edges = []
        kante.body = body

        class Skizze(object):
            def __init__(s):
                s.name, s.profiles = "", Liste([object()])
                s.sketchCurves = type("SC", (), {"sketchLines": s})()

            def modelToSketchSpace(s, p):
                return p

            def addByTwoPoints(s, a, b):
                log.append(("linie", a, b))
                return type("Ln", (), {"endSketchPoint": b, "startSketchPoint": a})()

        class Eingabe2(object):
            def setSymmetricExtent(s, d, voll):
                log.append(("symm", d))

            def setDistanceExtent(s, sym, d):
                log.append(("dist", d))
        versuch = []

        def add(ei):
            versuch.append(1)
            if wirft_erste and len(versuch) == 1:
                raise RuntimeError("falsche Richtung")
            neu = type("B", (), {"volume": volumen_nach, "edges": list(body.edges)})()
            if mit_zielkante:
                neu.edges.append(Kante(*self.ziel))
            f = Feature([], "ext")
            f.bodies = Liste([neu])
            return f
        ef = type("EF", (), {"createInput": lambda s, p, op: Eingabe2(), "add": staticmethod(add)})()
        comp = type("Comp", (), {"sketches": type("Sk", (), {"add": lambda s, f: Skizze()})(),
                                 "features": type("Fe", (), {"extrudeFeatures": ef})()})()
        body.parentComponent = comp
        return kante, log, versuch, t * 10

    def lauf(self, kante, mm, dicke):
        alt = adsk.fusion.FeatureOperations
        adsk.fusion.FeatureOperations = type("FO", (), {"CutFeatureOperation": "cut", "JoinFeatureOperation": "join"})
        alt_vi = adsk.core.ValueInput
        adsk.core.ValueInput = type("VI", (), {"createByReal": staticmethod(lambda x: x), "createByString": staticmethod(lambda x: x)})
        alt_p = adsk.core.Point3D
        adsk.core.Point3D = type("P3", (), {"create": staticmethod(lambda x, y, z: V(x, y, z))})
        alt_oc = adsk.core.ObjectCollection
        adsk.core.ObjectCollection = type("OC", (), {"create": staticmethod(lambda: Liste())})
        Liste.add = lambda self, x: self.append(x)
        try:
            return fa._versatz_anwenden(kante, mm, dicke) if not isinstance(kante, list) else fa._versatz_gruppe(kante, mm, dicke)
        finally:
            adsk.fusion.FeatureOperations, adsk.core.ValueInput, adsk.core.Point3D, adsk.core.ObjectCollection = alt, alt_vi, alt_p, alt_oc

    def test_rueckversatz_schneidet_und_findet_neue_kante(self):
        self.ziel = ((0, -1.0, 0), (50, -1.0, 0))        # 10 mm nach innen (y von 0 auf −1 cm)
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 - 50 * 1.0 * 0.07)
        erzeugt, neu = self.lauf(kante, 10.0, d)
        self.assertEqual(len(erzeugt), 2, "Skizze und Schnitt")
        self.assertAlmostEqual(neu.geometry.startPoint.y, -1.0)
        self.assertEqual([round(x[1], 3) for x in log if x[0] == "dist"], [0.105], "einseitig 1.5 × Dicke ins Blech (nicht symmetrisch)")

    def test_proxy_kante_wird_im_bauteilsystem_gerechnet(self):
        """Bericht 31.10.: Auswahlkante als Proxy (verschobenes Bauteil) – gerechnet wird mit der nativen Kante, sonst 0 Treffer."""
        self.ziel = ((0, -1.0, 0), (50, -1.0, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 - 50 * 1.0 * 0.07)
        proxy = Kante((100, 7, 0), (150, 7, 0))        # andere Koordinaten (Baugruppe)
        proxy.nativeObject, proxy.body = kante, kante.body
        erzeugt, neu = self.lauf(proxy, 10.0, d)
        self.assertAlmostEqual(neu.geometry.startPoint.y, -1.0)

    def test_anfuegen_richtung_ins_blech_aus_der_flaechennormale(self):
        """Bericht 31.10.: falsche Richtung verdoppelte die Blechdicke. Jetzt zuerst die Richtung gegen die Aussennormale der Fläche."""
        self.ziel = ((0, 0.5, 0), (50, 0.5, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 + 50 * 0.5 * 0.07)
        flaeche = kante.faces[0]
        flaeche.geometry = type("Pl", (), {"normal": V(0, 0, 1)})()      # Aussennormale +z, Blech liegt darunter
        flaeche.isParamReversed = False
        orig_add = comp_sketch_add = kante.body.parentComponent.sketches.add

        def mit_richtung(f):
            sk = orig_add(f)
            sk.xDirection, sk.yDirection = V(1, 0, 0), V(0, 1, 0)         # Skizzennormale +z → in das Blech ist NEGATIV
            return sk
        kante.body.parentComponent.sketches = type("Sk", (), {"add": lambda s_, f: mit_richtung(f)})()
        self.lauf(kante, -5.0, d)
        self.assertEqual([x[1] for x in log if x[0] == "dist"], [-0.07], "gleich beim ersten Versuch in Richtung Blech")
        flaeche.isParamReversed = True                                     # umgekehrte Fläche → Richtung dreht sich
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 + 50 * 0.5 * 0.07)
        flaeche = kante.faces[0]
        flaeche.geometry, flaeche.isParamReversed = type("Pl", (), {"normal": V(0, 0, 1)})(), True
        orig_add = kante.body.parentComponent.sketches.add

        def mit_richtung2(f):
            sk = orig_add(f)
            sk.xDirection, sk.yDirection = V(1, 0, 0), V(0, 1, 0)
            return sk
        kante.body.parentComponent.sketches = type("Sk", (), {"add": lambda s_, f: mit_richtung2(f)})()
        self.lauf(kante, -5.0, d)
        self.assertEqual([x[1] for x in log if x[0] == "dist"], [0.07])

    def test_flaechenprofil_der_skizze_wird_nicht_extrudiert(self):
        """Live 31.10.: In der Skizze lagen auch Profile der Blechfläche (projizierte Kanten) → Dicke verdoppelt bzw. Körper weggeschnitten."""
        self.ziel = ((0, 0.5, 0), (50, 0.5, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 + 50 * 0.5 * 0.07)
        comp = kante.body.parentComponent
        orig = comp.sketches.add

        def add(f):
            sk = orig(f)
            klein = type("P", (), {"areaProperties": lambda s_: type("A", (), {"area": 25.0})()})()
            gross = type("P", (), {"areaProperties": lambda s_: type("A", (), {"area": 5000.0})()})()
            sk.profiles = Liste([gross, klein])
            return sk
        comp.sketches = type("Sk", (), {"add": lambda s_, f: add(f)})()
        gewaehlt = []
        ef = comp.features.extrudeFeatures
        alt_create = ef.createInput
        ef.createInput = lambda p, op: (gewaehlt.append(len(p)) or alt_create(p, op))
        self.lauf(kante, -5.0, d)
        self.assertEqual(gewaehlt, [1], "nur das kleine Streifenprofil")

    def test_koerper_leer_nach_schnitt_wird_nicht_als_erfolg_gewertet(self):
        """Bericht 31.10.: nach dem Schnitt war der gemeldete Körper leer (Volumen 0) – früher als «Volumen gesunken» durchgewunken."""
        self.ziel = ((0, -1.0, 0), (50, -1.0, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=0.0)
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf(kante, 10.0, d)
        self.assertIn("nicht gefunden", str(cm.exception))

    def test_nicht_gefunden_nennt_naechste_kante(self):
        self.ziel = ((0, -0.5, 0), (50, -0.5, 0))        # 5 mm statt 10 mm entfernt
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 - 50 * 1.0 * 0.07)
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf(kante, 10.0, d)
        self.assertIn("5.00 mm vom Soll entfernt", str(cm.exception))

    def test_vorversatz_probiert_zweite_richtung(self):
        self.ziel = ((0, 0.5, 0), (50, 0.5, 0))          # 5 mm nach aussen
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 + 50 * 0.5 * 0.07, wirft_erste=True)
        erzeugt, neu = self.lauf(kante, -5.0, d)
        self.assertEqual(len(versuch), 2)
        self.assertAlmostEqual(neu.geometry.startPoint.y, 0.5)
        self.assertEqual([x[1] for x in log if x[0] == "dist"], [0.07, -0.07])

    def test_zwei_zusammenstossende_kanten_eine_extrusion(self):
        """Ecke bei (0, 0): Kante 1 entlang x, Kante 2 entlang y – beide werden um 5 mm nach aussen versetzt, in einer Skizze/Extrusion."""
        t = 0.07
        gross = Flaeche(area=100.0)
        gross.pointOnFace = V(25.0, -25.0, 0.0)
        k1 = Kante((0, 0, 0), (50, 0, 0), flaechen=[gross])
        gross2 = Flaeche(area=100.0)
        gross2.pointOnFace = V(25.0, -25.0, 0.0)
        k2 = Kante((0, 0, 0), (0, -50, 0), flaechen=[gross2])
        k1.body = k2.body = body = type("Body", (), {"volume": 100.0, "edges": []})()
        zeilen, ext = [], []

        class Skizze(object):
            def __init__(s):
                s.profiles = Liste([object(), object(), object()])
                s.sketchCurves = type("SC", (), {"sketchLines": s})()

            def modelToSketchSpace(s, p):
                return p

            def addByTwoPoints(s, a, b):
                zeilen.append((a, b))
                return type("Ln", (), {"endSketchPoint": b, "startSketchPoint": a})()

        def add(ei):
            neu = type("B", (), {"volume": 100.0 + 2 * 50 * 0.5 * t})()
            neu.edges = [Kante((-0.5, 0.5, 0), (50, 0.5, 0)), Kante((-0.5, 0.5, 0), (-0.5, -50, 0))]
            f = Feature([], "ext")
            f.bodies = Liste([neu])
            ext.append(f)
            return f
        ei = type("EI", (), {"setDistanceExtent": lambda s, a, b: None})()
        ef = type("EF", (), {"createInput": lambda s, p, op: (ext.append(("profile", len(p))) or ei), "add": staticmethod(add)})()
        body.parentComponent = type("Comp", (), {"sketches": type("Sk", (), {"add": lambda s, f: Skizze()})(),
                                                 "features": type("Fe", (), {"extrudeFeatures": ef})()})()
        erzeugt, neue = self.lauf([k1, k2], -5.0, 0.7)
        self.assertEqual(len(neue), 2)
        self.assertEqual(ext[0], ("profile", 3), "alle Profile der Skizze gehen in EINE Extrusion")
        self.assertEqual(len(zeilen), 8, "zwei Rechtecke")
        # Ecke gefüllt: Streifen 1 beginnt 5 mm VOR dem Anfang der Kante (x = −0.5 cm), Streifen 2 ebenso
        self.assertAlmostEqual(min(a.x for a, _ in zeilen), -0.5)

    def test_volumen_passt_nicht_dann_fehler(self):
        self.ziel = ((0, -1.0, 0), (50, -1.0, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0)
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf(kante, 10.0, d)
        self.assertIn("nicht an das Blech", str(cm.exception))

    def test_neue_kante_nicht_gefunden(self):
        self.ziel = ((0, -1.0, 0), (50, -1.0, 0))
        kante, log, versuch, d = self.aufbau(volumen_nach=100.0 - 50 * 0.07, mit_zielkante=False)
        with self.assertRaises(fa.AdapterFehler) as cm:
            self.lauf(kante, 10.0, d)
        self.assertIn("nicht eindeutig", str(cm.exception))

    def test_runde_kante_und_fehlende_dicke(self):
        rund = Kante((0, 0, 0), (50, 0, 0), typ="KREIS")
        with self.assertRaises(fa.AdapterFehler):
            fa._versatz_anwenden(rund, 5.0, 0.7)
        with self.assertRaises(fa.AdapterFehler):
            fa._versatz_anwenden(Kante((0, 0, 0), (50, 0, 0)), 5.0, None)


if __name__ == "__main__":
    unittest.main()

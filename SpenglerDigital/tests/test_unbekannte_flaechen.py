"""Korrekturauftrag 0.4.49, Phase 1: nicht lesbare/unbekannte Flächen werden NIE als eben behandelt – Attrappen und reine Logik, KEIN Fusion-Test."""
import unittest

import fake_fusion_blech  # noqa: F401  (Fusion-Attrappe in sys.path)
from _basis import test_material
from test_operation_plan import kante
from test_templates import testvorlage


def _fa():
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class _Patch(unittest.TestCase):
    def patche(self, obj, **attrs):
        for name, wert in attrs.items():
            original = getattr(obj, name)
            self.addCleanup(setattr, obj, name, original)
            setattr(obj, name, wert)


class Bauplan(unittest.TestCase):
    def test_fehlende_flaecheninfo_wird_abgelehnt(self):
        from spengler_cad.core import operation_plan as op
        k = kante()
        del k["flaeche"]
        p = op.erstelle(testvorlage(), {"H": 25}, test_material(), [k])
        self.assertFalse(op.ist_ausfuehrbar(p))
        self.assertIn("nicht sicher bestimmbar", " ".join(p["validation"]["errors"]))

    def test_diagnose_wird_genannt_und_jede_bauweise_lehnt_ab(self):
        from spengler_cad.core import operation_plan as op
        for bauweise in ("nativ", "eigen"):
            p = op.erstelle(testvorlage(), {"H": 25}, test_material(innerRadius=1.0, kFactor=0.4),
                            [kante(flaeche="unbekannt", flaeche_diagnose="Flächengrösse nicht lesbar (kaputt)")], bauweise, True)
            self.assertFalse(op.ist_ausfuehrbar(p), bauweise)
            self.assertIn("Flächengrösse nicht lesbar (kaputt)", " ".join(p["validation"]["errors"]))

    def test_gueltige_ebene_flaeche_unveraendert(self):
        from spengler_cad.core import operation_plan as op
        self.assertTrue(op.ist_ausfuehrbar(op.erstelle(testvorlage(), {"H": 25}, test_material(), [kante()])))


class Adapter(_Patch):
    """kante_beschreiben/flaechentyp_kante/matrix_sperre bei Lesefehlern."""
    def edge(self, faces=None, faces_fehler=None, area_fehler=False):
        class F(object):
            pass
        class E(object):
            length = 10.0
            body = object()
        e = E()
        if faces_fehler:
            type(e).faces = property(lambda s: (_ for _ in ()).throw(RuntimeError(faces_fehler)))
        else:
            fl = []
            for g in faces or []:
                f = F()
                if area_fehler:
                    type(f).area = property(lambda s: (_ for _ in ()).throw(RuntimeError("area kaputt")))
                else:
                    f.area = 5.0
                f.geometry = g
                fl.append(f)
            e.faces = fl
        return e

    def test_flaechentyp_kante(self):
        fa = _fa()
        from test_fusion_logik import ebene
        self.assertEqual(fa.flaechentyp_kante(self.edge([ebene()]))[0], "eben", "gültige ebene Fläche")
        typ, diag = fa.flaechentyp_kante(self.edge(faces_fehler="faces kaputt"))
        self.assertEqual(typ, "unbekannt")
        self.assertIn("faces kaputt", diag)
        typ, diag = fa.flaechentyp_kante(self.edge([ebene()], area_fehler=True))
        self.assertEqual((typ, "area kaputt" in diag), ("unbekannt", True))
        self.assertEqual(fa.flaechentyp_kante(self.edge([]))[0], "unbekannt")
        g = type("G", (), {"surfaceType": object()})()               # von Fusion unbekannter Typ
        self.assertEqual(fa.flaechentyp_kante(self.edge([g]))[0], "unbekannt")
        self.assertEqual(fa.flaechentyp(None), "unbekannt")

    def test_matrix_sperre_lehnt_ab_ohne_geometrie(self):
        fa = _fa()
        self.patche(fa, _kurventyp=lambda e: "linie")
        for e in (self.edge(faces_fehler="faces kaputt"), self.edge([type("G", (), {"surfaceType": object()})()]), self.edge([])):
            with self.assertRaises(fa.AdapterFehler) as cm:
                fa.matrix_sperre("flansch", [e])
            self.assertIn("unbekannt", str(cm.exception))

    def test_kante_beschreiben_setzt_unbekannt_nicht_eben(self):
        fa = _fa()
        import adsk.fusion
        self.patche(adsk.fusion.BRepEdge, cast=staticmethod(lambda x: x))
        self.patche(fa, _kurventyp=lambda e: "linie", blechdicke_mm=lambda b: 1.0, ist_blech=lambda b: True, profil_attribut=lambda b: None)
        e = self.edge(faces_fehler="faces kaputt")
        e.startVertex = e.endVertex = None
        d = fa.kante_beschreiben(e)
        self.assertEqual((d["flaeche"], d["flaechen"]), ("unbekannt", None))
        self.assertIn("faces kaputt", d["flaeche_diagnose"])
        from spengler_cad.core import operation_plan as op
        self.assertFalse(op.ist_ausfuehrbar(op.erstelle(testvorlage(), {"H": 25}, test_material(), [d])), "nichts wird gebaut")


if __name__ == "__main__":
    unittest.main()

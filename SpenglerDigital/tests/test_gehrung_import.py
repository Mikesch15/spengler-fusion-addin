"""Gehrungsecke geometrisch (reine Rechnung) und atomares Einsetzen eines 3D-Details (Attrappen) – KEIN Fusion-Live-Test."""
import math
import unittest

import fake_fusion_blech as ff
from _basis import DatenTest  # noqa: F401
from spengler_cad.core import gehrung

R = 1 / math.sqrt(2)


class Gehrungsecke(unittest.TestCase):
    """Ecke im Ursprung, Kanten entlang +x und +y, Blech in XY (nb = z)."""
    E1, E2, NB, ECKE = (1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)

    def test_gehrungsflaechen_werden_erkannt(self):
        k = [("gehrung_a", (R, -R, 0), (1, 1, 1)), ("gehrung_b", (-R, R, 0), (1.1, 1.0, 1)),
             ("flansch_aussen", (0, -1, 0), (5, 0, 1)), ("oben", (0, 0, 1), (5, 5, 0)), ("schraeg", (0.95, 0.31, 0), (1, 1, 1))]
        self.assertEqual(gehrung.gehrungsflaechen(k, self.E1, self.E2, self.NB, self.ECKE), ["gehrung_a", "gehrung_b"])
        self.assertEqual(gehrung.gehrungsflaechen(k, self.E1, self.E2, self.NB, self.ECKE, reichweite_mm=0.5), [], "zu weit von der Ecke")

    def test_stumpfe_ecke_hat_keine_gehrungsflaechen(self):
        k = [("stirn_a", (1, 0, 0), (0, 0, 1)), ("stirn_b", (0, 1, 0), (0, 0, 1))]
        self.assertEqual(gehrung.gehrungsflaechen(k, self.E1, self.E2, self.NB, self.ECKE), [])

    def test_eckspalt(self):
        self.assertEqual(gehrung.bewerte_eckspalt(0.2, 1.0)[0], "ok")
        s, t = gehrung.bewerte_eckspalt(3.0, 1.0)
        self.assertEqual(s, "fehler")
        self.assertIn("offen", t)
        self.assertEqual(gehrung.bewerte_eckspalt(None, 1.0)[0], "unbekannt")


def _fa():
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class Param(object):
    def __init__(self, liste, name, loeschbar=True):
        self.name, self._liste, self._ok = name, liste, loeschbar

    def deleteMe(self):
        if self._ok:
            self._liste.elemente.remove(self)
        return self._ok


class Parameter(ff.Liste):
    def itemByName(self, n):
        return next((p for p in self.elemente if p.name == n), None)


class DetailEinsetzen(unittest.TestCase):
    """Jeder Fehler nach dem Import entfernt Occurrence und neue Parameter wieder."""
    def setUp(self):
        fa = _fa()
        self.fa = fa
        self.d = ff.Design()
        self.d.userParameters = Parameter()
        self.occ = ff.Objekt("Import")
        namen = ("design", "detail_importieren", "matrix_fusion", "koerper_neu", "detail_integrieren")
        alt = {n: getattr(fa, n) for n in namen}
        self.addCleanup(lambda: [setattr(fa, n, f) for n, f in alt.items()])
        self.addCleanup(fa.TESTFEHLER.clear)
        fa.design = lambda: self.d

        def importieren(f3d, comp):
            p = Param(self.d.userParameters, "SD_H_1")
            self.d.userParameters.elemente.append(p)
            return self.occ, ["SD_H_1"]
        fa.detail_importieren = importieren
        fa.matrix_fusion = lambda T: "M"
        fa.koerper_neu = lambda t: "ziel"
        fa.detail_integrieren = lambda occ, body, neu: ("CF", ["w"])

    def test_erfolg_ohne_integration(self):
        erg = self.fa.detail_einsetzen("x.f3d", None, [], lambda occ, neu: {"gesetzt": neu})
        self.assertIs(erg["occ"], self.occ)
        self.assertEqual(erg["gesetzt"], ["SD_H_1"])
        self.assertTrue(self.occ.isValid)

    def test_fehler_in_jeder_phase_baut_zurueck(self):
        for stelle in ("detail_import", "detail_ausrichten", "detail_parameter"):
            self.setUp()
            self.fa.TESTFEHLER.clear()
            self.fa.TESTFEHLER.add(stelle)
            with self.assertRaises(self.fa.AdapterFehler) as cm:
                self.fa.detail_einsetzen("x.f3d", None, [], None, "tok")
            self.assertIn(self.fa.testfehler_text(stelle), str(cm.exception))
            self.assertIn("Import wieder entfernt", str(cm.exception))
            self.assertFalse(self.occ.isValid, stelle)
            self.assertEqual(self.d.userParameters.count, 0, "neuer Parameter entfernt")

    def test_integration_scheitert(self):
        def kaputt(occ, body, neu):
            raise self.fa.AdapterFehler("Fusion konnte nicht vereinigen")
        self.fa.detail_integrieren = kaputt
        with self.assertRaises(self.fa.AdapterFehler) as cm:
            self.fa.detail_einsetzen("x.f3d", None, [], None, "tok")
        self.assertTrue(cm.exception.rueckbau_ok)
        self.assertFalse(self.occ.isValid)

    def test_rueckbau_unvollstaendig_wird_gemeldet(self):
        self.occ = ff.Objekt("Import", ergebnis=False)
        self.fa.TESTFEHLER.add("detail_ausrichten")
        with self.assertRaises(self.fa.AdapterFehler) as cm:
            self.fa.detail_einsetzen("x.f3d", None, [], None)
        self.assertFalse(cm.exception.rueckbau_ok)
        self.assertIn("ACHTUNG", str(cm.exception))


if __name__ == "__main__":
    unittest.main()


class DetailAnpassen(unittest.TestCase):
    """Modus B «an Zylinder anpassen» (Prototyp): nur über einen Anschlussradius-Parameter, keine freie Verformung – reine Logik, KEIN Fusion-Test."""
    def vorlage(self, *rollen, lo=None, hi=None):
        return {"parameters": [{"name": "H", "role": None}] + [{"name": "R%d" % i, "role": r, "min": lo, "max": hi} for i, r in enumerate(rollen)]}

    def test_anschlussradius_wird_gesetzt(self):
        from spengler_cad.details import detail_validation as dv
        self.assertEqual(dv.anpassung(self.vorlage("anschlussradius"), "zylinder", 101.0), ("R0", 101.0))

    def test_ablehnungen(self):
        from spengler_cad.details import detail_validation as dv
        for v, typ, r, text in ((self.vorlage("anschlussradius"), "kegel", 100, "nur auf Zylinderflächen"),
                                (self.vorlage(), "zylinder", 100, "keinen"),
                                (self.vorlage("anschlussradius", "anschlussradius"), "zylinder", 100, "mehrere"),
                                (self.vorlage("anschlussradius", lo=200, hi=500), "zylinder", 100, "ausserhalb"),
                                (self.vorlage("anschlussradius"), "zylinder", 0, "nicht lesbar")):
            with self.assertRaises(ValueError) as cm:
                dv.anpassung(v, typ, r)
            self.assertIn(text, str(cm.exception))

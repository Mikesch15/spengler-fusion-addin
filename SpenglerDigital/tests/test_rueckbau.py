"""Rückbau nach einem Fehler: «Bauteil erstellen» und «Blech aus Massaufnahme» dürfen keine halbfertige Komponente zurücklassen.
Mit Attrappen (Fusion-Stub) – KEIN echter Fusion-Test."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))

from _basis import DatenTest  # noqa: F401,E402


def _fa():
    """Das Adapter-Modul, das die Befehle tatsächlich benutzen (nach früheren Tests kann es ein neu geladenes Objekt sein)."""
    from spengler_cad.commands import bauteil_command
    return bauteil_command.fa


class FakeKomponente(object):
    def __init__(self, name, token="T1"):
        self.name, self.entityToken = name, token


class FakeOcc(object):
    def __init__(self, comp, ok=True, wirft=False):
        self.component, self._ok, self._wirft, self.geloescht = comp, ok, wirft, False

    def deleteMe(self):
        if self._wirft:
            raise RuntimeError("Fusion verweigert das Löschen")
        self.geloescht = self._ok
        return self._ok


class FakeDesign(object):
    def __init__(self, occs):
        class Root(object):
            pass
        self.rootComponent = Root()
        self.rootComponent.occurrences = occs


class _Patch(unittest.TestCase):
    def patche(self, **attrs):
        fa = _fa()
        for name, wert in attrs.items():
            original = getattr(fa, name)
            self.addCleanup(setattr, fa, name, original)
            setattr(fa, name, wert)


class KomponenteEntfernen(_Patch):
    def test_entfernt_die_richtige(self):
        fa = _fa()
        a, b = FakeKomponente("A", "T1"), FakeKomponente("B", "T2")
        oa, ob = FakeOcc(a), FakeOcc(b)
        self.patche(design=lambda: FakeDesign([oa, ob]))
        self.assertTrue(fa.komponente_entfernen(b))
        self.assertTrue(ob.geloescht)
        self.assertFalse(oa.geloescht, "eine fremde Komponente darf nie entfernt werden")

    def test_nicht_gefunden_oder_fehler_ist_false(self):
        fa = _fa()
        a = FakeKomponente("A", "T1")
        self.patche(design=lambda: FakeDesign([FakeOcc(FakeKomponente("X", "T9"))]))
        self.assertFalse(fa.komponente_entfernen(a))
        self.patche(design=lambda: FakeDesign([FakeOcc(a, wirft=True)]))
        self.assertFalse(fa.komponente_entfernen(a))
        self.patche(design=lambda: FakeDesign([FakeOcc(a, ok=False)]))
        self.assertFalse(fa.komponente_entfernen(a))

    def test_abbruchmeldung(self):
        fa = _fa()
        a = FakeKomponente("Mauer")
        self.patche(design=lambda: FakeDesign([FakeOcc(a)]))
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abbruch_mit_rueckbau(a, RuntimeError("Traceback (most recent call last):\n3 : edge is not suitable for a sheet metal flange"), "Bauteil «Mauer»")
        self.assertIn("edge is not suitable", str(cm.exception))
        self.assertNotIn("Traceback", str(cm.exception), "von Fusion-Ausnahmen steht nur die letzte Zeile in der Meldung")
        self.assertIn("wieder entfernt", str(cm.exception))
        self.assertTrue(cm.exception.rueckbau_ok)
        self.patche(design=lambda: FakeDesign([]))
        with self.assertRaises(fa.AdapterFehler) as cm:
            fa.abbruch_mit_rueckbau(a, fa.AdapterFehler("Grundblech fehlt"), "Bauteil «Mauer»")
        self.assertIn("ACHTUNG", str(cm.exception))
        self.assertIn("Strg+Z", str(cm.exception))
        self.assertFalse(cm.exception.rueckbau_ok)


class BauteilRueckbau(_Patch):
    def _plan(self):
        from spengler_cad.core import bauteil, models
        v = models.neue_bauteilvorlage("Test")
        v["breite"] = "60"
        v["verlauf"] = {"art": "gerade", "beispiel": "", "seite": "links"}
        v["seiten"] = bauteil.seiten_aus_texten({"verlauf": "90 20"})
        mat = {"id": "m", "name": "Alu", "thickness": 1.0, "innerRadius": 1.0, "kFactor": 0.4}
        return bauteil.plan(v, {}, mat, "", 500), v, mat

    def test_fehler_im_flansch_entfernt_die_komponente(self):
        fa = _fa()
        from spengler_cad.commands import bauteil_command as bc
        ereignisse = []
        comp = FakeKomponente("Test")
        self.patche(zeitleiste_stand=lambda: 5, neue_komponente=lambda n: comp, blech_aus_profil=lambda c, s, d: object(), blechdicke_mm=lambda b: 1.0,
                    kanten_nach_ketten=lambda b, k: {"verlauf": ["t1"]},
                    kanten_folge_bauen=lambda *a, **k: (_ for _ in ()).throw(fa.AdapterFehler("Fusion hat den Flansch nicht erzeugt")),
                    komponente_entfernen=lambda c: ereignisse.append(("entfernt", c.name)) or True,
                    zeitleiste_gruppieren=lambda *a: ereignisse.append(("gruppe",)) or True)
        p, v, mat = self._plan()
        with self.assertRaises(fa.AdapterFehler) as cm:
            bc.bauen(p, v, mat, "Test")
        self.assertEqual(ereignisse, [("entfernt", "Test")], "Rückbau ja, Zeitleisten-Gruppe nein")
        self.assertIn("Flansch nicht erzeugt", str(cm.exception))
        self.assertIn("wieder entfernt", str(cm.exception))

    def test_fehler_beim_grundblech_entfernt_die_komponente(self):
        fa = _fa()
        from spengler_cad.commands import bauteil_command as bc
        entfernt = []
        self.patche(zeitleiste_stand=lambda: 5, neue_komponente=lambda n: FakeKomponente(n),
                    blech_aus_profil=lambda c, s, d: (_ for _ in ()).throw(fa.AdapterFehler("Das Grundblech liess sich nicht erzeugen")),
                    komponente_entfernen=lambda c: entfernt.append(c.name) or True)
        p, v, mat = self._plan()
        with self.assertRaises(fa.AdapterFehler):
            bc.bauen(p, v, mat, "Test")
        self.assertEqual(entfernt, ["Test"])

    def test_erfolg_laesst_die_komponente_stehen(self):
        from spengler_cad.commands import bauteil_command as bc
        ereignisse = []
        self.patche(zeitleiste_stand=lambda: 5, neue_komponente=lambda n: FakeKomponente(n), blech_aus_profil=lambda c, s, d: object(), blechdicke_mm=lambda b: 1.0,
                    kanten_nach_ketten=lambda b, k: {"verlauf": ["t1", "t2"]}, kanten_folge_bauen=lambda *a, **k: ["f1"],
                    komponente_entfernen=lambda c: ereignisse.append("entfernt") or True,
                    zeitleiste_gruppieren=lambda *a: ereignisse.append("gruppe") or True)
        p, v, mat = self._plan()
        bericht, hinweise = bc.bauen(p, v, mat, "Test")
        self.assertEqual(ereignisse, ["gruppe"])
        self.assertTrue(any("Zeitleiste" in z for z in bericht))
        self.assertTrue(any("Kante am Verlauf: 1 Feature(s) an 2 Kante(n)" in z for z in bericht))

    def test_rueckbau_scheitert_wird_gemeldet(self):
        fa = _fa()
        from spengler_cad.commands import bauteil_command as bc
        self.patche(zeitleiste_stand=lambda: 5, neue_komponente=lambda n: FakeKomponente(n),
                    blech_aus_profil=lambda c, s, d: (_ for _ in ()).throw(RuntimeError("Fusion stürzt ab")), komponente_entfernen=lambda c: False)
        p, v, mat = self._plan()
        with self.assertRaises(fa.AdapterFehler) as cm:
            bc.bauen(p, v, mat, "Test")
        self.assertIn("ACHTUNG", str(cm.exception))
        self.assertFalse(cm.exception.rueckbau_ok)


class BlechAusMassaufnahmeRueckbau(_Patch):
    G = {"breite": 80.0, "ops": [{"typ": "flansch", "winkel": 90.0, "laenge": 25.0, "radius": None}], "hinweise": [], "laenge": 1000.0}
    M = {"id": 41, "title": "Stirn", "art": "massaufnahme"}
    MAT = {"id": "m", "name": "Alu", "thickness": 1.0}

    def test_fehler_bei_den_kanten_entfernt_die_komponente(self):
        fa = _fa()
        from spengler_cad.commands import grundblech_command as gc
        entfernt, gruppen = [], []
        self.patche(zeitleiste_stand=lambda: 1, neue_komponente=lambda n: FakeKomponente(n), grundblech_bauen=lambda c, l, b, d: object(), blechdicke_mm=lambda b: 1.0,
                    grundblech_kante=lambda b: object(),
                    folge_anbringen=lambda *a, **k: (_ for _ in ()).throw(fa.AdapterFehler("Richtung weicht ab")),
                    komponente_entfernen=lambda c: entfernt.append(c.name) or True, zeitleiste_gruppieren=lambda *a: gruppen.append(1))
        with self.assertRaises(fa.AdapterFehler) as cm:
            gc.bauen(self.M, self.G, self.MAT, 1000.0, "Blech", True)
        self.assertEqual((entfernt, gruppen), (["Blech"], []))
        self.assertIn("Richtung weicht ab", str(cm.exception))

    def test_ohne_kanten_und_erfolg(self):
        from spengler_cad.commands import grundblech_command as gc
        gruppen = []
        self.patche(zeitleiste_stand=lambda: 1, neue_komponente=lambda n: FakeKomponente(n), grundblech_bauen=lambda c, l, b, d: object(), blechdicke_mm=lambda b: 0.7,
                    zeitleiste_gruppieren=lambda *a: gruppen.append(1))
        bericht, hinweise = gc.bauen(self.M, self.G, self.MAT, 1000.0, "Blech", False)
        self.assertEqual(gruppen, [1])
        self.assertTrue(any("Blechregel in Fusion hat 0.70 mm" in z for z in bericht), "abweichende Blechregel wird gemeldet")


if __name__ == "__main__":
    unittest.main()

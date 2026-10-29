"""Vorlagen: Engine, Prüfung, Speichern/Laden/Kopieren/Umbenennen/Löschen/Import/Export, leere Bibliothek."""
import os
import unittest

from _basis import ADDIN, DatenTest, datei_inhalt, test_material
from spengler_cad.core import models, template_engine as te
from spengler_cad.core.expressions import AusdruckFehler, berechne
from spengler_cad.storage.template_repository import VorlagenRepository, VorlagenSpeicherFehler


def testvorlage(name="TEST Falz"):
    """Technische Testvorlage (nur Tests)."""
    return te.vorlage_aus_kurzschrift(name, "90 H U+ u+4*t", {"H": 25, "u": 7})


class LeereBibliothekTest(DatenTest):
    def test_system_und_benutzer_leer(self):
        repo = VorlagenRepository()
        self.assertEqual(repo.liste("kantenvorlage"), [])
        self.assertEqual(repo.liste("detailvorlage"), [])
        sysordner = os.path.join(ADDIN, "templates", "system")
        dateien = [n for r, _, ns in os.walk(sysordner) for n in ns if n.endswith(".json")]
        self.assertEqual(dateien, [], "Systemvorlagen müssen produktiv leer sein")

    def test_keine_vorlagen_im_programmcode(self):
        """Kein Python-Modul des Add-ins enthält Spengler-Profile/Kurzschriften als Vorlagen."""
        verboten = ["Doppelstehfalz", "Ortgang", "Traufe", "Wasserfalz", "BAUSTEINE"]
        for wurzel, _, namen in os.walk(os.path.join(ADDIN, "spengler_cad")):
            for n in namen:
                if n.endswith(".py"):
                    text = datei_inhalt(os.path.join(wurzel, n))
                    for v in verboten:
                        self.assertNotIn(v, text, "%s enthält «%s»" % (n, v))


class EngineTest(unittest.TestCase):
    def test_ausdruecke(self):
        self.assertEqual(berechne("H + 2*t", {"H": 25, "t": 0.5}), 26)
        self.assertEqual(berechne("max(u, 3*t)", {"u": 1, "t": 1}), 3)
        self.assertEqual(berechne("12,5", {}), 12.5)
        for falsch in ("__import__('os')", "H.x", "1/0", "a", "2**99", "[1]"):
            with self.assertRaises(AusdruckFehler, msg=falsch):
                berechne(falsch, {})

    def test_vorlage_aus_kurzschrift(self):
        v = testvorlage()
        self.assertEqual([p["name"] for p in v["parameters"]], ["H", "u"])
        ops, warn = te.aufloesen(v, {"H": 30}, test_material())
        self.assertEqual(ops[0]["laenge"], 30)
        self.assertAlmostEqual(ops[1]["laenge"], 9.8)
        self.assertEqual(ops[1]["winkel"], 180)

    def test_fehlender_wert_und_bereich(self):
        v = te.vorlage_aus_kurzschrift("X", "90 H")   # kein Standardwert → Pflichteingabe
        with self.assertRaises(te.VorlagenFehler):
            te.aufloesen(v, {}, test_material())
        v["parameters"][0].update({"min": 10, "max": 40})
        with self.assertRaises(te.VorlagenFehler):
            te.aufloesen(v, {"H": 50}, test_material())
        ops, _ = te.aufloesen(v, {"H": 40}, test_material())
        self.assertEqual(ops[0]["laenge"], 40)

    def test_materialwerte_noetig(self):
        v = testvorlage()
        m = test_material()
        m["thickness"] = 0.7
        ohne_t = dict(m)
        ohne_t.pop("thickness")
        with self.assertRaises(te.VorlagenFehler) as cm:
            te.aufloesen(v, {}, ohne_t)
        self.assertIn("t", str(cm.exception))

    def test_ungueltige_vorlagen(self):
        from spengler_cad.core.validation import pruefe_kantenvorlage
        faelle = {
            "leer": models.neue_kantenvorlage("leer"),
            "winkel0": models.neue_kantenvorlage("w", operations=[models.operation("flansch", 0, 10)]),
            "unbekannt": models.neue_kantenvorlage("u", operations=[models.operation("flansch", 90, "Q")]),
            "reserviert": models.neue_kantenvorlage("r", operations=[models.operation("flansch", 90, 10)], parameters=[models.parameter("t")]),
            "umschlag90": models.neue_kantenvorlage("h", operations=[models.operation("umschlag", 90, 10)]),
            "neg": models.neue_kantenvorlage("n", operations=[models.operation("flansch", 90, -5)]),
            "bereich": models.neue_kantenvorlage("b", operations=[models.operation("flansch", 90, "H")], parameters=[models.parameter("H", standard=5, minimum=10)]),
        }
        for name, v in faelle.items():
            f, _ = pruefe_kantenvorlage(v)
            self.assertTrue(f, name)

    def test_expertenmodus_operationen(self):
        v = testvorlage()
        v2 = te.op_hinzufuegen(v, models.operation("flansch", -45, 10))
        self.assertEqual(len(v2["operations"]), 3)
        self.assertEqual(len(v["operations"]), 2, "Original unverändert")
        v3 = te.op_verschieben(v2, 2, -1)
        self.assertEqual(v3["operations"][1]["winkel"], -45)
        v4 = te.op_entfernen(v3, 0)
        self.assertEqual(len(v4["operations"]), 2)
        v5 = te.op_aendern(v4, 0, laenge=12)
        self.assertEqual(v5["operations"][0]["laenge"], 12)


class RepositoryTest(DatenTest):
    def test_speichern_version_kopieren_umbenennen(self):
        repo = VorlagenRepository()
        v = repo.speichern(testvorlage())
        self.assertEqual(v["version"], 1)
        self.assertEqual(repo.speichern(v)["version"], 1, "unverändert → keine neue Version")
        v["operations"][0]["laenge"] = "H+1"
        v2 = repo.speichern(v)
        self.assertEqual(v2["version"], 2)
        self.assertEqual([x["version"] for x in repo.versionen(v["id"])], [1])
        k = repo.duplizieren(v["id"])
        self.assertNotEqual(k["id"], v["id"])
        self.assertEqual(k["version"], 1)
        self.assertEqual(repo.holen(v["id"])["version"], 2, "Original unverändert")
        repo.umbenennen(k["id"], "Neu")
        self.assertEqual(repo.holen(k["id"])["name"], "Neu")
        repo.favorit(k["id"], True)
        repo.kategorie(k["id"], "Dach")
        self.assertEqual(repo.liste()[0]["id"], k["id"], "Favoriten zuerst")
        self.assertIn("Dach", repo.kategorien())

    def test_loeschen_nur_mit_bestaetigung(self):
        repo = VorlagenRepository()
        v = repo.speichern(testvorlage())
        with self.assertRaises(VorlagenSpeicherFehler):
            repo.loeschen(v["id"])
        self.assertEqual(len(repo.liste()), 1)
        p = repo.loeschen(v["id"], bestaetigt=True)
        self.assertEqual(repo.liste(), [])
        self.assertTrue(os.path.exists(p))
        repo.wiederherstellen(p)
        self.assertEqual(repo.liste()[0]["id"], v["id"])

    def test_ungueltig_wird_nicht_gespeichert(self):
        repo = VorlagenRepository()
        with self.assertRaises(VorlagenSpeicherFehler):
            repo.speichern(models.neue_kantenvorlage(""))
        self.assertEqual(repo.liste(), [])

    def test_neuere_version_bleibt_unberuehrt(self):
        repo = VorlagenRepository()
        v = repo.speichern(testvorlage())
        from spengler_cad.storage import json_store
        roh = json_store.lesen(v["_datei"] if "_datei" in v else repo.holen(v["id"])["_datei"])
        roh["schemaVersion"] = 99
        roh["zukunftsfeld"] = {"x": 1}
        pfad = repo.holen(v["id"])["_datei"]
        json_store.schreiben(pfad, roh)
        vorher = datei_inhalt(pfad, True)
        x = repo.holen(v["id"])
        self.assertTrue(x["_nurLesen"])
        for aktion in (lambda: repo.umbenennen(v["id"], "z"), lambda: repo.speichern(x), lambda: repo.loeschen(v["id"], bestaetigt=True)):
            with self.assertRaises(VorlagenSpeicherFehler):
                aktion()
        self.assertEqual(datei_inhalt(pfad, True), vorher)

    def test_export_import(self):
        repo = VorlagenRepository()
        a = repo.speichern(testvorlage("A"))
        b = repo.speichern(testvorlage("B"))
        datei = os.path.join(self.ordner, "export.json")
        self.assertEqual(repo.exportieren([a["id"], b["id"]], datei), 2)
        erg = repo.importieren(datei)
        self.assertEqual(len(erg["kopien"]), 2, "gleiche IDs werden als Kopie importiert, nichts überschrieben")
        self.assertEqual(len(repo.liste()), 4)
        # in eine leere zweite Bibliothek
        os.environ["SPENGLER_CAD_DATEN"] = os.path.join(self.ordner, "zweit")
        repo2 = VorlagenRepository()
        erg = repo2.importieren(datei)
        self.assertEqual(sorted(erg["importiert"]), sorted([a["id"], b["id"]]))
        self.assertEqual(repo2.holen(a["id"])["operations"], a["operations"])

    def test_projektbibliothek(self):
        proj = os.path.join(self.ordner, "projekt")
        repo = VorlagenRepository(projekt_ordner=proj)
        repo.speichern(testvorlage("P"), ebene="projekt")
        self.assertEqual([v["_ebene"] for v in repo.liste()], ["projekt"])
        with self.assertRaises(VorlagenSpeicherFehler):
            repo.speichern(testvorlage("S"), ebene="system")


if __name__ == "__main__":
    unittest.main()

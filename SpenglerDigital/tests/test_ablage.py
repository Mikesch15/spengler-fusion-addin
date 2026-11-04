"""Ablagen: Ordner ohne Kundenauftrag (Logik, Kontext, Start, Exportordner)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))

from _basis import DatenTest  # noqa: F401,E402
from spengler_cad.core import ablage, start  # noqa: E402


class AblageLogik(unittest.TestCase):
    def test_pfad(self):
        self.assertEqual(ablage.pfad_aus_text(" Wettbewerbe / Schweizermeisterschaft "), ["Wettbewerbe", "Schweizermeisterschaft"])
        self.assertEqual(ablage.pfad_aus_text("a\\b//c"), ["a", "b", "c"])
        self.assertEqual(ablage.pfad_text(["a", "b"]), "a/b")
        for schlecht in ("", " / ", "a/b:c", "a/../b", "a?b", "/".join("x" * 1 for _ in range(7))):
            with self.assertRaises(ablage.AblageFehler):
                ablage.pfad_aus_text(schlecht)

    def test_liste(self):
        a = ablage.hinzufuegen(ablage.standard(), "Schweizermeisterschaft", ["Wettbewerbe", "SM"])
        a = ablage.hinzufuegen(a, "Muster", ["Muster"])
        self.assertEqual([x["name"] for x in a["liste"]], ["Muster", "Schweizermeisterschaft"])
        a = ablage.hinzufuegen(a, "schweizermeisterschaft", ["Neu", "Pfad"])            # gleicher Name (Gross/klein egal) → ändern, nicht doppeln
        self.assertEqual(len(a["liste"]), 2)
        self.assertEqual(ablage.finden(a, "schweizermeisterschaft")["pfad"], ["Neu", "Pfad"])
        a["aktiv"] = "Muster"
        self.assertEqual(ablage.entfernen(a, "Muster")["aktiv"], "")
        for schlecht in ("", "a/b", "x:y"):
            with self.assertRaises(ablage.AblageFehler):
                ablage.hinzufuegen(ablage.standard(), schlecht, ["p"])

    def test_kontext(self):
        a = ablage.hinzufuegen(ablage.hinzufuegen(ablage.standard(), "Wettbewerbe", ["Wettbewerbe"]), "SM", ["Wettbewerbe", "SM"])
        self.assertEqual(ablage.aus_dokumentpfad(a, ["wettbewerbe", "sm", "Modelle"])["name"], "SM", "der längste Pfad gewinnt, Gross/klein egal")
        self.assertEqual(ablage.aus_dokumentpfad(a, ["Wettbewerbe", "Anderes"])["name"], "Wettbewerbe")
        self.assertIsNone(ablage.aus_dokumentpfad(a, ["Projekte", "2026"]))
        self.assertIsNone(ablage.kontext(a, ["Projekte"]))
        a["aktiv"] = "SM"
        self.assertEqual(ablage.kontext(a, ["Projekte"]), {"name": "SM", "pfad": ["Wettbewerbe", "SM"], "quelle": "aktiv gesetzt"})
        self.assertEqual(ablage.kontext(a, ["Wettbewerbe"])["quelle"], "Fusion-Ordner")
        self.assertNotIn("/", ablage.exportname("a/b"))
        self.assertEqual(ablage.exportname("..."), "Ablage")


class AblageStart(unittest.TestCase):
    Z = {"angemeldet": True, "auftrag": "", "objekt": "SM", "ablage": "Schweizermeisterschaft", "projekt_in_app": None, "materialien": 1, "vorlagen": 1, "dokument_gespeichert": True,
         "fehlende_funktionen": []}

    def test_ohne_auftrag_aber_mit_ablage_darf_alles(self):
        for bid in start.BRAUCHT_AUFTRAG:
            self.assertEqual(start.voraussetzungen(bid, self.Z, True)[0], [], bid)
        self.assertTrue(start.voraussetzungen("spenglerKantenBearbeiten", dict(self.Z, ablage=""), True)[0])

    def test_start_uebersicht(self):
        e = start.bewerte(self.Z)
        texte = " | ".join(z["text"] for z in e["zeilen"])
        self.assertIn("Aktive Ablage: Schweizermeisterschaft", texte)
        self.assertEqual(e["naechster"], "kanten")
        self.assertTrue(e["ablauf"].startswith("✅ Ablage"))
        self.assertEqual(start.bewerte(dict(self.Z, ablage=""))["naechster"], "auftrag_wahl")


class AblageKontext(DatenTest):
    def test_auftrag_angaben_und_exportordner(self):
        from spengler_cad.commands import export_command as ex
        from spengler_cad.geometry import fusion_adapter as fa
        e = {"order": {"auftrag": "", "objekt": "", "jahr": None}, "auftrag": None, "export": {},
             "ablagen": ablage.hinzufuegen(ablage.standard(), "Schweizermeisterschaft", ["Wettbewerbe", "SM"])}
        original = fa.dokument_ordnerpfad
        self.addCleanup(setattr, fa, "dokument_ordnerpfad", original)
        fa.dokument_ordnerpfad = lambda: ["Wettbewerbe", "SM", "Modelle"]
        a = ex.auftrag_angaben(e)
        self.assertEqual((a["auftrag"], a["objekt"], a["ablage"], a["quelle"]), ("", "Schweizermeisterschaft", "Schweizermeisterschaft", "Ablage"))
        fa.dokument_ordnerpfad = lambda: ["Projekte"]
        self.assertNotIn("ablage", ex.auftrag_angaben(e), "ohne passenden Ordner und ohne aktive Ablage: kein Ablage-Kontext")
        e["ablagen"]["aktiv"] = "Schweizermeisterschaft"
        self.assertEqual(ex.auftrag_angaben(e)["ablage"], "Schweizermeisterschaft")
        e["order"]["auftrag"] = "17642"
        self.assertNotIn("ablage", ex.auftrag_angaben(e), "ein aktiver Auftrag hat Vorrang vor einer nur gesetzten Ablage")
        ordner = ex._exportordner(dict(e, export={"folder": os.path.join(os.environ["SPENGLER_CAD_DATEN"], "ex")}), {"ablage": "Schweizermeisterschaft", "auftrag": ""})
        self.assertIn("Schweizermeisterschaft", ordner)
        self.assertTrue(os.path.isdir(ordner))


if __name__ == "__main__":
    unittest.main()

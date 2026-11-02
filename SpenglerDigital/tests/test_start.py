"""Start/Übersicht und Voraussetzungen (ohne Fusion)."""
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import start


def zustand(**k):
    return dict({"angemeldet": True, "auftrag": "17642", "objekt": "Nägeligasse 1a, Bern", "projekt_in_app": True, "materialien": 2, "vorlagen": 3,
                 "dokument_gespeichert": True, "fehlende_funktionen": []}, **k)


class StartTest(unittest.TestCase):
    def test_alles_in_ordnung_naechster_schritt_kanten(self):
        e = start.bewerte(zustand())
        self.assertEqual(e["naechster"], "kanten")
        self.assertTrue(all(z["ok"] for z in e["zeilen"]))

    def test_reihenfolge_der_empfehlung(self):
        self.assertEqual(start.bewerte(zustand(materialien=0))["naechster"], "einstellungen")
        self.assertEqual(start.bewerte(zustand(vorlagen=0))["naechster"], "einstellungen")
        self.assertEqual(start.bewerte(zustand(auftrag=""))["naechster"], "auftrag_wahl")
        self.assertEqual(start.bewerte(zustand(projekt_in_app=False))["naechster"], "abgleich")
        self.assertEqual(start.bewerte(zustand(projekt_in_app=None))["naechster"], "kanten", "unbekannt (nicht angemeldet) bremst nicht")

    def test_zeilen_nennen_das_fehlende(self):
        e = start.bewerte(zustand(angemeldet=False, auftrag="", fehlende_funktionen=["Saum", "Flansch", "x", "y"]))
        texte = " | ".join(z["text"] for z in e["zeilen"])
        self.assertIn("nicht angemeldet", texte)
        self.assertIn("keiner – bitte «Auftrag wählen»", texte)
        self.assertIn("Saum; Flansch; x …", texte)

    def test_voraussetzungen(self):
        p, l = start.voraussetzungen("spenglerKantenBearbeiten", zustand(auftrag=""))
        self.assertEqual(l, "spenglerAuftragWaehlen")
        self.assertIn("kein Auftrag aktiv", p[0])
        self.assertEqual(start.voraussetzungen("spenglerKantenBearbeiten", zustand())[0], [])
        self.assertEqual(start.voraussetzungen("spenglerKantenBearbeiten", zustand(auftrag=""), auftrag_erforderlich=False)[0], [], "abschaltbar")
        p, l = start.voraussetzungen("spenglerKantenBearbeiten", zustand(materialien=0))
        self.assertIn("Materialprofil", p[0])
        self.assertEqual(l, "spenglerVorlagenEinstellungen")
        self.assertEqual(start.voraussetzungen("spenglerKantenBearbeiten", zustand(vorlagen=0))[0][0][:12], "Es gibt noch")
        self.assertEqual(start.voraussetzungen("spenglerHilfe", zustand(auftrag="", materialien=0))[0], [], "Hilfe und Einstellungen bleiben immer frei")
        p, _ = start.voraussetzungen("spenglerAbwicklungDxf", zustand(auftrag=""))
        self.assertEqual(len(p), 1)


if __name__ == "__main__":
    unittest.main()

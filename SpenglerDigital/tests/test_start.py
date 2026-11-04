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


class ProjektInfoTest(DatenTest):
    def test_zeilen_mit_projektinfo_und_neu(self):
        e = start.bewerte(zustand(projekt_info={"kunde": "Weyermann AG", "status": "In Arbeit", "hinweis": "Schlüssel beim Hauswart", "termin": "Montage, 10.11.2026", "aktiv": 2},
                                  app_neu={"text": "1 Auftrag aus der App wartet"}))
        texte = " | ".join(z["text"] for z in e["zeilen"])
        self.assertIn("Projekt: Weyermann AG · In Arbeit · Nächster Termin: Montage, 10.11.2026 · 2 aktive Massaufnahmen", texte)
        self.assertIn("Hinweis im Projekt: Schlüssel beim Hauswart", texte)
        self.assertIn("🔔 Neu aus der App: 1 Auftrag aus der App wartet", texte)
        e2 = start.bewerte(zustand())
        self.assertNotIn("Neu aus der App", " | ".join(z["text"] for z in e2["zeilen"]))

    def test_projekt_info_aus_roh(self):
        from spengler_cad.commands import zustand as zu
        roh = {"projekt": {"order_no": "18162", "customer": "K", "status": "offen", "hinweis": "h"}, "termine": [{"titel": "Montage", "start_datum": "2999-01-01"}],
               "massaufnahmen": [{"id": 1, "workflow_status": "freigegeben"}, {"id": 2, "workflow_status": "abgeschlossen"}], "teile": [], "auftraege": [{"status": "offen"}]}
        i = zu._projekt_info("18162", roh)
        self.assertEqual((i["projekt_info"]["kunde"], i["projekt_info"]["aktiv"], i["projekt_info"]["termin"]), ("K", 1, "Montage, 1.1.2999"))
        self.assertEqual(i["app_neu"]["offene_auftraege"], 1)

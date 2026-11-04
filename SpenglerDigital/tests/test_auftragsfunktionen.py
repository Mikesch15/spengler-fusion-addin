"""Prüfung vor dem Export, Abkantliste, Bestellliste, Teilenummer-Label, lokaler Exportpfad (alles ohne Fusion)."""
import os
import shutil
import tempfile
import unittest

from _basis import DatenTest, test_material  # noqa: F401
from spengler_cad.core import abgleich, auftrag
from spengler_cad.manufacturing import bend_list, bestellung, kalkulation, mappe, profilblatt, pruefung

OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "umschlag", "winkel": 180, "laenge": 6, "radius": 0.3}]


class PruefungTest(unittest.TestCase):
    def test_warnungen(self):
        teile = [{"name": "A", "nr": 1, "material": {"name": "m"}, "dicke": 0.7, "abwicklung": True, "operationen": OPS, "ri": 1.5},
                 {"name": "B", "nr": 1, "material": None, "dicke": 0.7, "abwicklung": False, "operationen": None, "ri": None},
                 {"name": "C", "nr": "", "material": {"name": "m"}, "dicke": 0.7, "abwicklung": True, "operationen": [], "ri": None}]
        w = " | ".join(pruefung.pruefe_teile(teile))
        self.assertIn("A, Schritt 2 (Umschlag): Schenkel 6.0 mm", w)
        self.assertIn("A, Schritt 2 (Umschlag): Innenradius 0.30 mm", w)
        self.assertNotIn("A, Schritt 1", w)
        self.assertIn("B: kein Materialprofil", w)
        self.assertIn("B: keine Fusion-Abwicklung", w)
        self.assertIn("C: keine Teilenummer", w)
        self.assertIn("Teilenummer 1 mehrfach vergeben: A, B", w)

    def test_schwellen_aus_einstellung(self):
        t = [{"name": "A", "nr": 1, "material": {"n": 1}, "dicke": 0.7, "abwicklung": True, "operationen": OPS[:1], "ri": 1.5}]
        self.assertEqual(pruefung.pruefe_teile(t, {"minSchenkel": 30}).__len__(), 1)
        self.assertEqual(pruefung.pruefe_teile(t, {"minSchenkel": 5}), [])


class AbkantlisteTest(unittest.TestCase):
    def test_html(self):
        h = bend_list.abkantliste_html([{"nr": 3, "name": "Ortgang <1>", "material": "Alu", "dicke": 0.7, "operationen": OPS, "ri": 1.5, "stueck": 4},
                                        {"nr": 4, "name": "Roh", "operationen": None}], "Testweg 1", "17999", "2026-10-30", "0.4")
        self.assertIn("Ortgang &lt;1&gt;", h)
        self.assertIn("<td>1</td><td>Abkanten</td><td>90°</td><td>25.0</td><td>1.50</td>", h)
        self.assertIn("<td>2</td><td>Umschlag</td><td>180°</td><td>6.0</td><td>0.30</td>", h)
        self.assertIn("Ohne Biegefolge", h)


class BestellungTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.m = test_material()

    def teile(self, n):
        return [{"nr": i, "name": "T%d" % i, "materialId": self.m["id"], "flaeche": 200000.0, "breite": 400.0, "laenge": 500.0, "stueck": 2} for i in range(1, n + 1)]

    def test_mehrere_dokumente_zusammenfuehren(self):
        self.assertFalse(bestellung.teile_merken("", "Dok", self.teile(1), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Dach", self.teile(2), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Wand", self.teile(1), self.tmp))
        self.assertTrue(bestellung.teile_merken("17999", "Dach", self.teile(1), self.tmp))   # ersetzt den alten Stand von «Dach»
        b = bestellung.bestellung("17999", [self.m], None, self.tmp)
        self.assertEqual(b["dokumente"], ["Dach", "Wand"])
        self.assertEqual(len(b["teile"]), 2)
        self.assertEqual(b["erg"]["materialien"][0]["teile"], 4)
        self.assertIn("Wand – Stand", b["text"])

    def test_ohne_daten(self):
        b = bestellung.bestellung("555", [self.m], None, self.tmp)
        self.assertIsNone(b["erg"])
        self.assertIn("noch keine gespeicherten Teile", b["text"])


class LabelTest(unittest.TestCase):
    def test_teil_label(self):
        self.assertEqual(auftrag.teil_label("17642", 3), "17642-03")
        self.assertEqual(auftrag.teil_label("17642", 12, False), "12")
        self.assertEqual(auftrag.teil_label("", 3), "3")
        self.assertEqual(auftrag.teil_label("17642", ""), "")

    def test_lokaler_exportpfad(self):
        a = {"lokalBasis": os.path.join("C:", "Auftraege"), "jahresordner": True}
        p = auftrag.lokaler_exportpfad(a, "17642", "Nägeligasse 1a, Bern", 2026)
        self.assertEqual(p, os.path.join("C:", "Auftraege", "2026", "17642 Nägeligasse 1a, Bern", "Export"))
        self.assertEqual(auftrag.lokaler_exportpfad(dict(a, jahresordner=False), "17642", "X", 2026), os.path.join("C:", "Auftraege", "17642 X", "Export"))
        self.assertIsNone(auftrag.lokaler_exportpfad({}, "17642", "X", 2026), "ohne Basis kein eigener Pfad")
        self.assertIsNone(auftrag.lokaler_exportpfad(a, "", "", 2026))


class KalkulationTest(unittest.TestCase):
    SAETZE = [{"name": "Spengler", "value": 110.0}, {"name": "Meister", "value": 145.0}]

    def test_stundensatz_wahl(self):
        self.assertEqual(kalkulation.stundensatz_waehlen({"stundensatzName": " spengler "}, self.SAETZE), (110.0, "App: Spengler"))
        self.assertEqual(kalkulation.stundensatz_waehlen({"stundensatzName": "Gibt es nicht", "stundensatzManuell": 99}, self.SAETZE), (99.0, "von Hand eingetragen"))
        satz, text = kalkulation.stundensatz_waehlen({"stundensatzName": "Gibt es nicht"}, [])
        self.assertIsNone(satz)
        self.assertIn("nicht in der App gefunden", text)
        self.assertIn("kein Stundensatz", kalkulation.stundensatz_waehlen({}, self.SAETZE)[1])

    def test_rechnung(self):
        m = {"thickness": 1.0, "density": 7.85, "pricePerKg": 2.0}
        teile = [{"nr": "17-01", "name": "A", "stueck": 2, "breite": 500.0, "laenge": 1000.0, "flaeche": 400000.0, "material": m, "operationen": OPS},
                 {"nr": "17-02", "name": "B", "stueck": 1, "breite": 100.0, "laenge": 100.0, "flaeche": None, "material": {"thickness": 1.0}, "operationen": None}]
        k = {"ruestMinProTeil": 6.0, "minProBiegung": 2.0, "minProMeterZuschnitt": 1.0, "zuschlagProzent": 0.0}
        erg = kalkulation.kalkuliere(teile, k, 120.0)
        a, b = erg["zeilen"]
        self.assertAlmostEqual(a["minuten_je"], 6 + 2 * 2 + 3.0 * 1.0)          # Umfang 2·(0.5+1.0) = 3 m
        self.assertAlmostEqual(a["arbeit"], 13 / 60 * 120 * 2)
        self.assertAlmostEqual(a["material"], 0.4 * 1.0 * 7.85 * 2.0 * 2)       # 0.4 m² · 1 mm · 7.85 kg/dm³ = 3.14 kg
        self.assertIsNone(b["material"], "ohne Dichte/Preis kein Materialpreis")
        self.assertAlmostEqual(erg["summe"]["gesamt"], a["summe"] + b["summe"])
        self.assertIn("Rüsten 6.0 min", erg["annahmen"])

    def test_ohne_stundensatz_nur_zeit(self):
        erg = kalkulation.kalkuliere([{"nr": 1, "name": "A", "stueck": 1, "breite": 100.0, "laenge": 100.0, "flaeche": None, "material": None, "operationen": None}], {}, None)
        self.assertIsNone(erg["summe"]["arbeit"])
        self.assertGreater(erg["summe"]["minuten"], 0)
        h = kalkulation.kalkulation_html(erg, "kein Stundensatz gewählt", "Testweg", "17999", "2026-10-31", "0.4")
        self.assertIn("kein Stundensatz gewählt", h)
        self.assertIn("Schätzwerte", h)


class MappeTest(unittest.TestCase):
    def test_deckblatt_abschnitte_und_stile(self):
        a = "<html><head><style>.a{}</style></head><body><h1>Stückliste</h1></body></html>"
        b = "<html><head><style>.a{}</style><style>.b{}</style></head><body><h1>Werkstattblatt</h1></body></html>"
        h = mappe.mappe_html([("Stückliste", a), ("Werkstattblatt 1", b)], "Testweg 1", "17999", "2026-10-31", "0.4")
        self.assertIn("Auftragsmappe", h)
        self.assertEqual(h.count('class="neueSeite"'), 2)
        self.assertIn("<li>Werkstattblatt 1</li>", h)
        self.assertIn("<h1>Stückliste</h1>", h)
        self.assertEqual(h.count("<style>.a{}</style>"), 1, "gleiche Stile nicht doppelt")

    def test_werkstattblaetter_merken_und_lesen(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        datei = os.path.join(tmp, "1_werkstattblatt.html")
        open(datei, "w").write("x")
        self.assertTrue(bestellung.blatt_merken("17999", "Dach", datei, tmp))
        bestellung.blatt_merken("17999", "Dach", datei, tmp)
        bestellung.blatt_merken("17999", "Wand", os.path.join(tmp, "gibtsnicht.html"), tmp)
        self.assertEqual(bestellung.blaetter_lesen("17999", tmp), [("Dach", datei)], "doppelt/fehlend wird ausgelassen")


class ProfilblattTest(unittest.TestCase):
    def test_profilblatt_mit_massen(self):
        from test_templates import testvorlage
        v = testvorlage()
        v["operations"] = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "umschlag", "winkel": 180, "laenge": 7, "radius": None}]
        h, grund = profilblatt.profilblatt_html(v, test_material(), None, "Testweg 1", "17999", "2026-10-31", "0.4")
        self.assertIsNone(grund)
        self.assertIn("<svg", h)
        self.assertIn("<td>1</td><td>Flansch</td><td>90°</td><td>25</td>", h)
        self.assertIn("Umschlag", h)
        self.assertIn("Auftrag: <b>17999</b>", h)
        h2, _ = profilblatt.profilblatt_html(v, None)
        self.assertIn("Skizze (ohne Materialprofil)", h2)
        v["operations"] = [{"typ": "flansch", "winkel": 90, "laenge": "zz", "radius": None}]
        self.assertIsNone(profilblatt.profilblatt_html(v, None)[0])

    def test_backend_schreibt_datei(self):
        from spengler_cad.ui.palette_backend import Backend
        from test_templates import testvorlage
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        b = Backend(tmp)
        e = b.a_init({})["einstellungen"]
        e["export"]["folder"] = os.path.join(tmp, "exp")
        b.a_einstellungen_speichern({"einstellungen": e})
        v = testvorlage()
        v["operations"] = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}]
        r = b.a_profilblatt({"vorlage": v})
        self.assertTrue(os.path.isfile(r["pfad"]) and r["pfad"].endswith(".html"))
        self.assertTrue(r["pfad"].startswith(os.path.join(tmp, "exp")))


class AbgleichTest(unittest.TestCase):
    def P(self, nr, objekt, **k):
        return dict({"id": len(str(nr)) + 1, "name": "Titel " + str(nr), "order_no": nr, "object": objekt, "archived": False, "created_at": "2025-09-27T09:41:00+00:00"}, **k)

    def O(self, nr, objekt):
        return {"nummer": nr, "objekt": objekt, "name": "%s %s" % (nr, objekt), "jahr": 2025}

    def test_vergleich(self):
        projekte = [self.P("17642", "Nägeligasse 1a, Bern"), self.P("17747", "Talstrasse 23, Kehrsatz"), self.P("18000", "Neu in der App, Bern"),
                    self.P("", "ohne Nummer"), self.P("ABC1", "Buchstaben"), self.P("19000", "Alt", archived=True), self.P("18001", "A/B: C")]
        ordner = [self.O("17642", "Nägeligasse 1a, Bern"), self.O("17747", "Talstrasse 23, Ittigen"), self.O("17999", "Nur in Fusion, Bern"), self.O("19000", "Alt")]
        e = abgleich.vergleiche(projekte, ordner)
        self.assertEqual([x["ordnername"] for x in e["nur_app"]], ["18000 Neu in der App, Bern", "18001 A-B- C"])
        self.assertEqual(e["nur_app"][0]["jahr"], 2025)
        self.assertEqual([o["nummer"] for o in e["nur_fusion"]], ["17999"], "19000 hat ein (archiviertes) Projekt → kein Doppelanlegen")
        self.assertEqual([p["order_no"] for p, _ in e["beide"]], ["17642"])
        self.assertEqual([p["order_no"] for p, _ in e["abweichend"]], ["17747"])
        self.assertEqual(sorted(g.split(" ")[0] for _, g in e["uebersprungen"]), ["Auftragsnummer", "keine"])
        self.assertEqual(e["archiviert"], 1)

    def test_projekt_aus_ordner(self):
        self.assertEqual(abgleich.projekt_aus_ordner(self.O("17999", "Weg 1, Bern")), {"order_no": "17999", "object": "Weg 1, Bern", "name": "Weg 1, Bern"})

    def test_ordnername_ohne_objekt_nimmt_den_namen(self):
        self.assertEqual(abgleich.ordnername_fuer_projekt({"order_no": "18308", "object": "", "name": "Mauerabdeckung Hirsbrunner"})[0], "18308 Mauerabdeckung Hirsbrunner")
        self.assertIsNone(abgleich.ordnername_fuer_projekt({"order_no": "18308", "object": "", "name": ""})[0])


class StatusTest(unittest.TestCase):
    def test_listentext(self):
        a = {"name": "18162 Sonneggweg 9, Bern", "nummer": "18162"}
        self.assertEqual(auftrag.listentext(a, {}), "18162 Sonneggweg 9, Bern")
        self.assertEqual(auftrag.listentext(a, {"18162": {"status": "in_arbeit"}}), "18162 Sonneggweg 9, Bern  [In Arbeit]")


class CloudStatusTest(unittest.TestCase):
    def test_projekte_lesen_und_anlegen(self):
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud, CloudFehler
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "Sonneggweg", "object": "Sonneggweg 9, Bern", "status": "in_arbeit"}]
        c = Cloud(tmp, url=url, timeout=5)
        c.anmelden("max", "pw")
        self.assertEqual([p["order_no"] for p in c.projekte_lesen()], ["18162"])
        neu = c.projekt_anlegen("17999", "Testweg 1, Bern")
        self.assertEqual((neu["order_no"], neu["object"], neu["name"]), ("17999", "Testweg 1, Bern", "Testweg 1, Bern"))
        self.assertEqual(len(c.projekte_lesen()), 2)
        with self.assertRaises(CloudFehler) as cm:
            c.projekt_anlegen("17999", "Nochmal")
        self.assertIn("gibt es in der App schon", str(cm.exception))
        self.assertEqual(len(z.projects), 2, "keine Doppelte")

    def test_status_und_app_daten_ueber_fake_supabase(self):
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud, CloudFehler
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        z.rates = [{"company_id": "firma-a", "name": "Spengler", "value": 110.0}, {"company_id": "firma-b", "name": "Fremd", "value": 1.0}]
        z.projects = [{"company_id": "firma-a", "order_no": "18162", "name": "Sonneggweg", "customer": "X", "object": "o", "status": "in_arbeit"}]
        c = Cloud(tmp, url=url, timeout=5)
        c.anmelden("max", "pw")
        c.status_setzen("18162", "in_arbeit")
        c.status_setzen("18162", "gefertigt", "fertig")
        self.assertEqual(c.status_alle()["18162"]["status"], "gefertigt")
        self.assertEqual(len(z.status), 1, "Upsert: ein Eintrag je Auftrag")
        with self.assertRaises(CloudFehler):
            c.status_setzen("18162", "unbekannt")
        self.assertEqual([r["name"] for r in c.stundensaetze()], ["Spengler"])
        self.assertEqual(c.projekt_zu_auftrag("18162")["status"], "in_arbeit")
        self.assertIsNone(c.projekt_zu_auftrag("99999"))


class SelbsttestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_einmal_je_version_und_meldung(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.diagnostics import auto_selbsttest, fusion_capabilities
        gesendet = []
        cloud = type("C", (), {"angemeldet": True, "test_speichern": lambda s, z: gesendet.append(z)})()
        alt = fusion_capabilities.pruefen
        fusion_capabilities.pruefen = lambda app: {"flansch": (True, "Flansch"), "saum": (False, "Saum")}
        self.addCleanup(setattr, fusion_capabilities, "pruefen", alt)
        app = type("A", (), {"activeProduct": type("D", (), {"rootComponent": object()})()})()
        self.assertTrue(auto_selbsttest.noetig(self.tmp))
        ok, text = auto_selbsttest.ausfuehren(app, cloud, self.tmp, "2706")
        self.assertFalse(ok)
        self.assertIn("Saum", gesendet[0]["notiz"])
        self.assertEqual((gesendet[0]["test_id"], gesendet[0]["status"]), (auto_selbsttest.TEST_ID, "fehler"))
        self.assertFalse(auto_selbsttest.noetig(self.tmp), "danach nicht nochmal in dieser Version")

    def test_ohne_design_spaeter(self):
        from spengler_cad.diagnostics import auto_selbsttest
        app = type("A", (), {"activeProduct": None})()
        self.assertIsNone(auto_selbsttest.ausfuehren(app, None, self.tmp))
        self.assertTrue(auto_selbsttest.noetig(self.tmp))


if __name__ == "__main__":
    unittest.main()


class NeuerAuftragAppProjektTest(unittest.TestCase):
    """Regression (Live 3.11., Bericht 98.487): _projekt_in_app war nicht definiert – «Neuer Auftrag» brach nach dem Anlegen der Ordner ab."""

    def test_projekt_in_app_anlegen_und_melden(self):
        import fake_supabase
        from spengler_cad.commands import auftrag_command
        from spengler_cad.storage.cloud_client import Cloud
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        c = Cloud(tmp, url=url, timeout=5)
        self.assertIn("nicht angemeldet", auftrag_command._projekt_in_app("17999", "Testweg 1, Bern", c))
        c.anmelden("max", "pw")
        self.assertIn("17999", auftrag_command._projekt_in_app("17999", "Testweg 1, Bern", c))
        self.assertIn("angelegt", auftrag_command._projekt_in_app("18000", "Zweiter Weg", c))
        self.assertEqual(len(z.projects), 2)
        self.assertIn("gibt es schon", auftrag_command._projekt_in_app("17999", "Nochmal", c))
        self.assertEqual(len(z.projects), 2, "keine Doppelten")

    def test_fehler_wird_gemeldet_nicht_geworfen(self):
        from spengler_cad.commands import auftrag_command

        class Kaputt(object):
            angemeldet = True

            def projekt_zu_auftrag(self, n):
                raise RuntimeError("Netz weg")
        self.assertIn("NICHT angelegt", auftrag_command._projekt_in_app("1", "x", Kaputt()))


class ProfilAuftraegeTest(unittest.TestCase):
    """«An CAD senden» in der App → offene Aufträge im Add-in → «gebaut»."""

    def _cloud(self):
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "Sonneggweg", "object": "Sonneggweg 9, Bern", "status": "in_arbeit"}]
        z.profil_auftraege = [
            {"company_id": "firma-a", "id": 1, "project_id": 7, "titel": "Ortgang Nord", "laenge_mm": 3200, "stueck": 4, "staerke_mm": 0.7, "status": "offen",
             "daten": {"schenkel": [{"laenge": 168, "winkel": 0}, {"laenge": 25, "winkel": 90}]}, "created_at": "2026-11-03T10:00:00Z"},
            {"company_id": "firma-a", "id": 2, "project_id": 7, "titel": "Schon gebaut", "laenge_mm": 100, "stueck": 1, "status": "gebaut", "daten": {}, "created_at": "2026-11-02T10:00:00Z"},
            {"company_id": "firma-b", "id": 3, "project_id": 7, "titel": "Fremde Firma", "laenge_mm": 1, "stueck": 1, "status": "offen", "daten": {}, "created_at": "2026-11-03T11:00:00Z"}]
        c = Cloud(tmp, url=url, timeout=5)
        c.anmelden("max", "pw")
        return c, z

    def test_nur_offene_der_eigenen_firma(self):
        c, z = self._cloud()
        liste = c.profil_auftraege("18162")
        self.assertEqual([a["id"] for a in liste], [1])
        self.assertEqual(c.profil_auftraege("99999"), [])

    def test_als_gebaut_markieren(self):
        c, z = self._cloud()
        from spengler_cad.commands import grundblech_command
        self.assertIn("vermerkt", grundblech_command.markieren_gebaut(1, c))
        self.assertEqual(z.profil_auftraege[0]["status"], "gebaut")
        self.assertTrue(z.profil_auftraege[0]["gebaut_am"])
        self.assertEqual(c.profil_auftraege("18162"), [], "danach nicht mehr offen")

    def test_markieren_scheitert_ohne_ausnahme(self):
        from spengler_cad.commands import grundblech_command

        class Kaputt(object):
            def profil_auftrag_gebaut(self, i):
                raise RuntimeError("Netz weg")
        self.assertIn("nicht als «gebaut»", grundblech_command.markieren_gebaut(1, Kaputt()))

    def test_auswahlliste(self):
        from spengler_cad.commands import grundblech_command as g
        e = g.eintraege([{"id": 1, "titel": "Ortgang Nord", "laenge_mm": 3200, "stueck": 4, "daten": {"schenkel": []}}],
                        [{"id": 41, "title": "Kehle", "type": "freies_profil", "data": {"schenkel": []}}])
        self.assertEqual([x["art"] for x in e], ["gesendet", "massaufnahme"])
        self.assertEqual((e[0]["laenge"], e[0]["stueck"]), (3200.0, 4))
        self.assertIn("3200 mm × 4 Stück", e[0]["text"])
        self.assertIsNone(e[1]["laenge"])
        self.assertEqual(g.eintraege(None, None), [])


class ProjektkarteCloudTest(unittest.TestCase):
    def _cloud(self):
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "Sonneggweg", "object": "Sonneggweg 9, Bern", "customer": "Muster AG", "status": "in_arbeit", "archived": False,
                       "hinweis": "Schlüssel beim Hauswart", "zugeteilt_an": ["u1"], "created_at": "2026-10-01T10:00:00Z"},
                      {"company_id": "firma-a", "id": 8, "order_no": "18200", "name": "Anderes", "object": "x", "status": "offen", "archived": False}]
        z.measurements = [{"company_id": "firma-a", "id": 41, "project_id": 7, "type": "freies_profil", "title": "Stirn", "workflow_status": "geruestet", "photo_paths": ["measurements/7/41/photo/a.jpg"]},
                          {"company_id": "firma-a", "id": 99, "project_id": 8, "type": "kehle", "title": "fremd"}]
        z.tab = {"reports": [{"company_id": "firma-a", "project_id": 7, "id": 1, "date": "2026-10-19", "work_entries": [{"hours": 2.5, "employee": "Mike"}], "material_entries": []}],
                 "termine": [{"company_id": "firma-a", "project_id": 7, "titel": "Montage", "start_datum": "2026-11-10"}],
                 "offerten": [], "leistungen": [], "profiles": [{"id": "u1", "first_name": "Mike", "last_name": "Ledermann"}]}
        z.projektdateien = [{"project_id": 7, "id": 3, "name": "Plan.pdf", "file_path": "project-files/7/x.pdf", "size_bytes": 2048}]
        z.teile = [{"company_id": "firma-a", "project_id": 7, "auftrag": "18162", "dokument": "d", "teil_nr": 1, "teil_label": "18162-01", "name": "Ortgang", "measurement_id": 41}]
        z.speicher["measurements/7/41/photo/a.jpg"] = b"\xff\xd8JPEG"
        c = Cloud(tmp, url=url, timeout=5)
        c.anmelden("max", "pw")
        return c, z

    def test_roh_nur_dieses_projekt(self):
        c, z = self._cloud()
        roh, hinweise = c.projekt_roh("18162")
        self.assertEqual(hinweise, [])
        self.assertEqual(roh["projekt"]["customer"], "Muster AG")
        self.assertEqual([m["id"] for m in roh["massaufnahmen"]], [41])
        self.assertEqual(roh["rapporte"][0]["id"], 1)
        self.assertEqual(roh["dateien"][0]["name"], "Plan.pdf")
        self.assertEqual(roh["teile"][0]["teil_label"], "18162-01")
        self.assertEqual(roh["personen"][0]["first_name"], "Mike")
        self.assertEqual(c.projekt_roh("99999"), (None, []))

    def test_foto_laden(self):
        c, z = self._cloud()
        self.assertEqual(c.foto_laden("measurements/7/41/photo/a.jpg"), b"\xff\xd8JPEG")
        from spengler_cad.storage.cloud_client import CloudFehler
        with self.assertRaises(CloudFehler):
            c.foto_laden("measurements/7/41/photo/gibtsnicht.jpg")

    def test_karte_aus_roh(self):
        from spengler_cad.core import projektkarte
        c, z = self._cloud()
        roh, _ = c.projekt_roh("18162")
        k = projektkarte.karte(roh, projektkarte.namen(roh["personen"]), "2026-11-04")
        self.assertEqual(k["kopf"]["zugeteilt"], ["Mike Ledermann"])
        self.assertEqual(k["massaufnahmen"][0]["status"], "Gerüstet")
        self.assertEqual(k["massaufnahmen"][0]["fotos"], 1)
        self.assertEqual(k["cad"]["teile"][0]["werkstatt"], "Gerüstet")
        self.assertEqual(k["naechster_termin"]["titel"], "Montage")


class AppAenderungenTest(unittest.TestCase):
    def _cloud(self, rolle="admin"):
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", rolle, "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "S", "object": "O", "status": "offen", "archived": False, "hinweis": None, "updated_at": "2026-11-01T10:00:00+00:00"}]
        c = Cloud(tmp, url=url, timeout=5)
        c.anmelden("max", "pw")
        return c, z

    def test_status_nur_wenn_unveraendert(self):
        from spengler_cad.storage.cloud_client import CloudFehler
        c, z = self._cloud()
        self.assertEqual(c.projekt_status_setzen(7, "in_arbeit", "offen")["status"], "in_arbeit")
        with self.assertRaises(CloudFehler) as cm:                       # inzwischen geändert (alt stimmt nicht mehr)
            c.projekt_status_setzen(7, "abgeschlossen", "offen")
        self.assertIn("inzwischen anderswo geändert", str(cm.exception))
        self.assertEqual(z.projects[0]["status"], "in_arbeit")

    def test_ohne_recht_wird_gemeldet_nicht_still_ignoriert(self):
        from spengler_cad.storage.cloud_client import CloudFehler
        c, z = self._cloud("employee")
        with self.assertRaises(CloudFehler) as cm:
            c.projekt_status_setzen(7, "in_arbeit", "offen")
        self.assertIn("Recht", str(cm.exception))
        self.assertEqual(z.projects[0]["status"], "offen")
        with self.assertRaises(CloudFehler):
            c.termin_anlegen({"titel": "x", "project_id": 7, "start_datum": "2026-11-10", "ende_datum": "2026-11-10"})

    def test_hinweis_mit_und_ohne_veraltete_karte(self):
        from spengler_cad.storage.cloud_client import CloudFehler
        c, z = self._cloud()
        r = c.projekt_hinweis_setzen(7, "Schlüssel beim Hauswart", "2026-11-01T10:00:00+00:00")
        self.assertEqual(r["hinweis"], "Schlüssel beim Hauswart")
        with self.assertRaises(CloudFehler):                              # Karte war veraltet (updated_at hat sich geändert)
            c.projekt_hinweis_setzen(7, "anders", "2026-11-01T10:00:00+00:00")
        self.assertEqual(c.projekt_hinweis_setzen(7, None)["hinweis"], None)      # löschen = null

    def test_termin_anlegen_und_aendern(self):
        from spengler_cad.core import projektaenderung as pa
        c, z = self._cloud()
        t = c.termin_anlegen(pa.termin_pruefen({"titel": "Montage", "start_datum": "10.11.2026", "start_zeit": "7:30"}, 7))
        self.assertEqual((t["titel"], t["start_datum"], t["start_zeit"], t["quelle"]), ("Montage", "2026-11-10", "07:30", "app"))
        g = c.termin_aendern(t["id"], pa.termin_pruefen({"titel": "Montage Dach", "start_datum": "11.11.2026"}, 7))
        self.assertEqual((g["titel"], g["start_datum"], g["projekt_pruefen"]), ("Montage Dach", "2026-11-11", False))

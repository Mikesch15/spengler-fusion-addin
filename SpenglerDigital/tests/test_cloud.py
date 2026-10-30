"""Anmeldung, Abgleich (zwei PCs, Konflikt, Löschen, Rechte, offline) und Updater – gegen den Supabase-Nachbau."""
import base64
import os
import shutil
import tempfile
import unittest

from _basis import ADDIN, datei_inhalt, test_material
import fake_supabase
from spengler_cad.storage import cloud_client, json_store, sync_service, updater
from spengler_cad.storage.cloud_client import Cloud, CloudFehler
from spengler_cad.storage.material_library import MaterialBibliothek
from spengler_cad.storage.template_repository import VorlagenRepository
from test_templates import testvorlage


class CloudBasis(unittest.TestCase):
    def setUp(self):
        self.z = fake_supabase.Zustand()
        self.srv, self.url = fake_supabase.server(self.z)
        self.z.benutzer_anlegen("chef@nfgryuzkpwjfmdlmevuy.supabase.co", "geheim", "admin", "firma-a", "Chef")
        self.z.benutzer_anlegen("max.muster@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a", "Max")
        self.z.benutzer_anlegen("fremd@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "admin", "firma-b", "Fremd")
        self.ordner = [tempfile.mkdtemp(prefix="pc_") for _ in range(3)]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        for o in self.ordner:
            shutil.rmtree(o, ignore_errors=True)

    def pc(self, i, benutzer="chef", pw="geheim"):
        c = Cloud(self.ordner[i], url=self.url, timeout=5)
        c.anmelden(benutzer, pw)
        return c, sync_service.Abgleich(c, self.ordner[i])


class AnmeldungTest(CloudBasis):
    def test_anmelden_wie_app(self):
        self.assertEqual(cloud_client.benutzer_zu_email(" Max.Muster "), "max.muster@nfgryuzkpwjfmdlmevuy.supabase.co")
        self.assertEqual(cloud_client.benutzer_zu_email("A@B.ch"), "a@b.ch")
        c = Cloud(self.ordner[0], url=self.url)
        k = c.anmelden("Chef", "geheim")
        self.assertEqual((k["rolle"], k["darf_aendern"], k["company_id"]), ("admin", True, "firma-a"))
        roh = json_store.lesen(os.path.join(self.ordner[0], "konto.json"))
        self.assertNotIn("geheim", str(roh), "Passwort wird nie gespeichert")
        self.assertTrue(Cloud(self.ordner[0], url=self.url).angemeldet, "Sitzung bleibt nach Neustart")
        c.abmelden()
        self.assertFalse(os.path.exists(os.path.join(self.ordner[0], "konto.json")))

    def test_falsches_passwort_und_echte_email(self):
        with self.assertRaises(CloudFehler) as cm:
            Cloud(self.ordner[0], url=self.url).anmelden("chef", "falsch")
        self.assertIn("falsch", str(cm.exception))
        self.z.benutzer["max.muster@nfgryuzkpwjfmdlmevuy.supabase.co"]["echte_email"] = "max@betrieb.ch"
        k = Cloud(self.ordner[0], url=self.url).anmelden("max@betrieb.ch", "pw")
        self.assertEqual((k["rolle"], k["darf_aendern"]), ("employee", False))

    def test_token_erneuern_und_abgelaufen(self):
        c = Cloud(self.ordner[0], url=self.url)
        c.anmelden("chef", "geheim")
        c._konto["ablauf"] = 0
        self.assertEqual(c.liste(), [])           # erneuert automatisch
        c._konto["ablauf"] = 0
        c._konto["refresh_token"] = "ungueltig"
        with self.assertRaises(CloudFehler) as cm:
            c.liste()
        self.assertIn("neu anmelden", str(cm.exception))

    def test_offline(self):
        c = Cloud(self.ordner[0], url="http://127.0.0.1:9", timeout=2)
        with self.assertRaises(CloudFehler) as cm:
            c.anmelden("chef", "geheim")
        self.assertTrue(cm.exception.offline)


class AbgleichTest(CloudBasis):
    def test_zwei_pcs(self):
        c1, a1 = self.pc(0)
        c2, a2 = self.pc(1)
        v = VorlagenRepository(self.ordner[0]).speichern(testvorlage("Ortblech"))
        m = MaterialBibliothek(self.ordner[0]).speichern(test_material())
        b = a1.ausfuehren()
        self.assertEqual(sorted(b["hochgeladen"]), ["Ortblech", "TEST Blech 0.7"])
        b = a2.ausfuehren()
        self.assertEqual(sorted(b["geladen"]), ["Ortblech", "TEST Blech 0.7"])
        v2 = VorlagenRepository(self.ordner[1]).holen(v["id"])
        self.assertEqual(v2["operations"], v["operations"])
        self.assertEqual(MaterialBibliothek(self.ordner[1]).holen(m["id"])["kFactor"], 0.4)
        # PC 2 ändert → PC 1 bekommt es
        v2["description"] = "geändert auf PC 2"
        VorlagenRepository(self.ordner[1]).speichern(v2)
        self.assertEqual(a2.ausfuehren()["hochgeladen"], ["Ortblech"])
        self.assertEqual(a1.ausfuehren()["geladen"], ["Ortblech"])
        self.assertEqual(VorlagenRepository(self.ordner[0]).holen(v["id"])["description"], "geändert auf PC 2")
        self.assertEqual(len(self.z.versionen), 1, "Cloud legt die alte Fassung ab")
        # nichts geändert → nichts zu tun
        self.assertEqual(sync_service.bericht_text(a1.ausfuehren()), "Alles abgeglichen – keine Änderungen.")

    def test_konflikt_verliert_nichts(self):
        c1, a1 = self.pc(0)
        c2, a2 = self.pc(1)
        v = VorlagenRepository(self.ordner[0]).speichern(testvorlage("Traufblech"))
        a1.ausfuehren()
        a2.ausfuehren()
        for i, text in ((0, "Fassung PC 1"), (1, "Fassung PC 2")):
            r = VorlagenRepository(self.ordner[i])
            x = r.holen(v["id"])
            x["description"] = text
            r.speichern(x)
        a1.ausfuehren()
        b = a2.ausfuehren()
        self.assertEqual(len(b["konflikte"]), 1)
        namen = {x["name"]: x["description"] for x in VorlagenRepository(self.ordner[1]).liste()}
        self.assertEqual(namen["Traufblech"], "Fassung PC 1", "Cloud-Fassung gilt")
        kopie = [n for n in namen if n.startswith("Traufblech (Konflikt")]
        self.assertEqual(namen[kopie[0]], "Fassung PC 2", "lokale Änderung bleibt als Kopie")
        a1.ausfuehren()
        self.assertEqual(len(VorlagenRepository(self.ordner[0]).liste()), 2, "Kopie kommt auch auf PC 1")

    def test_loeschen_ueber_papierkorb(self):
        c1, a1 = self.pc(0)
        c2, a2 = self.pc(1)
        v = VorlagenRepository(self.ordner[0]).speichern(testvorlage("Weg"))
        a1.ausfuehren()
        a2.ausfuehren()
        VorlagenRepository(self.ordner[1]).loeschen(v["id"], bestaetigt=True)
        self.assertEqual(a2.ausfuehren()["geloescht"], ["Weg"])
        self.assertTrue(self.z.cad[0]["geloescht"], "in der Cloud nur markiert, nicht gelöscht")
        self.assertEqual(a1.ausfuehren()["geloescht"], ["Weg"])
        self.assertEqual(VorlagenRepository(self.ordner[0]).liste(), [])
        self.assertEqual(len(VorlagenRepository(self.ordner[0]).papierkorb()), 1, "auf PC 1 im Papierkorb")

    def test_mitarbeiter_nur_lesen(self):
        c1, a1 = self.pc(0)
        VorlagenRepository(self.ordner[0]).speichern(testvorlage("Vom Chef"))
        a1.ausfuehren()
        c2, a2 = self.pc(1, "max.muster", "pw")
        self.assertEqual(a2.ausfuehren()["geladen"], ["Vom Chef"])
        VorlagenRepository(self.ordner[1]).speichern(testvorlage("Eigene von Max"))
        b = a2.ausfuehren()
        self.assertEqual(b["nur_lokal"], ["Eigene von Max"])
        self.assertFalse(b["darf_aendern"])
        self.assertEqual(len(self.z.cad), 1, "nichts hochgeladen")

    def test_mitarbeiter_konflikt_verliert_nichts(self):
        """Fehler bis 0.4.0: bei Konflikt wurde die lokale Änderung eines Mitarbeiters überschrieben."""
        c1, a1 = self.pc(0)
        v = VorlagenRepository(self.ordner[0]).speichern(testvorlage("Gemeinsam"))
        a1.ausfuehren()
        c2, a2 = self.pc(1, "max.muster", "pw")
        a2.ausfuehren()
        for i, text in ((0, "Chef ändert"), (1, "Max ändert")):
            r = VorlagenRepository(self.ordner[i])
            x = r.holen(v["id"])
            x["description"] = text
            r.speichern(x)
        a1.ausfuehren()
        b = a2.ausfuehren()
        beschr = sorted(x["description"] for x in VorlagenRepository(self.ordner[1]).liste())
        self.assertEqual(beschr, ["Chef ändert", "Max ändert"], "eigene Fassung bleibt als lokale Kopie")
        self.assertTrue(any("nur lokal" in k for k in b["konflikte"]))
        self.assertEqual(len(self.z.cad), 1, "Mitarbeiter lädt nichts hoch")

    def test_neuere_fassung_in_der_app_wird_nie_ueberschrieben(self):
        """Schutz (kein nachgewiesener Fehler): Datensätze aus einer neueren Add-in-Version werden nie überschrieben."""
        c1, a1 = self.pc(0)
        v = VorlagenRepository(self.ordner[0]).speichern(testvorlage("Zukunft"))
        a1.ausfuehren()
        zeile = self.z.cad[0]
        zeile.update({"schema_version": 99, "version": 2, "daten": dict(zeile["daten"], schemaVersion=99, zukunft={"neu": 1})})
        r = VorlagenRepository(self.ordner[0])
        x = r.holen(v["id"])
        x["description"] = "lokal geändert"
        r.speichern(x)
        b = a1.ausfuehren()
        self.assertEqual(self.z.cad[0]["daten"]["zukunft"], {"neu": 1}, "App-Fassung unverändert")
        self.assertEqual(self.z.versionen, [], "kein Überschreiben")
        self.assertEqual(b["neuer"], ["Zukunft"])
        lokal = VorlagenRepository(self.ordner[0]).liste()
        self.assertTrue(any(y.get("_nurLesen") for y in lokal), "neue Fassung lokal schreibgeschützt")
        self.assertTrue(any(y.get("description") == "lokal geändert" for y in lokal), "eigene Änderung als Kopie")

    def test_wiederherstellen_ueberschreibt_app_nicht(self):
        """Fehler bis 0.4.0: nach dem Wiederherstellen einer alten Sicherung hätte der Abgleich die App überschrieben."""
        from spengler_cad.storage import backup_service
        c1, a1 = self.pc(0)
        r = VorlagenRepository(self.ordner[0])
        v = r.speichern(testvorlage("Stand"))
        a1.ausfuehren()
        sicherung = backup_service.sichern(self.ordner[0], grund="manuell")
        x = r.holen(v["id"])
        x["description"] = "neu"
        r.speichern(x)
        a1.ausfuehren()
        backup_service.wiederherstellen(sicherung, self.ordner[0], bestaetigt=True)
        b = a1.ausfuehren()
        self.assertEqual(next(z for z in self.z.cad if z["record_id"] == v["id"])["daten"]["description"], "neu", "App behält die neuere Fassung")
        self.assertEqual(len(b["konflikte"]), 1, "alte Fassung bleibt als Konflikt-Kopie")

    def test_firmen_getrennt(self):
        c1, a1 = self.pc(0)
        VorlagenRepository(self.ordner[0]).speichern(testvorlage("Geheim A"))
        a1.ausfuehren()
        c3, a3 = self.pc(2, "fremd", "pw")
        self.assertEqual(a3.ausfuehren()["geladen"], [])
        self.assertEqual(VorlagenRepository(self.ordner[2]).liste(), [])

    def test_detailgeometrie(self):
        from test_validation import gueltige_detailvorlage
        c1, a1 = self.pc(0)
        r1 = VorlagenRepository(self.ordner[0])
        quelle = os.path.join(self.ordner[0], "q.f3d")
        with open(quelle, "wb") as f:
            f.write(b"F3D\x00inhalt")
        v = gueltige_detailvorlage()
        v["source"]["file"] = r1.geometrie_ablegen(quelle, v["id"], 1)
        r1.speichern(v)
        a1.ausfuehren()
        self.assertIn("firma-a/details/%s_v1.f3d" % v["id"], self.z.dateien)
        c2, a2 = self.pc(1)
        a2.ausfuehren()
        r2 = VorlagenRepository(self.ordner[1])
        with open(r2.geometrie_pfad(r2.holen(v["id"], "detailvorlage")["source"]["file"]), "rb") as f:
            self.assertEqual(f.read(), b"F3D\x00inhalt")

    def test_offline_lokal_bleibt(self):
        c1, a1 = self.pc(0)
        VorlagenRepository(self.ordner[0]).speichern(testvorlage("Offline"))
        self.z.offline = True
        with self.assertRaises(CloudFehler) as cm:
            a1.ausfuehren()
        self.assertTrue(cm.exception.offline)
        self.assertEqual(len(VorlagenRepository(self.ordner[0]).liste()), 1)
        self.z.offline = False
        self.assertEqual(a1.ausfuehren()["hochgeladen"], ["Offline"])


class UpdaterTest(CloudBasis):
    def setUp(self):
        CloudBasis.setUp(self)
        self.addin = os.path.join(self.ordner[2], "SpenglerDigital")
        shutil.copytree(ADDIN, self.addin, ignore=shutil.ignore_patterns("__pycache__", "tests", "*.pdf", "Metallisches*"))
        self.daten = self.ordner[0]

    def release(self, aenderungen, version="9.0.0", blobs=True):
        """Release = aktueller Stand + geänderte Dateien {pfad: bytes}."""
        m = updater.manifest(self.addin, version)
        for f in m["dateien"]:
            if f["pfad"] in aenderungen:
                d = aenderungen[f["pfad"]]
                f["sha256"], f["groesse"] = updater.sha256(d), len(d)
                if blobs:
                    self.z.blobs[f["sha256"]] = {"kodierung": "base64", "inhalt": base64.b64encode(d).decode()}
        self.z.releases.append({"version": version, "dateien": m["dateien"], "hinweise": "Test"})
        return m

    def test_update_installieren(self):
        c, _ = self.pc(0)
        self.assertIsNone(updater.neuestes(c, "9.0.0"))
        neu = b'"""geaendert"""\nVERSION = "9.0.0"\nNAME = "x"\n'
        self.release({"spengler_cad/__init__.py": neu})
        r = updater.neuestes(c, "0.4.0")
        self.assertEqual(r["version"], "9.0.0")
        self.assertEqual([x[0] for x in updater.benoetigt(r, self.addin)], ["spengler_cad/__init__.py"], "nur geänderte Dateien")
        ersetzt = updater.installieren(c, r, self.addin, self.daten)
        self.assertEqual(ersetzt, ["spengler_cad/__init__.py"])
        with open(os.path.join(self.addin, "spengler_cad", "__init__.py"), "rb") as f:
            self.assertEqual(f.read(), neu)
        self.assertTrue(os.path.exists(os.path.join(self.daten, "programm_sicherung")), "alter Programmstand gesichert")
        self.assertTrue(any("vor_update" in n for n in os.listdir(os.path.join(self.daten, "sicherungen"))), "Daten gesichert")
        self.assertEqual(updater.benoetigt(r, self.addin), [], "danach nichts mehr nötig (kein zweites Installieren)")
        self.assertEqual(updater.installieren(c, r, self.addin, self.daten), [])

    def test_manipuliert_oder_unvollstaendig(self):
        c, _ = self.pc(0)
        vorher = datei_inhalt(os.path.join(self.addin, "SpenglerDigital.py"), True)
        self.release({"SpenglerDigital.py": b"neu"}, "9.0.0", blobs=False)
        with self.assertRaises(updater.UpdateFehler):
            updater.installieren(c, updater.neuestes(c, "0.4.0"), self.addin, self.daten)
        m = self.release({"SpenglerDigital.py": b"neu2"}, "9.0.1")
        sha = next(f["sha256"] for f in m["dateien"] if f["pfad"] == "SpenglerDigital.py")
        self.z.blobs[sha]["inhalt"] = base64.b64encode(b"boese").decode()
        with self.assertRaises(updater.UpdateFehler):
            updater.installieren(c, updater.neuestes(c, "0.4.0"), self.addin, self.daten)
        self.assertEqual(datei_inhalt(os.path.join(self.addin, "SpenglerDigital.py"), True), vorher, "nichts verändert")

    def test_pfade_ausserhalb_abgelehnt(self):
        for p in ("../x.py", "/etc/passwd", "C:/x", "tests/a.py", "spengler_cad/../../x", "beliebig.txt"):
            with self.assertRaises(updater.UpdateFehler, msg=p):
                updater._sicherer_pfad(p, self.addin)

    def test_manifest_ohne_tests_und_daten(self):
        m = updater.manifest(ADDIN, "0.4.0")
        pfade = [f["pfad"] for f in m["dateien"]]
        self.assertIn("spengler_cad/__init__.py", pfade)
        self.assertIn("palette/vorlagen.js", pfade)
        self.assertFalse([p for p in pfade if p.startswith(("tests/", "supabase/")) or p.endswith(".pdf")])


class TestergebnisseTest(CloudBasis):
    """Register «Tests»: Ergebnisse lokal speichern und – angemeldet – in die Cloud übermitteln (Nachbau, nicht die echte Datenbank)."""
    def backend(self, i=0, anmelden=True, benutzer="chef", pw="geheim"):
        from spengler_cad.ui.palette_backend import Backend
        os.environ["SPENGLER_CAD_CLOUD_URL"] = self.url
        self.addCleanup(os.environ.pop, "SPENGLER_CAD_CLOUD_URL", None)
        if anmelden:
            Cloud(self.ordner[i], url=self.url, timeout=5).anmelden(benutzer, pw)
        return Backend(self.ordner[i], timeout=5)

    def test_plan_stimmt_mit_anleitung_ueberein(self):
        import json
        import sys
        sys.path.insert(0, os.path.join(ADDIN, "..", "werkzeug"))
        import testplan_json
        datei = json.load(open(os.path.join(ADDIN, "palette", "testplan.json"), encoding="utf-8"))["bloecke"]
        self.assertEqual(datei, testplan_json.lesen(), "palette/testplan.json veraltet – python3 werkzeug/testplan_json.py ausführen")
        ids = [p["id"] for b in datei for p in b["punkte"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_lokal_ohne_anmeldung(self):
        b = self.backend(anmelden=False)
        r = b.a_test_speichern({"test_id": "1.2", "text": "Start", "status": "ok", "notiz": "ging"})
        self.assertFalse(r["gesendet"])
        self.assertIn("anmelden", r["hinweis"])
        self.assertEqual(b.a_testplan({})["ergebnisse"]["1.2"]["status"], "ok")
        self.assertEqual(self.z.tests, [])
        for schlecht in ({"test_id": "x", "status": "ok"}, {"test_id": "1.2", "status": "vielleicht"}):
            with self.assertRaises(ValueError):
                b.a_test_speichern(schlecht)

    def test_angemeldet_wird_uebermittelt_und_ueberschrieben(self):
        b = self.backend()
        r = b.a_test_speichern({"test_id": "6.9", "text": "Integration", "status": "fehler", "notiz": "Meldung XY"})
        self.assertTrue(r["gesendet"])
        zeile = self.z.tests[0]
        self.assertEqual((zeile["test_id"], zeile["status"], zeile["notiz"], zeile["company_id"]), ("6.9", "fehler", "Meldung XY", "firma-a"))
        self.assertIn("protokoll", zeile)
        self.assertTrue(zeile["addin_version"])
        b.a_test_speichern({"test_id": "6.9", "text": "Integration", "status": "ok", "notiz": ""})
        self.assertEqual(len(self.z.tests), 1)
        self.assertEqual(self.z.tests[0]["status"], "ok")

    def test_mitarbeiter_darf_melden_fremde_firma_nicht_sichtbar(self):
        self.backend(1, benutzer="max.muster", pw="pw").a_test_speichern({"test_id": "2.1", "text": "t", "status": "ok"})
        self.backend(2, benutzer="fremd", pw="pw").a_test_speichern({"test_id": "2.1", "text": "t", "status": "fehler"})
        self.assertEqual(sorted((r["company_id"], r["status"]) for r in self.z.tests), [("firma-a", "ok"), ("firma-b", "fehler")])

    def test_offline_geht_nichts_verloren(self):
        b = self.backend()
        self.z.offline = True
        r = b.a_test_speichern({"test_id": "3.1", "text": "t", "status": "ok"})
        self.assertFalse(r["gesendet"])
        self.assertEqual(self.z.tests, [])
        self.assertEqual(b.a_testplan({})["ergebnisse"]["3.1"]["gesendet"], False)
        self.z.offline = False
        s = b.a_tests_senden({})
        self.assertEqual((s["gesendet"], s["offen"]), (1, 0))
        self.assertEqual(self.z.tests[0]["test_id"], "3.1")


if __name__ == "__main__":
    unittest.main()

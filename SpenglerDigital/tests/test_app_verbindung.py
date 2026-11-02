"""CAD ↔ App: Teile an die App (cad_teile), Massaufnahmen aus der App lesen, Umrechnung Schenkel/Operationen (Nachbau der Datenbank, nicht die echte)."""
import shutil
import tempfile
import unittest

from _basis import DatenTest, test_material  # noqa: F401
import fake_supabase
from spengler_cad.core import app_profil
from spengler_cad.storage.cloud_client import Cloud, CloudFehler

OPS = [{"typ": "flansch", "winkel": 90, "laenge": 25, "radius": None}, {"typ": "umschlag", "winkel": -180, "laenge": 7, "radius": None}]


class UmrechnungTest(unittest.TestCase):
    def test_cad_nach_app(self):
        art, data, hinweise = app_profil.app_daten({"breite": 200.0, "laenge": 3000.0}, OPS, "Alu 0.7")
        self.assertEqual(art, "freies_profil")
        self.assertEqual(hinweise, [])
        self.assertEqual(data["schenkel"], [{"laenge": 168.0, "winkel": 0}, {"laenge": 25.0, "winkel": 90.0}, {"laenge": 7.0, "winkel": 180.0}])
        seg = data["segmente"][0]
        self.assertEqual(seg["laenge"], 3000.0)
        self.assertAlmostEqual(sum(m["mass"] for m in seg["massen"]), 200.0, msg="Summe der Masse = Abwicklungsbreite des CAD")
        self.assertEqual(seg["massen"][1], {"mass": 25.0, "links": 25.0, "rechts": 0})

    def test_schenkel_laenger_als_breite(self):
        _, data, hinweise = app_profil.app_daten({"breite": 20.0, "laenge": 500.0}, OPS, "")
        self.assertEqual(data["schenkel"][0]["laenge"], 0.0)
        self.assertIn("länger als die Abwicklungsbreite", hinweise[0])

    def test_app_nach_cad(self):
        schenkel = [{"laenge": 12, "winkel": 270}, {"laenge": 295, "winkel": 180}, {"laenge": 28, "winkel": 100}, {"laenge": 20, "winkel": 80}, {"laenge": 8, "winkel": -25}, {"laenge": 5, "winkel": 0}]
        ops, hinweise = app_profil.operationen_aus_app(schenkel)
        self.assertEqual([(o["typ"], o["winkel"], o["laenge"]) for o in ops],
                         [("umschlag", 180.0, 295.0), ("flansch", 100.0, 28.0), ("flansch", 80.0, 20.0), ("flansch", -25.0, 8.0)])
        self.assertTrue(any("gerade weiter" in h for h in hinweise))
        self.assertTrue(any("bestehende Blech" in h for h in hinweise))
        self.assertEqual(app_profil.operationen_aus_app([{"laenge": 10, "winkel": 270 + 90}])[0], [], "nur der erste Schenkel → keine Biegung")
        self.assertEqual(app_profil.operationen_aus_app([{"laenge": 10, "winkel": 0}, {"laenge": 5, "winkel": 270}])[0][0]["winkel"], -90.0, "270° = −90°")


class AppDatenbankTest(unittest.TestCase):
    def setUp(self):
        self.z = fake_supabase.Zustand()
        self.srv, self.url = fake_supabase.server(self.z)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        self.z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "Sonneggweg", "customer": "X", "object": "o", "status": "in_arbeit"}]
        self.z.measurements = [{"company_id": "firma-a", "project_id": 7, "id": 127, "type": "freies_profil", "title": "Muster", "staerke_mm": 0.6, "workflow_status": "abgeschlossen",
                                "data": {"schenkel": [{"laenge": 12, "winkel": 270}, {"laenge": 28, "winkel": 100}]}},
                               {"company_id": "firma-a", "project_id": 99, "id": 5, "type": "freies_profil", "title": "Fremdes Projekt", "data": {}}]
        self.c = Cloud(self.tmp, url=self.url, timeout=5)
        self.c.anmelden("max", "pw")

    def test_teile_senden_ueberschreibt_und_trennt_firmen(self):
        t = [{"nr_zahl": 1, "nr": "18162-01", "name": "Ortgang", "stueck": 2, "breite": 200.0, "laenge": 3000.0, "flaeche": 600000.0, "material": test_material(),
              "operationen": OPS, "vorlage": "Winkelfalz", "vorlageVersion": 3}]
        zeilen = app_profil.teile_zeilen(t, "18162", "Dach", 7, "0.4.26")
        self.assertEqual(self.c.teile_senden(zeilen), 1)
        t[0]["breite"] = 210.0
        self.c.teile_senden(app_profil.teile_zeilen(t, "18162", "Dach", 7, "0.4.26"))
        self.assertEqual(len(self.z.teile), 1, "gleiches Teil wird überschrieben")
        z = self.z.teile[0]
        self.assertEqual((z["teil_label"], z["project_id"], z["zuschnitt_breite_mm"], z["status"]), ("18162-01", 7, 210.0, "neu"))
        self.assertEqual(z["app_data"]["schenkel"][1], {"laenge": 25.0, "winkel": 90.0})
        self.assertEqual([x["name"] for x in self.c.teile_lesen("18162")], ["Ortgang"])
        self.assertEqual(self.c.teile_lesen("999"), [])

    def test_teil_ohne_operationen(self):
        z = app_profil.teile_zeilen([{"nr_zahl": "", "nr": "", "name": "Roh", "stueck": 1, "breite": 100.0, "laenge": 100.0, "flaeche": None, "material": None, "operationen": None}], "1", "D")
        self.assertEqual((z[0]["app_data"], z[0]["teil_nr"], z[0]["material_name"]), ({}, 1, ""))

    def test_dateien_am_projekt_ablegen_und_ersetzen(self):
        self.z.speicher.clear()
        self.assertEqual(self.c.projekt_datei_ablegen(7, "CAD – Stückliste 18162.html", b"<html>v1</html>", "text/html"), "neu")
        self.assertEqual(self.c.projekt_datei_ablegen(7, "CAD – Stückliste 18162.csv", b"a;b", "text/csv"), "neu")
        self.assertEqual(len(self.z.projektdateien), 2)
        self.assertTrue(all(k.startswith("project-files/7/") for k in self.z.speicher))
        alt = self.z.projektdateien[0]["file_path"]
        self.assertEqual(self.c.projekt_datei_ablegen(7, "CAD – Stückliste 18162.html", b"<html>v2</html>", "text/html"), "ersetzt")
        self.assertEqual(len(self.z.projektdateien), 2, "gleicher Name → keine Verdopplung")
        neu = self.z.projektdateien[0]
        self.assertNotEqual(neu["file_path"], alt)
        self.assertEqual(self.z.speicher[neu["file_path"]], b"<html>v2</html>")
        self.assertNotIn(alt, self.z.speicher, "alte Datei wird entfernt")
        self.assertEqual((neu["size_bytes"], neu["mime_type"]), (len(b"<html>v2</html>"), "text/html"))
        with self.assertRaises(CloudFehler) as cm:
            self.c.projekt_datei_ablegen(99, "x.txt", b"x")      # fremdes/unbekanntes Projekt
        self.assertIn("Keine Berechtigung", str(cm.exception))

    def test_export_legt_vorhandene_dateien_ab(self):
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.commands import export_command as ex
        from spengler_cad.storage import cloud_client
        ordner = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, ordner, True)
        for n, inhalt in (("stueckliste.html", "<html/>"), ("stueckliste.csv", "x;y"), ("auftragsmappe.html", "<html>mappe</html>")):
            open(os.path.join(ordner, n), "w", encoding="utf-8").write(inhalt)
        alt = cloud_client.Cloud
        cloud_client.Cloud = lambda *a, **k: self.c
        self.addCleanup(setattr, cloud_client, "Cloud", alt)
        self.z.projektdateien.clear()
        t = ex._dateien_am_projekt({"id": 7, "name": "Sonneggweg"}, "18162", ordner)
        self.assertIn("3 neu, 0 ersetzt", t)
        self.assertEqual(sorted(r["name"] for r in self.z.projektdateien),
                         ["CAD – Auftragsmappe 18162.html", "CAD – Stückliste 18162.csv", "CAD – Stückliste 18162.html"])
        self.assertIn("0 neu, 3 ersetzt", ex._dateien_am_projekt({"id": 7}, "18162", ordner))
        self.assertIn("nicht gefunden", ex._dateien_am_projekt(None, "18162", ordner))

    def test_massaufnahmen_des_auftrags_lesen(self):
        liste = self.c.massaufnahmen_zum_auftrag("18162")
        self.assertEqual([m["id"] for m in liste], [127], "nur Aufnahmen des Projekts zum Auftrag")
        self.assertEqual(self.c.massaufnahmen_zum_auftrag("00000"), [])


if __name__ == "__main__":
    unittest.main()

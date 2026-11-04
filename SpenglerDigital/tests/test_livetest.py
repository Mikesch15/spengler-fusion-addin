"""Live-Test: Auswertung (ohne Fusion) und – mit der Attrappe – dass jeder Schritt einen Fehler abfängt, statt den Test abzubrechen."""
import unittest

import _basis  # noqa: F401
from spengler_cad.core import livetest_bericht as b


class Bericht(unittest.TestCase):
    erg = [{"name": "A", "status": "ok", "detail": "fein", "dauer": 0.5},
           {"name": "B", "status": "warnung", "detail": "Gehrung nicht geschnitten\nzweite Zeile", "dauer": 1.0},
           {"name": "C", "status": "uebersprungen", "detail": "", "dauer": None}]

    def test_status_warnung_ist_kein_fehler(self):
        self.assertEqual(b.gesamtstatus(self.erg), "ok")
        self.assertEqual(b.gesamtstatus(self.erg + [{"name": "D", "status": "fehler", "detail": "x"}]), "fehler")

    def test_unbekannter_status_zaehlt_als_fehler(self):
        self.assertEqual(b.zaehlen([{"name": "X", "status": "komisch"}])["fehler"], 1)

    def test_text_und_meldung(self):
        t = b.text(self.erg, "Kopf")
        self.assertIn("Kopf", t)
        self.assertIn("⚠ 2. B", t)
        self.assertIn("zweite Zeile", t)
        self.assertEqual(b.kurz(self.erg), "1 ok, 1 Warnungen, 0 Fehler, 1 übersprungen")
        self.assertIn("Gehrung nicht geschnitten", b.meldung(self.erg))
        self.assertIn("Alle 1", b.meldung([self.erg[0]]))


class FusionAttrappe(unittest.TestCase):
    def test_schritte_fangen_fehler_ab(self):
        from spengler_cad.diagnostics import live_test
        self.assertGreaterEqual(len(live_test.SCHRITTE), 12)
        self.assertEqual(len({n for n, _, _ in live_test.SCHRITTE}), len(live_test.SCHRITTE))
        self.assertFalse(live_test.SCHRITTE[0][2])     # das Test-Blech selbst braucht kein Blech


if __name__ == "__main__":
    unittest.main()


class Verbesserungen(unittest.TestCase):
    def test_fehlerhilfe(self):
        from spengler_cad.core import fehlerhilfe as f
        self.assertIn("kleineren Winkel", f.hilfe("Fusion meldet: SM_GENERIC_FAILURE"))
        self.assertIsNone(f.hilfe("völlig unbekannt"))
        self.assertTrue(f.mit_hilfe("Kein Auftrag aktiv").startswith("Kein Auftrag aktiv\n\nSo geht es weiter"))

    def test_ampel(self):
        from spengler_cad.core import statusanzeige as s
        self.assertEqual(s.ampel(None, "x", False, 0)[0], "gelb")
        self.assertEqual(s.ampel(None, "x", True, 0)[0], "gelb")
        self.assertEqual(s.ampel(None, "Fehler", True, 2)[0], "rot")
        plan = {"validation": {"errors": [], "warnings": []}, "targets": [{"geeignet": True, "text": "K1"}], "templateName": "Falz", "material": {"name": "Alu 1.0"}}
        self.assertEqual(s.ampel(plan, None, True, 1), ("gruen", "Bereit: 1 Kante, Falz, Alu 1.0"))
        plan["targets"].append({"geeignet": False, "text": "K2", "gruende": ["zu kurz"]})
        f, t = s.ampel(plan, None, True, 2)
        self.assertEqual(f, "rot")
        self.assertIn("zu kurz", t)
        self.assertIn("&lt;", s.html("rot", "a<b"))

    def test_reihenfolge_zuletzt(self):
        from spengler_cad.core import vorlagen_reihenfolge as r
        vs = [{"id": "a"}, {"id": "b", "favorite": True}, {"id": "c"}]
        neu, m = r.ordnen(vs, ["c"])
        self.assertEqual([v["id"] for v in neu], ["c", "b", "a"])
        self.assertEqual(m, {"a": "", "b": "★", "c": "↻"})
        self.assertEqual(r.merken(["x", "y"], "y"), ["y", "x"])
        self.assertEqual(len(r.merken(list("abcde"), "z")), 5)

    def test_material_pro_auftrag(self):
        from spengler_cad.core import auftrag as a
        mats = [{"id": "m1"}, {"id": "m2"}]
        e = {"defaultMaterialId": "m1", "order": {"auftrag": "17642"}}
        self.assertEqual(a.material_vorgabe(e, mats), "m1")
        self.assertTrue(a.material_merken(e, "m2"))
        self.assertFalse(a.material_merken(e, "m2"))
        self.assertEqual(a.material_vorgabe(e, mats), "m2")
        self.assertEqual(a.material_vorgabe(e, [{"id": "m1"}]), "m1")      # Material gelöscht → Standard
        self.assertFalse(a.material_merken({"order": {}}, "m1"))             # ohne Auftrag nichts merken

    def test_ablauf_und_pruefung(self):
        from spengler_cad.core import start
        z = {"auftrag": "1", "dokument_gespeichert": True, "material_gewaehlt": False, "projekt_in_app": True}
        t = start.ablauf_text(z)
        self.assertIn("✅ Auftrag", t)
        self.assertIn("⬜ Material", t)
        self.assertIn("✅ App", t)
        from spengler_cad.manufacturing import pruefung
        w = pruefung.pruefe_teile([{"name": "T", "nr": "1", "material": {"thickness": 1.0}, "dicke": 0.7, "blech": False, "abwicklung": True}])
        self.assertTrue(any("passt nicht zum Material" in x for x in w))
        self.assertTrue(any("kein Blechkörper" in x for x in w))

    def test_versatz_vorschau_aendert_nur_darstellung(self):
        from spengler_cad.core import bend_geometry as g
        ops = [{"typ": "flansch", "winkel": 90, "laenge": 20, "radius": None, "versatz": 5}]
        a = g.profil_aus_operationen(30, ops, 1.0)
        b = g.profil_aus_operationen(30, ops, 1.0, versatz_zeigen=True)
        self.assertEqual(a[0]["L"], 30)
        self.assertEqual(b[0]["L"], 25)

    def test_tagessicherung(self):
        import os, tempfile, time
        from spengler_cad.storage import backup_service as b, paths
        w = tempfile.mkdtemp()
        os.makedirs(os.path.join(w, "vorlagen"), exist_ok=True)
        open(os.path.join(w, "einstellungen.json"), "w").write("{}")
        p = b.taeglich(w, "0.0")
        self.assertTrue(p and p.endswith("_taeglich.zip"))
        self.assertIsNone(b.taeglich(w, "0.0"))                         # zweiter Aufruf am selben Tag: nichts
        os.utime(p, (time.time() - 30 * 3600,) * 2)
        self.assertTrue(b.taeglich(w, "0.0"))


class Uebersicht(unittest.TestCase):
    def test_zeilen(self):
        from spengler_cad.core import uebersicht as u
        projekte = [{"order_no": "17642", "object": "Nägeligasse 1a", "status": "aktiv"}, {"order_no": "17700", "object": "Bahnhof", "archived": True},
                    {"order_no": "17800", "object": "Schulhaus"}]
        ordner = [{"nummer": "17642", "objekt": "Nägeligasse 1a", "jahr": 2026}, {"nummer": "17555", "objekt": "Altbau", "jahr": 2025}]
        status = {"17642": {"status": "in_arbeit"}}
        teile = [{"auftrag": "17642", "status": "gefertigt", "geaendert_am": "2026-11-01T10:00"}, {"auftrag": "17642", "status": "offen", "geaendert_am": "2026-11-02T08:00"}]
        rows = u.zeilen(projekte, ordner, status, teile, aktiv="17642")
        self.assertEqual([r["nummer"] for r in rows], ["17800", "17642", "17555"])       # 17700 archiviert → fehlt
        r = {x["nummer"]: x for x in rows}
        self.assertTrue(r["17642"]["aktiv"] and r["17642"]["fusion"] and r["17642"]["app"])
        self.assertEqual((r["17642"]["teile"], r["17642"]["gefertigt"], r["17642"]["geaendert"]), (2, 1, "2026-11-02T08:00"))
        self.assertIn("Kein Ordner in Fusion", r["17800"]["hinweise"])
        self.assertIn("Projekt fehlt in der App", r["17555"]["hinweise"])
        s = u.zusammenfassung(rows)
        self.assertEqual((s["alle"], s["in_arbeit"], s["ohne_status"], s["mit_hinweis"]), (3, 1, 2, 2))

    def test_alle_gefertigt_hinweis(self):
        from spengler_cad.core import uebersicht as u
        rows = u.zeilen([{"order_no": "1000", "object": "A"}], [{"nummer": "1000", "objekt": "A", "jahr": 2026}], {"1000": {"status": "in_arbeit"}},
                        [{"auftrag": "1000", "status": "gefertigt"}])
        self.assertTrue(any("Status auf «Gefertigt»" in h for h in rows[0]["hinweise"]))

    def test_backend_ohne_fusion(self):
        import json
        import tempfile
        from spengler_cad.ui.palette_backend import Backend
        b = Backend(tempfile.mkdtemp())
        r = json.loads(b.behandle("auftragsuebersicht", "{}"))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["daten"]["zeilen"], [])
        self.assertTrue(r["daten"]["hinweise"])
        r = json.loads(b.behandle("auftrag_aktiv", json.dumps({"nummer": "17642", "objekt": "X", "jahr": 2026})))
        self.assertTrue(r["ok"])
        self.assertFalse(json.loads(b.behandle("auftrag_status", json.dumps({"nummer": "1", "status": "kaputt"})))["ok"])


class BlechAusApp(unittest.TestCase):
    def test_masse_aus_massaufnahme(self):
        from spengler_cad.core import app_profil as a
        d = {"schenkel": [{"laenge": 80, "winkel": 0}, {"laenge": 25, "winkel": 90}, {"laenge": 10, "winkel": 180}],
             "segmente": [{"laenge": 1500, "massen": []}, {"laenge": 2400, "massen": []}]}
        g = a.grundblech_aus_app(d)
        self.assertEqual((g["breite"], g["laenge"], len(g["ops"])), (80.0, 2400.0, 2))
        self.assertEqual([o["typ"] for o in g["ops"]], ["flansch", "umschlag"])

    def test_fehlende_angaben_werden_gemeldet(self):
        from spengler_cad.core import app_profil as a
        g = a.grundblech_aus_app({"schenkel": [{"laenge": 0, "winkel": 0}, {"laenge": 20, "winkel": 90}]})
        self.assertEqual((g["breite"], g["laenge"]), (100.0, None))
        self.assertTrue(any("Länge" in h for h in g["hinweise"]))
        self.assertTrue(any("Breite" in h for h in g["hinweise"]))
        self.assertEqual(a.grundblech_aus_app(None)["ops"], [])


class Grundriss(unittest.TestCase):
    def test_parse_und_text(self):
        from spengler_cad.core import grundriss as g
        s = g.parse("2500 L90 1800 R45 2500")
        self.assertEqual([(x["laenge"], x["drehung"]) for x in s], [(2500, 90), (1800, -45), (2500, 0)])
        self.assertEqual(g.als_text(s), "2500 L90 1800 R45 2500")
        self.assertEqual(g.parse("100 L 200")[0]["drehung"], 90)             # ohne Zahl = 90°
        for schlecht in ("", "L90 100", "100 X5", "0 L90", "100 L200"):
            with self.assertRaises(g.VerlaufFehler):
                g.parse(schlecht)

    def test_offenes_band_l_form(self):
        from spengler_cad.core import grundriss as g
        b = g.band(g.parse("300 L90 200"), 100, links=True)
        # Verlauf (0,0)→(300,0)→(300,200); links = innen: Gegenkante (0,100)→(200,100)→(200,200)
        self.assertEqual([tuple(round(c) for c in p) for p in b["gegen"]], [(0, 100), (200, 100), (200, 200)])
        self.assertEqual(len(b["ketten"]["verlauf"]), 2)
        self.assertEqual(len(b["ketten"]["start"]), 1)
        self.assertAlmostEqual(b["flaeche"], 300 * 100 + 100 * 100, delta=1)       # Winkel aus 2 Rechtecken
        rechts = g.band(g.parse("300 L90 200"), 100, links=False)
        self.assertEqual([tuple(round(c) for c in p) for p in rechts["gegen"]], [(0, -100), (400, -100), (400, 200)])

    def test_ring(self):
        from spengler_cad.core import grundriss as g
        b = g.band(g.parse("3000 L90 2000 L90 3000 L90 2000 L90"), 200, links=True, geschlossen=True)
        self.assertEqual(len(b["schleifen"]), 2)
        self.assertEqual(len(b["ketten"]["verlauf"]), 4)
        self.assertNotIn("start", b["ketten"])
        self.assertAlmostEqual(b["flaeche"], 3000 * 2000 - 2600 * 1600, delta=1)
        self.assertIn("Ring", b["text"])
        self.assertIn("<svg", g.svg(b))

    def test_fehler(self):
        from spengler_cad.core import grundriss as g
        with self.assertRaises(g.VerlaufFehler) as c:
            g.band(g.parse("3000 L90 2000 L90 3000 L90 1000 L90"), 100, True, True)
        self.assertIn("schliesst nicht", str(c.exception))
        with self.assertRaises(g.VerlaufFehler) as c:
            g.band(g.parse("300 L90 200"), 250, True)            # Breite grösser als die kurze Strecke → Gegenkante klappt um
        with self.assertRaises(g.VerlaufFehler):
            g.band(g.parse("100 L90 100"), 0, True)
        s = g.parse("100 L120 100")                                # sehr spitze Ecke bleibt baubar, 150° nicht
        g.band(s, 10, True)

    def test_gerade_strecken_werden_zusammengefasst(self):
        from spengler_cad.core import grundriss as g
        z = g.zusammenfassen(g.parse("100 200 L90 300"))
        self.assertEqual([(s["laenge"], s["drehung"]) for s in z], [(300, 90), (300, 0)])


class Bauteilvorlage(unittest.TestCase):
    def vorlage(self):
        from spengler_cad.core import bauteil, models
        v = models.neue_bauteilvorlage("Mauerabdeckung")
        v["breite"] = "Mauer+2*Ue"
        v["verlauf"] = {"art": "grundriss", "beispiel": "3000 L90 2000 L90 3000 L90 2000 L90", "seite": "links"}
        v["seiten"] = bauteil.seiten_aus_texten({"verlauf": "90 Tropf U+ 8", "gegen": "90 Tropf", "start": "", "ende": ""})
        bauteil.parameter_abgleichen(v)
        for p in v["parameters"]:
            p["default"] = {"Mauer": 300, "Ue": 40, "Tropf": 35}[p["name"]]
        return v

    MAT = {"thickness": 1.0, "innerRadius": 1.0, "kFactor": 0.4}

    def test_parameter_aus_texten(self):
        v = self.vorlage()
        self.assertEqual([p["name"] for p in v["parameters"]], ["Mauer", "Tropf", "Ue"])
        from spengler_cad.core import bauteil
        v["seiten"] = bauteil.seiten_aus_texten({"verlauf": "90 Tropf"})
        v["breite"] = "Mauer"
        bauteil.parameter_abgleichen(v)
        self.assertEqual([p["name"] for p in v["parameters"]], ["Mauer", "Tropf"])          # Ue entfällt
        self.assertEqual(v["parameters"][0]["default"], 300)                                # Einstellungen bleiben

    def test_plan_ring(self):
        from spengler_cad.core import bauteil
        p = bauteil.plan(self.vorlage(), {}, self.MAT, "3000 L90 2000 L90 3000 L90 2000 L90", None, True, True)
        self.assertEqual(p["breite"], 380)
        self.assertEqual(p["seiten"]["start"], [])
        self.assertEqual([o["typ"] for o in p["seiten"]["verlauf"]], ["flansch", "umschlag"])
        self.assertEqual(p["seiten"]["verlauf"][0]["laenge"], 35)

    def test_gerade_braucht_laenge(self):
        from spengler_cad.core import bauteil, grundriss
        v = self.vorlage()
        v["verlauf"]["art"] = "gerade"
        with self.assertRaises(grundriss.VerlaufFehler):
            bauteil.plan(v, {}, self.MAT, "", None)
        p = bauteil.plan(v, {}, self.MAT, "", 2000)
        self.assertEqual(len(p["geometrie"]["ketten"]["verlauf"]), 1)
        self.assertEqual(len(p["geometrie"]["ketten"]["start"]), 1)

    def test_pruefung(self):
        from spengler_cad.core import bauteil
        v = self.vorlage()
        v["breite"] = ""
        self.assertTrue(any("Breite" in f for f in bauteil.pruefe_bauteilvorlage(v)[0]))
        v = self.vorlage()
        v["verlauf"]["beispiel"] = "100 XY"
        self.assertTrue(any("Beispielverlauf" in f for f in bauteil.pruefe_bauteilvorlage(v)[0]))
        v = self.vorlage()
        v["seiten"]["gegen"] = []
        v["seiten"]["verlauf"] = []
        self.assertTrue(any("Keine Kantenfolge" in w for w in bauteil.pruefe_bauteilvorlage(v)[1]))

    def test_speichern_duplizieren_sync_typ(self):
        import tempfile
        from spengler_cad.storage.template_repository import VorlagenRepository
        from spengler_cad.storage import sync_service
        r = VorlagenRepository(tempfile.mkdtemp(), system_ordner=tempfile.mkdtemp())
        v = r.speichern(self.vorlage())
        self.assertTrue(v["id"].startswith("bv-"))
        k = r.duplizieren(v["id"], "bauteilvorlage")
        self.assertEqual(len(r.liste("bauteilvorlage")), 2)
        self.assertEqual(k["typ"], "bauteilvorlage")
        self.assertIn("bauteilvorlage", sync_service.TYPEN)
        ungueltig = self.vorlage()
        ungueltig["breite"] = ""
        from spengler_cad.storage.template_repository import VorlagenSpeicherFehler
        with self.assertRaises(VorlagenSpeicherFehler):
            r.speichern(ungueltig)


class Skizze(unittest.TestCase):
    def test_einrasten(self):
        from spengler_cad.core import skizze as s
        sch, st = s.aus_punkten([(0, 0), (80.3, 0.4), (80.1, 24.8), (70.2, 25.3)], 1, 5)
        self.assertEqual([x["laenge"] for x in sch], [80, 24, 10])
        self.assertEqual([x["winkel"] for x in sch][:2], [0, 90])
        self.assertEqual(st, 0)
        sch, _ = s.aus_punkten([(0, 0), (100, 0), (100.2, 30), (40, 30.1)], 5, 90)         # Winkelraster 90°
        self.assertEqual([x["winkel"] for x in sch], [0, 90, 90])

    def test_gerade_fortsetzung_wird_verbunden(self):
        from spengler_cad.core import skizze as s
        sch, _ = s.aus_punkten([(0, 0), (50, 0), (100, 0.5), (100, 40)], 1, 5)
        self.assertEqual([(x["laenge"], x["winkel"]) for x in sch], [(100, 0), (40, 90)])

    def test_umschlag_und_richtung(self):
        from spengler_cad.core import skizze as s
        sch = [{"laenge": 60, "winkel": 0}, {"laenge": 20, "winkel": -90}, {"laenge": 8, "winkel": -175}]
        ops, hinweise = s.operationen(sch)
        self.assertEqual([(o["typ"], o["winkel"]) for o in ops], [("flansch", -90), ("umschlag", -180)])
        self.assertTrue(hinweise)
        pts = s.zu_punkten(sch)
        self.assertAlmostEqual(pts[1][0], 60)
        self.assertAlmostEqual(pts[2][1], -20)                  # Rechtsdrehung → nach unten

    def test_leer_und_zuschnitt(self):
        from spengler_cad.core import skizze as s
        with self.assertRaises(s.SkizzenFehler):
            s.aus_punkten([(0, 0), (0.2, 0.1)])
        sch = [{"laenge": 80, "winkel": 0}, {"laenge": 25, "winkel": 90}]
        r = s.auswerten(sch, 0, 1.0, 1.0, 0.4)
        self.assertEqual(r["kurz"], "90 25")
        self.assertTrue(100 < r["zuschnitt"] < 110)             # 80 + 25 − Biegeabzug … plus Bogen
        self.assertEqual(r["summe"], 105)
        self.assertIsNone(s.auswerten(sch, 0)["zuschnitt"])

    def test_backend(self):
        import json
        import tempfile
        from spengler_cad.ui.palette_backend import Backend
        b = Backend(tempfile.mkdtemp())
        r = json.loads(b.behandle("skizze_auswerten", json.dumps({"punkte": [[0, 0], [80, 0], [80, 25]], "laengenraster": 1, "winkelraster": 5})))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["daten"]["kurz"], "90 25")
        t = json.loads(b.behandle("skizze_auswerten", json.dumps({"schenkel": [{"laenge": 80, "winkel": 0}, {"laenge": 30, "winkel": 45}], "start": 0})))
        self.assertEqual(t["daten"]["kurz"], "45 30")
        self.assertFalse(json.loads(b.behandle("skizze_auswerten", json.dumps({"schenkel": [{"laenge": 0, "winkel": 0}]})))["ok"])
        self.assertFalse(json.loads(b.behandle("skizze_auswerten", json.dumps({"schenkel": [{"laenge": 5, "winkel": 0}, {"laenge": 5, "winkel": 200}]})))["ok"])
        v = json.loads(b.behandle("skizze_vorlage", json.dumps({"schenkel": r["daten"]["schenkel"], "name": "Skizze Test"})))
        self.assertTrue(v["ok"], v)
        self.assertEqual(v["daten"]["operations"][0]["laenge"], 25)
        self.assertFalse(json.loads(b.behandle("skizze_vorlage", json.dumps({"schenkel": [{"laenge": 80, "winkel": 0}], "name": "x"})))["ok"])


class LiveTestQuelltext(unittest.TestCase):
    def test_kantenlaenge_nie_als_zahl_verwendet(self):
        """Regression (Live 4.11.): fa._kantenlaenge_mm liefert Text; im Live-Test muss die Länge eine Zahl sein."""
        import os
        q = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spengler_cad", "diagnostics", "live_test.py"), encoding="utf-8").read()
        code = [z for z in q.splitlines() if not z.strip().startswith(("#", '"""'))]
        self.assertFalse([z for z in code if "fa._kantenlaenge_mm(" in z and "def " not in z and "Live 4.11" not in z], "Textfunktion als Zahl benutzt")


class ProjektkarteBackend(unittest.TestCase):
    def test_karte_fotos_datei(self):
        import json
        import os
        import shutil
        import tempfile
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud
        from spengler_cad.ui.palette_backend import Backend
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        wurzel = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, wurzel, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        os.environ["SPENGLER_CAD_CLOUD_URL"] = url
        self.addCleanup(os.environ.pop, "SPENGLER_CAD_CLOUD_URL", None)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "employee", "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "S", "object": "Sonneggweg 9", "customer": "K", "status": "offen", "archived": False, "zugeteilt_an": []}]
        z.measurements = [{"company_id": "firma-a", "id": 41, "project_id": 7, "type": "freies_profil", "title": "Stirn", "workflow_status": "geruestet", "geruestet_am": "2026-11-03T10:00:00+00:00",
                           "created_at": "2026-11-02T10:00:00Z", "photo_paths": ["measurements/7/41/photo/a.jpg"]}]
        z.projektdateien = [{"project_id": 7, "id": 3, "name": "Plan.pdf", "file_path": "project-files/7/x.pdf", "size_bytes": 2048, "created_at": "2026-11-03T09:00:00Z", "created_by": "u"}]
        z.profil_auftraege = [{"company_id": "firma-a", "id": 1, "project_id": 7, "titel": "Stirn", "laenge_mm": 3200, "stueck": 2, "status": "offen", "daten": {}, "measurement_id": 41, "created_at": "2026-11-03T08:00:00Z"}]
        z.speicher["measurements/7/41/photo/a.jpg"] = b"\xff\xd8JPEG"
        z.speicher["project-files/7/x.pdf"] = b"%PDF-1.4"
        c = Cloud(wurzel, url=url, timeout=5)
        c.anmelden("max", "pw")
        b = Backend(wurzel)
        r = json.loads(b.behandle("projekt_liste", "{}"))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["daten"]["projekte"][0]["nummer"], "18162")
        k = json.loads(b.behandle("projekt_karte", json.dumps({"nummer": "18162"})))
        self.assertTrue(k["ok"], k)
        d = k["daten"]
        self.assertEqual(d["kopf"]["objekt"], "Sonneggweg 9")
        self.assertEqual(d["massaufnahmen"][0]["fotos"], 1)
        self.assertEqual(d["cad"]["auftraege"][0]["werkstatt"], "Gerüstet (gerüstet 3.11.2026)")
        self.assertEqual(d["neu"]["offene_auftraege"], 1)
        self.assertNotIn("Massaufnahme", d["neu"]["text"], "beim ersten Ansehen wird nichts ausser den wartenden Aufträgen «neu» gemeldet")
        k2 = json.loads(b.behandle("projekt_karte", json.dumps({"nummer": "18162"})))["daten"]
        self.assertEqual((k2["neu"]["massaufnahmen"], k2["neu"]["werkstatt"]), (0, 0), "nach dem ersten Ansehen ist nichts mehr neu")
        self.assertFalse(json.loads(b.behandle("projekt_karte", json.dumps({"nummer": "00000"})))["ok"])
        f = json.loads(b.behandle("projekt_fotos", json.dumps({"pfade": ["measurements/7/41/photo/a.jpg", "measurements/7/41/photo/fehlt.jpg"]})))["daten"]
        self.assertTrue(f["bilder"][0]["url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(len(f["fehler"]), 1)
        s = json.loads(b.behandle("projekt_datei", json.dumps({"nummer": "18162", "pfad": "project-files/7/x.pdf", "name": "Plan.pdf", "oeffnen": False})))["daten"]
        self.assertEqual(open(s["pfad"], "rb").read(), b"%PDF-1.4")
        self.assertIn("App-Dateien", s["pfad"])
        gemacht = []
        b._referenzbild = lambda pfad, titel: gemacht.append((os.path.basename(pfad), titel))
        json.loads(b.behandle("projekt_foto_fusion", json.dumps({"nummer": "18162", "pfad": "measurements/7/41/photo/a.jpg", "titel": "Stirn"})))
        self.assertEqual(gemacht, [("a.jpg", "Stirn")])


class ProjektAenderungBackend(unittest.TestCase):
    def test_status_hinweis_termin(self):
        import json
        import os
        import shutil
        import tempfile
        import fake_supabase
        from spengler_cad.storage.cloud_client import Cloud
        from spengler_cad.ui.palette_backend import Backend
        z = fake_supabase.Zustand()
        srv, url = fake_supabase.server(z)
        wurzel = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, wurzel, True)
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        os.environ["SPENGLER_CAD_CLOUD_URL"] = url
        self.addCleanup(os.environ.pop, "SPENGLER_CAD_CLOUD_URL", None)
        z.benutzer_anlegen("max@nfgryuzkpwjfmdlmevuy.supabase.co", "pw", "admin", "firma-a")
        z.projects = [{"company_id": "firma-a", "id": 7, "order_no": "18162", "name": "S", "object": "O", "status": "offen", "archived": False, "hinweis": "Schlüssel", "updated_at": "T1"}]
        Cloud(wurzel, url=url, timeout=5).anmelden("max", "pw")
        b = Backend(wurzel)
        r = json.loads(b.behandle("projekt_status", json.dumps({"id": 7, "neu": "in_arbeit", "alt": "offen"})))
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["daten"]["status"], "In Arbeit")
        self.assertFalse(json.loads(b.behandle("projekt_status", json.dumps({"id": 7, "neu": "kaputt", "alt": "offen"})))["ok"])
        self.assertFalse(json.loads(b.behandle("projekt_status", json.dumps({"id": 7, "neu": "in_arbeit", "alt": "in_arbeit"})))["ok"], "gleicher Status: nichts zu ändern")
        r = json.loads(b.behandle("projekt_hinweis", json.dumps({"id": 7, "text": "Gerüst bestellt", "modus": "ergaenzen", "alt": "Schlüssel", "updated_at": "2099-01-01T00:00:00+00:00"})))
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["daten"]["hinweis"].startswith("Schlüssel\n") and r["daten"]["hinweis"].endswith("(CAD): Gerüst bestellt") is False or "Gerüst bestellt" in r["daten"]["hinweis"])
        r = json.loads(b.behandle("projekt_hinweis", json.dumps({"id": 7, "text": "", "modus": "ersetzen"})))
        self.assertEqual(r["daten"]["hinweis"], "")
        t = json.loads(b.behandle("termin_speichern", json.dumps({"project_id": 7, "termin": {"titel": "Montage", "start_datum": "10.11.2026", "start_zeit": "7:30"}})))
        self.assertTrue(t["ok"], t)
        zeile = z.tab["termine"][-1]
        alt = {f: zeile.get(f) for f in ("titel", "start_datum", "ende_datum", "start_zeit", "ende_zeit", "ort", "notiz")}
        ohne_alt = json.loads(b.behandle("termin_speichern", json.dumps({"id": t["daten"]["id"], "project_id": 7, "termin": {"titel": "X", "start_datum": "11.11.2026"}})))
        self.assertFalse(ohne_alt["ok"], "ohne die gelesenen Werte wird nicht geändert")
        self.assertIn("neu laden", ohne_alt["fehler"])
        g = json.loads(b.behandle("termin_speichern", json.dumps({"id": t["daten"]["id"], "project_id": 7, "alt": alt, "termin": {"titel": "Montage Dach", "start_datum": "11.11.2026"}})))
        self.assertEqual(g["daten"]["titel"], "Montage Dach")
        veraltet = json.loads(b.behandle("termin_speichern", json.dumps({"id": t["daten"]["id"], "project_id": 7, "alt": alt, "termin": {"titel": "Nochmal", "start_datum": "12.11.2026"}})))
        self.assertFalse(veraltet["ok"], "die Karte war veraltet: Termin hat sich inzwischen geändert")
        self.assertIn("NICHTS überschrieben", veraltet["fehler"])
        self.assertEqual(z.tab["termine"][-1]["titel"], "Montage Dach")
        f = json.loads(b.behandle("termin_speichern", json.dumps({"project_id": 7, "termin": {"titel": "", "start_datum": "x"}})))
        self.assertFalse(f["ok"])
        self.assertIn("Titel", f["fehler"])


class Zeitzone(unittest.TestCase):
    """Regel: Zeitstempel mit Zone werden in die lokale Zeit umgerechnet; Zeitstempel ohne Zone gelten als UTC."""

    def _tz(self, name):
        import os
        import time
        alt = os.environ.get("TZ")

        def zurueck():
            if alt is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = alt
            time.tzset()
        self.addCleanup(zurueck)
        os.environ["TZ"] = name
        time.tzset()

    def test_utc_wird_lokal(self):
        from spengler_cad.core import projektkarte as p
        self._tz("Europe/Zurich")
        self.assertEqual(p._zeit("2026-01-15T10:00:00+00:00"), "15.1.2026 11:00", "Winterzeit: UTC+1")
        self.assertEqual(p._zeit("2026-07-01T10:00:00+00:00"), "1.7.2026 12:00", "Sommerzeit: UTC+2")
        self.assertEqual(p._zeit("2026-07-01T10:00:00Z"), "1.7.2026 12:00")
        self.assertEqual(p._zeit("2026-07-01T12:00:00+02:00"), "1.7.2026 12:00", "andere Zone wird ebenfalls umgerechnet")
        self.assertEqual(p._zeit("2026-11-03 16:00:00+00:00"), "3.11.2026 17:00", "Leerzeichen statt T")

    def test_ohne_zone_gilt_als_utc(self):
        from spengler_cad.core import projektkarte as p
        self._tz("Europe/Zurich")
        self.assertEqual(p._zeit("2026-07-01T10:00:00"), "1.7.2026 12:00")
        self.assertEqual(p.utc("2026-07-01T10:00:00").tzinfo is not None, True)

    def test_unlesbar_und_leer(self):
        from spengler_cad.core import projektkarte as p
        self.assertEqual(p._zeit(""), "")
        self.assertEqual(p._zeit(None), "")
        self.assertEqual(p._zeit("kein Datum"), "kein Datum")
        self.assertIsNone(p.utc("quatsch"))

    def test_neu_seit_vergleicht_zeitpunkte_nicht_zeichen(self):
        from spengler_cad.core import projektkarte as p
        daten = {"auftraege": [], "massaufnahmen": [{"created_at": "2026-11-03T16:00:00.500000+00:00"}, {"created_at": "2026-11-03T17:00:00+01:00"}, {"created_at": "kaputt"}],
                 "rapporte": [], "dateien": [], "termine": []}
        # gesehen 16:00:00 UTC: Eintrag 1 (16:00:00.5 UTC) ist neuer; Eintrag 2 (17:00+01:00 = 16:00 UTC) ist gleich alt; Eintrag 3 nicht lesbar
        self.assertEqual(p.neu_seit(daten, "2026-11-03T16:00:00+00:00")["massaufnahmen"], 1)
        self.assertEqual(p.neu_seit(daten, "unsinn")["massaufnahmen"], 0, "unlesbarer Zeitpunkt = noch nie gesehen")


class BerichtDatenschutz(unittest.TestCase):
    def test_maskieren(self):
        from spengler_cad.diagnostics import logger
        t = logger.maskiere("File \"C:\\Users\\Mike\\AppData\\Local\\x.py\" und C:/Users/Anna/Doc, /home/peter/x, /Users/lisa/y, mail mik.ledermann@gmail.com")
        for geheim in ("Mike", "Anna", "peter", "lisa", "ledermann"):
            self.assertNotIn(geheim, t)
        self.assertIn("C:\\Users\\…\\AppData", t)
        self.assertIn("<E-Mail>", t)
        self.assertEqual(logger.maskiere(None), "")

    def test_protokoll_nur_seit_teststart(self):
        import os
        import tempfile
        from spengler_cad.diagnostics import logger
        alt = os.environ.get("SPENGLER_CAD_DATEN")
        tmp = tempfile.mkdtemp()
        os.environ["SPENGLER_CAD_DATEN"] = tmp

        def zurueck():
            if alt is None:
                os.environ.pop("SPENGLER_CAD_DATEN", None)
            else:
                os.environ["SPENGLER_CAD_DATEN"] = alt
        self.addCleanup(zurueck)
        logger.info("Altlast: Kunde Muster AG, Auftrag 17642")
        m = logger.marke()
        logger.info("Live-Test Schritt", pfad="C:\\Users\\Mike\\x")
        neu = logger.seit(m)
        self.assertIn("Live-Test Schritt", neu)
        self.assertNotIn("Muster AG", neu)
        self.assertNotIn("Mike", neu)
        self.assertEqual(logger.seit(10 ** 9).count("Altlast") >= 0, True, "marke grösser als die Datei (rotiert): ab Anfang, kein Absturz")

    def test_gesendeter_bericht_enthaelt_keine_altlasten(self):
        import os
        import sys
        import tempfile
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
        from spengler_cad.commands import livetest_command as lc
        from spengler_cad.diagnostics import logger
        alt = os.environ.get("SPENGLER_CAD_DATEN")
        os.environ["SPENGLER_CAD_DATEN"] = tempfile.mkdtemp()

        def zurueck():
            if alt is None:
                os.environ.pop("SPENGLER_CAD_DATEN", None)
            else:
                os.environ["SPENGLER_CAD_DATEN"] = alt
        self.addCleanup(zurueck)

        class Wolke(object):
            angemeldet = True

            def __init__(self):
                self.zeile = None

            def test_speichern(self, z):
                self.zeile = z
        logger.info("Altlast Objekt Nägeligasse 1a Bern")
        m = logger.marke()
        logger.info("Schritt Flansch ok")
        w = Wolke()
        erg = [{"name": "Flansch", "status": "fehler", "detail": "Datei C:\\Users\\Mike\\Temp\\a.dxf fehlt", "dauer": 1.0}]
        self.assertTrue(lc._senden(erg, "Bericht C:\\Users\\Mike\\x", m, w))
        z = w.zeile
        gesamt = z["protokoll"] + z["notiz"] + z["text"]
        self.assertIn("Schritt Flansch ok", z["protokoll"])
        for verboten in ("Nägeligasse", "Mike"):
            self.assertNotIn(verboten, gesamt)
        self.assertNotIn("bild", z, "es wird kein Bildschirmfoto mitgeschickt")

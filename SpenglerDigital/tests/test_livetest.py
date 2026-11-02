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

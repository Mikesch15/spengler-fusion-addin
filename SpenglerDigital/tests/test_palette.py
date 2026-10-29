"""Palette «Vorlagen & Einstellungen»: Backend-Aktionen und – falls Node/Playwright vorhanden – die echte HTML-Seite im Browser."""
import json
import os
import shutil
import subprocess
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from _basis import ADDIN, DatenTest
from spengler_cad.ui.palette_backend import Backend


def rufe(b, aktion, daten=None):
    a = json.loads(b.behandle(aktion, json.dumps(daten or {})))
    if not a["ok"]:
        raise AssertionError(a["fehler"])
    return a["daten"]


class BackendTest(DatenTest):
    def test_ablauf(self):
        b = Backend()
        z = rufe(b, "init")
        self.assertEqual((z["vorlagen"], z["materialien"], z["details"]), ([], [], []))
        m = rufe(b, "material_neu", {"name": "TEST", "dicke": 0.7})
        m.update({"innerRadius": 1.0, "kFactor": 0.4})
        m = rufe(b, "material_speichern", {"material": m})
        kf = rufe(b, "k_faktor", {"zuschnitt": "128.61", "a": "50", "b": "80", "t": "0.7", "ri": "1"})
        self.assertTrue(kf["plausibel"] and 0.1 < kf["k"] < 0.6)
        self.assertFalse(json.loads(b.behandle("k_faktor", json.dumps({"zuschnitt": 140, "a": 50, "b": 80, "t": 0.7, "ri": 1})))["ok"])
        v = rufe(b, "neue_vorlage", {"name": "TEST V"})
        k = rufe(b, "kurzschrift", {"text": "90 H U+ 7"})
        v["operations"] = k["operations"]
        v["parameters"] = [{"name": "H", "label": "Höhe", "unit": "mm", "default": 25, "min": None, "max": None, "variable": True}]
        p = rufe(b, "pruefen", {"vorlage": v, "materialId": m["id"]})
        self.assertEqual(p["fehler"], [])
        self.assertIsNotNone(p["zugabe"])
        self.assertIn("Kanten: 1 gewählt, 1 geeignet", rufe(b, "bauplan_test", {"vorlage": v, "materialId": m["id"]}))
        vs = rufe(b, "vorschau", {"vorlage": v, "materialId": m["id"]})
        self.assertIn(">25<", vs["svg"])
        self.assertEqual(vs["material"], "TEST")
        self.assertIn("Etiketten pro Bogen", rufe(b, "etiketten_pruefen", {"labels": rufe(b, "init")["einstellungen"]["labels"]})["text"])
        g = rufe(b, "speichern", {"vorlage": v})
        self.assertIn("<svg", rufe(b, "init")["vorlagen"][0]["_vorschau"])
        self.assertEqual(len(rufe(b, "init")["vorlagen"]), 1)
        a = json.loads(b.behandle("loeschen", json.dumps({"id": g["id"]})))
        self.assertFalse(a["ok"], "ohne Bestätigung darf nicht gelöscht werden")
        rufe(b, "loeschen", {"id": g["id"], "bestaetigt": True})
        z = rufe(b, "init")
        self.assertEqual(len(z["papierkorb"]), 1)
        rufe(b, "papierkorb_zurueck", {"datei": z["papierkorb"][0]})
        s = rufe(b, "sicherung")
        self.assertTrue(os.path.exists(s))
        self.assertFalse(json.loads(b.behandle("unbekannt", "{}"))["ok"])
        self.assertIn("leer", rufe(b, "hilfe", {"thema": "vorlagen"}))


class _Brueckenserver(SimpleHTTPRequestHandler):
    backend = None

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers["Content-Length"])
        d = json.loads(self.rfile.read(n))
        if d["aktion"] == "frage":
            antwort = json.dumps({"ok": True, "daten": True})
        else:
            antwort = self.backend.behandle(d["aktion"], d["daten"])
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(antwort.encode("utf-8"))


@unittest.skipUnless(shutil.which("node"), "Node/Playwright nicht vorhanden")
class BrowserTest(DatenTest):
    def test_palette_im_browser(self):
        import fake_supabase
        z = fake_supabase.Zustand()
        z.benutzer_anlegen("chef@nfgryuzkpwjfmdlmevuy.supabase.co", "geheim", "admin", "firma-a", "Chef")
        cloud_srv, url = fake_supabase.server(z)
        os.environ["SPENGLER_CAD_CLOUD_URL"] = url
        self.addCleanup(os.environ.pop, "SPENGLER_CAD_CLOUD_URL", None)
        self.addCleanup(cloud_srv.server_close)
        self.addCleanup(cloud_srv.shutdown)
        _Brueckenserver.backend = Backend()
        os.chdir(ADDIN)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Brueckenserver)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            skript = os.path.join(os.path.dirname(os.path.abspath(__file__)), "palette_browser_test.cjs")
            r = subprocess.run(["node", skript, "http://127.0.0.1:%d/palette/vorlagen.html" % srv.server_address[1]],
                               capture_output=True, text=True, timeout=120)
            if "Cannot find module 'playwright'" in r.stderr:
                self.skipTest("Playwright nicht installiert")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("BROWSERTEST OK", r.stdout)
            self.assertIn("TEST Falz", [x["daten"]["name"] for x in z.cad], "nach Anmeldung in die App hochgeladen")
            falz = next(x for x in z.cad if x["daten"]["name"] == "TEST Falz")
            self.assertEqual(falz["daten"]["description"], "nach Anmeldung geändert", "Änderung automatisch abgeglichen")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()

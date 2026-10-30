"""Release-Knopf (werkzeug/veroeffentlichen.py) Ende-zu-Ende gegen einen NACHBAU der Supabase-Verwaltungsschnittstelle.

Läuft in einer Kopie des Projekts (die echten Dateien bleiben unverändert). Geprüft wird der Ablauf – nicht die echte Datenbank:
Reihenfolge (Dateien → Prüfsummen → Release-Eintrag zuletzt), Abbruch bei falscher Version / falscher Prüfsumme / fehlendem Token."""
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from _basis import ADDIN

WURZEL = os.path.abspath(os.path.join(ADDIN, ".."))
TOKEN = "sbp_testtoken"


class Datenbank(object):
    def __init__(self, releases=(), verfaelschen=False):
        self.blobs, self.releases, self.verfaelschen, self.log = {}, list(releases), verfaelschen, []


def server(db):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _antwort(self, code, daten):
            body = json.dumps(daten).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.headers.get("Authorization") != "Bearer " + TOKEN:
                return self._antwort(401, {"message": "Unauthorized"})
            if not re.match(r"^/v1/projects/[a-z0-9]+/database/query$", self.path):
                return self._antwort(404, {"message": "unbekannt"})
            sql = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["query"]
            if sql.startswith("insert into public.cad_addin_blobs"):
                m = re.match(r"insert into public\.cad_addin_blobs \(sha256, kodierung, inhalt\) values \('([0-9a-f]{64})', '(\w+)', '(.*)'\) on conflict do nothing;$", sql, re.S)
                inhalt = m.group(3).replace("''", "'")
                if db.verfaelschen:
                    inhalt += "x"
                db.blobs.setdefault(m.group(1), (m.group(2), inhalt))
                db.log.append("blob")
                return self._antwort(201, [])
            if sql.startswith("insert into public.cad_addin_releases"):
                db.releases.append(re.match(r"insert into public\.cad_addin_releases \(version, dateien, hinweise\) values \('([^']+)'", sql).group(1))
                db.log.append("release")
                return self._antwort(201, [])
            if sql.startswith("select version from public.cad_addin_releases"):
                return self._antwort(200, [{"version": v} for v in db.releases])
            if sql.startswith("select sha256 from public.cad_addin_blobs where sha256 in"):
                db.log.append("pruefen")
                gut = []
                for h in re.findall(r"'([0-9a-f]{64})'", sql):
                    kod, inhalt = db.blobs.get(h, (None, None))
                    if kod is None:
                        continue
                    roh = inhalt.encode("utf-8") if kod == "utf8" else base64.b64decode(inhalt)
                    if hashlib.sha256(roh).hexdigest() == h:
                        gut.append({"sha256": h})
                return self._antwort(200, gut)
            return self._antwort(400, {"message": "nicht nachgebaut: " + sql[:80]})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


class ReleaseKnopfTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="release_")
        shutil.copytree(os.path.join(WURZEL, "SpenglerDigital"), os.path.join(self.tmp, "SpenglerDigital"),
                        ignore=shutil.ignore_patterns("__pycache__", "tests"))
        shutil.copytree(os.path.join(WURZEL, "werkzeug"), os.path.join(self.tmp, "werkzeug"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(WURZEL, "releases"), os.path.join(self.tmp, "releases"), ignore=shutil.ignore_patterns("*.sql"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def lauf(self, db, version="9.9.9", token=TOKEN):
        srv, url = server(db)
        try:
            env = dict(os.environ, SUPABASE_API_URL=url, SUPABASE_PROJEKT="testprojekt", SUPABASE_ACCESS_TOKEN=token)
            return subprocess.run([sys.executable, os.path.join(self.tmp, "werkzeug", "veroeffentlichen.py"), version, "Testtext", "--ohne-tests"],
                                  env=env, capture_output=True, text=True, timeout=120)
        finally:
            srv.shutdown()
            srv.server_close()

    def datei(self, *teile):
        with open(os.path.join(self.tmp, *teile), encoding="utf-8") as f:
            return f.read()

    def test_erfolg_reihenfolge_und_dateien(self):
        db = Datenbank(releases=["0.4.5"])
        r = self.lauf(db)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(db.releases, ["0.4.5", "9.9.9"])
        self.assertGreater(db.log.count("blob"), 0)
        self.assertEqual(db.log[-2:], ["pruefen", "release"], "Release-Eintrag erst NACH der Prüfsummenkontrolle")
        self.assertIn('VERSION = "9.9.9"', self.datei("SpenglerDigital", "spengler_cad", "__init__.py"))
        self.assertIn('"version": "9.9.9"', self.datei("SpenglerDigital", "SpenglerDigital.manifest"))
        hochgeladen = json.loads(self.datei("releases", "hochgeladen.json"))
        self.assertTrue(set(db.blobs) <= set(hochgeladen), "alle hochgeladenen Dateien sind vermerkt")

    def test_auto_nimmt_naechste_nummer(self):
        db = Datenbank(releases=["0.4.5", "0.4.9"])
        r = self.lauf(db, "auto")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(db.releases, ["0.4.5", "0.4.9", "0.4.10"])
        self.assertIn('VERSION = "0.4.10"', self.datei("SpenglerDigital", "spengler_cad", "__init__.py"))

    def test_version_nicht_neuer(self):
        db = Datenbank(releases=["0.4.5"])
        for v in ("0.4.5", "0.4.4", "abc"):
            r = self.lauf(db, v)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("ABBRUCH", r.stderr)
        self.assertEqual((db.blobs, db.releases), ({}, ["0.4.5"]), "nichts hochgeladen")

    def test_falsche_pruefsumme_legt_keinen_release_an(self):
        db = Datenbank(releases=["0.4.5"], verfaelschen=True)
        r = self.lauf(db)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Prüfsumme", r.stderr)
        self.assertEqual(db.releases, ["0.4.5"], "ohne Release-Eintrag sieht kein Add-in ein Update")
        with open(os.path.join(WURZEL, "releases", "hochgeladen.json"), encoding="utf-8") as f:
            vorher = json.load(f)
        self.assertEqual(json.loads(self.datei("releases", "hochgeladen.json")), vorher, "hochgeladen.json bleibt unverändert")

    def test_falsches_oder_fehlendes_token(self):
        r = self.lauf(Datenbank(), token="falsch")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("401", r.stderr)
        r = self.lauf(Datenbank(), token="")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SUPABASE_ACCESS_TOKEN", r.stderr)


if __name__ == "__main__":
    unittest.main()

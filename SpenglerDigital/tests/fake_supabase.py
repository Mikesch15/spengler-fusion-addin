"""NACHBAU der benötigten Supabase-Endpunkte für Tests (Auth, PostgREST, Storage, RPC) – ohne Netz.

Bildet die Regeln der echten Migration (supabase/v_cad_addin_grundlagen.sql) nach, die per Probelauf gegen die
echte Datenbank geprüft wurden: Firma je Benutzer, Admin ändert, Mitarbeiter sieht, kein Löschen, Releases nur lesen.
PostgREST-Verhalten: UPDATE ohne Recht oder mit falscher Version → 200 und leere Liste (keine Fehlermeldung).
"""
import json
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Zustand(object):
    def __init__(self):
        self.benutzer = {}     # email → {pw, id, rolle, firma, vorname}
        self.tokens = {}       # access → uid
        self.refresh = {}      # refresh → uid
        self.firmen = {}       # id → name
        self.cad = []          # Zeilen
        self.tests = []        # cad_testergebnisse
        self.versionen = []
        self.dateien = {}      # pfad → bytes
        self.releases = []
        self.blobs = {}
        self.offline = False
        self.lock = threading.Lock()

    def benutzer_anlegen(self, email, pw, rolle, firma, vorname="Test"):
        uid = str(uuid.uuid4())
        self.firmen.setdefault(firma, "Firma " + firma[:4])
        self.benutzer[email] = {"pw": pw, "id": uid, "rolle": rolle, "firma": firma, "vorname": vorname}
        return uid

    def wer(self, uid):
        return next(b for b in self.benutzer.values() if b["id"] == uid)


def _filter(q):
    out = {}
    for k, v in urllib.parse.parse_qsl(q, keep_blank_values=True):
        if k in ("select", "order", "limit"):
            continue
        out[k] = v
    return out


def server(z):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _antwort(self, code, daten=None, roh=None):
            body = roh if roh is not None else (json.dumps(daten).encode() if daten is not None else b"")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(n) if n else b""

        def _uid(self):
            a = self.headers.get("Authorization", "")
            return z.tokens.get(a[7:]) if a.startswith("Bearer ") else None

        def _sitzung(self, uid):
            t, r = uuid.uuid4().hex, uuid.uuid4().hex
            z.tokens[t] = uid
            z.refresh[r] = uid
            return {"access_token": t, "refresh_token": r, "expires_in": 3600}

        def do_GET(self):
            self._weiter("GET")

        def do_POST(self):
            self._weiter("POST")

        def do_PATCH(self):
            self._weiter("PATCH")

        def do_DELETE(self):
            self._weiter("DELETE")

        def _weiter(self, m):
            if z.offline:
                self.connection.close()
                return
            with z.lock:
                self._behandle(m)

        def _behandle(self, m):
            u = urllib.parse.urlparse(self.path)
            pfad, q = u.path, u.query
            body = self._body()
            if pfad == "/auth/v1/token":
                d = json.loads(body)
                if "grant_type=password" in q:
                    b = z.benutzer.get(d["email"])
                    if not b or b["pw"] != d["password"]:
                        return self._antwort(400, {"error": "invalid_grant", "error_description": "Invalid login credentials"})
                    return self._antwort(200, self._sitzung(b["id"]))
                uid = z.refresh.pop(d["refresh_token"], None)
                return self._antwort(200, self._sitzung(uid)) if uid else self._antwort(400, {"error": "invalid_grant"})
            if pfad == "/functions/v1/resolve-login-email":
                d = json.loads(body)
                b = next((x for x in z.benutzer.values() if x.get("echte_email") == d["login"] and x["pw"] == d["password"]), None)
                return self._antwort(200, dict(self._sitzung(b["id"]), ok=True) if b else {"ok": False})
            uid = self._uid()
            if not uid:
                return self._antwort(401, {"message": "JWT expired"})
            me = z.wer(uid)
            admin = me["rolle"] == "admin"
            if pfad == "/auth/v1/user":
                return self._antwort(200, {"id": uid})
            if pfad == "/auth/v1/logout":
                return self._antwort(204)
            f = _filter(q)
            if pfad == "/rest/v1/profiles":
                b = z.wer(f["id"][3:])
                return self._antwort(200, [{"first_name": b["vorname"], "last_name": "Muster", "role": b["rolle"], "company_id": b["firma"]}])
            if pfad == "/rest/v1/companies":
                return self._antwort(200, [{"name": z.firmen[f["id"][3:]]}])
            if pfad == "/rest/v1/rpc/has_permission":
                d = json.loads(body)
                return self._antwort(200, admin if d["p_action"] == "edit" else True)
            if pfad == "/rest/v1/cad_daten":
                eigene = [r for r in z.cad if r["company_id"] == me["firma"]]
                if m == "GET":
                    return self._antwort(200, [{k: v for k, v in r.items() if k != "company_id"} for r in eigene])
                if m == "POST":
                    d = json.loads(body)
                    if not admin:
                        return self._antwort(403, {"message": 'new row violates row-level security policy for table "cad_daten"'})
                    if any(r["typ"] == d["typ"] and r["record_id"] == d["record_id"] for r in eigene):
                        return self._antwort(409, {"message": "duplicate key value violates unique constraint"})
                    r = dict(d, company_id=me["firma"])
                    r.setdefault("geloescht", False)
                    z.cad.append(r)
                    return self._antwort(201, [{k: v for k, v in r.items() if k != "company_id"}])
                if m == "PATCH":
                    d = json.loads(body)
                    treffer = [r for r in eigene if r["typ"] == f["typ"][3:] and r["record_id"] == f["record_id"][3:] and r["version"] == int(f["version"][3:])]
                    if not admin or not treffer:
                        return self._antwort(200, [])
                    r = treffer[0]
                    z.versionen.append(dict(r))
                    r.update(d)
                    return self._antwort(200, [{k: v for k, v in r.items() if k != "company_id"}])
                return self._antwort(405, {"message": "nicht erlaubt"})
            if pfad == "/rest/v1/cad_testergebnisse":
                eigene = [r for r in z.tests if r["company_id"] == me["firma"]]
                if m == "GET":
                    return self._antwort(200, eigene)
                if m == "POST":   # Upsert (on_conflict=company_id,test_id) – Firma darf nur die eigene sein (RLS)
                    for d in json.loads(body):
                        if d.get("company_id") != me["firma"]:
                            return self._antwort(403, {"message": 'new row violates row-level security policy for table "cad_testergebnisse"'})
                        alt = next((r for r in z.tests if r["company_id"] == me["firma"] and r["test_id"] == d["test_id"]), None)
                        if alt:
                            alt.update(d)
                        else:
                            z.tests.append(dict(d))
                    return self._antwort(201)
                return self._antwort(405, {"message": "nicht erlaubt"})
            if pfad.startswith("/storage/v1/object/cad/"):
                name = urllib.parse.unquote(pfad[len("/storage/v1/object/cad/"):])
                if name.split("/")[0] != me["firma"]:
                    return self._antwort(403, {"message": "row-level security"})
                if m == "POST":
                    if not admin:
                        return self._antwort(403, {"message": "new row violates row-level security policy"})
                    z.dateien[name] = body
                    return self._antwort(200, {"Key": name})
                if name not in z.dateien:
                    return self._antwort(404, {"message": "Object not found"})
                return self._antwort(200, roh=z.dateien[name])
            if pfad == "/rest/v1/cad_addin_releases":
                if m != "GET":
                    return self._antwort(403, {"message": "row-level security"})
                return self._antwort(200, [r for r in z.releases if r.get("aktiv", True)])
            if pfad == "/rest/v1/cad_addin_blobs":
                shas = f["sha256"][4:-1].split(",")
                return self._antwort(200, [dict(z.blobs[s], sha256=s) for s in shas if s in z.blobs])
            return self._antwort(404, {"message": "unbekannt " + pfad})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]

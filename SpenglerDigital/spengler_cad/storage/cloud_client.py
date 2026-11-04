"""Verbindung zur Spengler-Digital-App (Supabase) – nur Python-Standardbibliothek (urllib), läuft in Fusion.

Anmeldung wie in der App (js/03-login.js): «Vorname.Nachname» → interne Pseudo-Adresse, echte E-Mail direkt,
sonst Rückfall auf die Edge Function resolve-login-email (prüft das Passwort selbst, gibt nie Adressen heraus).
Zugriffsrechte prüft die Datenbank (RLS): Firma über my_company_id(), Ändern über has_permission('vorlagen','edit').

Gespeichert wird nur die Sitzung (Zugangs-/Erneuerungsschlüssel) in konto.json im Benutzerdatenordner –
das Passwort NIE.
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from . import json_store, paths

SUPABASE_URL = "https://nfgryuzkpwjfmdlmevuy.supabase.co"
# Öffentlicher Schlüssel der App (steht auch in der App selbst, js/01-basis.js) – Zugriff regelt RLS.
SUPABASE_KEY = "sb_publishable_U1YsWEdl4X9U94JO4sL5Lg_7_dU0erM"
RESSOURCE = "vorlagen"
BUCKET = "cad"


class CloudFehler(RuntimeError):
    def __init__(self, text, status=None, offline=False):
        RuntimeError.__init__(self, text)
        self.status = status
        self.offline = offline


def benutzer_zu_email(u):
    """Port von usernameToEmail (js/03-login.js)."""
    u = (u or "").strip()
    if "@" in u:
        return u.lower()
    return "".join(u.lower().split()) + "@nfgryuzkpwjfmdlmevuy.supabase.co"


class Cloud(object):
    def __init__(self, wurzel=None, url=None, key=None, timeout=15):
        self.wurzel = wurzel or paths.daten_ordner()
        self.url = (url or os.environ.get("SPENGLER_CAD_CLOUD_URL") or SUPABASE_URL).rstrip("/")
        self.key = key or SUPABASE_KEY
        self.timeout = timeout
        self.pfad = os.path.join(self.wurzel, "konto.json")
        self._konto = json_store.lesen(self.pfad) or {}

    # ------------------------------------------------------------------ HTTP
    def _anfrage(self, methode, pfad, daten=None, kopf=None, auth=True, roh=None):
        h = {"apikey": self.key, "Accept": "application/json"}
        if auth:
            h["Authorization"] = "Bearer " + self._token()
        body = None
        if roh is not None:
            body = roh
        elif daten is not None:
            body = json.dumps(daten).encode("utf-8")
            h["Content-Type"] = "application/json"
        h.update(kopf or {})
        req = urllib.request.Request(self.url + pfad, data=body, headers=h, method=methode)
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx if self.url.startswith("https") else None) as r:
                inhalt = r.read()
                return r.status, inhalt
        except urllib.error.HTTPError as e:
            inhalt = e.read()
            raise CloudFehler(self._fehlertext(e.code, inhalt), e.code)
        except (urllib.error.URLError, OSError) as e:
            raise CloudFehler("Keine Verbindung zur Spengler-Digital-App (%s). Es wird lokal weitergearbeitet." % getattr(e, "reason", e), offline=True)

    @staticmethod
    def _fehlertext(code, inhalt):
        try:
            d = json.loads(inhalt.decode("utf-8"))
            text = d.get("message") or d.get("msg") or d.get("error_description") or d.get("error") or ""
        except Exception:
            text = ""
        if code in (401, 403) and "row-level security" in text:
            return "Keine Berechtigung (in der App ist «Vorlagen ändern» für dieses Konto nicht freigegeben)."
        return "Spengler-Digital-App meldet %s%s" % (code, (": " + text) if text else "")

    def _json(self, *a, **k):
        status, inhalt = self._anfrage(*a, **k)
        return json.loads(inhalt.decode("utf-8")) if inhalt else None

    # ------------------------------------------------------------------ Anmeldung
    @property
    def angemeldet(self):
        return bool(self._konto.get("refresh_token"))

    @property
    def konto(self):
        return {k: v for k, v in self._konto.items() if k not in ("access_token", "refresh_token")}

    def _sitzung_speichern(self, d):
        self._konto.update({"access_token": d["access_token"], "refresh_token": d["refresh_token"],
                            "ablauf": time.time() + float(d.get("expires_in") or 3600) - 60})
        json_store.schreiben(self.pfad, self._konto)
        try:
            os.chmod(self.pfad, 0o600)
        except OSError:
            pass

    def anmelden(self, benutzer, passwort):
        if not benutzer or not passwort:
            raise CloudFehler("Bitte Benutzername und Passwort eingeben.")
        self._konto = {"benutzer": benutzer.strip()}
        try:
            d = self._json("POST", "/auth/v1/token?grant_type=password", {"email": benutzer_zu_email(benutzer), "password": passwort}, auth=False)
        except CloudFehler as e:
            if e.offline:
                raise
            d = None
            if "@" in benutzer:
                try:
                    r = self._json("POST", "/functions/v1/resolve-login-email", {"login": benutzer.strip(), "password": passwort}, auth=False)
                    if r and r.get("ok") is True and r.get("access_token") and r.get("refresh_token"):
                        d = r
                except CloudFehler as e2:
                    if e2.offline:
                        raise
            if d is None:
                raise CloudFehler("Benutzername oder Passwort falsch.", 400)
        self._sitzung_speichern(d)
        user = self._json("GET", "/auth/v1/user")
        self._konto["user_id"] = user["id"]
        profil = self._json("GET", "/rest/v1/profiles?select=first_name,last_name,role,company_id&id=eq.%s" % user["id"])
        if not profil:
            self.abmelden()
            raise CloudFehler("Zu diesem Konto gibt es kein Profil in der App.")
        p = profil[0]
        self._konto.update({"name": ("%s %s" % (p.get("first_name") or "", p.get("last_name") or "")).strip(),
                            "rolle": p.get("role"), "company_id": p.get("company_id")})
        self._konto["firma"] = self._firmenname(p.get("company_id"))
        self._konto["darf_aendern"] = self.darf_aendern()
        json_store.schreiben(self.pfad, self._konto)
        return self.konto

    def _firmenname(self, cid):
        try:
            r = self._json("GET", "/rest/v1/companies?select=name&id=eq.%s" % cid)
            return r[0]["name"] if r else ""
        except CloudFehler:
            return ""

    def _token(self):
        if not self.angemeldet:
            raise CloudFehler("Nicht angemeldet. Unter «Vorlagen & Einstellungen → Konto» mit dem App-Konto anmelden.")
        if time.time() < float(self._konto.get("ablauf") or 0):
            return self._konto["access_token"]
        try:
            d = self._json("POST", "/auth/v1/token?grant_type=refresh_token", {"refresh_token": self._konto["refresh_token"]}, auth=False)
        except CloudFehler as e:
            if not e.offline and e.status in (400, 401):
                self._konto.pop("refresh_token", None)
                json_store.schreiben(self.pfad, self._konto)
                raise CloudFehler("Die Anmeldung ist abgelaufen. Bitte neu anmelden.", e.status)
            raise
        self._sitzung_speichern(d)
        return self._konto["access_token"]

    def abmelden(self):
        try:
            if self.angemeldet:
                self._anfrage("POST", "/auth/v1/logout")
        except CloudFehler:
            pass
        self._konto = {}
        if os.path.exists(self.pfad):
            os.remove(self.pfad)

    def darf_aendern(self):
        try:
            return bool(self._json("POST", "/rest/v1/rpc/has_permission", {"p_resource": RESSOURCE, "p_action": "edit"}))
        except CloudFehler:
            return False

    # ------------------------------------------------------------------ CAD-Daten
    def liste(self):
        return self._json("GET", "/rest/v1/cad_daten?select=typ,record_id,daten,version,schema_version,geloescht,updated_at&order=typ,record_id") or []

    def einfuegen(self, typ, rid, daten, geloescht=False):
        r = self._json("POST", "/rest/v1/cad_daten", {"typ": typ, "record_id": rid, "daten": daten, "version": daten.get("version") or 1,
                                                       "schema_version": daten.get("schemaVersion") or 1, "geloescht": geloescht},
                       kopf={"Prefer": "return=representation"})
        return r[0] if r else None

    def aktualisieren(self, typ, rid, erwartet, daten, geloescht=False):
        """Nur wenn die Cloud-Version noch «erwartet» ist (optimistische Sperre). → neue Zeile oder None (Konflikt)."""
        q = "/rest/v1/cad_daten?typ=eq.%s&record_id=eq.%s&version=eq.%d" % (urllib.parse.quote(typ), urllib.parse.quote(rid), erwartet)
        r = self._json("PATCH", q, {"daten": daten, "version": erwartet + 1, "schema_version": daten.get("schemaVersion") or 1,
                                    "geloescht": geloescht}, kopf={"Prefer": "return=representation"})
        return r[0] if r else None

    def datei_hochladen(self, name, inhalt):
        pfad = "%s/details/%s" % (self._konto["company_id"], name)
        self._anfrage("POST", "/storage/v1/object/%s/%s" % (BUCKET, urllib.parse.quote(pfad)), roh=inhalt,
                      kopf={"Content-Type": "application/octet-stream", "x-upsert": "true"})

    def datei_laden(self, name):
        pfad = "%s/details/%s" % (self._konto["company_id"], name)
        return self._anfrage("GET", "/storage/v1/object/%s/%s" % (BUCKET, urllib.parse.quote(pfad)))[1]

    # ------------------------------------------------------------------ Programm-Updates
    def releases(self):
        return self._json("GET", "/rest/v1/cad_addin_releases?select=version,dateien,hinweise,veroeffentlicht_am&aktiv=eq.true") or []

    def blobs(self, shas):
        out = {}
        shas = list(shas)
        for i in range(0, len(shas), 20):
            teil = ",".join(shas[i:i + 20])
            for b in self._json("GET", "/rest/v1/cad_addin_blobs?select=sha256,kodierung,inhalt&sha256=in.(%s)" % teil) or []:
                out[b["sha256"]] = b
        return out

    # ------------------------------------------------------------------ Testergebnisse (Palette → Tests)
    def test_speichern(self, zeile):
        """Stand eines Testpunkts hochladen (je Firma und test_id eine Zeile, wird überschrieben)."""
        zeile = dict(zeile, company_id=self._konto["company_id"])
        self._anfrage("POST", "/rest/v1/cad_testergebnisse?on_conflict=company_id,test_id", [zeile],
                      kopf={"Prefer": "resolution=merge-duplicates,return=minimal"})

    # ------------------------------------------------------------------ Auftragsstatus, gemeinsames Änderungsprotokoll, Stundensätze (App)
    def status_alle(self):
        """Fertigungsstatus je Auftrag (cad_auftragsstatus) → {auftrag: {status, notiz, geaendert_am}}."""
        zeilen = self._json("GET", "/rest/v1/cad_auftragsstatus?select=auftrag,status,notiz,geaendert_am") or []
        return {z["auftrag"]: z for z in zeilen}

    def status_setzen(self, auftrag, status, notiz=""):
        if status not in ("offen", "in_arbeit", "gefertigt", "geliefert"):
            raise CloudFehler("Unbekannter Status «%s»." % status)
        self._anfrage("POST", "/rest/v1/cad_auftragsstatus?on_conflict=company_id,auftrag",
                      [{"company_id": self._konto["company_id"], "auftrag": str(auftrag), "status": status, "notiz": notiz[:1000],
                        "geaendert_am": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}],
                      kopf={"Prefer": "resolution=merge-duplicates,return=minimal"})

    def aenderung_senden(self, e):
        self._anfrage("POST", "/rest/v1/cad_aenderungen", [dict(e, company_id=self._konto["company_id"])], kopf={"Prefer": "return=minimal"})

    def aenderungen_lesen(self, anzahl=200):
        return self._json("GET", "/rest/v1/cad_aenderungen?select=zeit,benutzer,aktion,name,version,vorlage_id&order=zeit.desc&limit=%d" % anzahl) or []

    def stundensaetze(self):
        """Stundenansätze der App (Tabelle rates, nur lesen; sichtbar, wenn das Konto sie in der App sehen darf) → [{name, value}]."""
        return self._json("GET", "/rest/v1/rates?select=name,value&order=value.desc") or []

    def teile_senden(self, teile):
        """Teile an die App (Tabelle cad_teile, je Auftrag/Dokument/Teilnummer ein Eintrag, wird überschrieben). Schon übernommene Teile behalten
        measurement_id/status (diese Felder werden nicht mitgeschickt)."""
        if not teile:
            return 0
        zeilen = [dict(t, company_id=self._konto["company_id"]) for t in teile]
        self._anfrage("POST", "/rest/v1/cad_teile?on_conflict=company_id,auftrag,dokument,teil_nr", zeilen,
                      kopf={"Prefer": "resolution=merge-duplicates,return=minimal"})
        return len(zeilen)

    def teile_lesen(self, auftrag):
        return self._json("GET", "/rest/v1/cad_teile?select=teil_label,name,status,measurement_id,dokument,teil_nr,geaendert_am&auftrag=eq.%s&order=teil_nr" % urllib.parse.quote(str(auftrag))) or []

    def teile_uebersicht(self):
        """Alle Teile der Firma in Kurzform (Auftrag, Status, Änderungszeit) für die Auftragsübersicht."""
        return self._json("GET", "/rest/v1/cad_teile?select=auftrag,status,geaendert_am&limit=10000") or []

    def massaufnahmen_zum_auftrag(self, nummer):
        """Massaufnahmen (Freies Profil / Dachrandblech) der App zum Auftrag (nur lesen) → [{id,title,type,staerke_mm,data,workflow_status}]."""
        p = self.projekt_zu_auftrag(nummer)
        if not p or not p.get("id"):
            return []
        return self._json("GET", "/rest/v1/measurements?select=id,title,type,staerke_mm,workflow_status,data&project_id=eq.%s&type=in.(freies_profil,dachrandblech)&archived=eq.false&order=id.desc&limit=100" % p["id"]) or []

    def profil_auftraege(self, nummer):
        """Offene Profile, die in der App an das CAD gesendet wurden (Knopf «An CAD senden»), zum Auftrag → [{id, titel, laenge_mm, stueck, staerke_mm, daten, notiz}].
        Gibt es die Tabelle noch nicht (App-Version ohne diese Funktion), ist die Liste leer."""
        p = self.projekt_zu_auftrag(nummer)
        if not p or not p.get("id"):
            return []
        try:
            return self._json("GET", "/rest/v1/cad_profil_auftraege?select=id,titel,laenge_mm,stueck,staerke_mm,daten,notiz,created_at&project_id=eq.%s&status=eq.offen&order=created_at.desc&limit=100" % p["id"]) or []
        except CloudFehler as ex:
            if ex.status in (404, 400) and "cad_profil_auftraege" in str(ex):
                return []
            raise

    def profil_auftrag_gebaut(self, auftrag_id):
        """Gesendeten Auftrag als «gebaut» markieren (die App zeigt dann «im CAD gebaut»)."""
        self._anfrage("PATCH", "/rest/v1/cad_profil_auftraege?id=eq.%s" % int(auftrag_id),
                      {"status": "gebaut", "gebaut_am": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, kopf={"Prefer": "return=minimal"})

    # ------------------------------------------------------------------ Projektkarte (nur lesen)
    _KARTE = {
        "massaufnahmen": "/rest/v1/measurements?select=id,type,title,date,workflow_status,photo_path,photo_paths,sketch_path,sketch_paths,archived,created_at,updated_at,freigegeben_am,geruestet_am,montiert_am,montage_am&project_id=eq.{pid}&order=id.desc&limit=300",
        "rapporte": "/rest/v1/reports?select=id,date,work_entries,material_entries,photo_paths,created_at&project_id=eq.{pid}&order=date.desc&limit=100",
        "termine": "/rest/v1/termine?select=id,quelle,abo_id,titel,start_datum,ende_datum,start_zeit,ende_zeit,ort,notiz,mitarbeiter,created_at&project_id=eq.{pid}&order=start_datum.asc&limit=100",
        "dateien": "/rest/v1/project_files?select=id,name,file_path,size_bytes,mime_type,created_at,created_by&project_id=eq.{pid}&order=created_at.desc&limit=200",
        "offerten": "/rest/v1/offerten?select=id,offert_nr,title,date,gueltig_bis,kunde_name,positionen&project_id=eq.{pid}&order=date.desc&limit=50",
        "leistungen": "/rest/v1/leistungen?select=bezeichnung,status,menge,einheit,ausgefuehrte_menge&project_id=eq.{pid}&limit=200",
        "teile": "/rest/v1/cad_teile?select=teil_nr,teil_label,name,stueck,material_name,measurement_id,status,geaendert_am&project_id=eq.{pid}&order=teil_nr&limit=300",
        "auftraege": "/rest/v1/cad_profil_auftraege?select=id,titel,laenge_mm,stueck,status,measurement_id,gebaut_am,created_at&project_id=eq.{pid}&order=created_at.desc&limit=100",
    }

    def projekt_roh(self, nummer, personen=True):
        """Alles zum Projekt der Auftragsnummer, nur lesen → ({'projekt', 'massaufnahmen', 'rapporte', 'termine', 'dateien', 'offerten', 'leistungen', 'teile', 'auftraege', 'personen'}, [Hinweise]) oder
        (None, []), wenn es das Projekt nicht gibt. Die Abfragen laufen gleichzeitig; eine, die scheitert (fehlendes Recht, Tabelle fehlt), ergibt eine leere Liste und einen Hinweis.
        Offline: CloudFehler."""
        from concurrent.futures import ThreadPoolExecutor
        z = self._json("GET", "/rest/v1/projects?select=id,name,order_no,customer,object,status,hinweis,zugeteilt_an,created_at,updated_at,archived&order_no=eq.%s&limit=1" % urllib.parse.quote(str(nummer))) or []
        if not z:
            return None, []
        pid = z[0]["id"]
        auftraege = dict(self._KARTE)
        if personen:
            auftraege["personen"] = "/rest/v1/profiles?select=id,first_name,last_name&limit=500"
        hinweise = []

        def holen(item):
            name, pfad = item
            try:
                return name, self._json("GET", pfad.format(pid=pid)) or []
            except CloudFehler as ex:
                if ex.offline:
                    raise
                hinweise.append("%s: nicht lesbar (%s)" % (name, ex))
                return name, []
        with ThreadPoolExecutor(max_workers=8) as pool:
            roh = dict(pool.map(holen, auftraege.items()))
        roh["projekt"] = z[0]
        return roh, hinweise

    # ------------------------------------------------------------------ Änderungen in der App (nur nach ausdrücklicher Bestätigung im Aufrufer)
    def _geaendert(self, methode, pfad, daten, fehler_text):
        """PATCH/POST mit Rückgabe der betroffenen Zeilen. Wie in der App: ein von RLS blockierter oder durch einen Filter nicht getroffener PATCH meldet keinen Fehler, sondern betrifft 0 Zeilen –
        deshalb wird das Ergebnis geprüft statt Erfolg anzunehmen. → Liste der Zeilen."""
        try:
            _, inhalt = self._anfrage(methode, pfad, daten, kopf={"Prefer": "return=representation"})
        except CloudFehler as ex:
            if ex.status in (401, 403):
                raise CloudFehler("%s – das Recht «Projekte bearbeiten» (bzw. das Modul) fehlt." % fehler_text, ex.status)
            raise
        zeilen = json.loads(inhalt.decode("utf-8")) if inhalt else []
        if not zeilen:
            raise CloudFehler("%s – entweder wurde es inzwischen anderswo geändert (bitte die Karte neu laden) oder das Recht «Projekte bearbeiten» fehlt." % fehler_text)
        return zeilen

    def projekt_status_setzen(self, projekt_id, neu, alt):
        """Projektstatus ändern (nur wenn er noch `alt` ist – so überschreibt das CAD keine Änderung aus der App)."""
        return self._geaendert("PATCH", "/rest/v1/projects?id=eq.%d&status=eq.%s" % (int(projekt_id), urllib.parse.quote(str(alt))), {"status": neu},
                               "Der Projektstatus konnte nicht geändert werden")[0]

    def projekt_hinweis_setzen(self, projekt_id, text, updated_at=None):
        """Hinweis des Projekts setzen (None = löschen). Mit updated_at nur, wenn das Projekt seither nicht geändert wurde."""
        pfad = "/rest/v1/projects?id=eq.%d" % int(projekt_id) + (("&updated_at=eq.%s" % urllib.parse.quote(str(updated_at))) if updated_at else "")
        return self._geaendert("PATCH", pfad, {"hinweis": text}, "Der Hinweis konnte nicht gespeichert werden")[0]

    def termin_anlegen(self, zeile):
        """Neuer Termin am Projekt (Zeile wie die App sie schreibt; quelle, Firma und Ersteller setzt die Datenbank)."""
        try:
            _, inhalt = self._anfrage("POST", "/rest/v1/termine", [zeile], kopf={"Prefer": "return=representation"})
        except CloudFehler as ex:
            if ex.status in (401, 403):
                raise CloudFehler("Der Termin konnte nicht angelegt werden – das Recht «Projekte bearbeiten» fehlt oder das Modul «Termine» ist für die Firma nicht eingeschaltet.", ex.status)
            raise
        return (json.loads(inhalt.decode("utf-8")) if inhalt else [{}])[0]

    TERMIN_FELDER = ("titel", "start_datum", "ende_datum", "start_zeit", "ende_zeit", "ort", "notiz")

    @staticmethod
    def _gleich(a, b):
        """Vergleich eines Datenbankwerts mit dem gelesenen: Uhrzeiten «07:30» = «07:30:00», None = None."""
        if a is None or b is None:
            return a is None and b is None
        a, b = str(a), str(b)
        if len(a) >= 5 and a[2:3] == ":" and len(b) >= 5 and b[2:3] == ":":
            return a[:5] == b[:5]
        return a == b

    def termin_aendern(self, termin_id, zeile, erwartet):
        """Termin ändern – NUR wenn er in der Datenbank noch genau die Werte hat, die die Projektkarte gelesen hat (`erwartet`, alle sieben Felder, None = leer).
        Die Bedingung steht im PATCH selbst (WHERE), die Datenbank prüft und schreibt in einem Schritt: ein zwischenzeitlich in der App geänderter Termin wird nicht überschrieben.
        Trifft der PATCH nichts, wird nachgesehen und genau gemeldet: gelöscht, geändert oder Recht fehlt."""
        if not isinstance(erwartet, dict) or any(f not in erwartet for f in self.TERMIN_FELDER):
            raise CloudFehler("Der Termin kann nicht sicher geändert werden, weil die gelesenen Werte fehlen. Bitte die Projektkarte neu laden.")
        pfad = "/rest/v1/termine?id=eq.%d" % int(termin_id)
        for f in self.TERMIN_FELDER:
            w = erwartet[f]
            pfad += "&%s=%s" % (f, "is.null" if w is None else "eq." + urllib.parse.quote(str(w), safe=""))
        try:
            return self._geaendert("PATCH", pfad, dict(zeile, projekt_pruefen=False), "Der Termin konnte nicht geändert werden")[0]
        except CloudFehler as ex:
            if ex.status is not None or ex.offline:
                raise
            jetzt = self._json("GET", "/rest/v1/termine?select=%s&id=eq.%d" % (",".join(self.TERMIN_FELDER), int(termin_id))) or []
            if not jetzt:
                raise CloudFehler("Der Termin wurde inzwischen in der App gelöscht. Es wurde nichts geändert – bitte die Projektkarte neu laden.")
            if any(not self._gleich(jetzt[0].get(f), erwartet[f]) for f in self.TERMIN_FELDER):
                raise CloudFehler("Der Termin wurde seit dem Laden der Projektkarte in der App geändert. Es wurde NICHTS überschrieben – bitte die Projektkarte neu laden und die Änderung erneut vornehmen.")
            raise CloudFehler("Der Termin konnte nicht geändert werden – das Recht «Projekte bearbeiten» (bzw. das Modul «Termine») fehlt.")

    def foto_laden(self, pfad):
        """Foto/Skizze/Datei einer Massaufnahme bzw. eines Projekts aus dem Speicher der App (nur lesen) → Bytes. pfad wie in der Datenbank (measurements/<Projekt>/<Aufnahme>/photo/<Datei>)."""
        return self._anfrage("GET", "/storage/v1/object/authenticated/measurements/%s" % urllib.parse.quote(str(pfad), safe="/"))[1]

    def projekte_lesen(self):
        """Projekte der App (nur lesen) → [{id,name,order_no,object,customer,status,archived,created_at}]."""
        return self._json("GET", "/rest/v1/projects?select=id,name,order_no,object,customer,status,archived,created_at&order=order_no.desc&limit=1000") or []

    def projekt_anlegen(self, order_no, objekt, name=None):
        """Neues Projekt in der App – dieselben Felder wie die App beim Anlegen (name, order_no, customer, object). Auftragsnummern sind je Firma
        eindeutig; die Datenbank meldet doppelte (→ CloudFehler mit Klartext). → angelegte Zeile (id, …)."""
        try:
            r = self._json("POST", "/rest/v1/projects", [{"name": (name or objekt)[:200], "order_no": str(order_no), "customer": "", "object": objekt}],
                           kopf={"Prefer": "return=representation"})
        except CloudFehler as ex:
            if ex.status in (409,) or "duplicate" in str(ex).lower():
                raise CloudFehler("Die Auftragsnummer %s gibt es in der App schon." % order_no, ex.status)
            if ex.status in (401, 403):
                raise CloudFehler("Keine Berechtigung, in der App Projekte anzulegen (Recht «Projekte» für dieses Konto).", ex.status)
            raise
        return (r or [{}])[0]

    def projekt_datei_ablegen(self, projekt_id, name, inhalt, mime="application/octet-stream"):
        """Datei am Projekt der App ablegen (Ablage «Dateien» im Projekt-Cockpit: Bucket measurements, Pfad project-files/<Projekt>/<Datei>,
        Zeile in project_files – genau wie die App selbst). Gibt es am Projekt schon eine Datei mit diesem Namen, wird sie ERSETZT (neue Datei
        zuerst hochladen, Eintrag umbiegen, alte Datei danach entfernen) – so häufen sich bei erneutem Ausführen keine Duplikate.
        → "neu" | "ersetzt". Rechte wie in der App (Projekte bearbeiten)."""
        import random
        import string
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        pfad = "project-files/%s/%d_%s%s" % (projekt_id, int(time.time() * 1000), "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6)),
                                              ("." + ext) if ext else "")
        try:
            self._anfrage("POST", "/storage/v1/object/measurements/%s" % urllib.parse.quote(pfad), roh=inhalt, kopf={"Content-Type": mime})
            vorhanden = self._json("GET", "/rest/v1/project_files?select=id,file_path&project_id=eq.%s&name=eq.%s&limit=1" % (projekt_id, urllib.parse.quote(name))) or []
            if vorhanden:
                self._anfrage("PATCH", "/rest/v1/project_files?id=eq.%s" % vorhanden[0]["id"],
                              {"file_path": pfad, "size_bytes": len(inhalt), "mime_type": mime, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                              kopf={"Prefer": "return=minimal"})
                try:
                    self._anfrage("DELETE", "/storage/v1/object/measurements/%s" % urllib.parse.quote(vorhanden[0]["file_path"]))
                except CloudFehler:
                    pass        # die alte Datei bleibt dann liegen, der Eintrag zeigt auf die neue
                return "ersetzt"
            self._anfrage("POST", "/rest/v1/project_files", [{"project_id": projekt_id, "name": name, "file_path": pfad, "size_bytes": len(inhalt), "mime_type": mime}],
                          kopf={"Prefer": "return=minimal"})
            return "neu"
        except CloudFehler as ex:
            if ex.status in (401, 403):
                raise CloudFehler("Keine Berechtigung, am Projekt Dateien abzulegen (Recht «Projekte bearbeiten» in der App).", ex.status)
            raise

    def projekt_zu_auftrag(self, nummer):
        """Auftrag der App (Tabelle projects, nur lesen) zur Auftragsnummer → {name, order_no, customer, object, status} oder None."""
        z = self._json("GET", "/rest/v1/projects?select=id,name,order_no,customer,object,status&archived=eq.false&order_no=eq.%s&limit=1" % urllib.parse.quote(str(nummer))) or []
        return z[0] if z else None

    def fehlerberichte(self, anzahl=40):
        """Automatisch übermittelte Fehlerberichte (Testpunkte 98.x) der eigenen Firma, neueste zuerst."""
        return self._json("GET", "/rest/v1/cad_testergebnisse?select=test_id,text,notiz,protokoll,bild,addin_version,fusion_version,geaendert_am"
                                 "&test_id=like.98.*&order=geaendert_am.desc&limit=%d" % anzahl) or []

    def test_liste(self):
        return self._json("GET", "/rest/v1/cad_testergebnisse?select=test_id,status,notiz,geaendert_am&order=test_id") or []

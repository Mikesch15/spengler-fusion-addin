"""Release-Knopf: neue Version in einem Schritt veröffentlichen (Werkzeug für die Entwicklung, wird NICHT mit dem Add-in ausgeliefert).

  python3 werkzeug/veroeffentlichen.py 0.4.6 "Was ist neu?"      (Zugriffstoken in der Umgebungsvariable SUPABASE_ACCESS_TOKEN)

Läuft normalerweise per Knopf in GitHub (.github/workflows/release.yml). Ablauf, jeder Schritt bricht bei Fehler ab – der Release-Eintrag
(damit sieht jedes Add-in das Update) wird erst ganz am Ende angelegt:
  1. Version prüfen (Format, grösser als alle vorhandenen Releases)      5. jede Datei einzeln in die Datenbank schreiben
  2. automatische Tests ohne Fusion                                       6. in der Datenbank per SHA-256 nachprüfen
  3. Version in __init__.py und Manifest setzen, Testplan auffrischen      7. Release-Eintrag anlegen und prüfen
  4. SQL-Anweisungen aus release_sql.py erzeugen                          8. releases/hochgeladen.json nachführen
Zugriff: Supabase Management API (POST /v1/projects/<ref>/database/query) mit persönlichem Zugriffstoken.
"""
import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.path.join(HIER, "..", "SpenglerDigital")
sys.path.insert(0, HIER)
sys.path.insert(0, ADDIN)
import release_sql as rs  # noqa: E402
import testplan_json  # noqa: E402

PROJEKT = "nfgryuzkpwjfmdlmevuy"   # Supabase-Projekt «Spengler-Digital» (die Datenbank der App)
API = "https://api.supabase.com"


class Abbruch(Exception):
    pass


class VerwaltungsApi(object):
    def __init__(self, token, projekt=PROJEKT, url=API, timeout=120):
        self.token, self.projekt, self.url, self.timeout = token, projekt, url.rstrip("/"), timeout

    def abfrage(self, sql):
        req = urllib.request.Request("%s/v1/projects/%s/database/query" % (self.url, self.projekt),
                                     data=json.dumps({"query": sql}).encode("utf-8"), method="POST",
                                     headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json",
                                              "User-Agent": "spengler-release-knopf/1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                inhalt = r.read()
        except urllib.error.HTTPError as e:
            raise Abbruch("Datenbank-Schnittstelle meldet %s: %s" % (e.code, e.read().decode("utf-8", "replace")[:400]))
        except (urllib.error.URLError, OSError) as e:
            raise Abbruch("Keine Verbindung zur Datenbank-Schnittstelle: %s" % getattr(e, "reason", e))
        return json.loads(inhalt.decode("utf-8")) if inhalt else []


def versionszahl(v):
    return tuple(int(x) for x in v.split("."))


def version_pruefen(db, version):
    if not re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", version or ""):
        raise Abbruch("Version «%s» hat nicht die Form 1.2.3." % version)
    vorhanden = [r["version"] for r in db.abfrage("select version from public.cad_addin_releases")]
    if vorhanden and versionszahl(version) <= max(versionszahl(v) for v in vorhanden):
        raise Abbruch("Version %s ist nicht neuer als die vorhandene %s." % (version, max(vorhanden, key=versionszahl)))


def version_setzen(version):
    p = os.path.join(ADDIN, "spengler_cad", "__init__.py")
    s = open(p, encoding="utf-8").read()
    s, n = re.subn(r'VERSION = "[^"]*"', 'VERSION = "%s"' % version, s, count=1)
    if n != 1:
        raise Abbruch("VERSION in __init__.py nicht gefunden.")
    open(p, "w", encoding="utf-8").write(s)
    p = os.path.join(ADDIN, "SpenglerDigital.manifest")
    s = open(p, encoding="utf-8").read()
    s, n = re.subn(r'"version":\s*"[^"]*"', '"version": "%s"' % version, s, count=1)
    if n != 1:
        raise Abbruch("«version» im Manifest nicht gefunden.")
    open(p, "w", encoding="utf-8").write(s)
    import spengler_cad
    importlib.reload(spengler_cad)   # release_sql prüft gegen spengler_cad.VERSION


def testplan_auffrischen():
    with open(testplan_json.ZIEL, "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "bloecke": testplan_json.lesen()}, f, ensure_ascii=False, indent=1)


def tests_ausfuehren():
    r = subprocess.run([sys.executable, os.path.join(ADDIN, "tests", "run_all.py")], cwd=ADDIN, capture_output=True, text=True)
    if r.returncode != 0:
        raise Abbruch("Die automatischen Tests sind fehlgeschlagen – nichts veröffentlicht.\n" + (r.stdout + r.stderr)[-2500:])
    return (r.stdout.strip().splitlines() or [""])[-1]


def nachpruefen(db, hoch):
    """Stimmt jede hochgeladene Datei in der Datenbank mit ihrer Prüfsumme überein? Rückgabe: fehlende/fehlerhafte Prüfsummen."""
    if not hoch:
        return []
    liste = ",".join("'%s'" % h["sha256"] for h in hoch)
    ok = db.abfrage("select sha256 from public.cad_addin_blobs where sha256 in (%s) and "
                    "(case kodierung when 'utf8' then encode(sha256(convert_to(inhalt, 'UTF8')), 'hex') "
                    "else encode(sha256(decode(inhalt, 'base64')), 'hex') end) = sha256" % liste)
    gut = {r["sha256"] for r in ok}
    return [h["pfad"] for h in hoch if h["sha256"] not in gut]


def naechste_version(db):
    """Höchste vorhandene Version + 1 in der letzten Stelle (0.4.6 → 0.4.7)."""
    vorhanden = [r["version"] for r in db.abfrage("select version from public.cad_addin_releases")]
    if not vorhanden:
        raise Abbruch("Keine vorhandene Version – bitte eine Version angeben.")
    a, b, c = max(versionszahl(v) for v in vorhanden)
    return "%d.%d.%d" % (a, b, c + 1)


def veroeffentlichen(db, version, text, mit_tests=True, log=print):
    log("1/8 Version prüfen")
    version_pruefen(db, version)
    if mit_tests:
        log("2/8 Automatische Tests: " + tests_ausfuehren())
    else:
        log("2/8 Tests übersprungen (nur für Testläufe)")
    log("3/8 Version setzen, Testplan auffrischen")
    version_setzen(version)
    testplan_auffrischen()
    log("4/8 SQL erzeugen")
    sql, hoch = rs.anweisungen(version, text)
    log("5/8 %d geänderte Dateien hochladen" % len(hoch))
    for i, s in enumerate(sql[:-1], 1):
        db.abfrage(s)
        log("    %d/%d %s" % (i, len(hoch), hoch[i - 1]["pfad"]))
    log("6/8 Prüfsummen in der Datenbank nachprüfen")
    schlecht = nachpruefen(db, hoch)
    if schlecht:
        raise Abbruch("Prüfsumme in der Datenbank stimmt nicht für: %s – Release-Eintrag NICHT angelegt." % ", ".join(schlecht))
    log("7/8 Release-Eintrag anlegen")
    db.abfrage(sql[-1])
    if version not in [r["version"] for r in db.abfrage("select version from public.cad_addin_releases")]:
        raise Abbruch("Release-Eintrag nicht gefunden.")
    log("8/8 hochgeladen.json nachführen")
    rs.bestaetigen(version)
    log("Fertig: Version %s ist veröffentlicht." % version)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("version", help="z. B. 0.5.0 – oder «auto» für die nächste Nummer")
    ap.add_argument("text")
    ap.add_argument("--ohne-tests", action="store_true", help="nur für Testläufe")
    a = ap.parse_args(argv)
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("SUPABASE_ACCESS_TOKEN fehlt (GitHub: Settings → Secrets and variables → Actions).")
    db = VerwaltungsApi(token, os.environ.get("SUPABASE_PROJEKT", PROJEKT), os.environ.get("SUPABASE_API_URL", API))
    try:
        v = a.version.strip()
        if v.lower() in ("", "auto", "automatisch"):
            v = naechste_version(db)
            print("Automatische Version: %s" % v)
        veroeffentlichen(db, v, a.text.strip(), mit_tests=not a.ohne_tests)
    except Abbruch as e:
        sys.exit("ABBRUCH: %s" % e)


if __name__ == "__main__":
    main()

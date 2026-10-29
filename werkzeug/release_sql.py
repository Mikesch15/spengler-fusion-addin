"""Update veröffentlichen (Werkzeug für die Entwicklung, wird NICHT mit dem Add-in ausgeliefert).

  python3 werkzeug/release_sql.py basis 0.4.0            Dateiliste der ZIP-Grundinstallation festhalten
  python3 werkzeug/release_sql.py release 0.4.1 "Text"   SQL für Supabase erzeugen (releases/0.4.1.sql)

Ein Update braucht nur die Inhalte der Dateien, die sich gegenüber der ZIP-Grundinstallation (basis.json) geändert
haben und noch nicht hochgeladen sind (hochgeladen.json). Das SQL wird über das Supabase-Werkzeug ausgeführt;
erst danach hochgeladen.json mit «bestaetigen 0.4.1» nachführen.
"""
import base64
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.path.join(HIER, "..", "SpenglerDigital")
REL = os.path.join(HIER, "..", "releases")
sys.path.insert(0, ADDIN)
from spengler_cad.storage import updater  # noqa: E402


def lesen(n, standard):
    p = os.path.join(REL, n)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else standard


def schreiben(n, d):
    with open(os.path.join(REL, n), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def q(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    art, version = sys.argv[1], sys.argv[2]
    m = updater.manifest(ADDIN, version)
    # Markdown-Quellen der Doku braucht das Add-in nicht (Hilfe zeigt die HTML-Fassung) – hält Updates klein
    m["dateien"] = [f for f in m["dateien"] if not (f["pfad"].startswith("docs/") and f["pfad"].endswith(".md"))]
    from spengler_cad import VERSION
    if VERSION != version:
        sys.exit("spengler_cad.VERSION ist %s, nicht %s" % (VERSION, version))
    if art == "basis":
        schreiben("basis.json", m)
        print("Basis %s: %d Dateien" % (version, len(m["dateien"])))
        return
    basis = {f["pfad"]: f["sha256"] for f in lesen("basis.json", {"dateien": []})["dateien"]}
    oben = set(lesen("hochgeladen.json", []))
    if art == "bestaetigen":
        neu = [f["sha256"] for f in m["dateien"] if basis.get(f["pfad"]) != f["sha256"]]
        schreiben("hochgeladen.json", sorted(oben | set(neu)))
        print("hochgeladen.json nachgeführt")
        return
    hinweise = sys.argv[3] if len(sys.argv) > 3 else ""
    sql = ["begin;"]
    n = 0
    for f in m["dateien"]:
        if basis.get(f["pfad"]) == f["sha256"] or f["sha256"] in oben:
            continue
        d = open(os.path.join(ADDIN, *f["pfad"].split("/")), "rb").read()
        try:
            inhalt, kod = d.decode("utf-8"), "utf8"
            if inhalt.encode("utf-8") != d:
                raise UnicodeDecodeError("x", b"", 0, 1, "")
        except UnicodeDecodeError:
            inhalt, kod = base64.b64encode(d).decode("ascii"), "base64"
        sql.append("insert into public.cad_addin_blobs (sha256, kodierung, inhalt) values (%s, %s, %s) on conflict do nothing;"
                   % (q(f["sha256"]), q(kod), q(inhalt)))
        n += 1
    sql.append("insert into public.cad_addin_releases (version, dateien, hinweise) values (%s, %s::jsonb, %s);"
               % (q(version), q(json.dumps(m["dateien"], separators=(",", ":"))), q(hinweise)))
    sql.append("commit;")
    ziel = os.path.join(REL, version + ".sql")
    open(ziel, "w", encoding="utf-8").write("\n".join(sql) + "\n")
    print("%s: %d neue Dateiinhalte, %d Zeichen SQL" % (ziel, n, sum(len(s) for s in sql)))


if __name__ == "__main__":
    main()

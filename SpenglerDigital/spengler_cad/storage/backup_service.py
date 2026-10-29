"""Vollständige Sicherung und Wiederherstellung der Benutzerdaten (ZIP).

Sicherung: alle Benutzerdaten (Vorlagen inkl. 3D-Geometrie und Versionen, Papierkorb, Materialien,
Einstellungen, Datenformat) in eine ZIP-Datei mit Inhaltsverzeichnis sicherung.json.
Wiederherstellung: ZIP prüfen → automatische Sicherung des aktuellen Stands → entpacken in einen
Zwischenordner → erst dann austauschen. Bei einem Fehler bleibt der aktuelle Stand unverändert.
"""
import hashlib
import json
import os
import shutil
import tempfile
import zipfile

from ..core.models import jetzt
from . import paths


class SicherungsFehler(RuntimeError):
    pass


def _dateien(wurzel):
    for eintrag in paths.DATEN_INHALT:
        p = os.path.join(wurzel, eintrag)
        if os.path.isfile(p):
            yield eintrag
        elif os.path.isdir(p):
            for ordner, _, namen in os.walk(p):
                for n in namen:
                    if n.startswith(".tmp_"):
                        continue
                    voll = os.path.join(ordner, n)
                    yield os.path.relpath(voll, wurzel).replace(os.sep, "/")


def _pruefsumme(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def sichern(wurzel=None, ziel=None, grund="manuell", addin_version=""):
    """→ Pfad der ZIP-Datei."""
    wurzel = wurzel or paths.daten_ordner()
    if not ziel:
        ordner = paths.unterordner("sicherungen", wurzel)
        ziel = os.path.join(ordner, "sicherung_%s_%s.zip" % (jetzt().replace(":", "-"), grund))
        i = 1
        while os.path.exists(ziel):
            ziel = ziel[:-4] + "_%d.zip" % i
            i += 1
    inhalt = {}
    tmp = ziel + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in _dateien(wurzel):
            voll = os.path.join(wurzel, rel)
            z.write(voll, "daten/" + rel)
            inhalt[rel] = _pruefsumme(voll)
        z.writestr("sicherung.json", json.dumps({"typ": "spengler_sicherung", "schemaVersion": 1, "erstellt": jetzt(),
                                                  "grund": grund, "addinVersion": addin_version, "dateien": inhalt},
                                                 ensure_ascii=False, indent=1))
    os.replace(tmp, ziel)
    return ziel


def pruefen(zip_pfad):
    """Sicherung lesen und Prüfsummen kontrollieren → Inhaltsverzeichnis."""
    try:
        with zipfile.ZipFile(zip_pfad) as z:
            kopf = json.loads(z.read("sicherung.json").decode("utf-8"))
            if kopf.get("typ") != "spengler_sicherung":
                raise SicherungsFehler("Keine Spengler-Sicherung.")
            for rel, summe in kopf["dateien"].items():
                if hashlib.sha256(z.read("daten/" + rel)).hexdigest() != summe:
                    raise SicherungsFehler("Sicherung beschädigt: %s" % rel)
                if rel.startswith("/") or ".." in rel.split("/"):
                    raise SicherungsFehler("Ungültiger Pfad in der Sicherung: %s" % rel)
            return kopf
    except (KeyError, zipfile.BadZipFile, ValueError) as e:
        raise SicherungsFehler("Sicherung nicht lesbar: %s" % e)


def wiederherstellen(zip_pfad, wurzel=None, bestaetigt=False, addin_version=""):
    """→ Pfad der automatischen Sicherung des vorherigen Stands."""
    if not bestaetigt:
        raise SicherungsFehler("Wiederherstellen ersetzt die aktuellen Daten und braucht eine Bestätigung.")
    wurzel = wurzel or paths.daten_ordner()
    kopf = pruefen(zip_pfad)
    vorher = sichern(wurzel, grund="vor_wiederherstellung", addin_version=addin_version)
    zwischen = tempfile.mkdtemp(prefix="wiederherstellung_", dir=wurzel)
    try:
        with zipfile.ZipFile(zip_pfad) as z:
            for rel in kopf["dateien"]:
                ziel = os.path.join(zwischen, *rel.split("/"))
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                with open(ziel, "wb") as f:
                    f.write(z.read("daten/" + rel))
        # Austausch: erst alte Inhalte beiseite, dann neue hinein; bei Fehler zurück
        alt = tempfile.mkdtemp(prefix="alt_", dir=wurzel)
        verschoben = []
        try:
            for eintrag in paths.DATEN_INHALT:
                q = os.path.join(wurzel, eintrag)
                if os.path.exists(q):
                    shutil.move(q, os.path.join(alt, eintrag))
                    verschoben.append(eintrag)
            for eintrag in paths.DATEN_INHALT:
                q = os.path.join(zwischen, eintrag)
                if os.path.exists(q):
                    shutil.move(q, os.path.join(wurzel, eintrag))
        except Exception:
            for eintrag in paths.DATEN_INHALT:
                p = os.path.join(wurzel, eintrag)
                if eintrag in verschoben:
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    elif os.path.exists(p):
                        os.remove(p)
                    shutil.move(os.path.join(alt, eintrag), p)
            raise
        shutil.rmtree(alt, ignore_errors=True)
        # Abgleichstand passt nicht mehr zu den wiederhergestellten Daten: verwerfen, damit der nächste Abgleich mit der App
        # abweichende Fassungen als Konflikt-Kopie behält, statt die neueren Fassungen in der App zu überschreiben.
        stand = os.path.join(wurzel, "sync_stand.json")
        if os.path.exists(stand):
            os.replace(stand, stand + ".vor_wiederherstellung")
    finally:
        shutil.rmtree(zwischen, ignore_errors=True)
    return vorher


def liste(wurzel=None):
    ordner = paths.unterordner("sicherungen", wurzel or paths.daten_ordner())
    return sorted((os.path.join(ordner, n) for n in os.listdir(ordner) if n.endswith(".zip")), reverse=True)


def automatische_aufraeumen(wurzel=None, behalten=20):
    """Nur automatisch erstellte Sicherungen über der Anzahl entfernen – manuelle bleiben immer."""
    auto = [p for p in liste(wurzel) if not p.endswith("_manuell.zip")]
    for p in auto[behalten:]:
        os.remove(p)

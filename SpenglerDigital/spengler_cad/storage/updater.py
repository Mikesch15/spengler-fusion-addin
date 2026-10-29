"""Programm-Updates aus der Spengler-Digital-App.

Ein Release (Tabelle cad_addin_releases) ist eine Dateiliste [{pfad, sha256, groesse}] des Add-in-Ordners.
Geladen werden nur Dateien, deren Prüfsumme von der installierten abweicht (Inhalte aus cad_addin_blobs).
Ablauf: prüfen → Benutzerdaten sichern → alte Programmdateien nach programm_sicherung/<Version> kopieren →
neue Dateien prüfen (sha256) → erst dann ersetzen. Bei einem Fehler wird der alte Stand zurückgeschrieben.
Es wird ausschliesslich in den Add-in-Ordner geschrieben; Benutzerdaten liegen ausserhalb und bleiben unberührt.
Dateien, die im Release fehlen, werden nicht gelöscht (sicherer; alte Dateien stören nicht).
"""
import base64
import hashlib
import os
import shutil

from .. import VERSION
from . import backup_service, paths

ERLAUBT = ("SpenglerDigital.py", "SpenglerDigital.manifest", "README.md", "spengler_cad/", "palette/", "assets/", "docs/", "templates/")


class UpdateFehler(RuntimeError):
    pass


def version_tupel(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return (0,)


def sha256(daten):
    return hashlib.sha256(daten).hexdigest()


def _sicherer_pfad(rel, ordner):
    if not rel or rel.startswith(("/", "\\")) or ".." in rel.replace("\\", "/").split("/") or ":" in rel:
        raise UpdateFehler("Ungültiger Dateipfad im Update: %s" % rel)
    if not any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in ERLAUBT):
        raise UpdateFehler("Datei ausserhalb der Programmdateien im Update: %s" % rel)
    ziel = os.path.normpath(os.path.join(ordner, *rel.split("/")))
    if not paths.ist_innerhalb(ziel, ordner):
        raise UpdateFehler("Ungültiger Dateipfad im Update: %s" % rel)
    return ziel


def neuestes(cloud, aktuell=VERSION):
    """→ Release-dict, falls neuer als die installierte Version, sonst None."""
    rel = [r for r in cloud.releases() if version_tupel(r["version"]) > version_tupel(aktuell)]
    return max(rel, key=lambda r: version_tupel(r["version"])) if rel else None


def benoetigt(release, ordner=paths.ADDIN_ORDNER):
    """Dateien des Releases, die lokal fehlen oder anders sind → [(rel, ziel, sha)]"""
    out = []
    for f in release["dateien"]:
        ziel = _sicherer_pfad(f["pfad"], ordner)
        if os.path.exists(ziel):
            with open(ziel, "rb") as h:
                if sha256(h.read()) == f["sha256"]:
                    continue
        out.append((f["pfad"], ziel, f["sha256"]))
    return out


def installieren(cloud, release, ordner=paths.ADDIN_ORDNER, wurzel=None):
    """→ Liste ersetzter Dateien. Wirft UpdateFehler; dann ist der alte Stand wiederhergestellt."""
    wurzel = wurzel or paths.daten_ordner()
    noetig = benoetigt(release, ordner)
    if not noetig:
        return []
    blobs = cloud.blobs({sha for _, _, sha in noetig})
    neu = {}
    for rel, ziel, sha in noetig:
        b = blobs.get(sha)
        if b is None:
            raise UpdateFehler("Das Update ist unvollständig (%s fehlt). Bitte die Version %s als ZIP von Hand installieren." % (rel, release["version"]))
        inhalt = b["inhalt"].encode("utf-8") if b["kodierung"] == "utf8" else base64.b64decode(b["inhalt"])
        if sha256(inhalt) != sha:
            raise UpdateFehler("Prüfsumme stimmt nicht für %s – Update abgebrochen, nichts verändert." % rel)
        neu[ziel] = inhalt
    backup_service.sichern(wurzel, grund="vor_update_%s" % release["version"], addin_version=VERSION)
    sicherung = os.path.join(wurzel, "programm_sicherung", VERSION)
    gesichert = []
    for rel, ziel, _ in noetig:
        if os.path.exists(ziel):
            kopie = os.path.join(sicherung, *rel.split("/"))
            os.makedirs(os.path.dirname(kopie), exist_ok=True)
            shutil.copy2(ziel, kopie)
            gesichert.append((ziel, kopie))
    geschrieben = []
    try:
        for ziel, inhalt in neu.items():
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            tmp = ziel + ".sd_neu"
            with open(tmp, "wb") as h:
                h.write(inhalt)
            os.replace(tmp, ziel)
            geschrieben.append(ziel)
    except Exception as e:
        for ziel, kopie in gesichert:
            shutil.copy2(kopie, ziel)
        for ziel in geschrieben:
            if not any(z == ziel for z, _ in gesichert) and os.path.exists(ziel):
                os.remove(ziel)
        raise UpdateFehler("Update fehlgeschlagen (%s) – alter Stand wiederhergestellt." % e)
    return [rel for rel, _, _ in noetig]


def manifest(ordner, version, ausnahmen=("tests/", "supabase/", "docs/ABSCHLUSSBERICHT", "docs/handbuch_pdf.py")):
    """Dateiliste eines Add-in-Ordners für ein Release (Werkzeug für die Veröffentlichung)."""
    dateien = []
    for wurzel, ordnernamen, namen in os.walk(ordner):
        ordnernamen[:] = [o for o in ordnernamen if o != "__pycache__" and not o.startswith(".")]
        for n in namen:
            voll = os.path.join(wurzel, n)
            rel = os.path.relpath(voll, ordner).replace(os.sep, "/")
            if n.endswith((".pyc", ".pdf")) or any(rel.startswith(a) for a in ausnahmen) or rel.startswith("assets/logo/Metallisches"):
                continue
            if not any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in ERLAUBT):
                continue
            with open(voll, "rb") as h:
                d = h.read()
            dateien.append({"pfad": rel, "sha256": sha256(d), "groesse": len(d)})
    return {"version": version, "dateien": sorted(dateien, key=lambda f: f["pfad"])}

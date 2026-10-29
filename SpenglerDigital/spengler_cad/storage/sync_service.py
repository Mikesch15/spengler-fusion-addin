"""Abgleich der lokalen Ablage (Zwischenspeicher) mit der Spengler-Digital-App.

Grundsätze:
- Lokal wird immer zuerst gespeichert – das Add-in funktioniert auch ohne Internet.
- Die Cloud-Version (Spalte version) ist massgebend: hochgeladen wird nur, wenn sie seit dem letzten Abgleich
  unverändert ist (optimistische Sperre). Sonst Konflikt: die Cloud-Fassung gilt, die lokale Änderung wird als
  eigene Kopie «… (Konflikt TT.MM.)» behalten und ebenfalls hochgeladen – es geht nichts verloren.
- Gelöscht wird nie endgültig: lokal Papierkorb, in der Cloud geloescht = true.
- Ohne Recht «Vorlagen ändern» werden lokale Änderungen nicht hochgeladen und als «nur auf diesem PC» gemeldet.
Stand je Datensatz: sync_stand.json {"typ/id": {"version": Cloud-Version, "hash": Inhalt beim Abgleich}}.
"""
import datetime
import hashlib
import json
import os
import shutil

from ..core.models import SCHEMA, jetzt, kopie, neue_id
from . import json_store, paths
from .cloud_client import CloudFehler
from .material_library import MaterialBibliothek
from .template_repository import VorlagenRepository

TYPEN = ("kantenvorlage", "detailvorlage", "materialprofil")
OHNE = ("version", "modified", "_ebene", "_datei", "_nurLesen", "_fehler", "_vorschau", "_vorschauGrund")


def inhalt_hash(d):
    s = json.dumps({k: v for k, v in d.items() if k not in OHNE}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def l_geaendert_vor(L, s):
    return s is None or inhalt_hash(L) != s.get("hash")


def _sauber(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


class Abgleich(object):
    def __init__(self, cloud, wurzel=None):
        self.cloud = cloud
        self.wurzel = wurzel or paths.daten_ordner()
        self.repo = VorlagenRepository(self.wurzel)
        self.mat = MaterialBibliothek(self.wurzel)
        self.stand_pfad = os.path.join(self.wurzel, "sync_stand.json")

    # ------------------------------------------------------------------ lokale Ablage
    def _lokal(self):
        out = {}
        for typ in ("kantenvorlage", "detailvorlage"):
            for v in self.repo.liste(typ):
                if v.get("_ebene") == "benutzer" and not v.get("_fehler"):
                    out[(typ, v["id"])] = v
        for m in self.mat.liste():
            out[("materialprofil", m["id"])] = m
        return out

    def _datei(self, typ, rid):
        if typ == "materialprofil":
            return os.path.join(paths.unterordner("materialien", self.wurzel), json_store.dateiname_sicher(rid) + ".json")
        return self.repo._datei(typ, rid)

    def _lokal_schreiben(self, typ, rid, daten, version):
        d = kopie(daten)
        d["version"] = version
        json_store.schreiben(self._datei(typ, rid), d)
        if typ == "detailvorlage":
            self._geometrie_holen(d)

    def _lokal_papierkorb(self, typ, rid):
        q = self._datei(typ, rid)
        if os.path.exists(q):
            ziel = os.path.join(paths.unterordner("papierkorb", self.wurzel), "%s_%s.json" % (json_store.dateiname_sicher(rid), jetzt().replace(":", "-")))
            shutil.move(q, ziel)

    def _geometrie_holen(self, d):
        rel = (d.get("source") or {}).get("file")
        if not rel:
            return
        ziel = self.repo.geometrie_pfad(rel)
        if not os.path.exists(ziel):
            inhalt = self.cloud.datei_laden(os.path.basename(rel))
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            with open(ziel, "wb") as f:
                f.write(inhalt)

    def _geometrie_senden(self, d):
        rel = (d.get("source") or {}).get("file")
        if rel and os.path.exists(self.repo.geometrie_pfad(rel)):
            with open(self.repo.geometrie_pfad(rel), "rb") as f:
                self.cloud.datei_hochladen(os.path.basename(rel), f.read())

    # ------------------------------------------------------------------ Abgleich
    def ausfuehren(self):
        """→ Bericht {'geladen','hochgeladen','geloescht','konflikte','nur_lokal','fehler','neuer'}"""
        b = {"geladen": [], "hochgeladen": [], "geloescht": [], "konflikte": [], "nur_lokal": [], "fehler": [], "neuer": []}
        darf = self.cloud.darf_aendern()
        stand = json_store.lesen(self.stand_pfad, {}) or {}
        cloud = {(r["typ"], r["record_id"]): r for r in self.cloud.liste() if r.get("typ") in TYPEN}
        lokal = self._lokal()
        for key in sorted(set(cloud) | set(lokal)):
            typ, rid = key
            k = "%s/%s" % key
            try:
                self._eins(typ, rid, lokal.get(key), cloud.get(key), stand.get(k), stand, k, darf, b)
            except CloudFehler as e:
                if e.offline:
                    raise
                b["fehler"].append("%s: %s" % ((lokal.get(key) or (cloud.get(key) or {}).get("daten") or {}).get("name", rid), e))
            except Exception as e:  # ein defekter Datensatz stoppt nicht den ganzen Abgleich
                b["fehler"].append("%s: %s" % (rid, e))
        json_store.schreiben(self.stand_pfad, stand)
        b["zeit"] = jetzt()
        b["darf_aendern"] = darf
        return b

    def _eins(self, typ, rid, L, C, s, stand, k, darf, b):
        name = (L or (C or {}).get("daten") or {}).get("name", rid)
        if C and (C.get("schema_version") or 0) > SCHEMA[typ]:
            # aus neuerer Programmversion: nie mit einer älteren Fassung überschreiben, nur herunterladen
            b["neuer"].append(name)
            if L is not None and inhalt_hash(L) != inhalt_hash(C["daten"]) and l_geaendert_vor(L, s):
                self._konflikt_kopie(typ, L, b, stand, hochladen=False)
            if not C["geloescht"]:
                self._lokal_schreiben(typ, rid, C["daten"], C["version"])
                stand[k] = {"version": C["version"], "hash": inhalt_hash(C["daten"])}
            return
        lh = inhalt_hash(L) if L else None
        l_geaendert = L is not None and (s is None or lh != s.get("hash"))
        c_geaendert = C is not None and (s is None or C["version"] != s.get("version"))

        if L and not C:
            if not darf:
                b["nur_lokal"].append(name)
                return
            if typ == "detailvorlage":
                self._geometrie_senden(L)
            r = self.cloud.einfuegen(typ, rid, dict(_sauber(L), version=1))
            stand[k] = {"version": r["version"], "hash": lh}
            self._version_lokal(typ, rid, r["version"])
            b["hochgeladen"].append(name)
            return
        if C and not L:
            if C["geloescht"]:
                stand.pop(k, None)
                return
            if s is not None and not c_geaendert and darf:
                # lokal gelöscht (Papierkorb) → in der Cloud als gelöscht markieren
                r = self.cloud.aktualisieren(typ, rid, C["version"], C["daten"], geloescht=True)
                if r:
                    stand.pop(k, None)
                    b["geloescht"].append(name)
                    return
            self._lokal_schreiben(typ, rid, C["daten"], C["version"])
            stand[k] = {"version": C["version"], "hash": inhalt_hash(C["daten"])}
            b["geladen"].append(name)
            return
        # beide vorhanden
        if C["geloescht"]:
            if l_geaendert:   # lokal geändert, woanders gelöscht → lokale Fassung als Kopie retten
                self._konflikt_kopie(typ, L, b, stand, hochladen=darf)
            self._lokal_papierkorb(typ, rid)
            stand.pop(k, None)
            b["geloescht"].append(name)
            return
        if lh == inhalt_hash(C["daten"]):
            stand[k] = {"version": C["version"], "hash": lh}
            if L.get("version") != C["version"]:
                self._version_lokal(typ, rid, C["version"])
            return
        if c_geaendert and not l_geaendert:
            self._lokal_schreiben(typ, rid, C["daten"], C["version"])
            stand[k] = {"version": C["version"], "hash": inhalt_hash(C["daten"])}
            b["geladen"].append(name)
            return
        if l_geaendert and not c_geaendert:
            if not darf:
                b["nur_lokal"].append(name)
                return
            if typ == "detailvorlage":
                self._geometrie_senden(L)
            neu = dict(_sauber(L), version=C["version"] + 1)
            r = self.cloud.aktualisieren(typ, rid, C["version"], neu)
            if r:
                stand[k] = {"version": r["version"], "hash": lh}
                self._version_lokal(typ, rid, r["version"])
                b["hochgeladen"].append(name)
                return
            # zwischenzeitlich in der Cloud geändert → wie Konflikt behandeln
        # Konflikt: Cloud-Fassung gilt, lokale Änderung als Kopie
        self._konflikt_kopie(typ, L, b, stand, hochladen=darf)
        if not darf:
            b["nur_lokal"].append(name + " (eigene Fassung als lokale Kopie behalten)")
        self._lokal_schreiben(typ, rid, C["daten"], C["version"])
        stand[k] = {"version": C["version"], "hash": inhalt_hash(C["daten"])}

    def _version_lokal(self, typ, rid, version):
        p = self._datei(typ, rid)
        d = json_store.lesen(p)
        if d is not None and d.get("version") != version:
            d["version"] = version
            json_store.schreiben(p, d)

    def _konflikt_kopie(self, typ, L, b, stand, hochladen=True):
        k = _sauber(kopie(L))
        alt = k["id"]
        k["id"] = neue_id({"kantenvorlage": "kv", "detailvorlage": "dv", "materialprofil": "mat"}[typ])
        k["name"] = "%s (Konflikt %s)" % (k.get("name", ""), datetime.date.today().strftime("%d.%m."))
        k["version"] = 1
        k.setdefault("metadata", {})["konfliktVon"] = alt
        if typ == "detailvorlage" and (k.get("source") or {}).get("file"):
            rel = k["source"]["file"]
            if os.path.exists(self.repo.geometrie_pfad(rel)):
                k["source"]["file"] = self.repo.geometrie_ablegen(self.repo.geometrie_pfad(rel), k["id"], 1)
            if hochladen:
                self._geometrie_senden(k)
        json_store.schreiben(self._datei(typ, k["id"]), k)
        if not hochladen:   # ohne Recht: Kopie bleibt nur auf diesem PC
            b["konflikte"].append(k["name"] + " (nur lokal)")
            return
        r = self.cloud.einfuegen(typ, k["id"], k)
        stand["%s/%s" % (typ, k["id"])] = {"version": r["version"], "hash": inhalt_hash(k)}
        b["konflikte"].append(k["name"])


def bericht_text(b):
    z = []
    for k, t in (("geladen", "Aus der App geladen"), ("hochgeladen", "In die App hochgeladen"), ("geloescht", "Gelöscht (Papierkorb)"),
                 ("konflikte", "Konflikt – lokale Fassung als Kopie behalten"), ("nur_lokal", "Nur auf diesem PC (keine Berechtigung)"),
                 ("neuer", "Aus neuerer Add-in-Version (nur lesen)"), ("fehler", "Fehler")):
        if b.get(k):
            z.append("%s: %s" % (t, ", ".join(b[k])))
    return "\n".join(z) or "Alles abgeglichen – keine Änderungen."

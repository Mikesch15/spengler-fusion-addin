"""Vorlagenbibliothek: Benutzerbibliothek (Benutzerdatenordner), optionale Projektbibliothek und
Systemvorlagen (Add-in-Ordner, produktiv LEER).

Regeln:
- Speichern einer geänderten Vorlage erhöht deren Version; die alte Fassung wandert nach vorlagen/versionen.
- Löschen nur mit ausdrücklicher Bestätigung und auch dann nur in den Papierkorb.
- Vorlagen mit unbekannter, neuerer schemaVersion werden angezeigt, aber nie verändert.
- Bereits erzeugte Bauteile tragen Vorlagen-ID und -Version als Attribut; eine spätere Vorlagenänderung
  verändert sie nicht (es gibt keine Live-Verknüpfung).
"""
import base64
import os
import shutil

from ..core import models
from ..core.models import SCHEMA, jetzt, kopie, neue_id
from ..core.validation import pruefe_kantenvorlage
from . import json_store, paths

TYPEN = {"kantenvorlage": "kanten", "detailvorlage": "details"}


class VorlagenSpeicherFehler(RuntimeError):
    pass


def _vergleichbar(v):
    d = kopie(v)
    for k in ("version", "modified", "favorite", "category", "_ebene", "_nurLesen", "_datei"):
        d.pop(k, None)
    return d


class VorlagenRepository(object):
    def __init__(self, wurzel=None, projekt_ordner=None, system_ordner=None):
        self.wurzel = wurzel or paths.daten_ordner()
        self.projekt = projekt_ordner or None
        self.system = system_ordner if system_ordner is not None else paths.SYSTEM_VORLAGEN

    # -------------------------------------------------------------- Ordner
    def _ordner(self, typ, ebene="benutzer"):
        if typ not in TYPEN:
            raise VorlagenSpeicherFehler("Unbekannter Vorlagentyp %s" % typ)
        if ebene == "benutzer":
            return paths.unterordner(TYPEN[typ], self.wurzel)
        if ebene == "projekt":
            if not self.projekt:
                raise VorlagenSpeicherFehler("Keine Projektbibliothek eingestellt.")
            p = os.path.join(self.projekt, paths.UNTERORDNER[TYPEN[typ]])
            os.makedirs(p, exist_ok=True)
            return p
        if ebene == "system":
            return os.path.join(self.system, TYPEN[typ])
        raise VorlagenSpeicherFehler("Unbekannte Bibliotheksebene %s" % ebene)

    def _datei(self, typ, vid, ebene="benutzer"):
        return os.path.join(self._ordner(typ, ebene), json_store.dateiname_sicher(vid) + ".json")

    # -------------------------------------------------------------- Lesen
    def liste(self, typ="kantenvorlage"):
        out = []
        for ebene in ("system", "benutzer", "projekt"):
            if ebene == "projekt" and not self.projekt:
                continue
            ordner = self._ordner(typ, ebene)
            if not os.path.isdir(ordner):
                continue
            for n in sorted(os.listdir(ordner)):
                if not n.endswith(".json") or n.startswith("."):
                    continue
                pfad = os.path.join(ordner, n)
                try:
                    v = json_store.lesen(pfad)
                except json_store.DatenFehler:
                    out.append({"id": n[:-5], "name": n, "typ": typ, "_ebene": ebene, "_fehler": "Datei nicht lesbar", "_nurLesen": True, "_datei": pfad})
                    continue
                if not isinstance(v, dict) or v.get("typ") != typ:
                    continue
                v["_ebene"] = ebene
                v["_datei"] = pfad
                v["_nurLesen"] = ebene == "system" or (v.get("schemaVersion") or 0) > SCHEMA[typ]
                out.append(v)
        return sorted(out, key=lambda v: (not v.get("favorite"), (v.get("category") or "").lower(), (v.get("name") or "").lower()))

    def holen(self, vid, typ="kantenvorlage"):
        for v in self.liste(typ):
            if v.get("id") == vid:
                return v
        raise VorlagenSpeicherFehler("Vorlage %s nicht gefunden." % vid)

    def kategorien(self, typ="kantenvorlage"):
        return sorted({v.get("category") or models.KATEGORIE_OHNE for v in self.liste(typ)})

    # -------------------------------------------------------------- Schreiben
    def speichern(self, vorlage, ebene="benutzer"):
        """Neue oder geänderte Vorlage speichern → gespeicherte Fassung. Prüft vorher."""
        typ = vorlage.get("typ")
        if typ not in TYPEN:
            raise VorlagenSpeicherFehler("Unbekannter Vorlagentyp.")
        if ebene == "system":
            raise VorlagenSpeicherFehler("Systemvorlagen sind schreibgeschützt.")
        if (vorlage.get("schemaVersion") or 0) > SCHEMA[typ]:
            raise VorlagenSpeicherFehler("Diese Vorlage stammt aus einer neueren Programmversion und wird nicht verändert.")
        if typ == "kantenvorlage":
            fehler, _ = pruefe_kantenvorlage(vorlage)
        else:
            from ..details.detail_validation import pruefe_detailvorlage
            fehler, _ = pruefe_detailvorlage(vorlage)
        if fehler:
            raise VorlagenSpeicherFehler("Vorlage nicht gespeichert:\n" + "\n".join(fehler))
        v = kopie(vorlage)
        for k in ("_ebene", "_datei", "_nurLesen", "_fehler"):
            v.pop(k, None)
        if not v.get("id"):
            v["id"] = neue_id("kv" if typ == "kantenvorlage" else "dv")
        pfad = self._datei(typ, v["id"], ebene)
        alt = json_store.lesen(pfad)
        if alt is not None:
            if (alt.get("schemaVersion") or 0) > SCHEMA[typ]:
                raise VorlagenSpeicherFehler("Die gespeicherte Fassung stammt aus einer neueren Programmversion und wird nicht überschrieben.")
            if _vergleichbar(alt) != _vergleichbar(v):
                self._version_ablegen(alt)
                v["version"] = int(alt.get("version") or 1) + 1
            else:
                v["version"] = alt.get("version") or 1
            v["created"] = alt.get("created") or v.get("created")
        else:
            v["version"] = int(v.get("version") or 1)
        v["modified"] = jetzt()
        v["schemaVersion"] = SCHEMA[typ]
        json_store.schreiben(pfad, v)
        return v

    def _version_ablegen(self, alt):
        ordner = os.path.join(paths.unterordner("versionen", self.wurzel), json_store.dateiname_sicher(alt["id"]))
        json_store.schreiben(os.path.join(ordner, "v%s.json" % (alt.get("version") or 1)), alt)

    def versionen(self, vid):
        ordner = os.path.join(paths.unterordner("versionen", self.wurzel), json_store.dateiname_sicher(vid))
        if not os.path.isdir(ordner):
            return []
        out = [json_store.lesen(os.path.join(ordner, n)) for n in os.listdir(ordner) if n.endswith(".json")]
        return sorted(out, key=lambda v: v.get("version") or 0)

    def duplizieren(self, vid, typ="kantenvorlage", neuer_name=None):
        """Kopie mit neuer ID und Version 1 – das Original bleibt unverändert."""
        quelle = self.holen(vid, typ)
        v = kopie(quelle)
        for k in ("_ebene", "_datei", "_nurLesen"):
            v.pop(k, None)
        v["id"] = neue_id("kv" if typ == "kantenvorlage" else "dv")
        v["name"] = neuer_name or ("Kopie von " + quelle.get("name", ""))
        v["version"] = 1
        v["created"] = jetzt()
        v.setdefault("metadata", {})["copiedFrom"] = {"id": quelle["id"], "version": quelle.get("version")}
        if typ == "detailvorlage" and (quelle.get("source") or {}).get("file"):
            v["source"]["file"] = self._geometrie_kopieren(quelle["source"]["file"], v["id"], 1)
        if (v.get("schemaVersion") or 0) > SCHEMA[typ]:
            raise VorlagenSpeicherFehler("Vorlagen aus einer neueren Programmversion können nicht kopiert werden.")
        return self.speichern(v)

    def umbenennen(self, vid, name, typ="kantenvorlage"):
        if not (name or "").strip():
            raise VorlagenSpeicherFehler("Der neue Name ist leer.")
        v = self._eigene(vid, typ)
        v["name"] = name.strip()
        return self.speichern(v, v.get("_ebene", "benutzer"))

    def favorit(self, vid, an=True, typ="kantenvorlage"):
        v = self._eigene(vid, typ)
        v["favorite"] = bool(an)
        return self.speichern(v, v.get("_ebene", "benutzer"))

    def kategorie(self, vid, kategorie, typ="kantenvorlage"):
        v = self._eigene(vid, typ)
        v["category"] = (kategorie or "").strip() or models.KATEGORIE_OHNE
        return self.speichern(v, v.get("_ebene", "benutzer"))

    def _eigene(self, vid, typ):
        v = self.holen(vid, typ)
        if v.get("_nurLesen"):
            raise VorlagenSpeicherFehler("Diese Vorlage ist schreibgeschützt (Systemvorlage oder neuere Programmversion).")
        return v

    def loeschen(self, vid, typ="kantenvorlage", bestaetigt=False):
        """Nur mit bestaetigt=True. Die Datei wandert in den Papierkorb (wiederherstellbar)."""
        if not bestaetigt:
            raise VorlagenSpeicherFehler("Löschen braucht eine ausdrückliche Bestätigung.")
        v = self._eigene(vid, typ)
        ziel = os.path.join(paths.unterordner("papierkorb", self.wurzel), "%s_%s.json" % (json_store.dateiname_sicher(vid), jetzt().replace(":", "-")))
        shutil.move(v["_datei"], ziel)
        return ziel

    def papierkorb(self):
        ordner = paths.unterordner("papierkorb", self.wurzel)
        return [os.path.join(ordner, n) for n in sorted(os.listdir(ordner)) if n.endswith(".json")]

    def wiederherstellen(self, papierkorb_datei):
        v = json_store.lesen(papierkorb_datei)
        ziel = self._datei(v["typ"], v["id"])
        if os.path.exists(ziel):
            raise VorlagenSpeicherFehler("Eine Vorlage mit derselben ID existiert bereits.")
        shutil.move(papierkorb_datei, ziel)
        return v

    # -------------------------------------------------------------- 3D-Geometrie
    def geometrie_pfad(self, relativ):
        return os.path.join(paths.unterordner("details", self.wurzel), relativ)

    def geometrie_ablegen(self, quelldatei, vid, version):
        ziel_rel = os.path.join("geometrie", "%s_v%s.f3d" % (json_store.dateiname_sicher(vid), version))
        ziel = self.geometrie_pfad(ziel_rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        shutil.copyfile(quelldatei, ziel)
        return ziel_rel.replace(os.sep, "/")

    def _geometrie_kopieren(self, rel, neue_id_, version):
        q = self.geometrie_pfad(rel)
        if not os.path.exists(q):
            return rel
        return self.geometrie_ablegen(q, neue_id_, version)

    # -------------------------------------------------------------- Import / Export
    def exportieren(self, ids, ziel_datei):
        """Dokumentiertes Austauschformat (JSON): {schemaVersion, typ:'bibliothek_export', vorlagen:[…], geometrie:{datei: base64}}."""
        alle = {v["id"]: v for t in TYPEN for v in self.liste(t)}
        paket = {"schemaVersion": SCHEMA["bibliothek_export"], "typ": "bibliothek_export", "exportiert": jetzt(),
                 "vorlagen": [], "geometrie": {}}
        for vid in ids:
            if vid not in alle:
                raise VorlagenSpeicherFehler("Vorlage %s nicht gefunden." % vid)
            v = kopie(alle[vid])
            for k in ("_ebene", "_datei", "_nurLesen"):
                v.pop(k, None)
            paket["vorlagen"].append(v)
            rel = (v.get("source") or {}).get("file") if v["typ"] == "detailvorlage" else None
            if rel and os.path.exists(self.geometrie_pfad(rel)):
                with open(self.geometrie_pfad(rel), "rb") as f:
                    paket["geometrie"][rel] = base64.b64encode(f.read()).decode("ascii")
        json_store.schreiben(ziel_datei, paket)
        return len(paket["vorlagen"])

    def importieren(self, datei, ueberschreiben=False):
        """→ {'importiert': [...], 'kopien': [...], 'abgelehnt': [(name, grund)]}. Bestehende Vorlagen werden
        ohne ueberschreiben=True nie ersetzt: gleiche ID → Import als Kopie mit neuer ID."""
        paket = json_store.lesen(datei)
        if not isinstance(paket, dict) or paket.get("typ") != "bibliothek_export":
            raise VorlagenSpeicherFehler("Die Datei ist kein Spengler-Vorlagenexport.")
        if (paket.get("schemaVersion") or 0) > SCHEMA["bibliothek_export"]:
            raise VorlagenSpeicherFehler("Der Export stammt aus einer neueren Programmversion. Bitte das Add-in aktualisieren.")
        from .migration_service import migriere_datensatz, MigrationsFehler
        ergebnis = {"importiert": [], "kopien": [], "abgelehnt": []}
        vorhandene = {v["id"] for t in TYPEN for v in self.liste(t)}
        for v in paket.get("vorlagen", []):
            name = v.get("name", "?")
            try:
                v = migriere_datensatz(v)
            except MigrationsFehler as e:
                ergebnis["abgelehnt"].append((name, str(e)))
                continue
            if v.get("typ") not in TYPEN:
                ergebnis["abgelehnt"].append((name, "unbekannter Typ"))
                continue
            kopie_noetig = v.get("id") in vorhandene and not ueberschreiben
            if kopie_noetig:
                v.setdefault("metadata", {})["importedAsCopyOf"] = v["id"]
                v["id"] = neue_id("kv" if v["typ"] == "kantenvorlage" else "dv")
                v["version"] = 1
            rel = (v.get("source") or {}).get("file")
            if rel and rel in paket.get("geometrie", {}):
                ziel_rel = os.path.join("geometrie", "%s_v%s.f3d" % (json_store.dateiname_sicher(v["id"]), v.get("version") or 1))
                ziel = self.geometrie_pfad(ziel_rel)
                os.makedirs(os.path.dirname(ziel), exist_ok=True)
                with open(ziel, "wb") as f:
                    f.write(base64.b64decode(paket["geometrie"][rel]))
                v["source"]["file"] = ziel_rel.replace(os.sep, "/")
            try:
                gesp = self.speichern(v)
            except VorlagenSpeicherFehler as e:
                ergebnis["abgelehnt"].append((name, str(e)))
                continue
            (ergebnis["kopien"] if kopie_noetig else ergebnis["importiert"]).append(gesp["id"])
        return ergebnis

"""Datenmigration beim Start.

Ablauf:
 1. Alle Datensätze lesen und nötige Migrationen bestimmen.
 2. Datensätze mit NEUERER schemaVersion (aus einer späteren Programmversion) bleiben unberührt.
 3. Vor jeder Migration: automatische Vollsicherung.
 4. Migration auf Kopien rechnen und jeden Datensatz prüfen (Typ, ID, Felder vollständig, Prüfung bestanden).
 5. Nur wenn ALLES gelingt, werden die Dateien (atomar) ersetzt. Sonst bleibt alles wie es war und
    der Fehler samt Sicherungspfad wird gemeldet.
 6. Als «kritisch» markierte Migrationen laufen erst nach Bestätigung durch den Benutzer.

Migrationen werden je Typ registriert: MIGRATIONEN[typ][von] = (funktion, kritisch).
Version 0 = Datensatz ohne schemaVersion (z. B. von Hand erstellt oder aus einer Vorversion importiert).
"""
import os

from ..core.models import SCHEMA, kopie, neue_id, neues_materialprofil, neue_detailvorlage, neue_kantenvorlage, standard_einstellungen
from . import backup_service, json_store, paths


class MigrationsFehler(RuntimeError):
    pass


def _ergaenze(d, vorlage):
    """Fehlende Felder aus der aktuellen Struktur ergänzen, vorhandene (auch unbekannte) unverändert lassen."""
    for k, v in vorlage.items():
        if k not in d:
            d[k] = kopie(v)
        elif isinstance(v, dict) and isinstance(d[k], dict):
            _ergaenze(d[k], v)
    return d


def _v0_kantenvorlage(d):
    neu = neue_kantenvorlage(d.get("name") or "Ohne Namen")
    neu.pop("id")
    d = _ergaenze(d, neu)
    d.setdefault("id", neue_id("kv"))
    d["schemaVersion"] = 1
    return d


def _v0_detailvorlage(d):
    neu = neue_detailvorlage(d.get("name") or "Ohne Namen")
    neu.pop("id")
    d = _ergaenze(d, neu)
    d.setdefault("id", neue_id("dv"))
    d["schemaVersion"] = 1
    return d


def _v0_material(d):
    neu = neues_materialprofil(d.get("name") or "Ohne Namen", d.get("thickness") or 0)
    neu.pop("id")
    d = _ergaenze(d, neu)
    d.setdefault("id", neue_id("mat"))
    d["schemaVersion"] = 1
    return d


def _v0_einstellungen(d):
    d = _ergaenze(d, standard_einstellungen())
    d["schemaVersion"] = 1
    return d


MIGRATIONEN = {
    "kantenvorlage": {0: (_v0_kantenvorlage, False)},
    "detailvorlage": {0: (_v0_detailvorlage, False)},
    "materialprofil": {0: (_v0_material, False)},
    "einstellungen": {0: (_v0_einstellungen, False)},
}


def migriere_datensatz(d, ziel=None):
    """Einen Datensatz bis zur aktuellen (oder ziel-)Version migrieren. Wirft MigrationsFehler."""
    typ = d.get("typ")
    if typ not in SCHEMA:
        raise MigrationsFehler("Unbekannter Datentyp %r" % typ)
    ziel = SCHEMA[typ] if ziel is None else ziel
    v = d.get("schemaVersion") or 0
    if v > SCHEMA[typ]:
        raise MigrationsFehler("Datensatz «%s» stammt aus einer neueren Programmversion (Format %s)." % (d.get("name", d.get("id")), v))
    d = kopie(d)
    while v < ziel:
        if v not in MIGRATIONEN.get(typ, {}):
            raise MigrationsFehler("Keine Migration für %s von Format %s." % (typ, v))
        d = MIGRATIONEN[typ][v][0](d)
        neu = d.get("schemaVersion")
        if neu != v + 1:
            raise MigrationsFehler("Migration %s %s→%s setzte falsche Version %s." % (typ, v, v + 1, neu))
        v = neu
    return d


def _pruefe(alt, neu):
    """Nach der Migration darf nichts fehlen: gleiche ID/Typ, alle alten Schlüssel noch da, Prüfung bestanden."""
    if neu.get("typ") != alt.get("typ"):
        return "Typ verändert"
    if alt.get("id") and neu.get("id") != alt.get("id"):
        return "ID verändert"
    fehlend = [k for k in alt if k not in neu and k != "schemaVersion"]
    if fehlend:
        return "Felder verloren: %s" % ", ".join(fehlend)
    typ = neu["typ"]
    if typ == "kantenvorlage":
        from ..core.validation import pruefe_kantenvorlage
        f, _ = pruefe_kantenvorlage(neu)
        if f and alt.get("operations"):
            return "; ".join(f)
    if typ == "materialprofil":
        from .material_library import pruefe_material
        f = pruefe_material(neu)
        if f:
            return "; ".join(f)
    return None


def _alle_dateien(wurzel):
    out = [os.path.join(wurzel, "einstellungen.json")]
    for name in ("kanten", "details", "materialien"):
        o = os.path.join(wurzel, paths.UNTERORDNER[name])
        if os.path.isdir(o):
            out += [os.path.join(o, n) for n in sorted(os.listdir(o)) if n.endswith(".json") and not n.startswith(".")]
    return [p for p in out if os.path.exists(p)]


def planen(wurzel=None):
    """→ {'noetig': [(pfad, typ, von, nach, kritisch)], 'neuer': [pfad], 'defekt': [(pfad, grund)]}"""
    wurzel = wurzel or paths.daten_ordner()
    plan = {"noetig": [], "neuer": [], "defekt": []}
    for p in _alle_dateien(wurzel):
        try:
            d = json_store.lesen(p)
        except json_store.DatenFehler as e:
            plan["defekt"].append((p, str(e)))
            continue
        typ = d.get("typ") if isinstance(d, dict) else None
        if typ not in SCHEMA:
            plan["defekt"].append((p, "unbekannter Typ"))
            continue
        v = d.get("schemaVersion") or 0
        if v > SCHEMA[typ]:
            plan["neuer"].append(p)
        elif v < SCHEMA[typ]:
            krit = any(MIGRATIONEN.get(typ, {}).get(x, (None, False))[1] for x in range(v, SCHEMA[typ]))
            plan["noetig"].append((p, typ, v, SCHEMA[typ], krit))
    return plan


def ausfuehren(wurzel=None, bestaetigt=False, addin_version=""):
    """Migration ausführen. → Bericht-dict. Wirft nie bei Datenfehlern – meldet sie im Bericht."""
    wurzel = wurzel or paths.daten_ordner()
    plan = planen(wurzel)
    bericht = {"status": "nichts", "migriert": 0, "neuer": plan["neuer"], "defekt": plan["defekt"], "sicherung": None, "fehler": []}
    if not plan["noetig"]:
        _datenformat(wurzel, addin_version)
        return bericht
    if any(k for *_, k in plan["noetig"]) and not bestaetigt:
        bericht["status"] = "bestaetigung_noetig"
        return bericht
    bericht["sicherung"] = backup_service.sichern(wurzel, grund="vor_migration", addin_version=addin_version)
    neu = []
    for p, typ, von, nach, _ in plan["noetig"]:
        alt = json_store.lesen(p)
        try:
            m = migriere_datensatz(alt)
            grund = _pruefe(alt, m)
        except Exception as e:  # jede Ausnahme = Migration verworfen
            grund = str(e)
        if grund:
            bericht["fehler"].append("%s: %s" % (os.path.basename(p), grund))
        else:
            neu.append((p, m))
    if bericht["fehler"]:
        bericht["status"] = "fehlgeschlagen"   # nichts wurde geschrieben
        return bericht
    for p, m in neu:
        json_store.schreiben(p, m)
    bericht["status"] = "migriert"
    bericht["migriert"] = len(neu)
    _datenformat(wurzel, addin_version)
    return bericht


def _datenformat(wurzel, addin_version):
    p = os.path.join(wurzel, "datenformat.json")
    d = json_store.lesen(p, {}) or {}
    d.update({"typ": "datenformat", "schema": dict(SCHEMA), "zuletztGeoeffnetMit": addin_version})
    os.makedirs(wurzel, exist_ok=True)
    json_store.schreiben(p, d)

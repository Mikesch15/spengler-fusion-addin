"""Migration, Sicherung und Wiederherstellung – Datenverlust muss ausgeschlossen sein."""
import json
import os
import zipfile

from _basis import DatenTest, datei_inhalt
from spengler_cad.core.models import SCHEMA
from spengler_cad.storage import backup_service, json_store, migration_service as ms, paths
from spengler_cad.storage.material_library import MaterialBibliothek
from spengler_cad.storage.settings_service import Einstellungen
from spengler_cad.storage.template_repository import VorlagenRepository


def alte_daten(wurzel):
    """Ältere Datensätze (Format 0: ohne schemaVersion, unvollständig, mit eigenen Zusatzfeldern)."""
    k = os.path.join(wurzel, paths.UNTERORDNER["kanten"])
    m = os.path.join(wurzel, paths.UNTERORDNER["materialien"])
    os.makedirs(k)
    os.makedirs(m)
    v = {"typ": "kantenvorlage", "id": "kv-alt1", "name": "Alte Vorlage", "category": "Werkstatt A",
         "favorite": True, "version": 4,
         "parameters": [{"name": "H", "label": "Höhe", "unit": "mm", "default": 30, "min": 10, "max": 60}],
         "operations": [{"typ": "flansch", "winkel": 90, "laenge": "H", "radius": None},
                        {"typ": "umschlag", "winkel": 180, "laenge": 8, "radius": 1.5}],
         "eigenesFeld": {"notiz": "darf nicht verloren gehen"}}
    json_store.schreiben(os.path.join(k, "kv-alt1.json"), v)
    mat = {"typ": "materialprofil", "id": "mat-alt", "name": "Mein Blech", "thickness": 0.7, "density": 7.2,
           "sheets": [[1000, 2000]], "werkstattNotiz": "Charge 12"}
    json_store.schreiben(os.path.join(m, "mat-alt.json"), mat)
    json_store.schreiben(os.path.join(wurzel, "einstellungen.json"), {"typ": "einstellungen", "ui": {"mode": "experte"}, "eigen": 1})
    return v, mat


class MigrationTest(DatenTest):
    def test_migration_erhaelt_alle_daten(self):
        v, mat = alte_daten(self.ordner)
        bericht = ms.ausfuehren(addin_version="test")
        self.assertEqual(bericht["status"], "migriert", bericht)
        self.assertEqual(bericht["migriert"], 3)
        self.assertTrue(os.path.exists(bericht["sicherung"]))
        neu = VorlagenRepository().holen("kv-alt1")
        self.assertEqual(neu["schemaVersion"], SCHEMA["kantenvorlage"])
        for k in v:
            self.assertEqual(neu[k], v[k], "Feld %s verändert" % k)
        m = MaterialBibliothek().holen("mat-alt")
        for k in mat:
            self.assertEqual(m[k], mat[k])
        e = Einstellungen().laden()
        self.assertEqual(e["ui"]["mode"], "experte")
        self.assertEqual(e["eigen"], 1)
        # zweiter Lauf: nichts mehr zu tun, keine neue Sicherung
        self.assertEqual(ms.ausfuehren()["status"], "nichts")
        # Sicherung enthält den ALTEN Stand
        with zipfile.ZipFile(bericht["sicherung"]) as z:
            alt = json.loads(z.read("daten/vorlagen/kanten/kv-alt1.json"))
        self.assertNotIn("schemaVersion", alt)

    def test_fehlgeschlagene_migration_aendert_nichts(self):
        alte_daten(self.ordner)
        pfad = os.path.join(self.ordner, paths.UNTERORDNER["materialien"], "mat-alt.json")
        d = json_store.lesen(pfad)
        d["thickness"] = -1   # ungültig → Migration muss abgelehnt werden
        json_store.schreiben(pfad, d)
        vorher = {p: datei_inhalt(p, True) for p in ms._alle_dateien(self.ordner)}
        bericht = ms.ausfuehren()
        self.assertEqual(bericht["status"], "fehlgeschlagen")
        self.assertTrue(bericht["fehler"])
        for p, inhalt in vorher.items():
            self.assertEqual(datei_inhalt(p, True), inhalt, "Datei wurde trotz Fehler verändert: " + p)
        self.assertTrue(os.path.exists(bericht["sicherung"]))

    def test_kritische_migration_braucht_bestaetigung(self):
        alte_daten(self.ordner)
        alt = ms.MIGRATIONEN["kantenvorlage"][0]
        ms.MIGRATIONEN["kantenvorlage"][0] = (alt[0], True)
        try:
            self.assertEqual(ms.ausfuehren()["status"], "bestaetigung_noetig")
            self.assertNotIn("schemaVersion", json_store.lesen(os.path.join(self.ordner, paths.UNTERORDNER["kanten"], "kv-alt1.json")))
            self.assertEqual(ms.ausfuehren(bestaetigt=True)["status"], "migriert")
        finally:
            ms.MIGRATIONEN["kantenvorlage"][0] = alt

    def test_mehrstufige_migration_mit_testmigration(self):
        """Gerüst für künftige Formate: eine Test-Migration 1→2 läuft nach 0→1, Daten bleiben vollständig."""
        alte_daten(self.ordner)
        alt_schema = SCHEMA["kantenvorlage"]

        def v1_v2(d):
            d = dict(d)
            d["neuesFeld"] = "x"
            d["schemaVersion"] = 2
            return d
        SCHEMA["kantenvorlage"] = 2
        ms.MIGRATIONEN["kantenvorlage"][1] = (v1_v2, False)
        try:
            b = ms.ausfuehren()
            self.assertEqual(b["status"], "migriert")
            d = json_store.lesen(os.path.join(self.ordner, paths.UNTERORDNER["kanten"], "kv-alt1.json"))
            self.assertEqual((d["schemaVersion"], d["neuesFeld"], d["eigenesFeld"]["notiz"]), (2, "x", "darf nicht verloren gehen"))
        finally:
            SCHEMA["kantenvorlage"] = alt_schema
            del ms.MIGRATIONEN["kantenvorlage"][1]

    def test_neuere_daten_werden_nicht_angefasst(self):
        alte_daten(self.ordner)
        pfad = os.path.join(self.ordner, paths.UNTERORDNER["kanten"], "kv-alt1.json")
        d = json_store.lesen(pfad)
        d["schemaVersion"] = 99
        json_store.schreiben(pfad, d)
        vorher = datei_inhalt(pfad, True)
        b = ms.ausfuehren()
        self.assertIn(pfad, b["neuer"])
        self.assertEqual(datei_inhalt(pfad, True), vorher)

    def test_defekte_datei_wird_gemeldet_nicht_geloescht(self):
        k = paths.unterordner("kanten")
        with open(os.path.join(k, "kaputt.json"), "w") as f:
            f.write("{nicht json")
        b = ms.ausfuehren()
        self.assertEqual(len(b["defekt"]), 1)
        self.assertTrue(os.path.exists(os.path.join(k, "kaputt.json")))


class SicherungTest(DatenTest):
    def test_sichern_und_wiederherstellen(self):
        alte_daten(self.ordner)
        ms.ausfuehren()
        repo = VorlagenRepository()
        geo = os.path.join(self.ordner, "quelle.f3d")
        with open(geo, "wb") as f:
            f.write(b"\x00F3D-Testinhalt")
        rel = repo.geometrie_ablegen(geo, "dv-x", 1)
        z = backup_service.sichern(grund="manuell")
        kopf = backup_service.pruefen(z)
        self.assertIn("vorlagen/kanten/kv-alt1.json", kopf["dateien"])
        self.assertIn("vorlagen/details/" + rel, kopf["dateien"])
        # Daten verändern / löschen
        repo.loeschen("kv-alt1", bestaetigt=True)
        MaterialBibliothek().loeschen("mat-alt", bestaetigt=True)
        self.assertEqual(repo.liste(), [])
        vorher = backup_service.wiederherstellen(z, bestaetigt=True)
        self.assertTrue(os.path.exists(vorher))
        self.assertEqual(VorlagenRepository().holen("kv-alt1")["name"], "Alte Vorlage")
        self.assertEqual(MaterialBibliothek().holen("mat-alt")["name"], "Mein Blech")
        self.assertEqual(datei_inhalt(repo.geometrie_pfad(rel), True), b"\x00F3D-Testinhalt")

    def test_wiederherstellen_braucht_bestaetigung_und_gueltige_datei(self):
        z = backup_service.sichern()
        with self.assertRaises(backup_service.SicherungsFehler):
            backup_service.wiederherstellen(z)
        kaputt = os.path.join(self.ordner, "kaputt.zip")
        with zipfile.ZipFile(kaputt, "w") as zz:
            zz.writestr("sicherung.json", json.dumps({"typ": "spengler_sicherung", "dateien": {"einstellungen.json": "falsch"}}))
            zz.writestr("daten/einstellungen.json", "{}")
        with self.assertRaises(backup_service.SicherungsFehler):
            backup_service.wiederherstellen(kaputt, bestaetigt=True)

    def test_aufraeumen_behaelt_manuelle(self):
        for i in range(3):
            backup_service.sichern(grund="auto%d" % i)
        m = backup_service.sichern(grund="manuell")
        backup_service.automatische_aufraeumen(behalten=1)
        rest = backup_service.liste()
        self.assertIn(m, rest)
        self.assertEqual(len(rest), 2)

    def test_daten_nicht_im_addin_ordner(self):
        os.environ["SPENGLER_CAD_DATEN"] = os.path.join(paths.ADDIN_ORDNER, "daten")
        with self.assertRaises(paths.PfadFehler):
            paths.daten_ordner()
if __name__ == "__main__":
    import unittest
    unittest.main()

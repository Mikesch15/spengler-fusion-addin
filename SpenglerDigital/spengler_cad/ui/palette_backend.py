"""Logik der Palette «Vorlagen & Einstellungen» – ohne Fusion, vollständig testbar.

Die HTML-Palette schickt (aktion, json) an Fusion; commands/palette_command.py ruft behandle() auf und
gibt die Antwort als JSON zurück: {"ok": true, "daten": …} oder {"ok": false, "fehler": "…"}.
"""
import json
import os

from .. import VERSION
from ..core import models, operation_plan, short_syntax, template_engine
from ..core.bend_geometry import ProfilFehler, zugabe_abwicklung
from ..manufacturing import drawing
from ..storage import backup_service, paths
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..storage.template_repository import VorlagenRepository
from . import help_content


AENDERNDE_AKTIONEN = {"speichern", "duplizieren", "umbenennen", "favorit", "kategorie", "loeschen", "papierkorb_zurueck",
                      "import", "material_speichern", "material_loeschen"}   # nach «wiederherstellen» bewusst kein Auto-Abgleich


def json_store_lesen(p):
    from ..storage import json_store
    try:
        return json_store.lesen(p)
    except Exception:
        return None


def _ohne_intern(v):
    return {k: x for k, x in v.items() if k not in ("_datei",)}


AENDERUNGEN = {"speichern": "gespeichert", "duplizieren": "dupliziert", "umbenennen": "umbenannt", "loeschen": "gelöscht",
               "papierkorb_zurueck": "wiederhergestellt", "import": "importiert", "material_speichern": "Material gespeichert",
               "material_loeschen": "Material gelöscht", "favorit": "Favorit geändert", "kategorie": "Kategorie geändert"}


class Backend(object):
    def __init__(self, wurzel=None, timeout=15):
        self.wurzel = wurzel
        self.timeout = timeout

    @property
    def repo(self):
        e = Einstellungen(self.wurzel).laden()
        return VorlagenRepository(self.wurzel, projekt_ordner=e.get("projectLibraryFolder") or None)

    def _standardmaterial(self, e, mid=None):
        mats = MaterialBibliothek(self.wurzel).liste()
        return next((m for m in mats if m["id"] == (mid or e.get("defaultMaterialId"))), None)

    def _mit_vorschau(self, v, material):
        v = _ohne_intern(v)
        v["_vorschau"], v["_vorschauGrund"] = drawing.vorlagen_vorschau(v, material, 150, 100, 9)
        return v

    def zustand(self):
        e = Einstellungen(self.wurzel).laden()
        r = self.repo
        m = self._standardmaterial(e)
        return {"version": VERSION, "datenordner": self.wurzel or paths.daten_ordner(),
                "vorlagen": [self._mit_vorschau(v, m) for v in r.liste("kantenvorlage")],
                "details": [_ohne_intern(v) for v in r.liste("detailvorlage")],
                "kategorien": r.kategorien("kantenvorlage"),
                "materialien": MaterialBibliothek(self.wurzel).liste(),
                "einstellungen": e,
                "sicherungen": [os.path.basename(p) for p in backup_service.liste(self.wurzel)],
                "papierkorb": [os.path.basename(p) for p in r.papierkorb()]}

    # ------------------------------------------------------------------ Aktionen
    def a_init(self, d):
        return self.zustand()

    def a_hilfe(self, d):
        return help_content.text(d.get("thema", ""))

    def a_neue_vorlage(self, d):
        return models.neue_kantenvorlage(d.get("name") or "Neue Vorlage")

    def a_kurzschrift(self, d):
        """Kurzschrift → Operationen (für Expertenmodus) inkl. neu erkannter Parameter."""
        v = template_engine.vorlage_aus_kurzschrift("x", d["text"])
        return {"operations": v["operations"], "parameter": [p["name"] for p in v["parameters"]], "text": short_syntax.als_text(v["operations"])}

    def a_vorschau(self, d):
        """Querschnitt der Vorlage mit Standardwerten – mit gewähltem oder Standardmaterial, sonst als Skizze."""
        e = Einstellungen(self.wurzel).laden()
        m = self._standardmaterial(e, d.get("materialId"))
        svg, grund = drawing.vorlagen_vorschau(d["vorlage"], m)
        return {"svg": svg, "grund": grund, "material": m["name"] if m else None}

    def a_pruefen(self, d):
        from ..core.validation import pruefe_kantenvorlage
        f, w = pruefe_kantenvorlage(d["vorlage"])
        erg = {"fehler": f, "warnungen": w, "kurzschrift": short_syntax.als_text(d["vorlage"].get("operations") or []) if not f else ""}
        if not f and d.get("materialId"):
            m = MaterialBibliothek(self.wurzel).holen(d["materialId"])
            try:
                ops, w2 = template_engine.aufloesen(d["vorlage"], d.get("werte") or {}, m)
                erg["aufgeloest"] = short_syntax.als_text(ops)
                erg["warnungen"] += w2
                if m.get("innerRadius") is not None and m.get("kFactor") is not None:
                    erg["zugabe"] = zugabe_abwicklung(ops, m["thickness"], m["innerRadius"], m["kFactor"])[0]
            except (template_engine.VorlagenFehler, ProfilFehler) as e:
                erg["fehler"].append(str(e))
        return erg

    def a_speichern(self, d):
        return _ohne_intern(self.repo.speichern(d["vorlage"], d.get("ebene", "benutzer")))

    def a_duplizieren(self, d):
        return _ohne_intern(self.repo.duplizieren(d["id"], d.get("typ", "kantenvorlage"), d.get("name")))

    def a_umbenennen(self, d):
        return _ohne_intern(self.repo.umbenennen(d["id"], d["name"], d.get("typ", "kantenvorlage")))

    def a_favorit(self, d):
        return _ohne_intern(self.repo.favorit(d["id"], d.get("an", True), d.get("typ", "kantenvorlage")))

    def a_kategorie(self, d):
        return _ohne_intern(self.repo.kategorie(d["id"], d.get("kategorie"), d.get("typ", "kantenvorlage")))

    def a_loeschen(self, d):
        return self.repo.loeschen(d["id"], d.get("typ", "kantenvorlage"), bestaetigt=d.get("bestaetigt") is True)

    def a_versionen(self, d):
        return self.repo.versionen(d["id"])

    def a_papierkorb_zurueck(self, d):
        r = self.repo
        pfad = next(p for p in r.papierkorb() if os.path.basename(p) == d["datei"])
        return _ohne_intern(r.wiederherstellen(pfad))

    def a_export(self, d):
        return self.repo.exportieren(d["ids"], d["pfad"])

    def a_import(self, d):
        return self.repo.importieren(d["pfad"], ueberschreiben=d.get("ueberschreiben") is True)

    def a_material_neu(self, d):
        return models.neues_materialprofil(d.get("name") or "Neues Material", d.get("dicke") or 1.0)

    def a_k_faktor(self, d):
        """Probebiegung → K-Faktor (Dicke/Innenradius kommen aus dem Materialeditor)."""
        from ..core.bend_geometry import k_faktor_aus_probe
        z = lambda k: float(d[k]) if d.get(k) not in (None, "") else None
        return k_faktor_aus_probe(z("zuschnitt"), z("a"), z("b"), z("t"), z("ri"))

    def a_material_speichern(self, d):
        return MaterialBibliothek(self.wurzel).speichern(d["material"])

    def a_material_loeschen(self, d):
        return MaterialBibliothek(self.wurzel).loeschen(d["id"], bestaetigt=d.get("bestaetigt") is True)

    def a_etiketten_pruefen(self, d):
        from ..manufacturing.parts_list import etiketten_pruefen
        f, text = etiketten_pruefen(d["labels"])
        return {"fehler": f, "text": text}

    def a_einstellungen_speichern(self, d):
        return Einstellungen(self.wurzel).speichern(d["einstellungen"])

    def a_sicherung(self, d):
        return backup_service.sichern(self.wurzel, ziel=d.get("pfad"), grund="manuell", addin_version=VERSION)

    def a_wiederherstellen(self, d):
        pfad = d.get("pfad")
        if not pfad and d.get("datei"):
            pfad = os.path.join(paths.unterordner("sicherungen", self.wurzel or paths.daten_ordner()), os.path.basename(d["datei"]))
        return backup_service.wiederherstellen(pfad, self.wurzel, bestaetigt=d.get("bestaetigt") is True, addin_version=VERSION)

    def a_bauplan_test(self, d):
        """Trockenlauf ohne Fusion: wie würde der Bauplan an einer gedachten geraden Blechkante aussehen?"""
        m = MaterialBibliothek(self.wurzel).holen(d["materialId"]) if d.get("materialId") else None
        k = {"ref": None, "text": "Testkante", "kurve": "linie", "laenge": 1000.0, "flaechen": 2, "blech": True,
             "dicke": m.get("thickness") if m else None, "frei": True}
        return operation_plan.beschreibung(operation_plan.erstelle(d["vorlage"], d.get("werte") or {}, m, [k]))

    # ------------------------------------------------------------------ Tests (Register «Tests»)
    def _testdatei(self):
        return os.path.join(self.wurzel or paths.daten_ordner(), "testergebnisse.json")

    def _testergebnisse(self):
        return json_store_lesen(self._testdatei()) or {}

    def a_testplan(self, d):
        plan = json_store_lesen(os.path.join(paths.ADDIN_ORDNER, "palette", "testplan.json")) or {"bloecke": []}
        return {"plan": plan["bloecke"], "ergebnisse": self._testergebnisse()}

    def _hochladen(self, test_id, e):
        """→ (hochgeladen, Hinweis). Fehler (offline, nicht angemeldet) verlieren nichts: der Stand bleibt lokal «nicht gesendet»."""
        from ..storage.cloud_client import CloudFehler
        try:
            c = self._cloud()
            if not c.angemeldet:
                return False, "nur lokal gespeichert – für die Übermittlung an Claude unter «Konto» anmelden"
            c.test_speichern({"test_id": test_id, "text": e["text"][:1000], "status": e["status"], "notiz": e["notiz"],
                              "protokoll": e.get("protokoll", ""), "addin_version": e["addinVersion"], "fusion_version": e["fusionVersion"],
                              "geaendert_am": e["geaendert"]})
            return True, ""
        except CloudFehler as ex:
            return False, str(ex)

    def a_test_speichern(self, d):
        import datetime
        import re
        from ..diagnostics import logger
        from ..storage import json_store
        tid, status = str(d.get("test_id", "")), d.get("status")
        if not re.match(r"^[0-9]{1,2}\.[0-9]{1,3}$", tid) or status not in ("offen", "ok", "fehler", "uebersprungen"):
            raise ValueError("Ungültiger Testpunkt oder Status.")
        alle = self._testergebnisse()
        e = {"text": str(d.get("text", ""))[:1000], "status": status, "notiz": str(d.get("notiz", ""))[:4000],
             "geaendert": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "addinVersion": VERSION, "fusionVersion": logger.fusion_version(), "gesendet": False}
        if status == "fehler" or d.get("mit_protokoll"):
            e["protokoll"] = logger.ende()
        alle[tid] = e
        json_store.schreiben(self._testdatei(), alle)
        ok, hinweis = self._hochladen(tid, e)
        if ok:
            e["gesendet"] = True
            json_store.schreiben(self._testdatei(), alle)
        return {"ergebnis": e, "gesendet": ok, "hinweis": hinweis}

    def a_tests_senden(self, d):
        """Alle noch nicht übermittelten Stände hochladen (z. B. nach Anmeldung oder wieder mit Netz)."""
        from ..storage import json_store
        alle = self._testergebnisse()
        n, hinweis = 0, ""
        for tid, e in alle.items():
            if e.get("gesendet"):
                continue
            ok, hinweis = self._hochladen(tid, e)
            if not ok:
                break
            e["gesendet"] = True
            n += 1
        json_store.schreiben(self._testdatei(), alle)
        return {"gesendet": n, "offen": sum(1 for e in alle.values() if not e.get("gesendet")), "hinweis": hinweis, "ergebnisse": alle}

    # ------------------------------------------------------------------ Eingang
    # ------------------------------------------------------------------ Spengler-Digital-App
    def _cloud(self):
        from ..storage.cloud_client import Cloud
        return Cloud(self.wurzel or paths.daten_ordner(), timeout=self.timeout)

    def a_konto(self, d):
        c = self._cloud()
        b = json_store_lesen(os.path.join(self.wurzel or paths.daten_ordner(), "sync_bericht.json"))
        return {"angemeldet": c.angemeldet, "konto": c.konto, "letzterAbgleich": b}

    def a_anmelden(self, d):
        c = self._cloud()
        k = c.anmelden(d.get("benutzer", ""), d.get("passwort", ""))
        return {"konto": k, "abgleich": self.a_abgleichen({})}

    def a_abmelden(self, d):
        self._cloud().abmelden()
        return True

    def a_abgleichen(self, d):
        from ..storage import sync_service
        c = self._cloud()
        b = sync_service.Abgleich(c, self.wurzel).ausfuehren()
        b["text"] = sync_service.bericht_text(b)
        from ..storage import json_store
        json_store.schreiben(os.path.join(self.wurzel or paths.daten_ordner(), "sync_bericht.json"), b)
        return b

    def a_update_pruefen(self, d):
        from ..storage import updater
        r = updater.neuestes(self._cloud())
        return {"aktuell": VERSION, "neu": r["version"] if r else None, "hinweise": r.get("hinweise") if r else ""}

    def _auto_abgleich(self, aktion):
        """Nach jeder Änderung in der Palette still abgleichen, wenn angemeldet. Fehler stoppen die Aktion nicht."""
        if aktion not in AENDERNDE_AKTIONEN:
            return None
        try:
            if not self._cloud().angemeldet:
                return None
            b = self.a_abgleichen({})
            return {"ok": True, "text": b["text"], "nur_lokal": b["nur_lokal"], "konflikte": b["konflikte"]}
        except Exception as e:
            return {"ok": False, "text": str(e)}

    # ------------------------------------------------------------------ Änderungsprotokoll (wer hat wann was an Vorlagen/Material geändert)
    def _aenderungsdatei(self):
        return os.path.join(self.wurzel or paths.daten_ordner(), "aenderungen.json")

    def _aenderung_merken(self, aktion, d, erg):
        """Fehler beim Protokollieren verhindern nie die Aktion selbst. Gilt für diesen PC (kein Abgleich zwischen PCs)."""
        import datetime
        from ..storage import json_store
        try:
            e = erg if isinstance(erg, dict) else {}
            vorlage = d.get("vorlage") if isinstance(d.get("vorlage"), dict) else {}
            material = d.get("material") if isinstance(d.get("material"), dict) else {}
            name = vorlage.get("name") or material.get("name") or e.get("name") or d.get("name") or d.get("id") or d.get("pfad") or ""
            try:
                konto = self._cloud().konto
                benutzer = konto.get("name") or konto.get("benutzer") or konto.get("email") or "lokal"
            except Exception:
                benutzer = "lokal"
            liste = json_store.lesen(self._aenderungsdatei()) or []
            liste.append({"zeit": datetime.datetime.now().isoformat(timespec="seconds"), "benutzer": benutzer, "aktion": AENDERUNGEN[aktion],
                          "name": str(name)[:200], "version": e.get("version"), "id": e.get("id") or d.get("id")})
            json_store.schreiben(self._aenderungsdatei(), liste[-1000:])
        except Exception:
            from ..diagnostics import logger
            logger.ausnahme("Änderungsprotokoll")

    def a_aenderungen(self, d):
        from ..storage import json_store
        return list(reversed((json_store.lesen(self._aenderungsdatei()) or [])[-int(d.get("max") or 200):]))

    def a_fehlerberichte(self, d):
        """Automatisch übermittelte Fehlerberichte der eigenen Firma (neueste zuerst)."""
        c = self._cloud()
        if not c.angemeldet:
            raise RuntimeError("Für die Fehlerberichte zuerst unter «Konto» anmelden.")
        return c.fehlerberichte()

    def behandle(self, aktion, daten_json):
        try:
            d = json.loads(daten_json) if isinstance(daten_json, str) and daten_json else (daten_json or {})
            f = getattr(self, "a_" + aktion, None)
            if f is None:
                return json.dumps({"ok": False, "fehler": "Unbekannte Aktion %s" % aktion})
            erg = f(d)
            if aktion in AENDERUNGEN:
                self._aenderung_merken(aktion, d, erg)
            return json.dumps({"ok": True, "daten": erg, "abgleich": self._auto_abgleich(aktion)}, ensure_ascii=False, default=str)
        except Exception as e:  # jede Meldung verständlich zurück an die Palette
            from ..diagnostics import logger
            logger.ausnahme("Palette", aktion=aktion)
            return json.dumps({"ok": False, "fehler": str(e) or type(e).__name__}, ensure_ascii=False)

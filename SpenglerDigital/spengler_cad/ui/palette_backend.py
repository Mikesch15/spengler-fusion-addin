"""Logik der Palette «Vorlagen & Einstellungen» – ohne Fusion, vollständig testbar.

Die HTML-Palette schickt (aktion, json) an Fusion; commands/palette_command.py ruft behandle() auf und
gibt die Antwort als JSON zurück: {"ok": true, "daten": …} oder {"ok": false, "fehler": "…"}.
"""
import json
import os

from .. import VERSION
from ..core import bauteil, grundriss, lernen, models, operation_plan, projektaenderung, projektkarte, short_syntax, skizze, template_engine
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
               "material_loeschen": "Material gelöscht", "rest_speichern": "Rest gespeichert", "rest_loeschen": "Rest gelöscht", "favorit": "Favorit geändert", "kategorie": "Kategorie geändert"}


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

    def _bauteil_ansicht(self, v):
        v = _ohne_intern(v)
        v["_texte"] = bauteil.texte_der_vorlage(v)
        return v

    def zustand(self):
        e = Einstellungen(self.wurzel).laden()
        r = self.repo
        m = self._standardmaterial(e)
        return {"version": VERSION, "datenordner": self.wurzel or paths.daten_ordner(),
                "vorlagen": [self._mit_vorschau(v, m) for v in r.liste("kantenvorlage")],
                "details": [_ohne_intern(v) for v in r.liste("detailvorlage")],
                "bauteile": [self._bauteil_ansicht(v) for v in r.liste("bauteilvorlage")],
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

    def a_skizze_auswerten(self, d):
        """Handskizze → Schenkel/Winkel (eingerastet), Operationen, Kurzschrift, Zuschnitt. Entweder gezeichnete Punkte (mm) oder die Tabelle (schenkel + start)."""
        e = Einstellungen(self.wurzel).laden()
        m = self._standardmaterial(e, d.get("materialId"))
        if d.get("punkte"):
            schenkel, start = skizze.aus_punkten(d["punkte"], float(d.get("laengenraster") or 0), float(d.get("winkelraster") or 0))
        else:
            schenkel, start = [], float(d.get("start") or 0)
            for i, s in enumerate(d.get("schenkel") or []):
                try:
                    L, w = float(s["laenge"]), float(s.get("winkel") or 0)
                except (KeyError, TypeError, ValueError):
                    raise ValueError("Strich %d: Länge und Winkel müssen Zahlen sein." % (i + 1))
                if L <= 0:
                    raise ValueError("Strich %d: Die Länge muss grösser als 0 sein." % (i + 1))
                if abs(w) > 180:
                    raise ValueError("Strich %d: Der Winkel muss zwischen −180° und 180° liegen." % (i + 1))
                schenkel.append({"laenge": L, "winkel": 0.0 if i == 0 else w})
            if not schenkel:
                raise ValueError("Es ist noch kein Strich gezeichnet.")
        return skizze.auswerten(schenkel, start, m and m["thickness"], m and m.get("innerRadius"), m and m.get("kFactor"))

    def a_skizze_vorlage(self, d):
        """Handskizze → neue (noch nicht gespeicherte) Kantenvorlage zum Weiterbearbeiten im Editor."""
        ops, hinweise = skizze.operationen(d["schenkel"])
        if not ops:
            raise ValueError("Die Skizze braucht mindestens zwei Striche (der erste ist das bestehende Blech).")
        v, fehler, warn = lernen.vorlage_aus_schritten(d.get("name") or "", ops, d.get("kategorie") or "Skizze",
                                                       "Von Hand skizziert (Kurzschrift %s). Mass und Richtung bitte prüfen." % lernen.kurzschrift(ops))
        if v is None:
            raise ValueError("\n".join(fehler))
        return _ohne_intern(v)

    def a_neues_bauteil(self, d):
        v = models.neue_bauteilvorlage(d.get("name") or "Neues Bauteil")
        return self._bauteil_ansicht(v)

    def a_bauteil_erkennen(self, d):
        """Kurzschrift der vier Seiten + Breite → Operationen, Parameterliste (vorhandene Einstellungen der Parameter bleiben)."""
        v = d["vorlage"]
        v["seiten"] = bauteil.seiten_aus_texten(d.get("texte") or {})
        bauteil.parameter_abgleichen(v)
        return self._bauteil_ansicht(v)

    def a_bauteil_vorschau(self, d):
        """Draufsicht des Bandes + Querschnitt je Seite mit den Standardwerten der Vorlage (oder den übergebenen Werten)."""
        v = d["vorlage"]
        e = Einstellungen(self.wurzel).laden()
        m = self._standardmaterial(e, d.get("materialId"))
        mat = dict(m) if m else {"name": "Skizze", "thickness": 1.0, "innerRadius": 1.0, "kFactor": 0.5}
        mat.setdefault("innerRadius", mat["thickness"])
        if mat.get("innerRadius") is None:
            mat["innerRadius"] = mat["thickness"]
        if mat.get("kFactor") is None:
            mat["kFactor"] = 0.5
        fehlen = [p["name"] for p in v.get("parameters", []) if p.get("default") is None and p["name"] not in (d.get("eingaben") or {})]
        if fehlen:
            return {"grund": "Für die Vorschau braucht jeder Parameter einen Standardwert (fehlt: %s)." % ", ".join(fehlen)}
        links = d.get("seite", (v.get("verlauf") or {}).get("seite", "links")) != "rechts"
        try:
            p = bauteil.plan(v, d.get("eingaben") or {}, mat, d.get("verlauf") or (v.get("verlauf") or {}).get("beispiel") or "", d.get("laenge") or 1000.0,
                             links, bool(d.get("geschlossen")))
        except (template_engine.VorlagenFehler, grundriss.VerlaufFehler, short_syntax.KurzschriftFehler) as ex:
            return {"grund": str(ex)}
        quer = {}
        for s in models.SEITEN:
            ops = (v.get("seiten") or {}).get(s) or []
            if not ops:
                continue
            pseudo = models.neue_kantenvorlage(v.get("name") or "Bauteil", operations=ops, parameters=v.get("parameters", []))
            svg, grund = drawing.vorlagen_vorschau(pseudo, mat, 250, 170, 10)
            quer[s] = {"titel": models.SEITEN_TEXT[s], "svg": svg, "grund": grund}
        return {"grundriss": grundriss.svg(p["geometrie"]), "text": p["text"], "querschnitte": quer, "warnungen": p["warnungen"], "grund": None}

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

    def a_profilblatt(self, d):
        """Profilzeichnung mit Massen als HTML-Datei im Exportordner → Pfad (die Palette lässt sie dann von Fusion öffnen)."""
        import datetime
        from ..manufacturing import profilblatt
        from ..storage import json_store
        e = Einstellungen(self.wurzel).laden()
        m = self._standardmaterial(e, d.get("materialId"))
        text, grund = profilblatt.profilblatt_html(d["vorlage"], m, d.get("werte"), datum=datetime.date.today().isoformat(), version=VERSION)
        if text is None:
            raise ValueError("Profilzeichnung nicht möglich: %s" % grund)
        ordner = (e.get("export") or {}).get("folder") or paths.unterordner("export")
        os.makedirs(ordner, exist_ok=True)
        pfad = os.path.join(ordner, "Profil_%s.html" % json_store.dateiname_sicher(d["vorlage"].get("name") or "Vorlage"))
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(text)
        return {"pfad": pfad}

    # ------------------------------------------------------------------ Reststücke (lokal je PC, Felder wie `reststuecke` der App)
    def a_auftragsuebersicht(self, d):
        """Alle Aufträge mit Ordner (Fusion), Projekt (App), Fertigungsstatus und Teilen. Fusion-Ordner nur innerhalb von Fusion lesbar; ohne Konto fehlen App-Spalten."""
        from ..core import auftrag, uebersicht
        from ..storage.settings_service import Einstellungen
        e = Einstellungen(self.wurzel).laden()
        a = auftrag.pruefe_einstellung(e.get("auftrag"))
        ordner, hinweise = [], []
        try:
            from ..geometry import fusion_adapter as fa
            ordner = fa.auftraege_lesen(a["wurzelOrdner"])
        except Exception:
            hinweise.append("Auftragsordner in Fusion nicht lesbar.")
        projekte, status, teile = [], {}, []
        c = self._cloud()
        if c.angemeldet:
            for name, f, ziel in (("Projekte", c.projekte_lesen, "p"), ("Status", c.status_alle, "s"), ("Teile", c.teile_uebersicht, "t")):
                try:
                    r = f()
                    if ziel == "p":
                        projekte = r
                    elif ziel == "s":
                        status = r
                    else:
                        teile = r
                except Exception as ex:
                    hinweise.append("%s der App nicht lesbar: %s" % (name, ex))
        else:
            hinweise.append("Nicht angemeldet – nur Ordner in Fusion (Register Konto).")
        rows = uebersicht.zeilen(projekte, ordner, status, teile, (e.get("order") or {}).get("auftrag", ""))
        return {"zeilen": rows, "summe": uebersicht.zusammenfassung(rows), "hinweise": hinweise, "status": auftrag.STATUS}

    # ------------------------------------------------------------------ Projektkarte (alles zum Projekt, nur lesen)
    def _gesehen_datei(self):
        return os.path.join(self.wurzel or paths.daten_ordner(), "projekt_gesehen.json")

    def a_projekt_liste(self, d):
        """Projekte der App zum Auswählen + der aktive Auftrag (zuerst angezeigt)."""
        e = Einstellungen(self.wurzel).laden()
        c = self._cloud()
        if not c.angemeldet:
            raise ValueError("Für die Projektkarte zuerst anmelden (Register Konto).")
        zeilen = [p for p in c.projekte_lesen() if not p.get("archived") and p.get("order_no")]
        return {"aktiv": (e.get("order") or {}).get("auftrag", ""),
                "projekte": [{"nummer": str(p["order_no"]), "objekt": p.get("object") or p.get("name") or "", "kunde": p.get("customer") or ""} for p in zeilen]}

    def a_projekt_karte(self, d):
        """Alles zum Projekt der Auftragsnummer: Kopf, Massaufnahmen mit Werkstattstand, CAD-Teile, Rapporte, Termine, Dateien, Offerten, Leistungen – und was seit dem letzten Besuch neu ist."""
        from ..storage import json_store
        nummer = str(d.get("nummer") or "").strip()
        if not nummer:
            raise ValueError("Bitte ein Projekt wählen.")
        c = self._cloud()
        if not c.angemeldet:
            raise ValueError("Für die Projektkarte zuerst anmelden (Register Konto).")
        roh, hinweise = c.projekt_roh(nummer)
        if roh is None:
            raise ValueError("Zur Auftragsnummer %s gibt es in der App kein Projekt." % nummer)
        gesehen = json_store.lesen(self._gesehen_datei(), {}) or {}
        karte = projektkarte.karte(roh, projektkarte.namen(roh.get("personen")))
        karte["neu"] = projektkarte.neu_seit(roh, gesehen.get(nummer, ""))
        karte["hinweise"] = hinweise
        try:
            karte["kopf"]["fertigung"] = (c.status_alle().get(nummer) or {}).get("status", "")
        except Exception:
            karte["kopf"]["fertigung"] = ""
        if d.get("als_gesehen", True):
            import datetime
            gesehen[nummer] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
            json_store.schreiben(self._gesehen_datei(), gesehen)
        return karte

    # ------------------------------------------------------------------ Änderungen in der App (Rückfrage macht die Palette vor dem Aufruf)
    def a_projekt_status(self, d):
        """Projektstatus der App ändern (nur wenn er noch dem angezeigten Stand entspricht)."""
        projektaenderung.pruefe_status(d.get("neu"), d.get("alt"))
        r = self._cloud().projekt_status_setzen(d["id"], d["neu"], d["alt"])
        return {"status": projektaenderung.STATUS_TEXT.get(r.get("status"), r.get("status"))}

    def a_projekt_hinweis(self, d):
        """Hinweis des Projekts ersetzen («ersetzen», leer = löschen) oder um eine Zeile ergänzen («ergaenzen»)."""
        c = self._cloud()
        if d.get("modus") == "ergaenzen":
            wer = ((c.konto or {}).get("name") or (c.konto or {}).get("benutzer") or "").split("@")[0]
            text = projektaenderung.hinweis_ergaenzt(d.get("alt"), d.get("text"), None, wer)
        else:
            text = projektaenderung.hinweis_text(d.get("text"))
        r = c.projekt_hinweis_setzen(d["id"], text, d.get("updated_at"))
        return {"hinweis": r.get("hinweis") or ""}

    def a_termin_speichern(self, d):
        """Termin am Projekt anlegen (ohne id) oder ändern (mit id) – Eingaben nach den Regeln der App geprüft."""
        zeile = projektaenderung.termin_pruefen(d.get("termin") or {}, d["project_id"])
        c = self._cloud()
        if d.get("id"):
            if not isinstance(d.get("alt"), dict):
                raise ValueError("Der Termin kann nicht sicher geändert werden, weil die gelesenen Werte fehlen. Bitte die Projektkarte neu laden.")
            r = c.termin_aendern(d["id"], {k: v for k, v in zeile.items() if k != "project_id"}, d["alt"])
        else:
            r = c.termin_anlegen(zeile)
        return {"id": r.get("id"), "titel": r.get("titel")}

    def a_projekt_fotos(self, d):
        """Fotos/Skizzen einer Massaufnahme als Bilddaten (data-URL) für die Anzeige; höchstens 8, grosse Dateien werden übersprungen."""
        import base64
        c = self._cloud()
        out, fehler = [], []
        for pfad in (d.get("pfade") or [])[:8]:
            try:
                inhalt = c.foto_laden(pfad)
            except Exception as ex:
                fehler.append("%s: %s" % (os.path.basename(pfad), ex))
                continue
            if len(inhalt) > 3 * 1024 * 1024:
                fehler.append("%s: zu gross für die Anzeige (%.1f MB) – bitte «In Fusion einfügen» oder «Speichern» nutzen" % (os.path.basename(pfad), len(inhalt) / 1048576))
                continue
            ext = os.path.splitext(pfad)[1].lower()
            mime = {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")
            out.append({"pfad": pfad, "url": "data:%s;base64,%s" % (mime, base64.b64encode(inhalt).decode("ascii"))})
        return {"bilder": out, "fehler": fehler}

    def _app_datei_speichern(self, nummer, pfad, name=None):
        """Datei aus der App in den Exportordner (Unterordner «App-Dateien/<Auftrag>») laden → lokaler Pfad."""
        from ..storage import json_store
        e = Einstellungen(self.wurzel).laden()
        ordner = os.path.join((e.get("export") or {}).get("folder") or paths.unterordner("export"), "App-Dateien", json_store.dateiname_sicher(nummer or "projekt"))
        os.makedirs(ordner, exist_ok=True)
        ziel = os.path.join(ordner, json_store.dateiname_sicher(name or os.path.basename(pfad)))
        with open(ziel, "wb") as f:
            f.write(self._cloud().foto_laden(pfad))
        return ziel

    def a_projekt_datei(self, d):
        """Datei oder Foto der App speichern (und, unter Windows, öffnen) → Pfad."""
        ziel = self._app_datei_speichern(d.get("nummer"), d["pfad"], d.get("name"))
        geoeffnet = False
        if d.get("oeffnen", True) and hasattr(os, "startfile"):
            try:
                os.startfile(ziel)
                geoeffnet = True
            except Exception:
                pass
        return {"pfad": ziel, "geoeffnet": geoeffnet}

    def _referenzbild(self, pfad, titel):
        from ..geometry import fusion_adapter as fa
        return fa.referenzbild_einfuegen(pfad, titel)

    def a_projekt_foto_fusion(self, d):
        """Foto/Skizze der Massaufnahme als Referenzbild (Canvas) in das aktive Fusion-Dokument einfügen. Nicht live geprüft."""
        ziel = self._app_datei_speichern(d.get("nummer"), d["pfad"], d.get("name"))
        self._referenzbild(ziel, d.get("titel") or "Referenzbild")
        return {"pfad": ziel}

    def a_auftrag_status(self, d):
        from ..core import auftrag
        if d.get("status") not in dict(auftrag.STATUS):
            raise ValueError("Unbekannter Status.")
        c = self._cloud()
        if not c.angemeldet:
            raise ValueError("Zum Setzen des Status zuerst anmelden.")
        c.status_setzen(str(d["nummer"]), d["status"])
        return True

    def a_auftrag_aktiv(self, d):
        from ..storage.settings_service import Einstellungen
        s = Einstellungen(self.wurzel)
        e = s.laden()
        alt = e.get("order") or {}
        e["order"] = {"auftrag": str(d["nummer"]), "objekt": d.get("objekt") or "", "jahr": d.get("jahr")}
        if isinstance(e.get("ablagen"), dict):
            e["ablagen"]["aktiv"] = ""
        if alt.get("auftrag") == str(d["nummer"]) and alt.get("materialId"):
            e["order"]["materialId"] = alt["materialId"]
        s.speichern(e)
        return True

    def a_reste(self, d):
        from ..storage import reste
        return reste.liste(self.wurzel)

    def a_rest_speichern(self, d):
        from ..storage import reste
        try:
            return reste.speichern(d["rest"], self.wurzel)
        except reste.RestFehler as e:
            raise ValueError(str(e))

    def a_rest_loeschen(self, d):
        from ..storage import reste
        return reste.loeschen(d["id"], self.wurzel)

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
             "dicke": m.get("thickness") if m else None, "frei": True,
             "flaeche": "eben"}   # ausdrücklich gedachte EBENE Kante (Trockenlauf) – kein Rückfall
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
            self._aenderung_hochladen(liste[-1])
        except Exception:
            from ..diagnostics import logger
            logger.ausnahme("Änderungsprotokoll")

    def _aenderung_hochladen(self, e):
        """Eintrag auch in die gemeinsame Tabelle (alle PCs der Firma sehen ihn); offline/abgemeldet bleibt er lokal."""
        try:
            c = self._cloud()
            if c.angemeldet:
                c.aenderung_senden({"zeit": e["zeit"], "benutzer": str(e["benutzer"])[:200], "aktion": str(e["aktion"])[:80], "name": str(e["name"])[:200],
                                    "version": e["version"] if isinstance(e.get("version"), int) else None, "vorlage_id": str(e.get("id") or "")[:80]})
        except Exception:
            from ..diagnostics import logger
            logger.warnung("Änderungsprotokoll nicht an die App übermittelt")

    def a_aenderungen(self, d):
        """Angemeldet: gemeinsames Protokoll der Firma (alle PCs), sonst nur dieser PC."""
        from ..storage import json_store
        n = int(d.get("max") or 200)
        try:
            c = self._cloud()
            if c.angemeldet:
                return [dict(z, zeit=str(z["zeit"])) for z in c.aenderungen_lesen(n)]
        except Exception:
            from ..diagnostics import logger
            logger.warnung("Gemeinsames Änderungsprotokoll nicht lesbar – lokaler Stand")
        return list(reversed((json_store.lesen(self._aenderungsdatei()) or [])[-n:]))

    def a_protokoll_senden(self, d):
        """Protokollauszug (letzte Zeilen) mit einer Notiz als Bericht an die eigene Firma – wenn etwas nicht wie erwartet geht, aber keine Fehlermeldung kam."""
        import datetime
        import time
        from ..diagnostics import logger
        c = self._cloud()
        if not c.angemeldet:
            raise RuntimeError("Zum Senden zuerst unter «Konto» anmelden.")
        notiz = str(d.get("notiz", "")).strip()[:3000] or "(ohne Notiz)"
        c.test_speichern({"test_id": "98.%03d" % ((int(time.time()) // 600) % 1000), "text": ("Protokoll gesendet: " + notiz)[:1000], "status": "offen",
                          "notiz": notiz, "protokoll": logger.ende(zeilen=400, max_zeichen=19000), "addin_version": VERSION,
                          "fusion_version": logger.fusion_version(), "geaendert_am": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
        return {"gesendet": True}

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

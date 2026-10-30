"""Befehle «Abwicklung & DXF» und «Stückliste & Zuschnitt».

Abwicklung & DXF: je gewähltem Blechkörper die Fusion-Abwicklung verwenden (oder mit der gewählten
feststehenden Fläche erzeugen), Masse lesen, DXF mit dem Fusion-Exporter schreiben (Einzel- und
Sammelexport in einen Ordner) und optional ein Werkstattblatt (HTML) erstellen. Erfolg wird nur
gemeldet, wenn die Datei tatsächlich existiert.

Stückliste & Zuschnitt: Teilenummern, Stückliste, Etiketten; Abwicklungsmasse der gewählten Körper → Materialberechnung und Zuschnittplan
(Rechnung aus der App, siehe manufacturing/nesting.py) → Bericht, SVG, CSV, DXF.
"""
import datetime
import json
import os
import pathlib

import adsk.core
import adsk.fusion

from .. import VERSION
from ..diagnostics import logger
from ..core import auftrag
from ..geometry import fusion_adapter as fa
from ..manufacturing import bend_list, bestellung, dxf_lesen, dxf_writer, material_calculator, nesting, parts_list, pruefung, workshop_sheet
from ..storage import json_store, paths
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..ui import help_content
from . import base

BID_ABW = "spenglerAbwicklungDxf"
BID_ZUS = "spenglerMaterialZuschnitt"
Z = {}


def _exportordner(e, angaben=None):
    """Exportordner: mit eingestelltem lokalen Auftragsordner <Basis>/[Jahr]/<Nummer Objekt>/Export, sonst der allgemeine Exportordner."""
    o = None
    if angaben:
        try:
            o = auftrag.lokaler_exportpfad(e.get("auftrag"), angaben.get("auftrag"), angaben.get("objekt"), angaben.get("jahr") or e["order"].get("jahr"))
        except auftrag.AuftragsFehler:
            o = None
    o = o or (e.get("export") or {}).get("folder") or paths.unterordner("export")
    o = os.path.join(o, datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(o, exist_ok=True)
    return o


def _dateiname(e, bauteil, material, dicke):
    muster = (e.get("export") or {}).get("fileNamePattern") or "{bauteil}"
    try:
        n = muster.format(bauteil=bauteil, material=material or "", dicke=("%g" % dicke) if dicke else "")
    except (KeyError, IndexError, ValueError):
        n = bauteil
    return json_store.dateiname_sicher(n)


def _koerper(inp):
    sel = inp.itemById("koerper")
    out = []
    for i in range(sel.selectionCount):
        b = adsk.fusion.BRepBody.cast(sel.selection(i).entity)
        out.append(b.nativeObject or b)
    return out


def _quelle(body):
    """Vorlagen-Attribute der Features eines Körpers (falls mit dem Add-in erzeugt)."""
    try:
        for f in body.parentComponent.features:
            a = f.attributes.itemByName(fa.ATTR_GRUPPE, "quelle")
            if a:
                return json.loads(a.value)
    except Exception:
        pass
    return None


# ====================================================================== Abwicklung & DXF
def abw_erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    s = inp.addSelectionInput("koerper", "Blechkörper", "Ein oder mehrere Blechkörper")
    s.addSelectionFilter("SolidBodies")
    s.setSelectionLimits(1, 0)
    f = inp.addSelectionInput("flaeche", "Feststehende Fläche (falls noch keine Abwicklung)", "Nur bei einem Körper ohne Abwicklung nötig")
    f.addSelectionFilter("PlanarFaces")
    f.setSelectionLimits(0, 1)
    inp.addBoolValueInput("dxf", "DXF exportieren", True, "", True)
    inp.addBoolValueInput("blatt", "Werkstattblatt (HTML) erstellen", True, "", True)
    inp.addBoolValueInput("hilfe", "Hilfe", False, "", False)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged,
                 lambda a: a.input.id == "hilfe" and base.melden("Hilfe", help_content.text("abwicklung") + "\n\n" + help_content.text("zeichnung")))
    base.handler(adsk.core.CommandEventHandler, cmd.execute, abw_ausfuehren)


@base.sicher("Abwicklung & DXF")
def _abw(self, args):
    inp = args.command.commandInputs
    e = Einstellungen().laden()
    angaben = auftrag_angaben(e)
    ordner = _exportordner(e, angaben)
    mit_auftrag = bool((e.get("auftrag") or {}).get("teilnummerMitAuftrag", True))
    pruef = []
    fsel = inp.itemById("flaeche")
    flaeche = adsk.fusion.BRepFace.cast(fsel.selection(0).entity) if fsel.selectionCount else None
    if flaeche is not None:
        flaeche = flaeche.nativeObject or flaeche
    z, ok_n, sammel = [], 0, []
    mats = MaterialBibliothek().liste()
    koerper_liste = _koerper(inp)
    for nr, body in enumerate(koerper_liste, 1):
        comp = body.parentComponent
        name = body.name or comp.name
        try:
            if not fa.ist_blech(body):
                raise fa.AdapterFehler("kein Blechkörper")
            fp, neu = fa.abwicklung(comp, flaeche if flaeche is not None and flaeche.body == body else None)
            masse = fa.abwicklung_masse(fp)
            t = fa.blechdicke_mm(body)
            q = _quelle(body) or {}
            mat = (q.get("material") or {}).get("name") or next((m["name"] for m in mats if t and abs(m["thickness"] - t) < 0.005), "")
            nr = fa.teilnummer(body, True)
            nr_text = auftrag.teil_label(angaben["auftrag"], nr, mit_auftrag)
            pruef.append({"name": name, "nr": nr, "material": {"name": mat} if mat else None, "dicke": t, "abwicklung": True,
                          "operationen": q.get("operationen"), "ri": None})
            zeile = "Teil %s %s: Abwicklung %.1f × %.1f mm%s" % (nr_text, name, masse["breite"], masse["laenge"], " (neu erzeugt)" if neu else "")
            basis = "%s_%s" % (nr_text, _dateiname(e, name, mat, t))
            dxf_pfad = None
            if inp.itemById("dxf").value:
                dxf_pfad = fa.dxf_abwicklung(fp, os.path.join(ordner, basis + ".dxf"))
                zeile += ", DXF ✓"
                sammel.append(dxf_pfad)
            if inp.itemById("blatt").value:
                svg_abw, abw_hinweis = _abwicklung_zeichnen(fp, dxf_pfad)
                m = next((x for x in mats if x["id"] == (q.get("material") or {}).get("id")), None)
                logo = os.path.join(paths.ADDIN_ORDNER, "assets", "logo", "logo_256.png")
                html = workshop_sheet.erstelle({
                    "bauteil": name, "teilnummer": nr_text, "objekt": angaben["objekt"], "auftrag": angaben["auftrag"],
                    "material": mat or "nicht zugeordnet", "dicke": t, "vorlage": q.get("vorlageName") or "–",
                    "vorlagenVersion": q.get("vorlageVersion") or "–", "abwicklung": masse, "abwicklungSvg": svg_abw, "abwicklungHinweis": abw_hinweis,
                    "operationen": q.get("operationen"), "ri": (m or {}).get("innerRadius"), "k": (m or {}).get("kFactor"), "datum": datetime.date.today().isoformat(),
                    "addinVersion": VERSION, "logo": pathlib.Path(logo).as_uri() if os.path.exists(logo) else None,
                    "hinweise": ["Querschnitt/Biegeliste nur für Bauteile, die mit «Kanten bearbeiten» erzeugt wurden."] if not q else []})
                with open(os.path.join(ordner, basis + "_werkstattblatt.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                zeile += ", Werkstattblatt ✓"
            z.append("✓ " + zeile)
            ok_n += 1
        except fa.AdapterFehler as ex:
            z.append("✗ %s: %s" % (name, ex))
        except Exception as ex:
            logger.ausnahme("Abwicklung", koerper=name)
            z.append("✗ %s: Fusion meldet: %s" % (name, base.fehlertext(ex)))
    warn = pruefung.pruefe_teile(pruef, e.get("pruefung"))
    if warn:
        z.append("\nPrüfung:\n" + "\n".join("⚠ " + w for w in warn))
    z.append("\n%d von %d Körpern erfolgreich. Ordner:\n%s" % (ok_n, len(koerper_liste), ordner))
    base.melden("Abwicklung & DXF", "\n".join(z), ok_n == 0)
    if ok_n:
        try:
            base.oeffnen(ordner)
        except Exception:
            pass


def _abwicklung_zeichnen(fp, dxf_pfad):
    """Abwicklung für das Werkstattblatt als SVG aus der Fusion-DXF (vorhandene oder kurz erzeugte). → (svg, Hinweis)."""
    import shutil
    import tempfile
    tmp = None
    try:
        if dxf_pfad is None:
            tmp = tempfile.mkdtemp(prefix="spengler_abw_")
            dxf_pfad = fa.dxf_abwicklung(fp, os.path.join(tmp, "abwicklung.dxf"))
        svg, ignoriert = dxf_lesen.svg_aus_datei(dxf_pfad)
        if not svg:
            return None, "die DXF enthält keine lesbaren Linien/Bögen"
        return svg, ("%d Kurve(n) (Spline/Ellipse) nicht gezeichnet" % ignoriert if ignoriert else None)
    except Exception as ex:
        logger.ausnahme("Abwicklung zeichnen")
        return None, "Zeichnen nicht möglich (%s)" % base.fehlertext(ex)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def abw_ausfuehren(args):
    _abw(None, args)


# ====================================================================== Stückliste & Zuschnitt
def zus_erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    Z["mat"] = MaterialBibliothek().liste()
    s = inp.addSelectionInput("koerper", "Blechkörper", "Körper mit vorhandener Fusion-Abwicklung")
    s.addSelectionFilter("SolidBodies")
    s.setSelectionLimits(1, 0)
    md = inp.addDropDownCommandInput("material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle)
    for m in Z["mat"]:
        md.listItems.add("%s (%.2f mm)" % (m["name"], m["thickness"]), m["id"] == e.get("defaultMaterialId"))
    if Z["mat"] and md.selectedItem is None:
        md.listItems.item(0).isSelected = True
    inp.addIntegerSpinnerCommandInput("stueck", "Stück je Teil", 1, 10000, 1, 1)
    inp.addValueInput("fuge", "Schnittfuge", "mm", adsk.core.ValueInput.createByString("%s mm" % e["nesting"]["kerf"]))
    inp.addValueInput("rand", "Randabstand", "mm", adsk.core.ValueInput.createByString("%s mm" % e["nesting"]["margin"]))
    inp.addBoolValueInput("drehen", "Drehen erlaubt", True, "", bool(e["nesting"]["rotationAllowed"]))
    vorbelegt = auftrag_angaben(e)
    inp.addStringValueInput("objekt", "Objekt", vorbelegt["objekt"])
    inp.addStringValueInput("auftrag", "Auftrag Nr.", vorbelegt["auftrag"])
    inp.addBoolValueInput("nummern", "Teilenummern vergeben (fehlende)", True, "", True)
    inp.addBoolValueInput("liste", "Stückliste (CSV + HTML)", True, "", True)
    inp.addBoolValueInput("etiketten", "Etiketten (A4-Bogen, HTML)", True, "", True)
    inp.addBoolValueInput("zuschnitt", "Materialbedarf & Zuschnittplan", True, "", True)
    inp.addBoolValueInput("abkant", "Abkantliste für die Werkstatt (HTML)", True, "", True)
    inp.addBoolValueInput("bestell", "Bestellliste für den ganzen Auftrag (alle Dokumente)", True, "", False)
    inp.addBoolValueInput("hilfe", "Hilfe", False, "", False)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged,
                 lambda a: a.input.id == "hilfe" and base.melden("Hilfe", help_content.text("stueckliste") + "\n\n" + help_content.text("zuschnitt")))
    base.handler(adsk.core.CommandEventHandler, cmd.execute, zus_ausfuehren)


@base.sicher("Stückliste & Zuschnitt")
def _zus(self, args):
    from ..core import units
    inp = args.command.commandInputs
    objekt, auftrag_nr = inp.itemById("objekt").value.strip(), inp.itemById("auftrag").value.strip()
    if not Z["mat"]:
        raise fa.AdapterFehler("Kein Materialprofil vorhanden. Bitte unter «Vorlagen & Einstellungen → Materialien» anlegen.")
    m = Z["mat"][inp.itemById("material").selectedItem.index]
    stueck = inp.itemById("stueck").value
    teile, fehlt = [], []
    for body in _koerper(inp):
        fp = getattr(body.parentComponent, "flatPattern", None)
        if not fp:
            fehlt.append(body.name)
            continue
        masse = fa.abwicklung_masse(fp)
        nr = fa.teilnummer(body, inp.itemById("nummern").value)
        q = _quelle(body) or {}
        teile.append({"nr": nr if nr is not None else "", "name": body.name, "materialId": m["id"], "material": m, "flaeche": masse["flaeche"],
                      "breite": masse["breite"], "laenge": masse["laenge"], "stueck": stueck, "dicke": m.get("thickness"), "abwicklung": True,
                      "operationen": q.get("operationen"), "ri": m.get("innerRadius")})
    if not teile:
        raise fa.AdapterFehler("Keiner der gewählten Körper hat eine Abwicklung. Zuerst «Abwicklung & DXF» ausführen.")
    teile.sort(key=lambda t: (t["nr"] == "", t["nr"] if t["nr"] != "" else 0, t["name"]))
    e = Einstellungen().laden()
    try:   # Objekt/Auftrag für das nächste Mal merken – Fehler hier verhindern die Ausgabe nicht
        e["order"] = {"objekt": objekt, "auftrag": auftrag_nr, "jahr": auftrag_angaben(e).get("jahr")}
        Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Auftragsangaben nicht gespeichert")
    e["nesting"].update({"kerf": units.cm_zu_mm(inp.itemById("fuge").value), "margin": units.cm_zu_mm(inp.itemById("rand").value),
                         "rotationAllowed": inp.itemById("drehen").value})
    angaben = {"auftrag": auftrag_nr, "objekt": objekt, "jahr": auftrag_angaben(e).get("jahr")}
    ordner = _exportordner(e, angaben)
    mit_auftrag = bool((e.get("auftrag") or {}).get("teilnummerMitAuftrag", True))
    warn = pruefung.pruefe_teile(teile, e.get("pruefung"))
    for t in teile:      # Anzeige: «17642-01»; Sortierung und Speicherung bleiben bei der laufenden Nummer
        t["nr_zahl"], t["nr"] = t["nr"], auftrag.teil_label(auftrag_nr, t["nr"], mit_auftrag)
    text, dateien = "", []
    logo = os.path.join(paths.ADDIN_ORDNER, "assets", "logo", "logo_256.png")
    logo = pathlib.Path(logo).as_uri() if os.path.exists(logo) else None
    liste = parts_list.stueckliste(teile)
    if inp.itemById("liste").value:
        kopf = [["Objekt", objekt], ["Auftrag", auftrag_nr], ["Datum", datetime.date.today().isoformat()], []]
        with open(os.path.join(ordner, "stueckliste.csv"), "w", encoding="utf-8", newline="") as f:
            f.write(parts_list.stueckliste_csv(liste, kopf))
        with open(os.path.join(ordner, "stueckliste.html"), "w", encoding="utf-8") as f:
            f.write(parts_list.stueckliste_html(liste, objekt, auftrag_nr, datetime.date.today().isoformat(), logo, VERSION))
        dateien += ["stueckliste.csv", "stueckliste.html"]
    if inp.itemById("etiketten").value:
        seite, n = parts_list.etiketten_html(liste, e["labels"], objekt, auftrag_nr)
        with open(os.path.join(ordner, "etiketten.html"), "w", encoding="utf-8") as f:
            f.write(seite)
        dateien.append("etiketten.html (%d Etiketten)" % n)
    if inp.itemById("abkant").value:
        with open(os.path.join(ordner, "abkantliste.html"), "w", encoding="utf-8") as fh:
            fh.write(bend_list.abkantliste_html(teile, objekt, auftrag_nr, datetime.date.today().isoformat(), VERSION))
        dateien.append("abkantliste.html")
    try:    # Stand dieses Dokuments für die Bestellliste des Auftrags merken
        bestellung.teile_merken(auftrag_nr, fa.dokument_name(), teile)
    except Exception:
        logger.ausnahme("Teile für die Bestellliste nicht gespeichert")
    if inp.itemById("bestell").value:
        b = bestellung.bestellung(auftrag_nr, Z["mat"], e)
        with open(os.path.join(ordner, "bestellliste.txt"), "w", encoding="utf-8") as fh:
            fh.write(b["text"])
        dateien.append("bestellliste.txt (%d Dokument(e))" % len(b["dokumente"]))
    if warn:
        text += "Prüfung:\n" + "\n".join("⚠ " + w for w in warn) + "\n\n"
    text += "Teile: " + ", ".join("%s %s" % (t["nr"], t["name"]) for t in teile) + "\n"
    erg = material_calculator.berechne(teile, [m], e) if inp.itemById("zuschnitt").value else {"materialien": []}
    if erg["materialien"]:
        text += material_calculator.bericht_text(erg)
    x = erg["materialien"][0] if erg["materialien"] else {}
    if x.get("zuschnitt") and x["zuschnitt"]["bestes"]:
        best = x["zuschnitt"]["bestes"]
        blaetter = nesting.lage(best, e["nesting"]["kerf"], e["nesting"]["margin"])
        koll = nesting.kollisionen(blaetter, e["nesting"]["kerf"], e["nesting"]["margin"])
        if koll:
            text += "\nKOLLISIONEN:\n" + "\n".join(koll)
        with open(os.path.join(ordner, "zuschnittplan.svg"), "w", encoding="utf-8") as f:
            f.write(nesting.als_svg(blaetter))
        with open(os.path.join(ordner, "zuschnittplan.csv"), "w", encoding="utf-8") as f:
            f.write(nesting.als_csv(best))
        dxf_writer.zuschnittplan_dxf(blaetter, m["name"], e["export"]["layerContour"], e["export"]["layerText"]).speichern(os.path.join(ordner, "zuschnittplan.dxf"))
        dateien += ["zuschnittplan.svg/.csv/.dxf"]
    if fehlt:
        text += "\nOhne Abwicklung (nicht berechnet): " + ", ".join(fehlt)
    text += "\n\nAnnahme: Teile als umschliessendes Rechteck der Abwicklung; Rechnung der Spengler-Digital-App (ohne Rollenmischung)."
    with open(os.path.join(ordner, "bericht.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    base.melden("Stückliste & Zuschnitt", text + "\n\nErstellt: " + (", ".join(dateien) or "–") + ", bericht.txt\nOrdner: " + ordner)
    try:
        base.oeffnen(ordner)
    except Exception:
        pass


def zus_ausfuehren(args):
    _zus(None, args)


def auftrag_angaben(e):
    """Objekt/Auftrag: aus dem Ordner des aktiven Fusion-Dokuments («17642 Nägeligasse 1a, Bern»), sonst zuletzt verwendet."""
    try:
        z = auftrag.aus_pfad_voll(fa.dokument_ordnerpfad())
    except Exception:
        z = None
    if z:
        return {"auftrag": z[0], "objekt": z[1], "jahr": z[2], "quelle": "Fusion-Ordner"}
    return {"auftrag": e["order"].get("auftrag", ""), "objekt": e["order"].get("objekt", ""), "jahr": e["order"].get("jahr"), "quelle": "zuletzt verwendet"}


def registrieren():
    return [base.befehl_definieren(BID_ABW, "Abwicklung & DXF", "Fusion-Abwicklung, DXF-Export (einzeln/gesammelt) und Werkstattblatt.", abw_erstellt),
            base.befehl_definieren(BID_ZUS, "Stückliste & Zuschnitt", "Teilenummern, Stückliste, Etiketten, Materialbedarf, Gewicht (Schätzung) und Zuschnittplan aus den Abwicklungen.", zus_erstellt)]

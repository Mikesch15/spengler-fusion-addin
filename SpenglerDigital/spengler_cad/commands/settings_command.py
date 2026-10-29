"""Befehle «Vorlagen & Einstellungen» (HTML-Palette) und «Hilfe»."""
import json
import os

import adsk.core

from .. import VERSION
from ..diagnostics import fusion_capabilities, logger
from ..storage import paths
from ..ui import help_content
from ..ui.palette_backend import Backend
from . import base

BID_PALETTE = "spenglerVorlagenEinstellungen"
BID_HILFE = "spenglerHilfe"
PALETTE_ID = "spenglerPalette"
HTML = os.path.join(paths.ADDIN_ORDNER, "palette", "vorlagen.html")
BACKEND = Backend()


def _dialog_aktion(aktion, d):
    """Aktionen, die einen Fusion-Dialog brauchen (Dateiauswahl, Ja/Nein)."""
    if aktion == "frage":
        return base.frage("Bestätigung", d.get("text", ""))
    if aktion == "export_dialog":
        p = base.datei_dialog("Vorlagen exportieren", "Spengler-Vorlagen (*.json)", True, "spengler_vorlagen.json")
        return BACKEND.repo.exportieren(d["ids"], p) if p else None
    if aktion == "import_dialog":
        p = base.datei_dialog("Vorlagen importieren", "Spengler-Vorlagen (*.json)")
        return BACKEND.repo.importieren(p) if p else None
    if aktion == "sicherung_dialog":
        p = base.datei_dialog("Sicherung speichern", "Sicherung (*.zip)", True, "spengler_sicherung.zip")
        return json.loads(BACKEND.behandle("sicherung", {"pfad": p}))["daten"] if p else None
    if aktion == "wiederherstellen_dialog":
        p = base.datei_dialog("Sicherung wiederherstellen", "Sicherung (*.zip)")
        if not p or not base.frage("Wiederherstellen", "Aktuelle Vorlagen, Materialien und Einstellungen durch die Sicherung ersetzen?\n"
                                   "Der aktuelle Stand wird vorher automatisch gesichert."):
            return None
        a = json.loads(BACKEND.behandle("wiederherstellen", {"pfad": p, "bestaetigt": True}))
        if not a["ok"]:
            raise RuntimeError(a["fehler"])
        return a["daten"]
    if aktion == "update_installieren":
        return update_anbieten(nachfragen_wenn_aktuell=True)
    if aktion == "protokoll":
        base.oeffnen(logger.pfad())
        return True
    return KeyError


def update_anbieten(nachfragen_wenn_aktuell=False, timeout=15):
    """Neuere Version in der App? → nachfragen → installieren. Rückgabe: Text für die Palette."""
    from ..storage import updater
    from ..storage.cloud_client import Cloud
    c = Cloud(timeout=timeout)
    if not c.angemeldet:
        raise RuntimeError("Für Updates zuerst unter «Konto» mit dem App-Konto anmelden.")
    r = updater.neuestes(c)
    if not r:
        if nachfragen_wenn_aktuell:
            base.melden("Update", "Sie haben die neueste Version (%s)." % VERSION)
        return "Neueste Version (%s) installiert." % VERSION
    if not updater.benoetigt(r):
        base.melden("Update", "Version %s ist bereits installiert. Bitte das Add-in neu starten (Shift+S → Stoppen → Ausführen)." % r["version"])
        return "Version %s bereits installiert – Add-in neu starten." % r["version"]
    if not base.frage("Update", "Version %s ist verfügbar (installiert: %s).\n\n%s\n\nJetzt aktualisieren? Ihre Daten werden vorher gesichert."
                      % (r["version"], VERSION, r.get("hinweise") or "")):
        return "Update auf %s verschoben." % r["version"]
    ersetzt = updater.installieren(c, r)
    logger.info("Update installiert", von=VERSION, nach=r["version"], dateien=len(ersetzt))
    base.melden("Update", "Version %s ist installiert (%d Dateien).\n\nBitte das Add-in neu starten:\nShift+S → SpenglerDigital → Stoppen → Ausführen\n"
                "(oder Fusion neu starten)." % (r["version"], len(ersetzt)))
    return "Version %s installiert – bitte Add-in neu starten." % r["version"]


def beim_start():
    """Beim Add-in-Start: still abgleichen und nach Updates fragen (nur wenn angemeldet und eingeschaltet). Offline → nichts."""
    from ..storage.cloud_client import Cloud, CloudFehler
    from ..storage.settings_service import Einstellungen
    e = Einstellungen().laden().get("cloud", {})
    c = Cloud(timeout=6)
    if not c.angemeldet:
        return
    try:
        if e.get("syncOnStart", True):
            b = json.loads(Backend(timeout=6).behandle("abgleichen", {}))
            if b.get("ok") and (b["daten"].get("konflikte") or b["daten"].get("fehler")):
                base.melden("Abgleich mit der App", b["daten"]["text"])
        if e.get("updateCheckOnStart", True):
            update_anbieten(timeout=6)
    except CloudFehler as ex:
        logger.warnung("Start-Abgleich", fehler=ex)
    except Exception:
        logger.ausnahme("Start-Abgleich")


def html_ereignis(args):
    args = adsk.core.HTMLEventArgs.cast(args)
    aktion = args.action
    if aktion in ("response", ""):
        return
    try:
        d = json.loads(args.data) if args.data else {}
        r = _dialog_aktion(aktion, d)
        if r is KeyError:
            args.returnData = BACKEND.behandle(aktion, d)
        else:
            args.returnData = json.dumps({"ok": True, "daten": r}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.ausnahme("Palette-Dialog", aktion=aktion)
        args.returnData = json.dumps({"ok": False, "fehler": base.fehlertext(e)}, ensure_ascii=False)


def html_url(pfad=HTML):
    import pathlib
    return pathlib.Path(pfad).resolve().as_uri()


def palette_erstellt(args):
    ui = base.ui()
    pal = ui.palettes.itemById(PALETTE_ID)
    if pal is None:
        # Als file:-URL übergeben: mit einem Windows-Pfad (Backslashes) machte Fusion daraus file:///C:/%5CUsers… (Live-Test 29.10.2026)
        pal = ui.palettes.add(PALETTE_ID, "Spengler Digital CAD – Vorlagen & Einstellungen", html_url(), True, True, True, 760, 640, True)
        pal.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight
        base.handler(adsk.core.HTMLEventHandler, pal.incomingFromHTML, html_ereignis)
    else:
        try:
            if pal.htmlFileURL != html_url():
                pal.htmlFileURL = html_url()
        except Exception:
            logger.ausnahme("Palette-URL")
    pal.isVisible = True


def hilfe_erstellt(args):
    cmd = args.command
    inp = cmd.commandInputs
    dd = inp.addDropDownCommandInput("thema", "Thema", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (k, (titel, _)) in enumerate(help_content.HILFE.items()):
        dd.listItems.add(titel, i == 0)
    inp.addTextBoxCommandInput("text", "", "", 14, True)
    inp.addBoolValueInput("pdf", "Bedienungsanleitung öffnen", False, "", False)
    inp.addBoolValueInput("faehig", "Fusion-Fähigkeiten prüfen", False, "", False)
    inp.addBoolValueInput("selbsttest", "Selbsttest in neuem Dokument", False, "", False)
    keys = list(help_content.HILFE.keys())

    def zeigen(a):
        i = a.inputs if hasattr(a, "inputs") else inp
        if getattr(a, "input", None) is not None and a.input.id == "pdf":
            # HTML wird mit jedem Update mitgeliefert, die PDF nur mit dem Installations-ZIP
            for name in ("Benutzerhandbuch.html", "Benutzerhandbuch.pdf"):
                p = os.path.join(paths.ADDIN_ORDNER, "docs", name)
                if os.path.exists(p):
                    base.oeffnen(p)
                    break
            else:
                base.melden("Hilfe", "Bedienungsanleitung nicht gefunden.", True)
            return
        if getattr(a, "input", None) is not None and a.input.id == "faehig":
            f = fusion_capabilities.pruefen(adsk.core.Application.get())
            base.melden("Fusion-Fähigkeiten", "Add-in %s, Fusion %s\nGeladen aus: %s\n\n%s" % (VERSION, adsk.core.Application.get().version, paths.ADDIN_ORDNER, fusion_capabilities.text(f)))
            return
        if getattr(a, "input", None) is not None and a.input.id == "selbsttest":
            from ..diagnostics import selftest
            base.melden("Selbsttest", selftest.ausfuehren() + "\n\nProtokoll: " + logger.pfad())
            return
        k = keys[i.itemById("thema").selectedItem.index]
        i.itemById("text").text = help_content.text(k).replace("\n", "<br>")
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, zeigen)
    cmd.isOKButtonVisible = False
    inp.itemById("text").text = help_content.text(keys[0]).replace("\n", "<br>")


def registrieren():
    return [base.befehl_definieren(BID_PALETTE, "Vorlagen & Einstellungen", "Vorlagen erstellen/bearbeiten, Materialprofile, Einstellungen, Sicherung.", palette_erstellt),
            base.befehl_definieren(BID_HILFE, "Hilfe", "Hilfe, Bedienungsanleitung und Prüfung der Fusion-Fähigkeiten.", hilfe_erstellt)]


def aufraeumen():
    try:
        pal = base.ui().palettes.itemById(PALETTE_ID)
        if pal:
            pal.deleteMe()
    except Exception:
        pass

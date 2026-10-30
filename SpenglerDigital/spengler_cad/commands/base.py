"""Gemeinsame Bausteine für alle Fusion-Befehle: Definition, Handler am Leben halten, Fehlerbehandlung."""
import os
import traceback

import adsk.core
import adsk.fusion

from .. import VERSION
from ..diagnostics import logger
from ..storage import paths

HANDLER = []        # Fusion verlangt, dass Ereignis-Handler referenziert bleiben
ICONS = os.path.join(paths.ADDIN_ORDNER, "assets", "icons")


def ui():
    return adsk.core.Application.get().userInterface


FEHLERBERICHT_ID = "98.1"      # Testpunkt-Nummer für den letzten automatisch übermittelten Fehler (je Firma eine Zeile, wird überschrieben)


def fehlerbericht_senden(titel, text):
    """Meldung und Protokollauszug in die Ergebnistabelle der eigenen Firma (cad_testergebnisse) – nur wenn angemeldet; nie ein Fehler."""
    try:
        import datetime
        from ..storage.cloud_client import Cloud
        c = Cloud(paths.daten_ordner(), timeout=6)
        if not c.angemeldet:
            return False
        c.test_speichern({"test_id": FEHLERBERICHT_ID, "text": ("%s: %s" % (titel, text))[:1000], "status": "fehler", "notiz": text[:4000],
                          "protokoll": logger.ende(), "addin_version": VERSION, "fusion_version": logger.fusion_version(),
                          "geaendert_am": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
        return True
    except Exception:
        return False


def melden(titel, text, fehler=False):
    if fehler and fehlerbericht_senden(titel, text):
        text += "\n\n(Fehlerbericht mit Protokoll wurde an Spengler Digital übermittelt.)"
    try:
        ui().messageBox(text, "Spengler Digital CAD – " + titel, adsk.core.MessageBoxButtonTypes.OKButtonType,
                        adsk.core.MessageBoxIconTypes.CriticalIconType if fehler else adsk.core.MessageBoxIconTypes.InformationIconType)
    except Exception:
        pass


def frage(titel, text):
    r = ui().messageBox(text, "Spengler Digital CAD – " + titel, adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                        adsk.core.MessageBoxIconTypes.QuestionIconType)
    return r == adsk.core.DialogResults.DialogYes


def sicher(titel):
    """Dekorator für notify(): jede Ausnahme wird protokolliert und verständlich gemeldet – Fusion stürzt nicht ab."""
    def deko(f):
        def innen(self, args):
            try:
                return f(self, args)
            except Exception as e:
                logger.ausnahme(titel)
                melden(titel, "Das hat nicht geklappt:\n%s\n\nTechnische Details stehen im Protokoll:\n%s" % (
                    str(e) or type(e).__name__, logger.pfad()), True)
        return innen
    return deko


def handler(klasse, ereignis, funktion):
    """Kleiner Adapter: Fusion-Handlerklasse mit einer Funktion verbinden und registrieren."""
    class H(klasse):
        def __init__(self):
            super(H, self).__init__()

        def notify(self, args):
            funktion(args)
    h = H()
    ereignis.add(h)
    HANDLER.append(h)
    return h


def befehl_definieren(bid, name, tooltip, erstellt):
    """Button-Definition anlegen (alte gleiche ID vorher entfernen). erstellt(args) baut die Eingaben."""
    alt = ui().commandDefinitions.itemById(bid)
    if alt:
        alt.deleteMe()
    res = ICONS if os.path.isdir(ICONS) else ""
    cdef = ui().commandDefinitions.addButtonDefinition(bid, name, tooltip, res)
    handler(adsk.core.CommandCreatedEventHandler, cdef.commandCreated, erstellt)
    return cdef


def fehlertext(e):
    return str(e) or type(e).__name__


def trace():
    return traceback.format_exc()


def datei_dialog(titel, filter_text, speichern=False, dateiname=""):
    d = ui().createFileDialog()
    d.title = titel
    d.filter = filter_text
    if dateiname:
        d.initialFilename = dateiname
    r = d.showSave() if speichern else d.showOpen()
    return d.filename if r == adsk.core.DialogResults.DialogOK else None


def ordner_dialog(titel):
    d = ui().createFolderDialog()
    d.title = titel
    return d.folder if d.showDialog() == adsk.core.DialogResults.DialogOK else None


def oeffnen(pfad):
    """Datei/Ordner mit dem Standardprogramm des Systems öffnen."""
    import subprocess
    import sys
    if sys.platform.startswith("win"):
        os.startfile(pfad)  # noqa: S606 – nur lokale Benutzerdateien
    else:
        subprocess.Popen(["open", pfad])

# Spengler Digital CAD – Add-in für Autodesk Fusion
# Einstiegspunkt: Fusion ruft run() beim Start und stop() beim Beenden auf.
# Programmcode liegt im Paket spengler_cad/, Benutzerdaten IMMER ausserhalb dieses Ordners (siehe README.md).
import os
import sys
import traceback

import adsk.core

ORDNER = os.path.dirname(os.path.abspath(__file__))
if ORDNER not in sys.path:
    sys.path.insert(0, ORDNER)


def _alte_module_entfernen():
    """Fusion behält geladene Python-Module über Stoppen/Ausführen hinweg im Speicher. Ohne das hier liefe nach einem
    Update bis zum Neustart von Fusion weiter der ALTE Code (Live-Test 29.10.2026). Daten sind davon nicht betroffen."""
    for name in [m for m in sys.modules if m == "spengler_cad" or m.startswith("spengler_cad.")]:
        del sys.modules[name]


def _ui():
    return adsk.core.Application.get().userInterface


def _migration():
    """Benutzerdaten beim Start prüfen und bei Bedarf migrieren (mit automatischer Sicherung)."""
    from spengler_cad import VERSION
    from spengler_cad.storage import migration_service
    b = migration_service.ausfuehren(addin_version=VERSION)
    if b["status"] == "bestaetigung_noetig":
        r = _ui().messageBox("Die gespeicherten Vorlagen/Einstellungen müssen auf ein neues Datenformat umgestellt werden.\n"
                             "Vorher wird automatisch eine Sicherung erstellt. Jetzt umstellen?",
                             "Spengler Digital CAD – Datenumstellung", adsk.core.MessageBoxButtonTypes.YesNoButtonType)
        if r == adsk.core.DialogResults.DialogYes:
            b = migration_service.ausfuehren(bestaetigt=True, addin_version=VERSION)
    if b["status"] == "fehlgeschlagen":
        _ui().messageBox("Die Datenumstellung ist fehlgeschlagen. Ihre Daten wurden NICHT verändert.\n\n%s\n\nSicherung: %s"
                         % ("\n".join(b["fehler"]), b["sicherung"]), "Spengler Digital CAD")
    if b["neuer"]:
        _ui().messageBox("%d Datei(en) stammen aus einer neueren Add-in-Version und werden nur gelesen, nicht verändert.\n"
                         "Bitte das Add-in aktualisieren." % len(b["neuer"]), "Spengler Digital CAD")
    return b


def run(context):
    try:
        _alte_module_entfernen()
        from spengler_cad import VERSION
        from spengler_cad.diagnostics import logger
        from spengler_cad.commands import command_registry
        logger.setze_fusion_version(adsk.core.Application.get().version)
        try:
            m = _migration()
            logger.info("Start", migration=m["status"], migriert=m["migriert"])
        except Exception:
            logger.ausnahme("Migration beim Start")
            _ui().messageBox("Benutzerdaten konnten nicht geprüft werden – sie wurden nicht verändert.\nDetails: %s" % logger.pfad(), "Spengler Digital CAD")
        ort = command_registry.registrieren()
        logger.info("Add-in gestartet", version=VERSION, werkzeugleiste=ort)
        try:   # Abgleich mit der Spengler-Digital-App und Update-Frage – nie ein Startfehler
            from spengler_cad.commands import settings_command
            settings_command.beim_start()
        except Exception:
            logger.ausnahme("Start-Abgleich")
    except Exception:
        _ui().messageBox("Spengler Digital CAD startet nicht:\n" + traceback.format_exc())


def stop(context):
    try:
        from spengler_cad.commands import command_registry
        command_registry.entfernen()
    except Exception:
        pass

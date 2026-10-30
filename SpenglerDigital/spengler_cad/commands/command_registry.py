"""Werkzeugleiste: eigenes Register «SPENGLER» im Konstruktionsarbeitsbereich mit allen Befehlen.
Falls die Register-API fehlt: Befehle im Blech- bzw. Volumenkörper-Panel «Erstellen» (wie Prototyp 0.1)."""
from ..diagnostics import logger
from . import auftrag_command, base, detail_generator_command, edge_apply_command, export_command, forming_command, settings_command

TAB_ID = "SpenglerDigitalTab"
GRUPPEN = [  # (Panel-ID, Titel, Befehle)
    ("SpenglerKantenPanel", "Kanten & Details", []),
    ("SpenglerFertigungPanel", "Fertigung", []),
    ("SpenglerVerwaltungPanel", "Verwaltung", []),
]
ERSATZ_PANELS = ("SheetMetalCreatePanel", "SolidCreatePanel")
_angelegt = []   # (panel, control-id)


def _definitionen():
    kanten = [edge_apply_command.registrieren()] + detail_generator_command.registrieren() + [forming_command.registrieren()]
    fertigung = export_command.registrieren() + auftrag_command.registrieren() + auftrag_command.registrieren_wahl()
    verwaltung = settings_command.registrieren()
    return [kanten, fertigung, verwaltung]


def registrieren():
    ui = base.ui()
    gruppen = _definitionen()
    try:
        ws = ui.workspaces.itemById("FusionSolidEnvironment")
        tab = ws.toolbarTabs.itemById(TAB_ID) or ws.toolbarTabs.add(TAB_ID, "SPENGLER")
        for (pid, titel, _), defs in zip(GRUPPEN, gruppen):
            panel = tab.toolbarPanels.itemById(pid) or tab.toolbarPanels.add(pid, titel)
            for i, d in enumerate(defs):
                c = panel.controls.itemById(d.id) or panel.controls.addCommand(d)
                if i == 0:
                    c.isPromoted = True
                _angelegt.append((panel, d.id))
        return "Register SPENGLER"
    except Exception:
        logger.ausnahme("Eigenes Register nicht möglich – Ersatz-Panels")
        for pid in ERSATZ_PANELS:
            panel = ui.allToolbarPanels.itemById(pid)
            if not panel:
                continue
            for defs in gruppen:
                for d in defs:
                    if not panel.controls.itemById(d.id):
                        panel.controls.addCommand(d)
                    _angelegt.append((panel, d.id))
        return "Ersatz-Panels"


def entfernen():
    ui = base.ui()
    for panel, cid in _angelegt:
        try:
            c = panel.controls.itemById(cid)
            if c:
                c.deleteMe()
        except Exception:
            pass
    del _angelegt[:]
    try:
        ws = ui.workspaces.itemById("FusionSolidEnvironment")
        tab = ws.toolbarTabs.itemById(TAB_ID)
        if tab:
            for pid, _, _ in GRUPPEN:
                p = tab.toolbarPanels.itemById(pid)
                if p:
                    p.deleteMe()
            tab.deleteMe()
    except Exception:
        pass
    settings_command.aufraeumen()
    for defs in (edge_apply_command.BID, detail_generator_command.BID_ERFASSEN, detail_generator_command.BID_ANWENDEN, forming_command.BID,
                 export_command.BID_ABW, export_command.BID_ZUS, settings_command.BID_PALETTE, settings_command.BID_HILFE):
        try:
            d = ui.commandDefinitions.itemById(defs)
            if d:
                d.deleteMe()
        except Exception:
            pass
    del base.HANDLER[:]

"""Werkzeugleiste: eigenes Register «SPENGLER» im Konstruktionsarbeitsbereich mit allen Befehlen.
Falls die Register-API fehlt: Befehle im Blech- bzw. Volumenkörper-Panel «Erstellen» (wie Prototyp 0.1)."""
from ..diagnostics import logger
from . import ablage_command, app_massaufnahme_command, auftrag_command, bauteil_command, start_command, base, detail_generator_command, edge_apply_command, export_command, forming_command, grundblech_command, lernen_command, livetest_command, quetschfalte_command, eigene_abwicklung_command, settings_command

TAB_ID = "SpenglerDigitalTab"
GRUPPEN = [  # (Panel-ID, Titel, Befehle) – in der Reihenfolge der Arbeit: erst der Auftrag, dann Konstruieren, dann Fertigung
    ("SpenglerAuftragPanel", "1 · Auftrag", []),
    ("SpenglerKonstruierenPanel", "2 · Konstruieren", []),
    ("SpenglerFertigungPanel2", "3 · Fertigung", []),
    ("SpenglerVerwaltungPanel2", "Verwaltung", []),
]
ALTE_PANELS = ("SpenglerKantenPanel", "SpenglerFertigungPanel", "SpenglerVerwaltungPanel")   # bis 0.4.33 – werden entfernt
ERSATZ_PANELS = ("SheetMetalCreatePanel", "SolidCreatePanel")
_angelegt = []   # (panel, control-id)


def _definitionen():
    auftrag = start_command.registrieren() + auftrag_command.registrieren() + auftrag_command.registrieren_wahl() + auftrag_command.registrieren_abgleich() + ablage_command.registrieren()
    konstruieren = ([edge_apply_command.registrieren()] + bauteil_command.registrieren() + detail_generator_command.registrieren() + [forming_command.registrieren()]
                    + lernen_command.registrieren() + app_massaufnahme_command.registrieren() + grundblech_command.registrieren()
                    + [quetschfalte_command.registrieren()])
    fertigung = export_command.registrieren() + [eigene_abwicklung_command.registrieren()]
    verwaltung = settings_command.registrieren() + livetest_command.registrieren()
    return [auftrag, konstruieren, fertigung, verwaltung]


def registrieren():
    ui = base.ui()
    gruppen = _definitionen()
    try:
        ws = ui.workspaces.itemById("FusionSolidEnvironment")
        tab = ws.toolbarTabs.itemById(TAB_ID) or ws.toolbarTabs.add(TAB_ID, "SPENGLER")
        for alt in ALTE_PANELS:
            try:
                p = tab.toolbarPanels.itemById(alt)
                if p:
                    p.deleteMe()
            except Exception:
                pass
        for (pid, titel, _), defs in zip(GRUPPEN, gruppen):
            panel = tab.toolbarPanels.itemById(pid) or tab.toolbarPanels.add(pid, titel)
            for i, d in enumerate(defs):
                c = panel.controls.itemById(d.id) or panel.controls.addCommand(d)
                if i == 0:
                    c.isPromoted = True
                _angelegt.append((panel, d.id))
        try:
            start_command.ereignisse_anmelden()
        except Exception:
            logger.ausnahme("Ereignisse für Start/Voraussetzungen")
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
    try:
        start_command.ereignisse_abmelden()
    except Exception:
        pass
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
                 export_command.BID_ABW, export_command.BID_ZUS, settings_command.BID_PALETTE, settings_command.BID_HILFE, livetest_command.BID, grundblech_command.BID, bauteil_command.BID, ablage_command.BID):
        try:
            d = ui.commandDefinitions.itemById(defs)
            if d:
                d.deleteMe()
        except Exception:
            pass
    del base.HANDLER[:]

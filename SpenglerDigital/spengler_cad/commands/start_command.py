"""Befehl «Start»: Übersicht, was eingerichtet ist und was als Nächstes sinnvoll ist (mit Sprung zum nächsten Befehl); dazu die Voraussetzungs-Prüfung, die
Befehle ohne Auftrag/Material gar nicht erst öffnet. NICHT live in Fusion geprüft."""
import adsk.core

from ..core import start as logik
from ..diagnostics import logger
from . import base, zustand

BID = "spenglerStart"
EREIGNIS = "spenglerFolgeBefehl"
_ereignis = []
Z_ = {"schluessel": []}


@base.sicher("Start")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    z = zustand.lesen(mit_app=True)
    e = logik.bewerte(z)
    symbol = {True: "✅", False: "⚠️", None: "ℹ️"}
    inp.addTextBoxCommandInput("status", "", "<br>".join("%s %s" % (symbol[x["ok"]], x["text"]) for x in e["zeilen"]), 7, True)
    dd = inp.addDropDownCommandInput("naechster", "Nächster Schritt", adsk.core.DropDownStyles.TextListDropDownStyle)
    for k, name in logik.SCHRITTE:
        dd.listItems.add(("➜ " if k == e["naechster"] else "") + name, k == e["naechster"])
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)
    Z_["schluessel"] = [k for k, _ in logik.SCHRITTE]


def erstellt(args):
    _erstellt(None, args)


@base.sicher("Start")
def _ausfuehren_innen(self, args):
    sel = args.command.commandInputs.itemById("naechster").selectedItem
    if sel is None:
        return
    k = Z_["schluessel"][sel.index]
    bid = logik.BEFEHL_ID.get(k)
    if bid:
        befehl_folgen(bid)


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def befehl_folgen(bid):
    """Einen anderen Befehl NACH dem aktuellen starten (ein Befehl lässt sich nicht aus einem laufenden heraus starten → benutzerdefiniertes Ereignis)."""
    try:
        adsk.core.Application.get().fireCustomEvent(EREIGNIS, bid)
    except Exception:
        logger.ausnahme("Folgebefehl nicht gestartet", befehl=bid)


def _folge(args):
    try:
        bid = adsk.core.CustomEventArgs.cast(args).additionalInfo
        d = base.ui().commandDefinitions.itemById(bid)
        if d:
            d.execute()
    except Exception:
        logger.ausnahme("Folgebefehl")


def _start_pruefen(args):
    """Vor dem Start eines Befehls: fehlen Voraussetzungen (Auftrag, Material, Vorlage), wird er NICHT geöffnet, sondern erklärt, was zu tun ist."""
    try:
        bid = args.commandId
        if bid not in logik.BRAUCHT_AUFTRAG:
            return
        z = zustand.lesen(mit_app=False)
        probleme, loesung = logik.voraussetzungen(bid, z, z.get("auftrag_erforderlich", True))
        if not probleme:
            return
        args.isCanceled = True
        text = "\n".join("• " + p for p in probleme)
        if loesung and base.frage("Erst vorbereiten", text + "\n\nJetzt dorthin wechseln?"):
            befehl_folgen(loesung)
        elif not loesung:
            base.melden("Erst vorbereiten", text)
    except Exception:
        logger.ausnahme("Voraussetzungen prüfen")


def ereignisse_anmelden():
    app = adsk.core.Application.get()
    try:
        app.unregisterCustomEvent(EREIGNIS)
    except Exception:
        pass
    ev = app.registerCustomEvent(EREIGNIS)
    base.handler(adsk.core.CustomEventHandler, ev, _folge)
    base.handler(adsk.core.ApplicationCommandEventHandler, base.ui().commandStarting, _start_pruefen)


def ereignisse_abmelden():
    try:
        adsk.core.Application.get().unregisterCustomEvent(EREIGNIS)
    except Exception:
        pass


def registrieren():
    return [base.befehl_definieren(BID, "Start / Übersicht", "Zeigt, was eingerichtet ist und was als Nächstes sinnvoll ist: Konto, Material, Vorlagen, Auftrag, Projekt in der App.", erstellt)]

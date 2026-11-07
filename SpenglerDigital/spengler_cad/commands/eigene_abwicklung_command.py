"""Befehl «Abwicklung (eigen)»: vollständige Abwicklung eines Rechteck-Blechs mit geraden Aufkantungen und Quetschfalten durch das Add-in (ohne Fusions
Flat Pattern): DXF mit allen Ausschnitten und Biegelinien und ein flacher Körper in eigener Komponente «Abwicklung …», aus dem in Fusion eine Zeichnung
erstellt werden kann (Anwender 7. 11. 2026). NICHT live geprüft."""
import os
import time

import adsk.core
import adsk.fusion

from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage import paths
from . import base

BID = "spenglerAbwicklungEigen"


def erstellt(args):
    if base.gesperrt(args, BID):
        return
    cmd = args.command
    inp = cmd.commandInputs
    s = inp.addSelectionInput("koerper", "Blechteil", "Das Blech (Körper) mit Aufkantungen und evtl. Quetschfalte")
    s.addSelectionFilter("Bodies")
    s.setSelectionLimits(1, 1)
    inp.addBoolValueInput("koerperbauen", "Flachen Körper für eine Zeichnung erzeugen", True, "", True)
    inp.addTextBoxCommandInput("info", "Hinweis", "Rechteck-Grundblech mit geraden 90°-Aufkantungen nach oben (+Z); Quetschfalten an Ecken zweier gleich hoher "
                               "Aufkantungen. Fusions Abwicklung wird nicht benutzt.", 4, True)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, ausfuehren)


@base.sicher("Abwicklung (eigen)")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    sel = inp.itemById("koerper")
    body = adsk.fusion.BRepBody.cast(sel.selection(0).entity) if sel.selectionCount else None
    if body is None:
        base.melden("Abwicklung (eigen)", "Bitte einen Körper wählen.", True)
        return
    ordner = os.path.join(paths.daten_ordner(), "Abwicklung")
    os.makedirs(ordner, exist_ok=True)
    pfad = os.path.join(ordner, "Abwicklung_%s_%s.dxf" % (body.name.replace(" ", "_"), time.strftime("%Y%m%d_%H%M%S")))
    von = fa.zeitleiste_stand()
    try:
        res = fa.eigene_blech_abwicklung(body, pfad, inp.itemById("koerperbauen").value)
    except fa.AdapterFehler as e:
        base.melden("Abwicklung (eigen)", "Keine Abwicklung: %s" % e, True)
        return
    fa.zeitleiste_gruppieren(von, "Spengler: Abwicklung (eigen)")
    r, m = res["ergebnis"], res["daten"]
    zeilen = ["Abwicklung von «%s»: %.1f × %.1f mm, Fläche %.0f mm² (Dicke %.2f, ri %.2f, K %.2f)." % (
        body.name, r["breite"], r["hoehe"], r["flaeche"], m["dicke"], m["ri"], m["k"]),
        "Aufkantungen: " + ", ".join("%s %.1f" % (s, h) for s, h in sorted(m["aufkantungen"].items())) + ("; Quetschfalten: " + ", ".join(m["ecken"]) if m["ecken"] else "") + ".",
        "DXF (Kontur, Biegelinien, Ecklinien, Faltlinie): " + pfad]
    if res["koerper"] is not None:
        zeilen.append("Flacher Körper in der Komponente «%s» – dort kann eine Fusion-Zeichnung erstellt werden (Biegelinien als Kanten der Oberseite)." % res["komponente"].component.name)
    zeilen += r["hinweise"]
    zeilen.append("Nicht live geprüft. Biegezugabe und Lagendicke der Quetschfalte sind nicht eingerechnet.")
    logger.info("Eigene Abwicklung", datei=os.path.basename(pfad), breite=r["breite"], hoehe=r["hoehe"])
    base.melden("Abwicklung (eigen)", "\n\n".join(zeilen))


def ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return base.befehl_definieren(BID, "Abwicklung (eigen)", "Vollständige Abwicklung des Blechteils inkl. Quetschfalte (DXF und flacher Körper für die Zeichnung).", erstellt)

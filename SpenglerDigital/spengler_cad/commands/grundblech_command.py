"""Befehl «Blech aus Massaufnahme»: erzeugt aus einer Massaufnahme der App (Freies Profil/Dachrandblech des aktiven Auftrags, nur lesen) direkt ein Blech
mit den Massen: Grundblech (Breite = erster Schenkel, Länge aus der App) und auf Wunsch die Kantenfolge (Flansche/Umschläge). NICHT live in Fusion geprüft."""
import adsk.core

from .. import VERSION
from ..core import app_profil, auftrag as auftrag_logik
from ..diagnostics import logger
from ..geometry import fusion_adapter as fa
from ..storage.cloud_client import Cloud
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from . import base, export_command

BID = "spenglerBlechAusApp"
Z = {}


@base.sicher("Blech aus Massaufnahme")
def _erstellt(self, args):
    cmd = args.command
    inp = cmd.commandInputs
    e = Einstellungen().laden()
    angaben = export_command.auftrag_angaben(e)
    if not angaben["auftrag"]:
        raise fa.AdapterFehler("Kein aktiver Auftrag. Bitte zuerst «Auftrag wählen».")
    c = Cloud(timeout=10)
    if not c.angemeldet:
        raise fa.AdapterFehler("Für die App-Daten zuerst unter «Konto» anmelden.")
    Z.clear()
    Z["liste"] = c.massaufnahmen_zum_auftrag(angaben["auftrag"])
    Z["mat"] = MaterialBibliothek().liste()
    Z["auftrag"] = angaben["auftrag"]
    if not Z["liste"]:
        raise fa.AdapterFehler("In der App gibt es zum Auftrag %s keine Massaufnahme «Freies Profil» oder «Dachrandblech»." % angaben["auftrag"])
    if not Z["mat"]:
        raise fa.AdapterFehler("Es gibt noch kein Materialprofil (Vorlagen & Einstellungen → Materialien).")
    dd = inp.addDropDownCommandInput("aufnahme", "Massaufnahme in der App", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, m in enumerate(Z["liste"]):
        dd.listItems.add("%s (%s)" % (m.get("title") or "ohne Titel", m["type"]), i == 0)
    md = inp.addDropDownCommandInput("material", "Material", adsk.core.DropDownStyles.TextListDropDownStyle)
    vorgabe = auftrag_logik.material_vorgabe(e, Z["mat"])
    for m in Z["mat"]:
        md.listItems.add("%s (%.2f mm)" % (m["name"], m["thickness"]), m["id"] == vorgabe)
    if md.selectedItem is None:
        md.listItems.item(0).isSelected = True
    inp.addStringValueInput("name", "Name des Bauteils", "")
    inp.addValueInput("laenge", "Länge", "mm", adsk.core.ValueInput.createByString("1000 mm"))
    inp.addBoolValueInput("kanten", "Kantenfolge (Flansche/Umschläge) auch bauen", True, "", True)
    inp.addTextBoxCommandInput("info", "", "", 4, True)
    base.handler(adsk.core.InputChangedEventHandler, cmd.inputChanged, _geaendert)
    base.handler(adsk.core.CommandEventHandler, cmd.execute, _ausfuehren)
    _vorbelegen(inp)


def erstellt(args):
    _erstellt(None, args)


def _aufnahme(inp):
    sel = inp.itemById("aufnahme").selectedItem
    return Z["liste"][sel.index] if sel is not None else None


def _vorbelegen(inp):
    m = _aufnahme(inp)
    if m is None:
        return
    g = app_profil.grundblech_aus_app(m.get("data"))
    inp.itemById("name").value = (m.get("title") or "Blech aus App")[:60]
    if g["laenge"]:
        inp.itemById("laenge").expression = "%g mm" % g["laenge"]
    inp.itemById("info").text = ("Grundblech %.0f mm breit, %d Biegung(en) aus der App.<br>%s" % (g["breite"], len(g["ops"]), "<br>".join(g["hinweise"]))).replace("\n", "<br>")


def _geaendert(args):
    if args.input.id == "aufnahme":
        _vorbelegen(args.inputs)


@base.sicher("Blech aus Massaufnahme")
def _ausfuehren_innen(self, args):
    inp = args.command.commandInputs
    m = _aufnahme(inp)
    mat = Z["mat"][inp.itemById("material").selectedItem.index]
    g = app_profil.grundblech_aus_app(m.get("data"))
    laenge = inp.itemById("laenge").value * 10.0          # cm → mm
    if laenge <= 0:
        raise fa.AdapterFehler("Die Länge muss grösser als 0 sein.")
    name = inp.itemById("name").value.strip() or "Blech aus App"
    von = fa.zeitleiste_stand()
    comp = fa.neue_komponente(name)
    bericht = []
    body = fa.grundblech_bauen(comp, laenge, g["breite"], mat["thickness"])
    dicke = fa.blechdicke_mm(body)
    bericht.append("Grundblech %.0f × %.0f mm erzeugt." % (laenge, g["breite"]))
    if dicke is not None and abs(dicke - mat["thickness"]) > 0.01:
        bericht.append("⚠ Die Blechregel in Fusion hat %.2f mm, das Material «%s» %.2f mm – bitte die Blechregel (Blech → Blechregeln) anpassen." % (dicke, mat["name"], mat["thickness"]))
    hinweise = list(g["hinweise"])
    if inp.itemById("kanten").value and g["ops"]:
        kante = fa.grundblech_kante(body)
        markierung = {"vorlageName": "Massaufnahme " + (m.get("title") or str(m["id"])), "material": mat, "operationen": g["ops"], "addin": VERSION, "quelle": "app"}
        h2 = []
        feats = fa.folge_anbringen(kante, g["ops"], dicke or mat["thickness"], markierung, h2)
        bericht.append("%d Schritt(e) an der Kante gebaut." % len(feats))
        hinweise += h2
    fa.zeitleiste_gruppieren(von, "Spengler: %s" % name)
    try:
        e = Einstellungen().laden()
        if auftrag_logik.material_merken(e, mat["id"]):
            Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Material des Auftrags nicht gemerkt")
    logger.info("Blech aus Massaufnahme", massaufnahme=m["id"], laenge=laenge, breite=g["breite"], schritte=len(g["ops"]))
    base.melden("Blech aus Massaufnahme", "\n".join(bericht + hinweise + ["", "Bitte Richtung und Masse mit der Massaufnahme vergleichen (nicht live geprüft)."]))


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Blech aus Massaufnahme", "Erzeugt aus einer Massaufnahme der App (Freies Profil/Dachrandblech) ein Blech mit Länge, Breite und Kantenfolge.", erstellt)]

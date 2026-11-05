"""Befehl «Blech aus Massaufnahme»: erzeugt aus einer Massaufnahme der App (Freies Profil/Dachrandblech des aktiven Auftrags, nur lesen) direkt ein Blech
mit den Massen: Grundblech (Breite = erster Schenkel, Länge aus der App) und auf Wunsch die Kantenfolge (Flansche/Umschläge).
Zuerst stehen die Profile, die in der App mit «An CAD senden» (Länge, Stück) geschickt wurden; nach dem Bauen werden sie als «gebaut» markiert.
NICHT live in Fusion geprüft."""
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
    Z["liste"] = eintraege(c.profil_auftraege(angaben["auftrag"]), c.massaufnahmen_zum_auftrag(angaben["auftrag"]))
    Z["mat"] = MaterialBibliothek().liste()
    Z["auftrag"] = angaben["auftrag"]
    if not Z["liste"]:
        raise fa.AdapterFehler("In der App gibt es zum Auftrag %s weder ein gesendetes Profil («An CAD senden») noch eine Massaufnahme «Freies Profil» oder «Dachrandblech»." % angaben["auftrag"])
    if not Z["mat"]:
        raise fa.AdapterFehler("Es gibt noch kein Materialprofil (Vorlagen & Einstellungen → Materialien).")
    dd = inp.addDropDownCommandInput("aufnahme", "Massaufnahme in der App", adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, m in enumerate(Z["liste"]):
        dd.listItems.add(m["text"], i == 0)
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


def eintraege(auftraege, massaufnahmen):
    """Auswahlliste: zuerst die in der App gesendeten Profile (mit Länge und Stück), dann die Massaufnahmen. Reine Logik. → [{'text', 'art', 'data', 'title', 'id', 'laenge', 'stueck'}]"""
    out = []
    for a in auftraege or []:
        out.append({"art": "gesendet", "id": a["id"], "title": a.get("titel") or "Profil", "data": a.get("daten") or {}, "laenge": float(a["laenge_mm"]),
                    "stueck": int(a.get("stueck") or 1), "text": "📤 aus der App: %s – %g mm × %d Stück" % (a.get("titel") or "Profil", float(a["laenge_mm"]), int(a.get("stueck") or 1))})
    for m in massaufnahmen or []:
        out.append({"art": "massaufnahme", "id": m["id"], "title": m.get("title") or "", "data": m.get("data") or {}, "laenge": None, "stueck": 1,
                    "text": "%s (%s)" % (m.get("title") or "ohne Titel", m["type"])})
    return out


def _aufnahme(inp):
    sel = inp.itemById("aufnahme").selectedItem
    return Z["liste"][sel.index] if sel is not None else None


def _vorbelegen(inp):
    m = _aufnahme(inp)
    if m is None:
        return
    g = app_profil.grundblech_aus_app(m.get("data"))
    inp.itemById("name").value = (m.get("title") or "Blech aus App")[:60]
    laenge = m.get("laenge") or g["laenge"]
    if laenge:
        inp.itemById("laenge").expression = "%g mm" % laenge
    if m["art"] == "gesendet":
        g["hinweise"] = list(g["hinweise"]) + ["Aus der App gesendet: %g mm, %d Stück (gebaut wird ein Bauteil)." % (m["laenge"], m["stueck"])]
    inp.itemById("info").formattedText = ("Grundblech %.0f mm breit, %d Biegung(en) aus der App.<br>%s" % (g["breite"], len(g["ops"]), "<br>".join(g["hinweise"]))).replace("\n", "<br>")


def _geaendert(args):
    if args.input.id == "aufnahme":
        _vorbelegen(args.inputs)


def bauen(m, g, mat, laenge, name, mit_kanten):
    """Baut das Blech in einer NEUEN Komponente. → (Bericht, Hinweise). Bei JEDEM Fehler wird die halbfertige Komponente wieder entfernt (fa.abbruch_mit_rueckbau)."""
    von = fa.zeitleiste_stand()
    comp = fa.neue_komponente(name)
    try:
        bericht = []
        body = fa.grundblech_bauen(comp, laenge, g["breite"], mat["thickness"])
        dicke = fa.blechdicke_mm(body)
        bericht.append("Grundblech %.0f × %.0f mm erzeugt." % (laenge, g["breite"]))
        if dicke is not None and abs(dicke - mat["thickness"]) > 0.01:
            bericht.append("⚠ Die Blechregel in Fusion hat %.2f mm, das Material «%s» %.2f mm – bitte die Blechregel (Blech → Blechregeln) anpassen." % (dicke, mat["name"], mat["thickness"]))
        hinweise = list(g["hinweise"])
        if mit_kanten and g["ops"]:
            kante = fa.grundblech_kante(body)
            markierung = {"vorlageName": "Massaufnahme " + (m.get("title") or str(m["id"])), "material": mat, "operationen": g["ops"], "addin": VERSION, "quelle": "app"}
            h2 = []
            feats = fa.folge_anbringen(kante, g["ops"], dicke or mat["thickness"], markierung, h2)
            bericht.append("%d Schritt(e) an der Kante gebaut." % len(feats))
            hinweise += h2
    except Exception as ex:
        logger.ausnahme("Blech aus Massaufnahme abgebrochen")
        fa.abbruch_mit_rueckbau(comp, ex, "Blech «%s»" % name)
    fa.zeitleiste_gruppieren(von, "Spengler: %s" % name)
    return bericht, hinweise


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
    bericht, hinweise = bauen(m, g, mat, laenge, name, bool(inp.itemById("kanten").value))
    try:
        e = Einstellungen().laden()
        if auftrag_logik.material_merken(e, mat["id"]):
            Einstellungen().speichern(e)
    except Exception:
        logger.ausnahme("Material des Auftrags nicht gemerkt")
    logger.info("Blech aus Massaufnahme", massaufnahme=m["id"], art=m["art"], laenge=laenge, breite=g["breite"], schritte=len(g["ops"]))
    if m["art"] == "gesendet":
        bericht.append(markieren_gebaut(m["id"]))
        if m["stueck"] > 1:
            bericht.append("Der Auftrag verlangt %d Stück – in Fusion das Bauteil kopieren." % m["stueck"])
    base.melden("Blech aus Massaufnahme", "\n".join(bericht + hinweise + ["", "Bitte Richtung und Masse mit der Massaufnahme vergleichen (nicht live geprüft)."]))


def markieren_gebaut(auftrag_id, cloud=None):
    """Gesendeten Auftrag in der App als «gebaut» vermerken. → Meldungstext, nie eine Ausnahme (das Blech ist dann schon gebaut)."""
    try:
        (cloud or Cloud(timeout=10)).profil_auftrag_gebaut(auftrag_id)
        return "In der App als «gebaut» vermerkt."
    except Exception as ex:
        logger.warnung("Gesendeten Auftrag nicht als gebaut markiert", fehler=ex)
        return "Hinweis: In der App konnte der Auftrag nicht als «gebaut» vermerkt werden (%s)." % (str(ex) or type(ex).__name__)


def _ausfuehren(args):
    _ausfuehren_innen(None, args)


def registrieren():
    return [base.befehl_definieren(BID, "Blech aus Massaufnahme", "Erzeugt aus einer Massaufnahme der App (Freies Profil/Dachrandblech) ein Blech mit Länge, Breite und Kantenfolge.", erstellt)]

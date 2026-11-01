"""Abgleich Aufträge: Projekte der Spengler-Digital-App ↔ Auftragsordner in Fusion (Nummer + Objekt). Reine Logik ohne Fusion/Netz.

Zuordnung über die Auftragsnummer: App `projects.order_no` = Ordner «<Nummer> <Objekt>». Beim Anlegen in der App wird `object` = Objekt des Ordners
und `name` (Titel des Projekts in der App) = Objekt; ein anderer Titel lässt sich dort jederzeit ändern."""
import re

from . import auftrag

_UNGUELTIG = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _nr(x):
    return str(x or "").strip()


def ordnername_fuer_projekt(p):
    """App-Projekt → Ordnername «Nummer Objekt» oder (None, Grund). Unzulässige Zeichen im Objekt werden durch «-» ersetzt."""
    nr = _nr(p.get("order_no"))
    if not nr:
        return None, "keine Auftragsnummer"
    if not re.match(r"^\d{3,}$", nr):
        return None, "Auftragsnummer «%s» ist nicht rein numerisch (mindestens 3 Ziffern)" % nr
    objekt = _UNGUELTIG.sub("-", str(p.get("object") or p.get("name") or "")).strip()
    if not objekt:
        return None, "weder Objekt noch Name"
    try:
        return auftrag.ordnername(nr, objekt), None
    except auftrag.AuftragsFehler as ex:
        return None, str(ex)


def vergleiche(projekte, ordner):
    """projekte: Zeilen der App (id, name, order_no, object, archived, created_at, status); ordner: [{'nummer','objekt','name','jahr'}] aus Fusion.
    → {'nur_app': [{'projekt', 'ordnername', 'jahr'}], 'nur_fusion': [ordner], 'beide': [(projekt, ordner)], 'abweichend': [(projekt, ordner)],
       'uebersprungen': [(projekt, Grund)], 'archiviert': n}"""
    nach_nr = {}
    for o in ordner:
        nach_nr.setdefault(_nr(o["nummer"]), o)
    erg = {"nur_app": [], "nur_fusion": [], "beide": [], "abweichend": [], "uebersprungen": [], "archiviert": 0}
    bekannt = set()
    for p in projekte:
        if p.get("archived"):
            erg["archiviert"] += 1
            continue
        nr = _nr(p.get("order_no"))
        o = nach_nr.get(nr) if nr else None
        if o is not None:
            bekannt.add(nr)
            gleich = (o["objekt"] or "").strip().lower() == str(p.get("object") or "").strip().lower()
            erg["beide" if gleich else "abweichend"].append((p, o))
            continue
        name, grund = ordnername_fuer_projekt(p)
        if name is None:
            erg["uebersprungen"].append((p, grund))
        else:
            jahr = str(p.get("created_at") or "")[:4]
            erg["nur_app"].append({"projekt": p, "ordnername": name, "jahr": int(jahr) if jahr.isdigit() else None})
    erg["nur_fusion"] = [o for nr, o in nach_nr.items() if nr not in bekannt and not any(_nr(p.get("order_no")) == nr for p in projekte)]
    return erg


def projekt_aus_ordner(o):
    """Fusion-Auftrag → Felder für ein neues Projekt der App."""
    return {"order_no": _nr(o["nummer"]), "object": o["objekt"], "name": o["objekt"]}

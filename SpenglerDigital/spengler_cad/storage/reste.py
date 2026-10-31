"""Reststücke (Tafel-/Blechreste) – vorerst lokal je PC. Die Felder heissen wie in der Tabelle `reststuecke` der Spengler-Digital-App
(material_name, staerke_mm, breite_mm, laenge_mm, anzahl, herkunft, notiz, verbraucht), damit eine spätere echte Verbindung zur App ohne
Umbau möglich ist (noch NICHT angebunden, siehe docs/ANFORDERUNGEN_STATUS.md)."""
import datetime
import os
import uuid

from . import json_store, paths


class RestFehler(ValueError):
    pass


def _datei(wurzel=None):
    return os.path.join(wurzel or paths.daten_ordner(), "reste.json")


def liste(wurzel=None):
    return json_store.lesen(_datei(wurzel)) or []


def pruefe(r):
    f = []
    for k, label in (("breite_mm", "Breite"), ("laenge_mm", "Länge"), ("staerke_mm", "Dicke")):
        if not isinstance(r.get(k), (int, float)) or isinstance(r.get(k), bool) or r[k] <= 0:
            f.append("%s fehlt oder ist keine Zahl grösser 0." % label)
    if not isinstance(r.get("anzahl"), int) or isinstance(r.get("anzahl"), bool) or r["anzahl"] < 1:
        f.append("Anzahl muss eine ganze Zahl ab 1 sein.")
    if f:
        raise RestFehler(" ".join(f))


def speichern(r, wurzel=None):
    """Neu (ohne id) oder ändern (mit id). → gespeicherter Rest."""
    r = dict(r)
    r["anzahl"] = int(r["anzahl"]) if str(r.get("anzahl", "")).strip().lstrip("-").isdigit() else r.get("anzahl")
    pruefe(r)
    alle = liste(wurzel)
    r.setdefault("material_name", "")
    r["material_name"] = str(r["material_name"])[:120]
    r["herkunft"] = str(r.get("herkunft", ""))[:200]
    r["notiz"] = str(r.get("notiz", ""))[:500]
    r["verbraucht"] = bool(r.get("verbraucht"))
    r["geaendert"] = datetime.datetime.now().isoformat(timespec="seconds")
    if r.get("id"):
        alle = [r if x["id"] == r["id"] else x for x in alle]
    else:
        r["id"] = "rest-" + uuid.uuid4().hex[:10]
        alle.append(r)
    json_store.schreiben(_datei(wurzel), alle)
    return r


def loeschen(rest_id, wurzel=None):
    alle = liste(wurzel)
    json_store.schreiben(_datei(wurzel), [x for x in alle if x["id"] != rest_id])
    return len(alle) - len(liste(wurzel))


def vorschlaege(teile, reste, drehen=True):
    """Welche Teile passen in vorhandene (nicht verbrauchte) Reste? teile: [{'nr','name','breite','laenge','stueck','material' (Profil)}].
    Passt = gleiche Dicke (±0.005 mm), Material gleich (Profilname oder Werkstoff; leeres Material im Rest passt zu jedem), Rechteck des Teils liegt im
    Rest (gedreht nur mit drehen=True) und genug Stück. Je Teil der kleinste passende Rest. → [(Teil, Rest)] (Rest None → kein passender)."""
    frei = [dict(r) for r in reste if not r.get("verbraucht") and r.get("anzahl", 0) >= 1]
    out = []
    for t in teile:
        m = t.get("material") or {}
        namen = {str(m.get("name", "")).strip().lower(), str(m.get("material", "")).strip().lower()} - {""}
        beste = None
        for r in frei:
            if not m.get("thickness") or abs(r["staerke_mm"] - m["thickness"]) > 0.005:
                continue
            rn = str(r.get("material_name", "")).strip().lower()
            if rn and rn not in namen:
                continue
            if r["anzahl"] < max(1, int(t.get("stueck") or 1)):
                continue
            passt = (t["breite"] <= r["breite_mm"] and t["laenge"] <= r["laenge_mm"]) or (
                drehen and t["breite"] <= r["laenge_mm"] and t["laenge"] <= r["breite_mm"])
            if passt and (beste is None or r["breite_mm"] * r["laenge_mm"] < beste["breite_mm"] * beste["laenge_mm"]):
                beste = r
        out.append((t, beste))
    return out

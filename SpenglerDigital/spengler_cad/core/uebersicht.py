"""Auftragsübersicht: führt Auftragsordner (Fusion), Projekte der App, Fertigungsstatus und Teile je Auftrag zu einer Tabelle zusammen. Reine Logik."""
from . import abgleich
from .auftrag import STATUS_TEXT

REIHENFOLGE = {"offen": 0, "in_arbeit": 1, "gefertigt": 2, "geliefert": 3}


def zeilen(projekte, ordner, status, teile, aktiv=""):
    """projekte: Zeilen der App; ordner: [{'nummer','objekt','name','jahr'}]; status: {auftrag: {status, geaendert_am}}; teile: [{'auftrag','status','geaendert_am'}];
    aktiv: Nummer des aktiven Auftrags. → Liste von Zeilen, neueste Nummer zuerst."""
    n = abgleich._nr
    per = {}

    def z(nr, objekt=""):
        return per.setdefault(nr, {"nummer": nr, "objekt": objekt or "", "jahr": None, "fusion": False, "app": False, "app_status": "", "fertigung": "", "teile": 0,
                                    "gefertigt": 0, "geaendert": "", "aktiv": False, "hinweise": []})
    for o in ordner:
        r = z(n(o["nummer"]) or str(o["nummer"]), o.get("objekt"))
        r.update(fusion=True, jahr=o.get("jahr"), objekt=o.get("objekt") or r["objekt"])
    for p in projekte:
        if p.get("archived"):
            continue
        nr = n(p.get("order_no"))
        if not nr:
            continue
        r = z(nr, p.get("object") or p.get("name"))
        r.update(app=True, app_status=p.get("status") or "")
        if not r["objekt"]:
            r["objekt"] = p.get("object") or p.get("name") or ""
    for a, s in (status or {}).items():
        nr = n(a) or str(a)
        if nr in per:
            per[nr]["fertigung"] = s.get("status") or ""
    for t in teile or []:
        nr = n(t.get("auftrag")) or str(t.get("auftrag"))
        if nr not in per:
            continue
        r = per[nr]
        r["teile"] += 1
        if t.get("status") in ("gefertigt", "fertig", "erledigt"):
            r["gefertigt"] += 1
        r["geaendert"] = max(r["geaendert"], str(t.get("geaendert_am") or ""))
    akt = n(aktiv) or str(aktiv or "")
    for nr, r in per.items():
        r["aktiv"] = bool(akt) and nr == akt
        r["fertigung_text"] = STATUS_TEXT.get(r["fertigung"], "")
        if not r["fusion"]:
            r["hinweise"].append("Kein Ordner in Fusion")
        if not r["app"]:
            r["hinweise"].append("Projekt fehlt in der App")
        if r["fusion"] and not r["teile"] and r["fertigung"] in ("in_arbeit", "gefertigt", "geliefert"):
            r["hinweise"].append("Status «%s», aber keine Teile an die App gesendet" % r["fertigung_text"])
        if r["teile"] and r["gefertigt"] == r["teile"] and r["fertigung"] in ("", "offen", "in_arbeit"):
            r["hinweise"].append("Alle Teile gefertigt – Status auf «Gefertigt» setzen?")
    return sorted(per.values(), key=lambda r: (-(int(r["nummer"]) if str(r["nummer"]).isdigit() else 0), r["nummer"]))


def zusammenfassung(rows):
    z = {"alle": len(rows), "offen": 0, "in_arbeit": 0, "gefertigt": 0, "geliefert": 0, "ohne_status": 0, "mit_hinweis": 0}
    for r in rows:
        z[r["fertigung"] if r["fertigung"] in REIHENFOLGE else "ohne_status"] += 1
        if r["hinweise"]:
            z["mit_hinweis"] += 1
    return z

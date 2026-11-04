"""Projektkarte: macht aus den Zeilen der App (Projekt, Massaufnahmen, Rapporte, Termine, Dateien, Offerten, Leistungen, CAD-Teile, gesendete Aufträge) eine
lesbare Übersicht für das CAD – nur Anzeige, nichts wird verändert. Dazu «Neu seit dem letzten Besuch» und der Werkstattstand der CAD-Teile. Reine Logik."""
import datetime

ART = {"skizze_foto": "Skizze/Foto", "einlaufblech_gerade": "Einlaufblech gerade", "rinne_halbrund": "Dachrinne", "einlaufblech_konisch": "Einlaufblech konisch",
       "freies_profil": "Freies Profil", "dachrandblech": "Dachrandblech", "mauerabdeckung": "Mauerabdeckung", "lukarne": "Lukarne Seitenverkleidung",
       "metalldach": "Metalldach", "ablaufrohr": "Ablaufrohr", "anschlussblech": "Ort- und Seitenbleche", "einfassung_rund": "Einfassung Rund",
       "kamineinfassung": "Kamineinfassung", "dachfenstereinfassung": "Dachfenstereinfassung", "kehle": "Kehle", "rinne": "Rinne"}
WORKFLOW = {"in_bearbeitung": "In Bearbeitung", "freigegeben": "Freigegeben", "zu_ruesten": "Zu rüsten", "geruestet": "Gerüstet", "zu_montieren": "Zu montieren",
            "montiert": "Montiert", "abgeschlossen": "Abgeschlossen"}
WORKFLOW_ZEICHEN = {"in_bearbeitung": "✎", "freigegeben": "✓", "zu_ruesten": "▸", "geruestet": "✓", "zu_montieren": "▸", "montiert": "✓", "abgeschlossen": "✓"}
PROJEKT_STATUS = {"offen": "Offen", "in_arbeit": "In Arbeit", "abgeschlossen": "Abgeschlossen", "storniert": "Storniert"}
AUFTRAG_STATUS = {"offen": "wartet auf das CAD", "gebaut": "im CAD gebaut", "storniert": "zurückgezogen"}


def _datum(s):
    s = str(s or "")
    return s[:10]


def utc(s):
    """ISO-Zeitstempel → datetime mit Zeitzone. REGEL: Zeitstempel MIT Zeitzone (z. B. «+00:00», «Z», «+01:00») behalten ihre Zone; Zeitstempel OHNE Zeitzone gelten als UTC
    (alle Quellen – Supabase timestamptz – liefern UTC). Nicht lesbar → None."""
    s = str(s or "").strip()
    if not s:
        return None
    try:
        d = datetime.datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T", 1) if "T" not in s and " " in s else s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo is not None else d.replace(tzinfo=datetime.timezone.utc)


def _zeit(s):
    """ISO-Zeit → «3.11.2026 16:00» in der LOKALEN Zeit des PCs (Sommer-/Winterzeit eingerechnet, Regel für Zeitstempel ohne Zone siehe utc())."""
    d = utc(s)
    if d is None:
        return str(s or "")[:16]
    d = d.astimezone()
    return "%d.%d.%d %02d:%02d" % (d.day, d.month, d.year, d.hour, d.minute)


def _neuer_als(wert, gesehen_dt):
    """Ist der Zeitstempel `wert` später als `gesehen_dt` (datetime mit Zone)? Nicht lesbar → False."""
    d = utc(wert)
    return d is not None and d > gesehen_dt


def _tag(s):
    s = _datum(s)
    return "%d.%d.%s" % (int(s[8:10]), int(s[5:7]), s[:4]) if len(s) == 10 and s[4] == "-" and s[7] == "-" else s


def _liste(x):
    return x if isinstance(x, list) else []


def _zahl(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def namen(profile):
    """[{id, first_name, last_name}] → {id: 'Vorname Nachname'}"""
    return {p["id"]: ("%s %s" % (p.get("first_name") or "", p.get("last_name") or "")).strip() or "?" for p in profile or [] if p.get("id")}


def kopf(projekt, personen=None):
    p = projekt or {}
    zug = [(personen or {}).get(i) or "?" for i in _liste(p.get("zugeteilt_an"))]
    return {"id": p.get("id"), "updated_at": p.get("updated_at") or "", "hinweis_roh": p.get("hinweis") or "", "nummer": p.get("order_no") or "", "kunde": p.get("customer") or "", "objekt": p.get("object") or p.get("name") or "",
            "status": PROJEKT_STATUS.get(p.get("status"), PROJEKT_STATUS["offen"]), "status_key": p.get("status") or "offen", "hinweis": p.get("hinweis") or "",
            "zugeteilt": zug, "angelegt": _tag(p.get("created_at")), "archiviert": bool(p.get("archived"))}


def massaufnahmen(zeilen, teile=None, auftraege=None):
    """Liste der Massaufnahmen mit Art, Werkstattstatus, Daten und Zahl der Fotos/Skizzen; aktive zuerst. Mit den CAD-Teilen/gesendeten Aufträgen, die daran hängen."""
    teile_je, auftr_je = {}, {}
    for t in teile or []:
        if t.get("measurement_id") is not None:
            teile_je.setdefault(t["measurement_id"], []).append(t)
    for a in auftraege or []:
        if a.get("measurement_id") is not None and a.get("status") != "storniert":
            auftr_je.setdefault(a["measurement_id"], []).append(a)
    out = []
    for m in zeilen or []:
        ws = m.get("workflow_status") or "in_bearbeitung"
        fotos = len(_liste(m.get("photo_paths"))) or (1 if m.get("photo_path") else 0)
        skizzen = len(_liste(m.get("sketch_paths"))) or (1 if m.get("sketch_path") else 0)
        stufen = []
        for feld, text in (("freigegeben_am", "freigegeben"), ("geruestet_am", "gerüstet"), ("montiert_am", "montiert")):
            if m.get(feld):
                stufen.append("%s %s" % (text, _tag(m[feld])))
        pfade = []
        for p_ in _liste(m.get("photo_paths")) + ([m["photo_path"]] if m.get("photo_path") else []) + _liste(m.get("sketch_paths")) + ([m["sketch_path"]] if m.get("sketch_path") else []):
            if isinstance(p_, str) and p_ and p_ not in pfade and not p_.startswith("data:"):
                pfade.append(p_)
        out.append({"pfade": pfade, "id": m.get("id"), "art": ART.get(m.get("type"), m.get("type") or "Massaufnahme"), "typ": m.get("type"), "titel": m.get("title") or "",
                    "datum": _tag(m.get("date")), "status": WORKFLOW.get(ws, ws), "status_key": ws, "zeichen": WORKFLOW_ZEICHEN.get(ws, "•"), "stufen": stufen,
                    "montage": _tag(m.get("montage_am")) if m.get("montage_am") else "", "fotos": fotos, "skizzen": skizzen, "archiviert": bool(m.get("archived")),
                    "cad_teile": len(teile_je.get(m.get("id"), [])), "cad_auftraege": len(auftr_je.get(m.get("id"), []))})
    out.sort(key=lambda x: (x["archiviert"], x["status_key"] == "abgeschlossen", -(x["id"] or 0)))
    return out


def rapporte(zeilen):
    out = []
    for r in zeilen or []:
        arbeit = [e for e in _liste(r.get("work_entries")) if isinstance(e, dict)]
        stunden = sum(_zahl(e.get("hours")) for e in arbeit)
        personen = sorted({e.get("employee") for e in arbeit if e.get("employee")})
        out.append({"id": r.get("id"), "datum": _tag(r.get("date")), "stunden": round(stunden, 2), "personen": personen, "arbeiten": [str(e.get("desc") or "")[:100] for e in arbeit[:3]],
                    "material": len(_liste(r.get("material_entries"))), "fotos": len(_liste(r.get("photo_paths")))})
    out.sort(key=lambda x: x["datum"], reverse=True)
    return out


def termine(zeilen):
    out = []
    for t in zeilen or []:
        von, bis = _tag(t.get("start_datum")), _tag(t.get("ende_datum"))
        zeit = " ".join(x for x in (str(t.get("start_zeit") or "")[:5], ("– " + str(t.get("ende_zeit"))[:5]) if t.get("ende_zeit") else "") if x)
        out.append({"id": t.get("id"), "aenderbar": (t.get("quelle") or "app") == "app" and not t.get("abo_id") and t.get("id") is not None, "quelle": t.get("quelle") or "app",
                    "start": str(t.get("start_datum") or "")[:10], "ende": str(t.get("ende_datum") or "")[:10], "start_zeit": str(t.get("start_zeit") or "")[:5],
                    "ende_zeit": str(t.get("ende_zeit") or "")[:5], "titel": t.get("titel") or "", "wann": (von if not bis or bis == von else "%s – %s" % (von, bis)) + ((" " + zeit) if zeit else ""),
                    "sortierung": str(t.get("start_datum") or ""), "ort": t.get("ort") or "", "notiz": t.get("notiz") or "", "mitarbeiter": _liste(t.get("mitarbeiter"))})
    out.sort(key=lambda x: x["sortierung"])
    return out


def naechster_termin(zeilen, heute=None):
    heute = heute or datetime.date.today().isoformat()
    kommende = [t for t in termine(zeilen) if t["sortierung"][:10] >= heute]
    return kommende[0] if kommende else None


def dateien(zeilen):
    def gr(b):
        b = _zahl(b)
        return "%.1f MB" % (b / 1048576) if b >= 1048576 else "%d KB" % max(1, round(b / 1024)) if b else ""
    return [{"id": f.get("id"), "name": f.get("name") or "", "groesse": gr(f.get("size_bytes")), "typ": f.get("mime_type") or "", "datum": _tag(f.get("created_at")),
             "pfad": f.get("file_path") or ""} for f in sorted(zeilen or [], key=lambda x: str(x.get("created_at") or ""), reverse=True)]


def offerten(zeilen):
    return [{"id": o.get("id"), "nr": o.get("offert_nr") or "", "titel": o.get("title") or "", "datum": _tag(o.get("date")), "gueltig_bis": _tag(o.get("gueltig_bis")),
             "kunde": o.get("kunde_name") or "", "positionen": len(_liste(o.get("positionen"))), "pdf": o.get("pdf_name") or ""}
            for o in sorted(zeilen or [], key=lambda x: str(x.get("date") or ""), reverse=True)]


def leistungen(zeilen):
    return [{"bezeichnung": l.get("bezeichnung") or "", "status": l.get("status") or "", "menge": l.get("menge"), "einheit": l.get("einheit") or "",
             "ausgefuehrt": l.get("ausgefuehrte_menge")} for l in zeilen or []]


def cad(teile, auftraege, massaufnahmen_zeilen):
    """CAD-Teile und gesendete Aufträge mit dem Stand der Werkstatt (Status der verknüpften Massaufnahme: gerüstet, montiert …)."""
    ws = {m.get("id"): m for m in massaufnahmen_zeilen or []}

    def werkstatt(mid):
        m = ws.get(mid)
        if not m:
            return ""
        k = m.get("workflow_status") or "in_bearbeitung"
        s = WORKFLOW.get(k, k)
        if m.get("montiert_am"):
            s += " (montiert %s)" % _tag(m["montiert_am"])
        elif m.get("geruestet_am"):
            s += " (gerüstet %s)" % _tag(m["geruestet_am"])
        return s
    t_out = [{"label": t.get("teil_label") or str(t.get("teil_nr") or ""), "name": t.get("name") or "", "stueck": t.get("stueck") or 1, "material": t.get("material_name") or "",
              "app": "in der App übernommen" if t.get("measurement_id") else "noch nicht übernommen", "werkstatt": werkstatt(t.get("measurement_id")),
              "geaendert": _zeit(t.get("geaendert_am"))} for t in sorted(teile or [], key=lambda x: x.get("teil_nr") or 0)]
    a_out = [{"id": a.get("id"), "titel": a.get("titel") or "Profil", "laenge": a.get("laenge_mm"), "stueck": a.get("stueck") or 1,
              "status": AUFTRAG_STATUS.get(a.get("status"), a.get("status") or ""), "status_key": a.get("status") or "", "gebaut": _zeit(a.get("gebaut_am")) if a.get("gebaut_am") else "",
              "werkstatt": werkstatt(a.get("measurement_id"))} for a in auftraege or [] if a.get("status") != "storniert"]
    return {"teile": t_out, "auftraege": a_out}


def neu_seit(daten, gesehen):
    """Was ist seit `gesehen` (ISO-Zeit; leer = noch nie angesehen) in der App neu oder geändert? → {'offene_auftraege', 'massaufnahmen', 'werkstatt', 'rapporte', 'dateien', 'termine', 'text'}.
    Beim ersten Mal (gesehen leer) wird nur gezählt, was wartet (offene Aufträge) – nicht alles andere als «neu» gemeldet."""
    g = str(gesehen or "")
    gd = utc(g) if g else None
    g = g if gd is not None else ""             # unlesbarer Zeitpunkt wie «noch nie gesehen» behandeln
    n = {"offene_auftraege": sum(1 for a in daten.get("auftraege", []) if a.get("status") == "offen"), "massaufnahmen": 0, "werkstatt": 0, "rapporte": 0, "dateien": 0, "termine": 0}
    if g:
        n["massaufnahmen"] = sum(1 for m in daten.get("massaufnahmen", []) if _neuer_als(m.get("created_at"), gd))
        n["werkstatt"] = sum(1 for m in daten.get("massaufnahmen", []) for f in ("freigegeben_am", "geruestet_am", "montiert_am") if _neuer_als(m.get(f), gd))
        n["rapporte"] = sum(1 for r in daten.get("rapporte", []) if _neuer_als(r.get("created_at"), gd))
        n["dateien"] = sum(1 for f in daten.get("dateien", []) if _neuer_als(f.get("created_at"), gd) and f.get("created_by") is not None)
        n["termine"] = sum(1 for t in daten.get("termine", []) if _neuer_als(t.get("created_at"), gd))
    teile = []
    if n["offene_auftraege"]:
        teile.append("%d Auftrag%s aus der App wartet%s" % (n["offene_auftraege"], "" if n["offene_auftraege"] == 1 else "e", "" if n["offene_auftraege"] == 1 else "n"))
    if n["massaufnahmen"]:
        teile.append("%d neue Massaufnahme%s" % (n["massaufnahmen"], "" if n["massaufnahmen"] == 1 else "n"))
    if n["werkstatt"]:
        teile.append("%d Werkstatt-Schritt%s" % (n["werkstatt"], "" if n["werkstatt"] == 1 else "e"))
    if n["rapporte"]:
        teile.append("%d neuer Rapport" % n["rapporte"] if n["rapporte"] == 1 else "%d neue Rapporte" % n["rapporte"])
    if n["dateien"]:
        teile.append("%d neue Datei%s" % (n["dateien"], "" if n["dateien"] == 1 else "en"))
    if n["termine"]:
        teile.append("%d neuer Termin" % n["termine"] if n["termine"] == 1 else "%d neue Termine" % n["termine"])
    n["text"] = ", ".join(teile)
    n["gesamt"] = sum(v for k, v in n.items() if k not in ("text", "gesamt"))
    return n


def karte(roh, personen=None, heute=None):
    """Alles zusammen. roh: {'projekt', 'massaufnahmen', 'rapporte', 'termine', 'dateien', 'offerten', 'leistungen', 'teile', 'auftraege'} (Zeilen der App)."""
    ma = massaufnahmen(roh.get("massaufnahmen"), roh.get("teile"), roh.get("auftraege"))
    return {"kopf": kopf(roh.get("projekt"), personen), "massaufnahmen": ma, "rapporte": rapporte(roh.get("rapporte")), "termine": termine(roh.get("termine")),
            "naechster_termin": naechster_termin(roh.get("termine"), heute), "dateien": dateien(roh.get("dateien")), "offerten": offerten(roh.get("offerten")),
            "leistungen": leistungen(roh.get("leistungen")), "cad": cad(roh.get("teile"), roh.get("auftraege"), roh.get("massaufnahmen")),
            "zaehler": {"massaufnahmen": len(ma), "aktiv": sum(1 for m in ma if not m["archiviert"] and m["status_key"] != "abgeschlossen")}}

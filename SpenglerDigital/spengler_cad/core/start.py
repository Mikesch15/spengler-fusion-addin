"""Start/Übersicht und Voraussetzungen: was ist eingerichtet, was fehlt, was ist der sinnvolle nächste Schritt – und welche Befehle dürfen erst laufen,
wenn ein Auftrag aktiv ist. Reine Logik ohne Fusion (der Zustand wird vom Befehl gesammelt)."""

SCHRITTE = [  # (Schlüssel, Befehlsname) – Reihenfolge der Auswahl im Startfenster
    ("auftrag_wahl", "Auftrag wählen"), ("auftrag_neu", "Neuer Auftrag"), ("abgleich", "Aufträge abgleichen"), ("kanten", "Kanten bearbeiten"),
    ("zuschnitt", "Stückliste & Zuschnitt"), ("einstellungen", "Vorlagen & Einstellungen"), ("nichts", "– nur ansehen –")]

BEFEHL_ID = {"auftrag_wahl": "spenglerAuftragWaehlen", "auftrag_neu": "spenglerNeuerAuftrag", "abgleich": "spenglerAuftraegeAbgleichen",
             "kanten": "spenglerKantenBearbeiten", "zuschnitt": "spenglerMaterialZuschnitt", "einstellungen": "spenglerVorlagenEinstellungen"}

# Befehle, die einen aktiven Auftrag verlangen (Schlüssel = Befehls-ID)
BRAUCHT_AUFTRAG = {"spenglerKantenBearbeiten": "Kanten bearbeiten", "spenglerAbwicklungDxf": "Abwicklung & DXF",
                   "spenglerMaterialZuschnitt": "Stückliste & Zuschnitt", "spenglerRundblech": "Rundblech / Umformung", "spenglerBauteil": "Bauteil erstellen"}
BRAUCHT_MATERIAL = {"spenglerKantenBearbeiten", "spenglerMaterialZuschnitt", "spenglerBauteil"}


def ablauf(z):
    """Schrittleiste: [(Name, True/False/None)] – None = lässt sich nicht automatisch feststellen."""
    if z.get("ablage") and not z.get("auftrag"):
        return [("Ablage", True), ("Material", bool(z.get("material_gewaehlt"))), ("Kanten", None), ("Prüfen & Zuschnitt", None)]
    return [("Auftrag", bool(z.get("auftrag")) and bool(z.get("dokument_gespeichert"))), ("Material", bool(z.get("material_gewaehlt"))), ("Kanten", None),
            ("Prüfen & Zuschnitt", None), ("App", True if z.get("projekt_in_app") else (False if z.get("projekt_in_app") is False else None))]


def ablauf_text(z):
    return "  ›  ".join(("✅ " if ok else "⬜ " if ok is False else "▫ ") + n for n, ok in ablauf(z))


def bewerte(z):
    """z: {'angemeldet': bool, 'auftrag': str, 'objekt': str, 'projekt_in_app': True/False/None (unbekannt/nicht geprüft), 'materialien': int, 'vorlagen': int,
    'dokument_gespeichert': bool, 'fehlende_funktionen': [str]} → {'zeilen': [{'ok': True/False/None, 'text': str}], 'naechster': Schlüssel aus SCHRITTE}"""
    zeilen = []

    def z_(ok, text):
        zeilen.append({"ok": ok, "text": text})
    z_(bool(z.get("angemeldet")), "Konto: angemeldet" if z.get("angemeldet") else "Konto: nicht angemeldet (Vorlagen-Abgleich, App-Verbindung und Updates brauchen die Anmeldung)")
    z_(z.get("materialien", 0) > 0, "Materialprofile: %d" % z.get("materialien", 0) if z.get("materialien", 0) else "Materialprofile: keine – zuerst eines anlegen")
    z_(z.get("vorlagen", 0) > 0, "Kantenvorlagen: %d" % z.get("vorlagen", 0) if z.get("vorlagen", 0) else "Kantenvorlagen: keine – zuerst eine anlegen")
    if z.get("auftrag"):
        z_(True, "Aktiver Auftrag: %s %s" % (z["auftrag"], z.get("objekt") or ""))
        p = z.get("projekt_in_app")
        if p is True:
            z_(True, "Projekt in der App: gefunden")
        elif p is False:
            z_(False, "Projekt in der App: nicht gefunden – «Aufträge abgleichen» legt es an")
        z_(bool(z.get("dokument_gespeichert")), "Dokument: im Auftragsordner gespeichert" if z.get("dokument_gespeichert")
           else "Dokument: noch nicht im Auftragsordner gespeichert (Auftrag wählen → Haken «Dokument speichern»)")
    elif z.get("ablage"):
        z_(True, "Aktive Ablage: %s (kein Kundenauftrag – Exporte im eigenen Ordner, nichts geht an die App)" % z["ablage"])
    else:
        z_(False, "Aktiver Auftrag: keiner – bitte «Auftrag wählen», «Neuer Auftrag» oder «Andere Ablage»")
    info = z.get("projekt_info")
    if info:
        z_(None, "Projekt: " + " · ".join(x for x in (info.get("kunde"), info.get("status"), ("Nächster Termin: " + info["termin"]) if info.get("termin") else "",
                                                       ("%d aktive Massaufnahme%s" % (info["aktiv"], "" if info["aktiv"] == 1 else "n")) if info.get("aktiv") else "") if x))
        if info.get("hinweis"):
            z_(None, "Hinweis im Projekt: " + info["hinweis"][:160])
    neu = z.get("app_neu") or {}
    if neu.get("text"):
        z_(None, "🔔 Neu aus der App: " + neu["text"] + " (Details: Palette → Register «Projekt»)")
    fehlt = z.get("fehlende_funktionen") or []
    if fehlt:
        z_(None, "Diese Fusion-Version kann nicht alles: " + "; ".join(fehlt[:3]) + (" …" if len(fehlt) > 3 else ""))
    # nächster sinnvoller Schritt
    if z.get("materialien", 0) == 0 or z.get("vorlagen", 0) == 0:
        n = "einstellungen"
    elif not z.get("auftrag") and not z.get("ablage"):
        n = "auftrag_wahl"
    elif z.get("projekt_in_app") is False:
        n = "abgleich"
    else:
        n = "kanten"
    return {"zeilen": zeilen, "naechster": n, "ablauf": ablauf_text(z)}


def voraussetzungen(befehl_id, z, auftrag_erforderlich=True):
    """→ (Probleme [Text], Lösungsbefehl-ID oder None). Leere Liste = Befehl darf laufen."""
    probleme, loesung = [], None
    if auftrag_erforderlich and befehl_id in BRAUCHT_AUFTRAG and not z.get("auftrag") and not z.get("ablage"):
        probleme.append("Es ist weder ein Auftrag noch eine Ablage aktiv. «%s» arbeitet immer für einen Auftrag (Teilenummern, Exportordner, App) – oder in einer «Anderen Ablage» für Modelle ohne Kundenauftrag." % BRAUCHT_AUFTRAG[befehl_id])
        loesung = "spenglerAuftragWaehlen"
    if befehl_id in BRAUCHT_MATERIAL and z.get("materialien", 0) == 0:
        probleme.append("Es gibt noch kein Materialprofil. Bitte zuerst unter «Vorlagen & Einstellungen → Materialien» eines anlegen.")
        loesung = loesung or "spenglerVorlagenEinstellungen"
    if befehl_id == "spenglerKantenBearbeiten" and z.get("vorlagen", 0) == 0:
        probleme.append("Es gibt noch keine Kantenvorlage (Im Expertenmodus kann eine Folge direkt eingegeben werden).")
    return probleme, loesung

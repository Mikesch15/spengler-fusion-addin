"""CAD-Teil ↔ Massaufnahme «Freies Profil» der Spengler-Digital-App. Reine Logik ohne Fusion.

App-Format (data der Massaufnahme, siehe js/14, js/31 der App):
  schenkel: [{laenge, winkel}] – winkel = Drehung gegenüber dem vorigen Schenkel (kumulativ, 180 = Umschlag); der erste Schenkel startet bei 0.
  segmente: [{laenge, massen: [{mass, links, rechts}]}] – je Segment die Länge des Streifens und je Schenkel das Mass; die Abwicklungsbreite der App
            ist die Summe der Masse.
Das CAD schickt Daten, die die App mit measurementAlsVorlage() in ihr eigenes Formular lädt; gerechnet und gespeichert wird dann von der App selbst."""

ART = "freies_profil"


def schenkel_aus_operationen(ops, basis_laenge):
    """CAD-Folge (Flansch/Umschlag, + links / − rechts) → App-Schenkel. Der erste Schenkel ist das bestehende Blech (Länge basis_laenge)."""
    schenkel = [{"laenge": round(float(basis_laenge), 2), "winkel": 0}]
    for op in ops:
        w = 180 if op["typ"] == "umschlag" else op["winkel"]
        schenkel.append({"laenge": round(float(op["laenge"]), 2), "winkel": round(float(w), 2)})
    return schenkel


def app_daten(teil, ops, material_name=""):
    """Teil des CAD → (art, data) für measurementAlsVorlage. teil: {'breite' (Zuschnittbreite mm = Abwicklung), 'laenge' (Streifenlänge mm)}.
    Der erste Schenkel ist so lang, dass die Summe der Masse die Abwicklungsbreite des CAD ergibt (Rest = Breite − Summe der übrigen Schenkel);
    ist das nicht positiv, bleibt die Breite offen (Hinweis) und der erste Schenkel erhält 0."""
    rest = sum(float(o["laenge"]) for o in ops)
    basis = teil["breite"] - rest
    hinweise = []
    if basis <= 0:
        hinweise.append("Die Schenkel sind zusammen länger als die Abwicklungsbreite – erster Schenkel 0, Breite bitte in der App prüfen.")
        basis = 0.0
    schenkel = schenkel_aus_operationen(ops, basis)
    massen = [{"mass": s["laenge"], "links": s["laenge"], "rechts": 0} for s in schenkel]
    data = {"material": "", "konisch": "nein", "ansicht": "rechts", "schenkel": schenkel,
            "segmente": [{"laenge": round(float(teil["laenge"]), 2), "massen": massen}],
            "cad": {"material_name": material_name, "abwicklung_breite_mm": round(float(teil["breite"]), 2)}}
    return ART, data, hinweise


def operationen_aus_app(schenkel):
    """App-Schenkel → CAD-Operationen: der erste Schenkel (bestehendes Blech) entfällt, jeder weitere ist ein Flansch (Winkel 180 → Umschlag).
    Winkel > 180 (App-Schreibweise 0–360) werden auf −180…180 gebracht. → (Operationen, Hinweise)."""
    ops, hinweise = [], []
    for i, s in enumerate(schenkel or []):
        if i == 0:
            continue
        try:
            L, w = float(s["laenge"]), float(s["winkel"])
        except (KeyError, TypeError, ValueError):
            hinweise.append("Schenkel %d ist unvollständig und wurde übersprungen." % (i + 1))
            continue
        w = ((w + 180.0) % 360.0) - 180.0
        if abs(abs(w) - 180.0) < 0.5:
            ops.append({"typ": "umschlag", "winkel": 180.0, "laenge": round(L, 2), "radius": None})
        elif abs(w) < 0.5:
            hinweise.append("Schenkel %d liegt gerade weiter (Winkel 0) – er ist keine Biegung und wurde übersprungen." % (i + 1))
        elif L > 0:
            ops.append({"typ": "flansch", "winkel": round(w, 2), "laenge": round(L, 2), "radius": None})
    if schenkel:
        hinweise.append("Der erste Schenkel (%g mm) ist das bestehende Blech und gehört nicht zur Vorlage." % float(schenkel[0].get("laenge") or 0))
    return ops, hinweise


def grundblech_aus_app(daten):
    """Massaufnahme der App (data) → {'breite', 'laenge', 'ops', 'hinweise'} für das Blech im CAD.
    breite = erster Schenkel (bestehendes Blech), laenge = längstes Segment (Streifenlänge) oder None, wenn die App keine nennt."""
    daten = daten or {}
    schenkel = daten.get("schenkel") or []
    ops, hinweise = operationen_aus_app(schenkel)
    breite = None
    if schenkel:
        try:
            breite = float(schenkel[0].get("laenge"))
        except (TypeError, ValueError):
            breite = None
    if not breite or breite < 5:
        hinweise.append("Der erste Schenkel fehlt oder ist sehr kurz – Breite des Grundblechs 100 mm angenommen, bitte prüfen.")
        breite = 100.0
    laengen = []
    for sg in daten.get("segmente") or []:
        try:
            laengen.append(float(sg.get("laenge")))
        except (TypeError, ValueError, AttributeError):
            pass
    laenge = max(laengen) if laengen and max(laengen) > 0 else None
    if laenge is None:
        hinweise.append("Die Massaufnahme nennt keine Länge – bitte im Dialog eintragen.")
    return {"breite": breite, "laenge": laenge, "ops": ops, "hinweise": hinweise}


def teile_zeilen(teile, auftrag, dokument, projekt_id=None, version=""):
    """Teile des CAD (wie in «Stückliste & Zuschnitt») → Zeilen für die Tabelle cad_teile der App.
    teile: [{'nr_zahl','nr' (Anzeige), 'name','stueck','breite','laenge','flaeche','material' (Profil),'operationen','vorlage','vorlageVersion'}]"""
    zeilen = []
    for i, t in enumerate(teile, 1):
        m = t.get("material") or {}
        ops = t.get("operationen") or []
        data, hinweise = {}, []
        if ops:
            _, data, hinweise = app_daten(t, ops, m.get("name", ""))
        nr = t.get("nr_zahl")
        zeilen.append({"project_id": projekt_id, "auftrag": str(auftrag), "dokument": dokument or "", "teil_nr": int(nr) if isinstance(nr, int) else i,
                       "teil_label": str(t.get("nr", "")), "name": t["name"], "stueck": int(t.get("stueck") or 1), "material_name": m.get("name", ""),
                       "staerke_mm": m.get("thickness"), "zuschnitt_breite_mm": round(t["breite"], 2), "zuschnitt_laenge_mm": round(t["laenge"], 2),
                       "flaeche_mm2": round(t["flaeche"], 1) if t.get("flaeche") is not None else None, "vorlage_name": t.get("vorlage") or "",
                       "vorlage_version": t.get("vorlageVersion") if isinstance(t.get("vorlageVersion"), int) else None, "operationen": ops,
                       "app_data": data, "addin_version": version})
    return zeilen

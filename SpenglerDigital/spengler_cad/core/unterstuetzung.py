"""Unterstützungs- und Machbarkeitsmatrix: welche Bearbeitung auf welcher FLÄCHE mit welcher KANTE – an EINER Stelle, damit Eignungsprüfung,
Adapter-Sperre, Meldungen und Doku übereinstimmen (Korrekturauftrag 5.11.2026: Kantentyp UND angrenzender Flächentyp zählen; eine gerade Kante
auf einem Zylinder ist KEIN ebener Fall).

Flächenklassen: eben | zylinder | kegel | einfach_gekruemmt (abwickelbar, aber weder Kreiszylinder noch Kreiskegel, z. B. elliptisch) |
doppelt_gekruemmt (Kugel, Torus) | freiform | unbekannt.   Kantentypen: gerade | bogen | kreis | kurve.
Stand: 'ja' (implementiert) | 'eingeschraenkt' (implementiert, mit genannter Grenze) | 'prototyp' (implementiert, im normalen Bau GESPERRT bis
ein Fusion-Live-Test bestanden ist; nur der Live-Test darf ihn ausführen) | 'nein' (abgelehnt, mit Grund).
Der Live-/Freigabestand steht bewusst NICHT hier, sondern im Statusdokument: implementiert ist nicht getestet und nicht freigegeben."""

FLAECHEN = ("eben", "zylinder", "kegel", "einfach_gekruemmt", "doppelt_gekruemmt", "freiform")
KANTEN = ("gerade", "bogen", "kreis", "kurve")
FLAECHEN_TEXT = {"eben": "eben", "zylinder": "Zylinder", "kegel": "Kegel", "einfach_gekruemmt": "einfach gekrümmt", "doppelt_gekruemmt": "doppelt gekrümmt",
                 "freiform": "Freiform", "unbekannt": "unbekannt"}
KANTEN_TEXT = {"gerade": "gerade Kante", "bogen": "Kreisbogen", "kreis": "Kreis", "kurve": "sonstige Kurve"}
OPS = ("grundblech", "flansch", "mehrkant_gehrung", "umschlag", "doppelfalz", "versatz", "abwicklung", "detail_starr", "detail_anpassen")
OP_TEXT = {"grundblech": "Grundblech", "flansch": "Flansch", "mehrkant_gehrung": "Mehrkantflansch mit Gehrung", "umschlag": "Umschlag", "doppelfalz": "Doppelfalz",
           "versatz": "Versatz", "abwicklung": "Abwicklung / DXF", "detail_starr": "3D-Detail starr", "detail_anpassen": "3D-Detail an Fläche angepasst"}
STAND_TEXT = {"ja": "implementiert", "eingeschraenkt": "eingeschränkt", "prototyp": "Prototyp (gesperrt)", "nein": "nicht unterstützt"}
KANTEN_OPS = ("flansch", "mehrkant_gehrung", "umschlag", "doppelfalz")


def flaechenklasse(typ):
    """Typ der Geometrie-Referenz (eben, zylinder, kegel, einfach_gekruemmt, kugel, torus, freiform, unbekannt) → Flächenklasse."""
    if typ in ("kugel", "torus"):
        return "doppelt_gekruemmt"
    return typ if typ in FLAECHEN else "unbekannt"


def kantentyp(kurve):
    """Kurventyp (linie, bogen, kreis, ellipse, spline, andere, None) → Kantentyp. Keine Kante (Flächenoperation) gilt als 'gerade'."""
    if kurve in (None, "linie"):
        return "gerade"
    return kurve if kurve in ("bogen", "kreis") else "kurve"


def _api_nur_gerade(op):
    return ("nein", "%s: Fusions Blech-Schnittstelle (EdgeFlange/Hem, Preview) ist nur für gerade Kanten beschrieben; der Live-Test fragt Fusion an, "
                    "freigegeben wird erst nach bestätigtem Ergebnis" % OP_TEXT[op])


def stand(op, flaeche, kante="gerade"):
    """→ ('ja'|'eingeschraenkt'|'prototyp'|'nein', Grund). Unbekannte Flächen/Kanten werden immer abgelehnt (keine stille Umdeutung zu «eben»)."""
    if op not in OPS:
        return "nein", "unbekannte Bearbeitung"
    if flaeche not in FLAECHEN:
        return "nein", "Flächentyp unbekannt – keine Bearbeitung ohne sichere Erkennung"
    if kante not in KANTEN:
        return "nein", "Kantentyp unbekannt"
    if op == "grundblech":
        if flaeche == "eben":
            return "ja", "ebenes Profil aus Linien und Bögen"
        return "nein", "Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)"
    if op == "abwicklung":                        # Körperoperation – Kantentyp ohne Bedeutung
        return {"eben": ("ja", "Fusion-Abwicklung + DXF-Gegenprobe"),
                "zylinder": ("eingeschraenkt", "exakt abwickelbar; nur wenn Fusion den Körper als Blech abwickelt"),
                "kegel": ("eingeschraenkt", "exakt abwickelbar; nur wenn Fusion den Körper als Blech abwickelt"),
                "einfach_gekruemmt": ("eingeschraenkt", "mathematisch abwickelbar; Fusion entscheidet, kein eigener Nachweis"),
                "doppelt_gekruemmt": ("nein", "Gausssche Krümmung ≠ 0 – keine exakte Abwicklung, keine DXF als exakt"),
                "freiform": ("nein", "Abwickelbarkeit nicht nachgewiesen – keine DXF als exakt; Näherung ist ein eigener, noch fehlender Modus")}[flaeche]
    if op == "detail_starr":
        if flaeche == "eben" and kante == "gerade":
            return "ja", "Rahmen an der Kante"
        return "eingeschraenkt", "starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen"
    if op == "detail_anpassen":
        if flaeche == "zylinder" and kante in ("gerade", "bogen", "kreis"):
            return "prototyp", "nur Vorlagen mit Anschlussradius-Parameter: der Radius wird auf den Zylinderradius gesetzt (keine freie Verformung)"
        if flaeche == "eben":
            return "nein", "auf ebener Fläche gibt es nichts anzupassen – starr einsetzen"
        return "nein", "keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt"
    if op == "versatz":
        if flaeche == "eben" and kante == "gerade":
            return "ja", "Biegelinie in der Blechebene senkrecht zur Kante verschoben"
        if flaeche == "zylinder" and kante == "gerade":
            return "prototyp", "gerade Kante parallel zur Zylinderachse: Versatz als Bogenlänge entlang des Mantels (Drehschnitt/-anfügung um die Achse, exakt)"
        if flaeche == "kegel":
            return "nein", "Kegel: tangentialer Versatz einer Mantellinie ist eine Drehung um die Spitze, Normal- und Radialrichtung unterscheiden sich – noch nicht umgesetzt"
        return "nein", "kein eindeutig definierter Versatz für diese Geometrie"
    # Kanten-Operationen
    if flaeche == "eben":
        if kante != "gerade":
            return _api_nur_gerade(op)
        if op == "mehrkant_gehrung":
            return "eingeschraenkt", "Kette gerader Kanten an einem Körper; Eckspalt wird gemessen"
        if op == "doppelfalz":
            return "eingeschraenkt", "als Kantenfolge Flansch + Umschläge"
        return "ja", ""
    if flaeche == "zylinder" and kante == "gerade":
        if op in ("flansch", "umschlag"):
            return "prototyp", "gerade Kante parallel zur Achse eines gerollten Blechsegments, Fusion-native %s; gesperrt bis Live-Test" % (
                "EdgeFlange" if op == "flansch" else "Hem")
        return "nein", "erst nach bestandenem Einzelkanten-Prototyp"
    if flaeche == "zylinder":
        return "nein", "%s entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test" % OP_TEXT[op]
    if flaeche == "kegel":
        return "nein", "kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben"
    return "nein", "%s auf %s: keine eindeutige, exakte Geometrie" % (OP_TEXT[op], FLAECHEN_TEXT[flaeche])


def pruefen(op, flaeche, kante="gerade", prototyp_erlaubt=False):
    """→ None (erlaubt) oder Text, warum nicht. 'prototyp' ist nur mit prototyp_erlaubt=True (Live-Test) erlaubt."""
    s, grund = stand(op, flaeche, kante)
    if s == "nein" or (s == "prototyp" and not prototyp_erlaubt):
        return "%s an %s auf «%s» %s: %s." % (OP_TEXT.get(op, op), KANTEN_TEXT.get(kante, kante), FLAECHEN_TEXT.get(flaeche, flaeche),
                                              "ist ein gesperrter Prototyp (erst nach bestandenem Fusion-Live-Test)" if s == "prototyp" else "wird nicht unterstützt", grund)
    return None


def hinweis(op, flaeche, kante="gerade"):
    """Einschränkung, die im Bauplan/Bericht angezeigt wird (None bei uneingeschränkt)."""
    s, grund = stand(op, flaeche, kante)
    if s in ("eingeschraenkt", "prototyp") and grund:
        return "%s (%s, %s) – %s: %s" % (OP_TEXT[op], FLAECHEN_TEXT[flaeche], KANTEN_TEXT[kante], STAND_TEXT[s], grund)
    return None


# ------------------------------------------------------------------ Machbarkeit (Doku, Phase 2)
def machbarkeit(op, flaeche, kante):
    """Technische Einordnung für die Doku: möglich?, Fusion-nativ?, eindeutig?, exakt/angenähert, Grenze, nötiger Live-Test."""
    s, grund = stand(op, flaeche, kante)
    doppelt = flaeche in ("doppelt_gekruemmt", "freiform")
    nativ = {"flansch": "EdgeFlange (Preview)", "mehrkant_gehrung": "EdgeFlange mehrere Kanten", "umschlag": "Hem (Preview)", "doppelfalz": "EdgeFlange + Hem",
             "versatz": "Extrude/Revolve (Schnitt/Anfügen)", "abwicklung": "FlatPattern", "detail_starr": "Import + Transform", "detail_anpassen": "Benutzerparameter",
             "grundblech": "BaseFlange (Preview)"}[op]
    return {"stand": s, "grund": grund, "nativ": nativ, "eindeutig": "nein" if doppelt and op in ("versatz", "detail_anpassen") else "ja",
            "exakt": "nicht exakt" if doppelt else "exakt", "live": "nötig" if s in ("ja", "eingeschraenkt", "prototyp") else "Live-Anfrage (Ablehnung bestätigen)"}


def als_markdown():
    """Tabelle je Bearbeitung: Zeilen = Flächenklasse, Spalten = Kantentyp, Wert = Stand. Danach die Gründe/Grenzen der nicht trivialen Fälle."""
    zeilen = ["| Bearbeitung | Fläche | " + " | ".join(KANTEN_TEXT[k] for k in KANTEN) + " |", "|---" * (len(KANTEN) + 2) + "|"]
    for op in OPS:
        for f in FLAECHEN:
            zeilen.append("| %s | %s | %s |" % (OP_TEXT[op], FLAECHEN_TEXT[f], " | ".join(STAND_TEXT[stand(op, f, k)[0]] for k in KANTEN)))
    gruende = []
    for op in OPS:
        for f in FLAECHEN:
            for k in KANTEN:
                s, g = stand(op, f, k)
                eintrag = "- **%s / %s** (%s): %s" % (OP_TEXT[op], FLAECHEN_TEXT[f], STAND_TEXT[s], g)
                if g and eintrag not in gruende and f != "eben":
                    gruende.append(eintrag)
    return "\n".join(zeilen) + "\n\nGrenzen und Gründe (gekrümmte Fälle):\n" + "\n".join(gruende)


def machbarkeit_markdown():
    """Technische Machbarkeit je Bearbeitung × gekrümmter Flächenklasse (Phase 2 Korrekturauftrag): Stand an gerader Kante bzw. Bogen/Kreis,
    Fusion-native Funktion, mathematisch eindeutig, exakt/angenähert, nötiger Live-Test."""
    z = ["| Bearbeitung | Fläche | gerade Kante | Bogen/Kreis | Fusion-nativ | eindeutig | exakt | Live-Test |", "|---|---|---|---|---|---|---|---|"]
    for op in OPS:
        for f in FLAECHEN:
            if f == "eben":
                continue
            m = machbarkeit(op, f, "gerade")
            z.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (OP_TEXT[op], FLAECHEN_TEXT[f], STAND_TEXT[m["stand"]], STAND_TEXT[stand(op, f, "bogen")[0]],
                                                                   m["nativ"], m["eindeutig"], m["exakt"], m["live"]))
    return "\n".join(z)

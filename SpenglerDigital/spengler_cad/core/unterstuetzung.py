"""Unterstützungs- und Machbarkeitsmatrix: welche Bearbeitung auf welcher FLÄCHE mit welcher KANTE – an EINER Stelle, damit Eignungsprüfung,
Adapter-Sperre, Meldungen und Doku übereinstimmen (Korrekturauftrag 5.11.2026: Kantentyp UND angrenzender Flächentyp zählen; eine gerade Kante
auf einem Zylinder ist KEIN ebener Fall).

Flächenklassen: eben | zylinder | kegel | einfach_gekruemmt (abwickelbar, aber weder Kreiszylinder noch Kreiskegel, z. B. elliptisch) |
doppelt_gekruemmt (Kugel, Torus) | freiform | unbekannt.   Kantentypen: gerade | bogen | kreis | kurve.
Stand: 'ja' (implementiert) | 'eingeschraenkt' (implementiert, mit genannter Grenze) | 'prototyp' (implementiert, im normalen Bau GESPERRT bis
ein Fusion-Live-Test bestanden ist; nur der Live-Test darf ihn ausführen) | 'nein' (abgelehnt, mit Grund).
Der Live-/Freigabestand steht bewusst NICHT hier, sondern im Statusdokument: implementiert ist nicht getestet und nicht freigegeben."""

FLAECHEN = ("eben", "zylinder", "kegel", "einfach_gekruemmt", "doppelt_gekruemmt", "freiform")
KANTEN = ("gerade", "bogen", "kreis", "ellipse", "kurve", "kette")
FLAECHEN_TEXT = {"eben": "eben", "zylinder": "Zylinder", "kegel": "Kegel", "einfach_gekruemmt": "einfach gekrümmt", "doppelt_gekruemmt": "doppelt gekrümmt",
                 "freiform": "Freiform", "unbekannt": "unbekannt"}
KANTEN_TEXT = {"gerade": "gerade Kante", "bogen": "Kreisbogen", "kreis": "Kreis", "ellipse": "Ellipse", "kurve": "Spline/freie Kurve",
               "kette": "Kette aus Linien und Bögen"}
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
    if kurve in ("bogen", "kreis", "ellipse", "kette"):
        return kurve
    return "kurve"


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
                "zylinder": ("eingeschraenkt", "mathematisch abwickelbar; nur wenn Fusion den Körper als Blech abwickelt"),
                "kegel": ("eingeschraenkt", "mathematisch abwickelbar; nur wenn Fusion den Körper als Blech abwickelt"),
                "einfach_gekruemmt": ("eingeschraenkt", "mathematisch abwickelbar; Fusion entscheidet, kein eigener Nachweis"),
                "doppelt_gekruemmt": ("nein", "Gausssche Krümmung ≠ 0 – nicht verzerrungsfrei abwickelbar, keine DXF"),
                "freiform": ("nein", "Abwickelbarkeit nicht nachgewiesen – keine DXF; Näherung ist ein eigener, noch fehlender Modus")}[flaeche]
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
            return "prototyp", "gerade Kante parallel zur Zylinderachse: Versatz als Bogenlänge entlang des Mantels (Drehschnitt/-anfügung um die Achse, geometrisch eindeutig)"
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
    return "nein", "%s auf %s: keine eindeutige, mathematisch abwickelbare Geometrie" % (OP_TEXT[op], FLAECHEN_TEXT[flaeche])


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
            "exakt": "nicht abwickelbar" if doppelt else "mathematisch abwickelbar", "live": "nötig" if s in ("ja", "eingeschraenkt", "prototyp") else "Live-Anfrage (Ablehnung bestätigen)"}


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
    z = ["| Bearbeitung | Fläche | gerade Kante | Bogen/Kreis | Fusion-nativ | eindeutig | Abwickelbarkeit (math.) | Live-Test |", "|---|---|---|---|---|---|---|---|"]
    for op in OPS:
        for f in FLAECHEN:
            if f == "eben":
                continue
            m = machbarkeit(op, f, "gerade")
            z.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (OP_TEXT[op], FLAECHEN_TEXT[f], STAND_TEXT[m["stand"]], STAND_TEXT[stand(op, f, "bogen")[0]],
                                                                   m["nativ"], m["eindeutig"], m["exakt"], m["live"]))
    return "\n".join(z)


# ------------------------------------------------------------------ Bauweise «eigene Geometrie» und geometrische Klasse a–e (Auftrag Kantenwerkzeug, Review C)
# Eine Ablehnung durch Fusions native Blech-API (EdgeFlange/Hem) ist KEIN Beweis geometrischer Unmöglichkeit. Deshalb getrennt:
#   nativ  – Fusion-Blechfunktion (stand(), oben)
#   eigen  – eigene Profilgeometrie: Querschnitt (Linien + Kreisbögen) senkrecht zur Kante, entlang einer GERADEN Kante extrudiert
#            (core/profil_engine, Adapter eigene_folge). Biegezonen sind dann Zylinder, Schenkel Ebenen → exakt abwickelbar.
#   klasse – a nativ unterstützt · b eigene exakte Geometrie möglich (implementiert oder zu prototypisieren) · c nur mit konstruktiver Änderung
#            (Freistellung/Segmentierung) · d mathematisch nicht verzerrungsfrei abwickelbar · e technisch ungeklärt
KLASSEN_AE = {"a": "native Fusion-Operation unterstützt", "b": "eigene, mathematisch abwickelbare Geometrie möglich", "c": "nur mit konstruktiver Änderung (Freistellung/Segmentierung)",
              "d": "mathematisch nicht verzerrungsfrei abwickelbar", "e": "technisch ungeklärt"}
PROFIL_OPS = ("flansch", "umschlag", "doppelfalz")      # alles, was als Querschnitts-Kette entlang der Kante entsteht


def eigen(op, flaeche, kante="gerade"):
    """Stand der Bauweise «eigene Geometrie». → ('ja'|'eingeschraenkt'|'prototyp'|'nein', Grund, Klasse a–e)."""
    if flaeche not in FLAECHEN or kante not in KANTEN:
        return "nein", "Flächen- oder Kantentyp unbekannt – keine Bearbeitung ohne sichere Erkennung", "e"
    if op in PROFIL_OPS:
        if kante == "gerade" and flaeche == "eben":
            return "eingeschraenkt", "Profil entlang gerader Kante (Linien + Kreisbögen), Masse auf Blechmitte bis virtuelle Kante; Ecken stumpf", "b"
        if kante == "gerade" and flaeche in ("zylinder", "kegel", "einfach_gekruemmt"):
            return ("prototyp", "gerade Kante = Mantellinie einer abwickelbaren Fläche: Tangentialebene längs der Kante konstant, das Profil wird "
                                "entlang der Kante extrudiert (Biegezone Zylinder, Schenkel eben) – mathematisch abwickelbar; Prüfung, dass die Normale "
                                "entlang der Kante konstant ist; gesperrt bis Live-Test", "b")
        if kante in ("bogen", "kreis") and flaeche in ("eben", "zylinder", "kegel"):
            return ("nein", "Aufkantung entlang einer Kreiskante: die Biegezone ist ein Torusabschnitt (Gausssche Krümmung ≠ 0) und der Schenkel "
                            "ein Kegel/Zylinder, der nur mit Stauchung/Streckung anschliesst – nicht verzerrungsfrei abwickelbar. Konstruktive Alternativen "
                            "(segmentierte Aufkantung mit Freistellungen, separater Zargenstreifen mit Naht) wären bewusst wählbare Varianten – "
                            "nicht umgesetzt", "d")
        if kante in ("ellipse", "kurve"):
            return "nein", "Biegezone entlang einer Kurve mit wechselnder Krümmung ist doppelt gekrümmt – nicht verzerrungsfrei abwickelbar", "d"
        if kante == "kette":
            return ("nein", "Kette aus Linien und Bögen: gerade Abschnitte einzeln möglich (b), Bogenabschnitte nicht exakt (d); an den Übergängen "
                            "wären Freistellungen nötig (c) – nicht umgesetzt", "c")
        if flaeche in ("doppelt_gekruemmt", "freiform"):
            return "nein", "Grundfläche selbst nicht (nachweislich) abwickelbar", "d"
        return "nein", "noch nicht untersucht", "e"
    if op == "mehrkant_gehrung":
        if kante == "gerade" and flaeche == "eben":
            return "nein", "Gehrung zwischen eigenen Profilen (Schnitt zweier Prismen an der Winkelhalbierenden) ist geometrisch exakt möglich – noch zu prototypisieren", "b"
        return "nein", "erst nach dem Einzelkanten-Prototyp", "e"
    if op == "versatz":
        if kante == "gerade" and flaeche == "eben":
            return "nein", "Versatz in der eigenen Profilkette = verlängerter/verkürzter Basisschenkel, exakt – noch zu prototypisieren (nativ vorhanden)", "b"
        return "nein", "Versatzart (normal/radial/tangential) muss je Fläche festgelegt werden", "e"
    s_, g = stand(op, flaeche, kante)
    return s_, g, "a" if s_ in ("ja", "eingeschraenkt") else "e"


def klasse(op, flaeche, kante="gerade"):
    """Geometrische Einordnung a–e: a, wenn nativ unterstützt; sonst die Klasse der eigenen Bauweise."""
    if stand(op, flaeche, kante)[0] in ("ja", "eingeschraenkt"):
        return "a"
    return eigen(op, flaeche, kante)[2]


def pruefen_bauweise(op, flaeche, kante, bauweise="nativ", prototyp_erlaubt=False):
    """Wie pruefen(), aber für die gewählte Bauweise ('nativ' | 'eigen'). → None (erlaubt) oder Text."""
    if bauweise != "eigen":
        return pruefen(op, flaeche, kante, prototyp_erlaubt)
    s_, grund, kl = eigen(op, flaeche, kante)
    if s_ == "nein" or (s_ == "prototyp" and not prototyp_erlaubt):
        return "%s (eigene Geometrie) an %s auf «%s» %s [%s – %s]: %s." % (
            OP_TEXT.get(op, op), KANTEN_TEXT.get(kante, kante), FLAECHEN_TEXT.get(flaeche, flaeche),
            "ist ein gesperrter Prototyp (Freigabe in den Einstellungen nach bestandenem Live-Test)" if s_ == "prototyp" else "ist nicht möglich",
            kl, KLASSEN_AE[kl], grund)
    return None


def kantenwerkzeug_markdown():
    """Support-Matrix Kante × angrenzende Fläche × Bearbeitung für das Kantenwerkzeug: nativ / eigene Geometrie / Klasse a–e."""
    z = ["| Bearbeitung | Fläche | Kante | nativ (Fusion) | eigene Geometrie | Klasse |", "|---|---|---|---|---|---|"]
    for op in ("flansch", "umschlag", "doppelfalz", "mehrkant_gehrung", "versatz"):
        for f in FLAECHEN:
            for k in KANTEN:
                n = stand(op, f, k)[0]
                e_ = eigen(op, f, k)
                z.append("| %s | %s | %s | %s | %s | %s |" % (OP_TEXT[op], FLAECHEN_TEXT[f], KANTEN_TEXT[k], STAND_TEXT[n], STAND_TEXT[e_[0]], e_[2] if n not in ("ja", "eingeschraenkt") else "a"))
    z.append("")
    z.append("Klassen: " + "; ".join("**%s** %s" % (k, v) for k, v in KLASSEN_AE.items()) + ". «implementiert» heisst NICHT live getestet.")
    return "\n".join(z)

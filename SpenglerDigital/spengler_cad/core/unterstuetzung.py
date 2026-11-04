"""Unterstützungsmatrix: welche Bearbeitung auf welcher Geometrieklasse – an EINER Stelle, damit Eignungsprüfung, Meldungen und Doku übereinstimmen.

Klassen (core/geometrie_referenz.klasse): eben_gerade | gekruemmte_kante | zylinder | kegel | freiform.
Stand je Feld: 'ja' (implementiert), 'eingeschraenkt' (implementiert mit genannter Grenze), 'nein' (abgelehnt, mit Grund).
Der LIVE-Stand (in Fusion bestätigt oder nicht) steht bewusst NICHT hier, sondern im Statusdokument – implementiert ist nicht getestet.
Neue Flächentypen: Zeile/Spalte ergänzen; die Prüfung (pruefen) und die Doku-Tabelle (als_markdown) folgen automatisch."""

KLASSEN = ("eben_gerade", "gekruemmte_kante", "zylinder", "kegel", "freiform")
KLASSEN_TEXT = {"eben_gerade": "eben, gerade Kante", "gekruemmte_kante": "gekrümmte Kante", "zylinder": "Zylinder", "kegel": "Kegel", "freiform": "Freiform"}

_FUSION_GERADE = ("nein", "Fusions Blech-Schnittstelle (EdgeFlange/Hem, Preview) ist nur für gerade Kanten beschrieben; der Live-Test fragt Fusion "
                          "ausdrücklich an (Schritt «Fusion-Antwort an gekrümmter Kante»), freigegeben wird erst nach bestätigtem Ergebnis")
_KEIN_BLECH = ("nein", "auf einer gekrümmten Fläche ohne Blechkörper gibt es keine Blechkante; gerollte Blechkörper: Kanten an den geraden "
                       "Enden sind wie «eben, gerade Kante» zu behandeln")

MATRIX = {
    "grundblech": {"eben_gerade": ("ja", "ebenes Profil aus Linien und Bögen"), "gekruemmte_kante": ("ja", "Umriss mit Bögen (Grundriss)"),
                   "zylinder": ("nein", "gerolltes Blech entsteht als Flansch mit grossem Radius; ein Grundblech direkt auf einer Zylinderfläche baut das Add-in nicht"),
                   "kegel": ("nein", "konische Bleche: Befehl «Rundblech» (Drehkörper, kein Blechkörper)"), "freiform": ("nein", "nicht abwickelbar im Allgemeinen")},
    "flansch": {"eben_gerade": ("ja", ""), "gekruemmte_kante": _FUSION_GERADE, "zylinder": _KEIN_BLECH, "kegel": _KEIN_BLECH, "freiform": _KEIN_BLECH},
    "mehrkant_gehrung": {"eben_gerade": ("eingeschraenkt", "Kette gerader Kanten an einem Körper; Eckspalt wird gemessen"), "gekruemmte_kante": _FUSION_GERADE,
                         "zylinder": _KEIN_BLECH, "kegel": _KEIN_BLECH, "freiform": _KEIN_BLECH},
    "umschlag": {"eben_gerade": ("ja", "ein Saum-Feature je Kante"), "gekruemmte_kante": _FUSION_GERADE, "zylinder": _KEIN_BLECH, "kegel": _KEIN_BLECH, "freiform": _KEIN_BLECH},
    "doppelfalz": {"eben_gerade": ("eingeschraenkt", "als Kantenfolge Flansch + Umschlag; Live-Test-Fall"), "gekruemmte_kante": _FUSION_GERADE,
                   "zylinder": _KEIN_BLECH, "kegel": _KEIN_BLECH, "freiform": _KEIN_BLECH},
    "versatz": {"eben_gerade": ("ja", "Biegelinien-Versatz in der Blechebene"),
                "gekruemmte_kante": ("nein", "Versatzstreifen nur über gerade Kanten"),
                "zylinder": ("nein", "der Streifen müsste der Krümmung folgen – keine verzerrte Ersatzgeometrie"), "kegel": ("nein", "wie Zylinder"),
                "freiform": ("nein", "wie Zylinder")},
    "abwicklung": {"eben_gerade": ("ja", "Fusion-Abwicklung + DXF-Gegenprobe"), "gekruemmte_kante": ("ja", "ebene Bleche mit Bogenkontur"),
                   "zylinder": ("eingeschraenkt", "gerollte Blechkörper (Biegezonen) über Fusion-Abwicklung; exakt abwickelbar"),
                   "kegel": ("eingeschraenkt", "nur wenn Fusion den Körper als Blech abwickelt; exakt abwickelbar"),
                   "freiform": ("nein", "doppelt gekrümmt: keine exakte Abwicklung, keine DXF als exakt")},
    "detail_starr": {"eben_gerade": ("ja", "Rahmen an der Kante"), "gekruemmte_kante": ("eingeschraenkt", "starr tangential am Kantenanfang"),
                     "zylinder": ("eingeschraenkt", "starr tangential, lokale Normale am Ankerpunkt, Abstand einstellbar"),
                     "kegel": ("eingeschraenkt", "wie Zylinder"), "freiform": ("eingeschraenkt", "starr tangential; Kontakt wird gemessen")},
    "detail_anpassen": {k: ("nein", "ein starres Detail wird nicht ungefragt verformt; Anpassen an die Krümmung ist nicht umgesetzt") for k in KLASSEN},
}

OP_TEXT = {"grundblech": "Grundblech", "flansch": "Flansch", "mehrkant_gehrung": "Mehrkantflansch mit Gehrung", "umschlag": "Umschlag", "doppelfalz": "Doppelfalz",
           "versatz": "Versatz", "abwicklung": "Abwicklung / DXF", "detail_starr": "3D-Detail starr", "detail_anpassen": "3D-Detail an Fläche angepasst"}


def stand(op, klasse_):
    """→ ('ja'|'eingeschraenkt'|'nein', Grund)."""
    if op not in MATRIX or klasse_ not in KLASSEN:
        return "nein", "unbekannte Bearbeitung/Geometrie"
    return MATRIX[op][klasse_]


def pruefen(op, klasse_):
    """→ None (erlaubt) oder Text, warum nicht – für Eignungsprüfungen und Meldungen."""
    s, grund = stand(op, klasse_)
    if s == "nein":
        return "%s auf «%s» wird nicht unterstützt: %s." % (OP_TEXT.get(op, op), KLASSEN_TEXT.get(klasse_, klasse_), grund)
    return None


def als_markdown():
    zeilen = ["| Bearbeitung | " + " | ".join(KLASSEN_TEXT[k] for k in KLASSEN) + " |", "|---" * (len(KLASSEN) + 1) + "|"]
    for op in MATRIX:
        zeilen.append("| %s | %s |" % (OP_TEXT[op], " | ".join({"ja": "implementiert", "eingeschraenkt": "eingeschränkt", "nein": "nicht unterstützt"}[MATRIX[op][k][0]]
                                                             for k in KLASSEN)))
    return "\n".join(zeilen)

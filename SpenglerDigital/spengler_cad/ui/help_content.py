"""Kontextbezogene Hilfetexte (Deutsch). Sie beschreiben nur, was das Add-in wirklich kann.
Funktionen, die noch nicht in Fusion geprüft wurden, sind als solche markiert."""

NICHT_GEPRUEFT = "Hinweis: Diese Funktion wurde noch nicht in Fusion selbst getestet. Bei Problemen bitte das Protokoll schicken (Einstellungen → Protokoll öffnen)."

HILFE = {
    "kanten": (
        "Kanten bearbeiten",
        "1. Eine oder mehrere gerade oder runde (Kreis/Bogen) Aussenkanten eines Blechkörpers wählen.\n"
        "2. Eigene Vorlage und Materialprofil wählen. Die Bibliothek ist anfangs leer – zuerst unter «Vorlagen verwalten» eine Vorlage anlegen.\n"
        "3. Parameter eingeben (Einheiten stehen am Feld). Im Expertenmodus kann die Operationsfolge als Kurzschrift direkt bearbeitet werden.\n"
        "4. Die Vorschau zeigt das Ergebnis; ungeeignete Kanten werden mit Grund aufgeführt und NICHT bearbeitet.\n"
        "5. OK erzeugt die Flansche/Umschläge. Schlägt ein Schritt fehl, werden die bereits erzeugten Schritte dieser Kante wieder entfernt. "
        "Mit Rückgängig (Strg+Z) wird der ganze Befehl zurückgenommen.\n\n" + NICHT_GEPRUEFT),
    "kurzschrift": (
        "Kurzschrift",
        "Folge ab der Kante: Winkel Schenkel Winkel Schenkel …\n"
        "90 25 = 90° zur Sichtseite, 25 mm.  -90 = nach hinten.  U+ 7 / U- 7 = Umschlag 180°, 7 mm.\n"
        "90r5 = Innenradius 5 mm.  Parameter: 90 H U+ u+4*t  (t = Blechdicke, ri = Innenradius aus dem Materialprofil).\n"
        "Winkel als Ausdruck in geschweiften Klammern: {w} 20."),
    "vorlagen": (
        "Vorlagen verwalten",
        "Die Vorlagenbibliothek beginnt leer – es gibt bewusst keine mitgelieferten Profile. Sie legen alle Vorlagen selbst an.\n"
        "Neue Vorlage: Name, Kategorie, Parameter (Name, Einheit, Standardwert, Bereich) und Operationen. Jede gespeicherte Änderung erhöht die "
        "Vorlagenversion; frühere Versionen bleiben erhalten. Kopieren erzeugt eine unabhängige Vorlage. Löschen verschiebt nach Bestätigung in den "
        "Papierkorb. Export/Import: JSON-Datei (Format «bibliothek_export», siehe Handbuch). Bereits erzeugte Bauteile ändern sich nicht, "
        "wenn eine Vorlage später geändert wird."),
    "details": (
        "Eigene 3D-Details",
        "Erfassen: Detail in einer eigenen Komponente modellieren, variable Masse als Fusion-Benutzerparameter anlegen, dann «3D-Detail erfassen»: "
        "Komponente, Anschlusskante und Bezugsfläche wählen und die Parameter markieren, die beim Anwenden veränderbar sein sollen.\n"
        "Anwenden: Vorlage und Zielkante wählen; das Add-in prüft Kantentyp, Länge und Dicke, importiert das Detail als neue Komponente, "
        "richtet es an der Kante aus und setzt die Parameter. Es wird NICHT automatisch mit dem Zielkörper vereinigt – das geschieht bewusst "
        "von Hand, damit ein Blechkörper gültig bleibt.\n"
        "Grenzen: Beliebige Körper werden nicht automatisch parametrisiert; nur die markierten Benutzerparameter sind veränderbar.\n\n" + NICHT_GEPRUEFT),
    "rundblech": (
        "Rundbleche und Werkstattumformung",
        "Fälle: Scheibe mit aufgebogenem Rand (Rand wird gestaucht), Kragen an rundem Ausschnitt (Rand wird gestreckt), Kegelstumpf (abwickelbar).\n"
        "Das Add-in unterscheidet: konstruierbar – abwickelbar – mit dem gewählten Verfahren herstellbar. «Herstellbar» wird nur beurteilt, wenn im "
        "Materialprofil ein EIGENER Grenzwert (Stauchen/Strecken in %) hinterlegt ist; sonst steht «nicht beurteilbar». Die Dehnung ist eine reine "
        "Umfangsrechnung, keine Garantie. Einschnitte oder Lappen werden nie automatisch erzeugt. Die Scheibe mit Rand wird als Drehkörper modelliert "
        "(kein Fusion-Blechkörper)."),
    "abwicklung": (
        "Abwicklung und DXF",
        "Die Abwicklung macht Fusion selbst (Blechregel). Das Add-in erzeugt sie bei Bedarf (feststehende Fläche wählen), liest die Masse und "
        "exportiert die DXF-Datei mit dem Fusion-Exporter. Eine DXF gilt erst als erstellt, wenn die Datei wirklich geschrieben wurde. Die Layer der "
        "Fusion-DXF bestimmt Fusion; die einstellbaren Layernamen gelten für den Zuschnittplan-DXF des Add-ins.\n\n" + NICHT_GEPRUEFT),
    "zeichnung": (
        "Werkstattblatt",
        "Fusion bietet per API keine automatische Zeichnungserstellung mit Ansichten an. Das Add-in erstellt deshalb ein druckbares Werkstattblatt "
        "(HTML): Bauteil, Material, Dicke, Vorlage mit Version, Abwicklungsmasse aus Fusion sowie Querschnitt und Biegeliste aus der Operationsfolge "
        "(theoretisch, wenn Innenradius/K-Faktor im Materialprofil stehen)."),
    "material": (
        "Materialprofile",
        "Materialprofile legen Sie selbst an: Name, Dicke (Pflicht), optional Dichte, Innenradius, K-Faktor, Fusion-Blechregel, Tafelformate, "
        "Rollenbreiten und eigene Umformgrenzwerte. Es werden keine Werte vorgegeben. Gewicht = Fläche × Dicke × Dichte und ist ein Schätzwert."),
    "kfaktor": (
        "K-Faktor aus Probebiegung",
        "Einen Streifen genau zuschneiden (Zuschnitt), EINE 90°-Biegung mit dem Innenradius des Materialprofils biegen und beide Schenkel "
        "AUSSEN messen (a, b). Dicke und Innenradius kommen aus den Feldern des Materialprofils. Das Add-in rechnet den K-Faktor zurück "
        "(gleiche Rechnung wie im CAD-Programm, Masse auf Blechmitte). Werte ausserhalb 0.1–0.6 gelten als unplausibel und werden nicht "
        "zum Übernehmen angeboten. Der K-Faktor wirkt nur auf die theoretische Abwicklung des Add-ins – die Fusion-Abwicklung folgt der "
        "Blechregel in Fusion (dort den K-Faktor ebenfalls eintragen)."),
    "zuschnitt": (
        "Zuschnittoptimierung",
        "Übernommen aus der Spengler-Digital-App (gleiche Rechnung): Teile werden als Streifen ihrer Abwicklungsbreite aus Rolle oder Tafel "
        "geschnitten; je Breite wird die kleinstmögliche Streifenzahl gesucht, die Schnittfuge liegt zwischen den Stücken. Neu im Add-in: "
        "Randabstand, Drehen nur wenn erlaubt, Überlappungsprüfung, SVG/CSV/DXF-Ausgabe.\n"
        "Nicht übernommen: Rollenmischung, Mischen verschiedener Breiten im selben Abschnitt, automatisches Teilen zu langer Stücke, Restelager. "
        "Teile werden als Rechtecke (umschliessendes Rechteck der Abwicklung) verschachtelt, keine freien Konturen."),
    "stueckliste": (
        "Stückliste, Teilenummern und Etiketten",
        "Befehl «Stückliste & Zuschnitt»: gewählte Blechkörper mit Fusion-Abwicklung. Jeder Körper bekommt eine Teilenummer (als Attribut am "
        "Körper gespeichert; vorhandene Nummern bleiben, neue Körper erhalten die nächste freie Nummer im Dokument). Ausgabe: Stückliste als "
        "CSV (Excel) und HTML (drucken), Etiketten als HTML-Seite im A4-Bogenformat aus den Einstellungen – eins pro Stück, im Browser drucken "
        "(Seitenränder 0, Skalierung 100 %). Fläche aus der Fusion-Abwicklung; fehlt sie, das umschliessende Rechteck (mit * markiert). "
        "Gewicht nur mit Dichte im Materialprofil und als Schätzwert."),
    "konto": (
        "Konto und Abgleich mit der Spengler-Digital-App",
        "Anmelden mit demselben Benutzernamen und Passwort wie in der App. Danach werden Kantenvorlagen, 3D-Details (samt Geometrie) und "
        "Materialprofile mit allen PCs der Firma abgeglichen: beim Start, nach jeder Änderung in der Palette und mit «Jetzt abgleichen». "
        "Lokal wird immer zuerst gespeichert, ohne Internet arbeitet das Add-in normal weiter. Ändern dürfen nur Konten mit dem Recht "
        "«Vorlagen ändern» der App (Standard: Admin) – das Recht gilt gleich für die Massaufnahme-Vorlagen. Haben zwei PCs dieselbe Vorlage "
        "geändert, gilt die Fassung aus der App; die eigene bleibt als Kopie «… (Konflikt TT.MM.)». Gelöscht wird nur in den Papierkorb. "
        "Updates: neue Versionen kommen aus der App; vor dem Installieren wird gefragt und werden Daten und Programm gesichert. "
        "Das Passwort wird nicht gespeichert, nur die Sitzung (konto.json im Benutzerdatenordner)."),
    "einstellungen": (
        "Einstellungen und Sicherung",
        "Benutzerdaten liegen ausserhalb des Add-in-Ordners und überleben Updates. Vor jeder Datenmigration wird automatisch gesichert. "
        "«Sicherung erstellen» schreibt eine ZIP-Datei mit allen Vorlagen, 3D-Geometrien, Materialien und Einstellungen. «Wiederherstellen» prüft die "
        "Sicherung, sichert den aktuellen Stand und ersetzt ihn erst dann."),
}


def text(thema):
    t = HILFE.get(thema)
    return "%s\n\n%s" % t if t else "Keine Hilfe für «%s»." % thema


TOOLTIPS = {
    "kanten": "Gerade Aussenkanten eines Blechkörpers. Mehrfachauswahl möglich.",
    "vorlage": "Eigene Kantenvorlage. Anlegen unter «Vorlagen verwalten».",
    "material": "Eigenes Materialprofil (Dicke, optional Radius/K-Faktor).",
    "experte": "Operationsfolge direkt bearbeiten (Kurzschrift).",
    "folge": "Winkel Schenkel … z. B. 90 25 U+ 7 – Parameter erlaubt.",
}

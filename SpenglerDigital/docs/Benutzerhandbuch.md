# Spengler Digital CAD – Bedienungsanleitung

Add-in für Autodesk Fusion · Version 0.4.2 · Stand 29.10.2026

> **Prüfstand dieser Version:** Die Rechenteile (Kurzschrift, Vorlagen, Bauplan, Zuschnitt, Material, Umformung, Sicherung, Migration) sind automatisch getestet. Die Bedienung in Fusion selbst ist **noch nicht in Fusion getestet**. Funktionen, die davon abhängen, sind mit **[nicht in Fusion geprüft]** markiert.

## 1. Installation und erster Start

1. ZIP-Datei entpacken; es entsteht der Ordner `SpenglerDigital`.
2. Ordner z. B. nach `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` (Windows) bzw. `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` (macOS) kopieren.
3. In Fusion **Dienstprogramme → Add-Ins → Skripte und Add-Ins** (Shift+S), Register **Add-Ins**. Fehlt «SpenglerDigital» in der Liste: **+** und den Ordner wählen.
4. **Ausführen** und **Beim Start ausführen** ankreuzen.
5. Im Arbeitsbereich **Konstruktion** erscheint das Register **SPENGLER**.

Beim ersten Start legt das Add-in den Benutzerdatenordner an (siehe Kapitel 14). Danach empfiehlt sich **Hilfe → Selbsttest in neuem Dokument**: Er prüft in einem neuen, leeren Dokument die Fusion-Funktionen, die das Add-in benutzt, und schreibt das Ergebnis ins Protokoll.

## 2. Werkzeugleiste und Befehle

Register **SPENGLER**, drei Gruppen:

| Gruppe | Befehl | Zweck |
|---|---|---|
| Kanten & Details | Kanten bearbeiten | Eigene Kantenvorlage auf eine oder mehrere Blechkanten anwenden |
| | 3D-Detail erfassen | Eigenes 3D-Blechdetail als Vorlage speichern |
| | 3D-Detail anwenden | Gespeichertes Detail an eine Kante bzw. ein Falzende ansetzen |
| | Rundblech / Umformung | Rundbleche, Kragen, Kegel: Beurteilung und Drehkörper |
| Fertigung | Abwicklung & DXF | Fusion-Abwicklung, DXF-Export, Werkstattblatt |
| | Stückliste & Zuschnitt | Teilenummern, Stückliste, Etiketten, Materialbedarf, Gewicht (Schätzung), Zuschnittplan |
| Verwaltung | Vorlagen & Einstellungen | Palette: Vorlagen, 3D-Details, Materialien, Einstellungen, Sicherung |
| | Hilfe | Hilfethemen, diese Anleitung, Fähigkeitsprüfung, Selbsttest |

Fehlt in Ihrer Fusion-Version die API für eigene Register, erscheinen die Befehle in den Panels **Blech → Erstellen** bzw. **Volumenkörper → Erstellen**.

## 3. Leere Vorlagenbibliothek

Die Vorlagenbibliothek ist beim ersten Start **leer**. Es werden bewusst keine Ortgänge, Traufen, Falze, Säume oder Standardmasse mitgeliefert – Sie legen jede Vorlage passend zu Ihrer Werkstatt selbst an. Auch die Materialbibliothek ist leer; das Add-in erfindet keine Radien, K-Faktoren oder Dichten.

Bibliotheksebenen:

- **Benutzerbibliothek** – Ihre Vorlagen im Benutzerdatenordner.
- **Projektbibliothek** (optional) – ein Ordner, der unter *Einstellungen → Projektbibliothek* eingetragen ist, z. B. auf einem Netzlaufwerk.
- **Systemvorlagen** – im Add-in-Ordner, produktiv leer und schreibgeschützt.

## 4. Eigene Kanten- und Operationsvorlagen

*Vorlagen & Einstellungen → Kantenvorlagen → Neue Vorlage erstellen.*

Eine Kantenvorlage besteht aus:

- **Name, Beschreibung, Kategorie, Favorit**
- **Parametern** – Name (z. B. `H`), Bezeichnung, Einheit (mm, deg oder ohne), Standardwert, Minimum, Maximum, variabel ja/nein
- **Operationen** – Folge ab der Kante: Flansch (Winkel, Länge, optional Radius) oder Umschlag (±180°, Länge)
- **Anschluss und Grenzen** (Expertenmodus) – Kantentyp, Dickenbereich, Mindestkantenlänge, Einschnitte ausdrücklich erlauben

**Schritt für Schritt:** Im Abschnitt **Schritte** der Vorlage legen Sie mit **+ Flansch** und **+ Umschlag** jeden Schritt einzeln an und tragen Winkel, Länge und optional den Radius in die Tabelle ein (Zahlen, Parameternamen wie `H` oder Ausdrücke). Winkel + = zur Sichtseite, − = nach hinten. Die **Vorschau** darüber zeichnet nach jeder Änderung den Querschnitt neu; Pfeile verschieben Schritte, ✕ löscht sie. Die Kurzschrift bleibt als Alternative erhalten und folgt der Tabelle.

Die schnellste Eingabe ist die **Kurzschrift**:

| Eingabe | Bedeutung |
|---|---|
| `90 25` | 90° zur Sichtseite abkanten, Schenkel 25 mm |
| `-90 30` | 90° nach hinten |
| `U+ 7` / `U- 7` | Umschlag 180° zur Sichtseite / nach hinten, 7 mm |
| `90r5 20` | Innenradius 5 mm für diese Biegung |
| `90 H U+ u+4*t` | Parameter `H`, `u`; `t` = Blechdicke, `ri` = Innenradius, `k` = K-Faktor aus dem Materialprofil |
| `{w} 20` | Winkel als Ausdruck |

**Mass und Lage (Schrittetabelle):** *Mass* legt fest, worauf die Schenkellänge zielt: aussen, innen oder tangential (Fusion: Höhenbezug). *Lage* sagt, wo der Flansch an der Bestandsfläche ansetzt: **benachbart** (an der Kante, Fusion «StartEdge»), innen, aussen oder tangential (Fusion: Biegeposition). «Standard» lässt Fusions Voreinstellung. Beim **Flansch** wird die gewählte Lage genau so verlangt (lehnt Fusion sie ab, kommt eine Meldung). Beim **Umschlag** sind nach Fusion nur benachbart und tangential zulässig; «innen»/«aussen» werden versucht, bei Ablehnung geht das Add-in automatisch auf benachbart/tangential weiter (steht im Protokoll). Ein freier «Versatz ±» ist in der Fusion-Flansch-API nicht vorgesehen. Vorschau und Abwicklung rechnen immer theoretisch mit der Blechmitte. **Versatz (mm):** verschiebt die Biegung von der Startkante weg: **+ nach innen** (das Blech wird um diesen Betrag zurückgeschnitten, es entsteht «Luft»), **− nach aussen** (das Blech wird um diesen Betrag verlängert). Beispiel: zwei aneinanderliegende Bleche je mit 90° 25 mm und Versatz 5 → 10 mm Abstand zwischen den Flanschen. Fusions Flansch-Werkzeug kann die Biegung nicht frei verschieben; das Add-in schneidet bzw. verlängert deshalb das Blech vorher mit einem Streifen (Skizze «Versatz …» und Extrusion in der Zeitleiste). Nur an geraden Kanten, einzeln gebaut (keine Gehrung zwischen Nachbarkanten); Vorschau und Abwicklung rechnen ohne Versatz. Nicht in Fusion geprüft. **Biegeradius:** Ohne eigenen Radius in der Vorlage gilt der Innenradius des Materialprofils (Flansch); der Umschlag ist immer ein geschlossener Saum mit dem Radius der Blechregel. Beim Umschlag probiert das Add-in mehrere Lagen/Richtungen durch und protokolliert die Versuche. Nicht in Fusion geprüft.

Nach «übernehmen» werden neue Parameternamen automatisch als Parameter angelegt; Werte und Bereiche tragen Sie selbst ein. Unter der Kurzschrift zeigt die **Vorschau** den Querschnitt mit den Standardwerten: das bestehende Blech gestrichelt, die Kante grün, Schenkelmasse und Biegungen B1, B2 … Sie aktualisiert sich beim Tippen. Ist unter «Prüfen» ein Testmaterial gewählt (sonst das Standardmaterial), zeichnet sie mit dessen Dicke und Innenradius; ohne Material als Skizze mit 1 mm Dicke. Fehlt einem Parameter der Standardwert, steht statt des Bildes der Grund. Dasselbe Bild erscheint verkleinert in der Vorlagenliste. **Prüfen & Trockenlauf** zeigt Fehler, die Folge mit den Standardwerten und – wenn Innenradius und K-Faktor im Material stehen – die theoretische Abwicklungszugabe.

Speichern: Jede inhaltliche Änderung erhöht die **Vorlagenversion**; frühere Versionen bleiben erhalten (*Versionen*). **Duplizieren** erzeugt eine unabhängige Kopie, **Umbenennen** ändert nur den Namen, **Löschen** verschiebt die Vorlage nach Bestätigung in den Papierkorb (wiederherstellbar unter *Sicherung*).

## 5. Eigene 3D-Vorlagen und Anschlussreferenzen [nicht in Fusion geprüft]

Für Details, die sich nicht als Flanschfolge beschreiben lassen (z. B. Ihren eigenen Doppelfalzabschluss mit Unter-/Oberfalz, Endlasche und Freistellungen), gibt es einen geführten Erfassungsablauf:

1. Detail in einer **eigenen Komponente** modellieren.
2. Masse, die später veränderbar sein sollen, als **Fusion-Benutzerparameter** anlegen (Ändern → Parameter ändern) und in den Features verwenden.
3. **3D-Detail erfassen**: Komponente wählen, die **Anschlusskante** (gerade Kante, an der das Detail später ansetzt) und optional eine **Bezugsfläche** (bestimmt die Z-Richtung). Name, Kategorie, Beschreibung eingeben und die **variablen Parameter** ankreuzen.

Gespeichert werden die Komponente als Fusion-Archiv (.f3d), das lokale Koordinatensystem der Anschlusskante (Ursprung = Kantenanfang, X = Kantenrichtung, Z = Normale der Bezugsfläche), die Kantenlänge, die Blechdicke aus der Blechregel, die variablen und festen Parameter und die Namen der Zeitachsen-Features.

**Grenzen:** Beliebige Körper werden nicht automatisch parametrisiert. Veränderbar ist nur, was Sie als Benutzerparameter angelegt und angekreuzt haben.

## 6. Variable Parameter

- **Variable Parameter** erscheinen beim Anwenden als Eingabefeld mit Einheit; Bereichsgrenzen werden geprüft.
- **Feste Parameter** behalten den gespeicherten Wert (in der Parameterliste das Häkchen «variabel» entfernen).
- **Materialwerte** `t`, `ri`, `k` kommen immer aus dem gewählten Materialprofil. Fehlt ein benötigter Wert, wird nicht gebaut.

## 7. Vorlagen auf Kanten und Falzenden anwenden [nicht in Fusion geprüft]

**Kanten bearbeiten:** Eine oder mehrere Aussenkanten eines Blechkörpers wählen (gerade Kanten; Kreis/Bogen werden versucht – Fusion entscheidet und seine Antwort wird gemeldet), Vorlage und Material wählen, Werte eingeben. Der **Bauplan** im Dialog zeigt die Folge, die geeigneten Kanten und alle Warnungen. Ungeeignete Kanten (Ellipse/Spline, kein Blechkörper, Biegezone, falsche Dicke, zu kurz) werden mit Grund genannt; dann ist OK gesperrt. Mit **Vorschau** zeigt Fusion das Ergebnis vor der Bestätigung.

Ablauf beim OK: Kante neu auflösen → Flansch/Umschlag Schritt für Schritt → nach jedem Schritt die neue Aussenkante bestimmen (gerade, parallel, gleich lang, in plausibler Entfernung; bei Mehrdeutigkeit Abbruch statt Raten) → Körper prüfen. Schlägt ein Schritt fehl, werden die bereits erzeugten Schritte dieser Kante wieder entfernt. Der ganze Befehl ist ein Rückgängig-Schritt (Strg+Z). Jedes erzeugte Feature trägt die Vorlagen-ID und -Version als Attribut; spätere Vorlagenänderungen verändern bestehende Bauteile nicht.

**3D-Detail anwenden:** Detailvorlage wählen, Zielkante (Falzende) und optional Bezugsfläche wählen, Werte eingeben. Die **Passung** prüft Kantentyp, Kantenlänge, Blechdicke und Wertebereiche. Mit «Um 180° wenden» wird die Richtung umgekehrt. Beim OK wird das Detail importiert, an der Kante ausgerichtet und die Parameter werden gesetzt. Standardmässig (Haken «Ins bestehende Modell integrieren») wird es danach in den Zielkörper übernommen (siehe Kapitel 16); ohne Haken bleibt es eine **eigene Komponente**. Überschneiden sich Begrenzungsrahmen mit anderen Körpern, erscheint ein Kollisionshinweis.

## 8. Standard- und Expertenmodus

Beide Modi benutzen dieselbe Rechen-Engine.

- **Standardmodus:** Vorlage wählen und die wenigen variablen Werte eingeben.
- **Expertenmodus** (Häkchen in Palette und Dialog): Operationen hinzufügen, ändern, löschen und umordnen, Radien je Biegung, Anschluss/Grenzen/Einschnitt-Freigabe. In «Kanten bearbeiten» kann die Folge für eine Ausführung angepasst und optional als neue Vorlage gespeichert werden – das Original bleibt unverändert.

## 9. Rundbleche und Werkstattumformung

Für Rundbleche als Drehkörper (kein Fusion-Blech) gibt es den Befehl **Rundblech / Umformung**:

| Fall | Was passiert mit dem Rand | Modell |
|---|---|---|
| Scheibe mit aufgebogenem Rand | wird gestaucht | Drehkörper |
| Kragen an rundem Ausschnitt | wird gestreckt | nur Beurteilung |
| Kegelstumpf / konischer Übergang | abwickelbar, keine Umformung | Drehkörper |

Das Add-in unterscheidet klar:

- **konstruierbar** – lässt sich modellieren bzw. rechnen;
- **abwickelbar** – ohne Dehnung in die Ebene abwickelbar (nur Kegel/Zylinder);
- **herstellbar** – mit dem gewählten Verfahren (Stauchen/Schweifen, Strecken/Schweifen, manuell, automatische Empfehlung). Das wird **nur** beurteilt, wenn im Materialprofil ein **eigener Grenzwert** (Stauchen/Strecken in %) mit Quelle hinterlegt ist. Sonst steht «nicht beurteilbar».

Die angegebene Dehnung ist die reine Umfangsänderung (Geometrie) – keine Garantie: Falten, Rückfederung und Wanddickenänderung sind nicht gerechnet. Einschnitte oder Lappen werden **nie** automatisch erzeugt. Der Drehkörper ist kein Fusion-Blechkörper; Zuschnittdurchmesser und Kegelabwicklung sind theoretisch.

**Zuschnitt ausgeben:** Mit «flach» entsteht zusätzlich ein flacher Körper (Rohling) mit sichtbaren Biegelinien (Skizze, Fläche geteilt) – daraus lässt sich eine Fusion-Zeichnung ableiten. Mit «dxf» wird der Zuschnitt (Layer ZUSCHNITT, BIEGELINIE) in den Exportordner geschrieben. Scheibe: Kreis + Biegekreis; Kegel/Zylinder: Kreisringsektor bzw. Rechteck; Kragen: nur Loch und Biegekreis (kein Körper). Nicht in Fusion geprüft.

## 10. Abwicklung und DXF [nicht in Fusion geprüft]

**Abwicklung & DXF:** Blechkörper wählen. Hat die Komponente noch keine Abwicklung, eine feststehende Fläche wählen – dann erzeugt Fusion die Abwicklung. Das Add-in liest das umschliessende Rechteck der Abwicklung und exportiert die DXF mit dem **Fusion-Exporter** (Ebenen und Biegelinien legt Fusion fest). Dateiname nach Muster `{bauteil}_{material}_{dicke}mm`, Ablage in einem Ordner mit Datum/Uhrzeit (Einzel- und Sammelexport). Erfolg wird nur gemeldet, wenn die Datei tatsächlich geschrieben wurde. «Abwickelbar» in Fusion heisst noch nicht «werkstattgerecht umformbar» (siehe Kapitel 9).

## 10a. Aufträge als Ordner in Fusion [nicht in Fusion geprüft]

Befehl **Neuer Auftrag** (Register SPENGLER → Fertigung): Auftragsnummer, Objekt (z. B. «Nägeligasse 1a, Bern») und Jahr eingeben. Das Add-in legt im aktiven Fusion-Projekt `Stammordner / Jahr / «17642 Nägeligasse 1a, Bern»` mit den Unterordnern (Standard: Modelle, Pläne, Export) an. Vorhandene Ordner werden wiederverwendet, nichts wird gelöscht oder umbenannt.

Einstellungen (Vorlagen & Einstellungen → Einstellungen → «Aufträge»): Stammordner (Projekt oder Ordner darin, Standard «Projekte»), Jahresordner ein/aus, Unterordner (Komma getrennt).

**Ableiten:** Liegt das aktive Dokument in einem Ordner nach dem Muster «Nummer Objekt» (mindestens 3 Ziffern, dann Leerzeichen), übernehmen **Stückliste & Zuschnitt**, Etiketten und das Werkstattblatt Auftragsnummer und Objekt automatisch aus dem Ordnernamen. Ohne passenden Ordner gelten die zuletzt verwendeten Angaben. Das Dokument speicherst du selbst im Ordner «Modelle» (die Fusion-Schnittstelle legt Dateien nicht automatisch dort ab).

## 11. Fertigungszeichnungen

Fusion bietet per API keine zuverlässige automatische Zeichnungserstellung mit Ansichten. Das Add-in erstellt deshalb ein **Werkstattblatt** (HTML, druckbar) mit Logo, Bauteilkennung, Material, Dicke, Vorlage und Version, Abwicklungsmassen aus Fusion sowie – für Bauteile aus «Kanten bearbeiten» mit Innenradius/K-Faktor im Material – Teilenummer, Objekt/Auftrag sowie – für Bauteile aus «Kanten bearbeiten» mit Innenradius/K-Faktor im Material – **Querschnitt mit Schenkelmassen und Biegungen**, **Abwicklung der Kante mit Biegelinien** (Masse ab Biegebeginn) und **Biegeliste**. Alles daraus ist als *theoretisch* gekennzeichnet (Blechmitte, K-Faktor des Materialprofils); die Zeichenlogik stammt aus dem CAD-Programm. Normgerechte Fusion-Zeichnungen erstellen Sie weiterhin im Arbeitsbereich Zeichnung.

## 12. Materialberechnung

**K-Faktor aus Probebiegung** (Palette → Materialien → Materialprofil öffnen): Streifen genau zuschneiden, **eine** 90°-Biegung mit dem Innenradius des Profils biegen, beide Schenkel **aussen** messen. Zuschnitt, a und b eintragen → «K-Faktor berechnen». Dicke und Innenradius kommen aus den Feldern des Profils. Ist das Ergebnis plausibel (0.1–0.6), lässt es sich mit einem Klick übernehmen; danach «Speichern». Die Rechnung ist dieselbe wie im CAD-Programm. Der K-Faktor gilt für die theoretische Abwicklung des Add-ins; für die Fusion-Abwicklung denselben Wert in der Fusion-Blechregel eintragen.

**Stückliste & Zuschnitt**: Blechkörper mit Fusion-Abwicklung wählen, Material, Stück je Teil, Objekt und Auftrag eingeben (werden für das nächste Mal gemerkt) und die gewünschten Ausgaben ankreuzen:

- **Teilenummern**: Jeder Körper bekommt eine Nummer, die als Attribut am Körper im Fusion-Dokument gespeichert wird. Vorhandene Nummern bleiben; ein neuer Körper erhält die nächste freie Nummer im Dokument. Dieselbe Nummer steht auf Stückliste, Etikett, Werkstattblatt und im DXF-Dateinamen.
- **Stückliste** als `stueckliste.csv` (Excel: Semikolon, Umlaute korrekt) und `stueckliste.html` (drucken): Nr, Teil, Material, Dicke, Zuschnitt × Länge, Stück, Laufmeter, Fläche, Gewicht, Summe je Material. Fläche aus der Fusion-Abwicklung; fehlt sie, das umschliessende Rechteck (mit * markiert). Ohne Dichte im Materialprofil kein Gewicht.
- **Etiketten** als `etiketten.html`: eins pro Stück (Objekt, Auftrag, Teil mit Nummer und i/n, Blech, Mass) im A4-Bogenformat aus *Einstellungen → Etikettenbogen* (Spalten, Zeilen, Etikettgrösse, Ränder, Abstände – vom Bogen des Herstellers ablesen; die Palette zeigt, ob der Bogen auf A4 passt). Im Browser drucken mit **Seitenränder: keine** und **Skalierung 100 %**.
- **Materialbedarf & Zuschnittplan** wie unten.

Die Materialberechnung ermittelt je Material: Anzahl Teile, Abwicklungsfläche (aus Fusion, sonst Rechteck – dann als obere Schätzung markiert), Gewicht (nur mit Dichte; Fläche × Dicke × Dichte, **Schätzwert**), Materialverbrauch und Ausnutzung des besten Lagerformats. Ergebnis: `bericht.txt` im Exportordner (wird nach dem Befehl geöffnet).

## 13. Zuschnittoptimierung

Die Rechnung ist aus der **Spengler-Digital-App** übernommen (gleiche Logik, gegen Referenzfälle aus der App getestet):

- Teile werden als **Streifen ihrer Abwicklungsbreite** aus Rolle oder Tafel geschnitten; Streifen je Abschnitt = ⌊(B + f) / (A + f)⌋.
- Je Breite wird die **kleinste Streifenzahl** gesucht (zuerst gierig, dann exakte Suche ab der Untergrenze); die Schnittfuge liegt zwischen zwei Stücken.
- Rolle mit mehreren Streifen nebeneinander: jeder Abschnitt nur so lang wie sein längstes Stück.
- Bestes Format = kleinste Blechfläche.

Neu im Add-in: Randabstand je Tafelseite, **Drehen nur wenn erlaubt** (Einstellung), Überlappungs- und Randprüfung der Lage, Ausgabe als `zuschnittplan.svg`, `.csv` und `.dxf` (Layer einstellbar).

**Nicht übernommen** (und so ausgewiesen): Rollenmischung, Mischen verschiedener Breiten im selben Abschnitt, automatisches Teilen zu langer Stücke mit Nahtüberlappung, Restelager der App. Teile werden als Rechtecke verschachtelt, freie Konturen nicht.

## 14. Import/Export und Sicherung

**Benutzerdatenordner** (überlebt Updates):

- Windows: `%APPDATA%\SpenglerDigitalCAD`
- macOS: `~/Library/Application Support/SpenglerDigitalCAD`

Inhalt: `vorlagen/kanten`, `vorlagen/details` (+ `geometrie/*.f3d`), `vorlagen/versionen`, `vorlagen/papierkorb`, `materialien`, `einstellungen.json`, `datenformat.json`, `sicherungen`, `protokoll`, `export`.

**Vorlagen exportieren/importieren** (Palette, Kantenvorlagen): Austauschformat ist eine JSON-Datei:

```
{ "schemaVersion": 1, "typ": "bibliothek_export", "exportiert": "<Zeit>",
  "vorlagen": [ <Kantenvorlage oder Detailvorlage, vollständig> ],
  "geometrie": { "<relativer Pfad .f3d>": "<Base64>" } }
```

Beim Import werden bestehende Vorlagen nie überschrieben: gleiche ID → Import als Kopie mit neuer ID. Vorlagen aus einer neueren Programmversion werden abgelehnt statt verändert.

**Sicherung** (Palette → Sicherung): «Sicherung erstellen» schreibt eine ZIP-Datei mit allen Benutzerdaten und Prüfsummen. «Wiederherstellen» prüft die Datei, sichert den aktuellen Stand automatisch und ersetzt ihn erst dann.

**Konto & Abgleich mit der Spengler-Digital-App** (Palette → Register **Konto**): Mit demselben Benutzernamen und Passwort wie in der App anmelden. Danach werden Kantenvorlagen, 3D-Details (samt .f3d-Geometrie) und Materialprofile mit allen PCs der Firma abgeglichen – beim Start, nach jeder Änderung in der Palette und mit «Jetzt abgleichen». Oben in der Palette steht der Stand («✓ mit der App abgeglichen», «nur lokal …»).

- **Lokal zuerst:** Jede Änderung wird zuerst auf dem PC gespeichert. Ohne Internet arbeitet das Add-in normal weiter und gleicht später ab.
- **Rechte:** Ändern dürfen Konten mit dem App-Recht «Vorlagen ändern» (Standard: Admin; in der App pro Person einstellbar – es ist dasselbe Recht wie für die Massaufnahme-Vorlagen). Alle anderen sehen und benutzen die Vorlagen; eigene Änderungen bleiben dann auf ihrem PC und werden als «nur auf diesem PC» gemeldet.
- **Firmen getrennt:** Jede Firma sieht nur ihre eigenen Daten (Regeln der App-Datenbank).
- **Konflikt:** Haben zwei PCs dieselbe Vorlage geändert, gilt die Fassung aus der App; die eigene bleibt als Kopie «… (Konflikt TT.MM.)» erhalten und wird ebenfalls abgeglichen.
- **Löschen** verschiebt auf allen PCs in den Papierkorb; in der App wird nur markiert, frühere Fassungen bleiben dort gespeichert.
- Das **Passwort** wird nicht gespeichert, nur die Sitzung (`konto.json` im Benutzerdatenordner). «Abmelden» löscht sie.

## 15. Updates und Wiederherstellung

**Mit Anmeldung (ab 0.4.0):** Beim Start fragt das Add-in, wenn in der App eine neuere Version bereitliegt (oder Palette → Konto → «Nach Updates suchen»). Bei «Ja»: Benutzerdaten sichern → bisherige Programmdateien nach `…\SpenglerDigitalCAD\programm_sicherung\<Version>` kopieren → nur geänderte Dateien laden und per Prüfsumme kontrollieren → ersetzen. Danach das Add-in neu starten (Shift+S → Stoppen → Ausführen). Stimmt eine Prüfsumme nicht oder fehlt etwas, wird abgebrochen und nichts verändert. Die PDF-Anleitungen kommen nur mit dem ZIP; «Hilfe → Bedienungsanleitung öffnen» zeigt die stets aktuelle HTML-Fassung.

**Von Hand (ZIP), z. B. Erstinstallation auf einem neuen PC:**

1. Add-in stoppen (Skripte und Add-Ins → Stoppen).
2. Inhalt des ZIP in **denselben** Ordner kopieren und ersetzen (danach liegt `SpenglerDigital.py` direkt im Ordner). Der Benutzerdatenordner wird dabei nicht berührt.
3. Add-in starten und unter Hilfe → Fusion-Fähigkeiten Version und Ladeordner prüfen. Das Add-in prüft das Datenformat (`schemaVersion` je Datensatz):
   - Umstellung nötig → **automatische Sicherung**, Umstellung auf Kopien, Prüfung jedes Datensatzes, erst dann Übernahme.
   - Kritische Umstellung → Rückfrage vor dem Start.
   - Fehler → **keine Datei wird verändert**, Meldung mit Pfad der Sicherung.
   - Datensätze aus einer neueren Version → werden gelesen, aber nie überschrieben.
4. Zurück zum alten Stand: Palette → Sicherung → gewünschte Sicherung → Wiederherstellen.

## 16. Fehlerbehebung und bekannte Grenzen

**Protokoll:** Palette → Sicherung → «Protokoll öffnen» (Datei `protokoll/spengler_cad.log`). Bei Problemen bitte diese Datei schicken.

| Meldung | Ursache / Lösung |
|---|---|
| «Die Vorlagenbibliothek ist leer» | Zuerst unter Vorlagen & Einstellungen eine Vorlage anlegen. |
| «… FlangeFeatures.createEdgeFlangeInput fehlt» | Fusion aktualisieren; die Blech-API ist neu. |
| «… lässt sich nicht einstellen – abgebrochen» | Diese Fusion-Version kennt die Eigenschaft nicht; es wird nichts mit falschen Werten gebaut. Protokoll schicken. |
| «Neue Aussenkante ist mehrdeutig» | Folge in Einzelschritten anwenden (je Schritt eine Vorlage). |
| «Fusion lehnt den Flansch an dieser runden Kante ab» | Fusions Flansch-Schnittstelle nennt nur gerade Kanten; Umschlag (Saum) oder Rundblech-Werkzeug verwenden. Ellipse/Spline werden nicht bearbeitet. Für Rundbleche als Drehkörper den Befehl Rundblech verwenden. |
| «Materialwerte fehlen: ri, k» | Innenradius/K-Faktor im Materialprofil ergänzen oder die Vorlage ohne `ri`/`k` schreiben. |
| «Parameter nicht gefunden» (3D-Detail) | Der Benutzerparameter wurde beim Import umbenannt oder nicht übernommen; Parameter in Fusion prüfen. |

**Bekannte Grenzen dieser Version:**

- Die Fusion-Blech-API ist bei Autodesk «Preview». Flansch und Umschlag sind **nicht in Fusion geprüft**; die Eigenschaftsnamen werden gesucht und protokolliert.
- Freistellungen/Ecken erzeugt Fusion nach der Blechregel; eigene Freistellungen erzeugt das Add-in nicht.
- Flansche über die ganze Kantenlänge. Fusions Flansch-Schnittstelle (EdgeFlange, ab API Oktober 2026) nennt in der Dokumentation nur gerade Kanten. An Kreis-/Bogenkanten wird der Flansch trotzdem **versucht**; lehnt Fusion ihn ab, wird nichts gebaut und Fusions Antwort gemeldet. Zusammenhängende Kanten bekommen den ersten Flansch gemeinsam in einem Feature (Gehrung an den Ecken); klappt das nicht, werden sie einzeln gebaut (Hinweis im Bericht).
- 3D-Details: Benutzerparameter gelten im ganzen Dokument; zweimal dasselbe Detail mit verschiedenen Werten im selben Dokument ist nicht geprüft.
- Rundbleche als Drehkörper, nicht als Fusion-Blechkörper; Umformbarkeit nur mit eigenen Grenzwerten.
- Keine automatische Fusion-Zeichnung (Werkstattblatt statt dessen).
- Zuschnitt mit Rechtecken; Rollenmischung und Restelager der App nicht übernommen.
- Abgleich mit der App: Einstellungen (Zuschnitt, Etiketten, Export) bleiben je PC; abgeglichen werden Vorlagen, 3D-Details und Materialprofile.


**3D-Detail anwenden – Integration:** Mit Haken «Ins bestehende Modell integrieren» (Standard) wird das Detail als Basis-Feature plus «Kombinieren» in den Zielkörper übernommen, ohne eigene Komponente; ein Rückgängig-Schritt. Berührt das Detail den Körper nicht oder ändert es das Volumen nicht, wird alles zurückgenommen und der Grund gemeldet. Ohne Haken bleibt es eine eigene Komponente. Die Masse sind danach fest. Nicht live geprüft.

## 17. Tests in Fusion abhaken

Palette → Register **Tests**: Die Testanleitung steht dort Punkt für Punkt. Pro Punkt **✓** (ok), **✗** (Fehler, mit Notiz – Meldungstext oder Messwert) oder **–** (übersprungen); nochmal klicken nimmt zurück. Die Ergebnisse werden auf diesem PC gespeichert (`testergebnisse.json` im Benutzerdatenordner) und, wenn Sie im Register Konto angemeldet sind, sofort an die Spengler-Digital-App übermittelt, damit die Entwicklung sie sieht. Bei ✗ wird zusätzlich der Protokollauszug (letzte Zeilen) mitgesendet; sonst werden keine Kundendaten übertragen. Ohne Netz oder Anmeldung bleibt alles lokal; **Nicht gesendete Ergebnisse senden** holt das nach.

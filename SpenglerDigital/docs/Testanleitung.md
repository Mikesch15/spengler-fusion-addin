# Spengler Digital CAD – Testanleitung

Live-Test in Fusion · zum Abhaken in der Palette (Register **Tests**) oder zum Ausdrucken

> **So vorgehen:** Blöcke der Reihe nach, je Zeile ☐ abhaken. Wenn etwas nicht wie erwartet ist: **Meldungstext notieren oder Bildschirmfoto**, weitertesten (ausser ein Block sagt «sonst abbrechen»). Am Ende das **Protokoll** und die Notizen schicken. Dauer gesamt ca. 60–75 Minuten; die Blöcke lassen sich auf mehrere Tage verteilen.

## 0. Vorbereitung (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Fusion aktualisieren (Konto-Menü oben rechts → Nach Updates suchen). Fusion-Version notieren (Hilfe → Info): ________ | – |
| ☐ | Alten Prototyp stoppen: Shift+S → Add-Ins → «SpenglerDigital» → Stoppen | – |
| ☐ | ZIP `SpenglerDigitalCAD_<Version>.zip` entpacken, Ordner `SpenglerDigital` an seinen Platz kopieren (siehe README) | – |
| ☐ | Ein Lineal/Massband und einen Probestreifen Blech mit bekannter Dicke bereitlegen (für den K-Faktor in Block 3) | – |

## 1. Installation und Start (5 Min.) – sonst abbrechen

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Shift+S → Add-Ins → SpenglerDigital → **Ausführen**, «Beim Start ausführen» ankreuzen | keine Fehlermeldung |
| ☐ | Arbeitsbereich Konstruktion | Register **SPENGLER** mit «Kanten & Details», «Fertigung», «Verwaltung» und 8 Befehlen, Logo als Symbol |
| ☐ | Falls kein Register: Befehle unter Blech → Erstellen? | notieren, wo sie stehen |
| ☐ | Fusion schliessen und neu starten | Add-in startet von selbst |
| ☐ | Ordner `%APPDATA%\SpenglerDigitalCAD` (Mac: `~/Library/Application Support/SpenglerDigitalCAD`) | existiert, enthält `protokoll` und `datenformat.json` |

## 2. Selbsttest und Fähigkeiten (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | SPENGLER → Hilfe → **Fusion-Fähigkeiten prüfen** | **Versionsnummer = installierte Version** und richtiger Ladeordner; Liste mit ✓/✗ – **Bildschirmfoto** |
| ☐ | Hilfe → **Selbsttest in neuem Dokument** | neues Dokument; ✓ Einheiten, ✓ Rundblech (Ø ca. 200.7 mm), ✓ 3D-Detail (Ursprung ca. (0, 100, 0) mm, «neu beim Import: SD_H_1», «Original SD_H unverändert») – **Bildschirmfoto** |
| ☐ | Testdokument ohne Speichern schliessen | – |
| ☐ | Hilfe: Themen durchklicken, «Bedienungsanleitung (PDF) öffnen» | Texte erscheinen, PDF öffnet |

## 3. Materialien und K-Faktor (10 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | SPENGLER → **Vorlagen & Einstellungen** | Palette öffnet rechts; Kantenvorlagen **leer** mit Hinweis |
| ☐ | Register Materialien | leer, Hinweis «keine Fertigungswerte vorgegeben» |
| ☐ | Neues Materialprofil: Name, Dicke, Innenradius, Dichte, Tafeln (z. B. `1000x2000`), Rollen (z. B. `670`) | – |
| ☐ | Probestreifen: Zuschnitt messen, eine 90°-Biegung, beide Schenkel **aussen** messen → Zuschnitt, a, b eintragen → **K-Faktor berechnen** | Wert zwischen 0.3 und 0.5, Knopf «In K-Faktor übernehmen» |
| ☐ | Übernehmen → Speichern | Profil in der Liste mit K-Faktor |
| ☐ | Probe mit Unsinn (Zuschnitt grösser als a + b) | rote Meldung, nichts übernommen |
| ☐ | Gleichen K-Faktor in der **Fusion-Blechregel** eintragen (Ändern → Blechregeln) und Dicke wie im Profil | – |

## 4. Kantenvorlagen in der Palette (10 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Neue Vorlage erstellen, Name eingeben, Kurzschrift `90 H U+ u` → **übernehmen** | Parameter H und u erscheinen |
| ☐ | Statt Kurzschrift: neue Vorlage, Schritte mit **+ Flansch** / **+ Umschlag** anlegen, Winkel und Länge in der Tabelle ändern | Vorschau zeichnet jeden Schritt sofort mit; Kurzschrift-Zeile folgt der Tabelle |
| ☐ | Standardwerte H = 25, u = 7 | **Vorschau** zeigt Querschnitt mit 25 und 7, Kante grün; ändert sich beim Tippen |
| ☐ | Testmaterial wählen → **Prüfen & Trockenlauf** | «Vorlage ist gültig», Abwicklungszugabe, Bauplan |
| ☐ | Speichern | «Version 1», Vorschaubild in der Liste |
| ☐ | Expertenmodus ankreuzen → Operation hinzufügen, mit ↑ verschieben → Speichern | Kurzschrift folgt der Tabelle, «Version 2» |
| ☐ | Versionen | Version 1 wird angezeigt |
| ☐ | Duplizieren, Kopie umbenennen, Kategorie und Favorit setzen, Kategoriefilter | Kopie unabhängig, Favorit steht oben |
| ☐ | Kopie löschen → Rückfrage → **Nein** | bleibt |
| ☐ | Löschen → **Ja** → Register Sicherung → Papierkorb → Zurückholen | Vorlage wieder da |
| ☐ | Vorlage mit leerem Namen speichern | rote Fehlermeldung, nichts gespeichert |
| ☐ | Zwei Vorlagen ankreuzen → Gewählte exportieren… → Datei speichern → Importieren… dieselbe Datei | Import «als Kopie» (nichts überschrieben) |

## 5. Kanten bearbeiten (15 Min.) – Kernfunktion

Vorbereitung: Blech-Arbeitsbereich, Blechregel mit Ihrer Dicke, Rechteck 300 × 200 skizzieren → **Lasche** (Grundlasche).

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | SPENGLER → **Kanten bearbeiten**, eine obere Aussenkante wählen, Ihre Vorlage, Material | Bauplan: «Kanten: 1 gewählt, 1 geeignet», Folge mit Werten |
| ☐ | Vorschau an | Flansch + Umschlag sichtbar **vor** OK |
| ☐ | Wert H im Dialog ändern | Vorschau passt sich an |
| ☐ | OK (auch bei eingeschalteter **Vorschau** muss OK klickbar sein) | Meldung «Erfolgreich»; Masse in Fusion nachmessen: ________ |
| ☐ | Strg+Z | **alles** dieses Befehls in einem Schritt weg |
| ☐ | Zwei gegenüberliegende Kanten zugleich → OK | beide bearbeitet |
| ☐ | Zwei aneinanderstossende Kanten (Ecke) → OK | erster Flansch gemeinsam, Ecke auf **Gehrung** («gemeinsamer Flansch mit Gehrung» im Bericht); bei Hinweis «einzeln gebaut» Grund notieren |
| ☐ | Eine Biegekante bzw. Kante eines normalen Volumenkörpers wählen | «ungeeignet» mit Grund, OK gesperrt |
| ☐ | Expertenmodus im Dialog, Folge `-90 20` → OK | Abkantung nach hinten; gespeicherte Vorlage unverändert |
| ☐ | Expertenmodus, Folge `90r5 20`, «als neue Vorlage speichern» → OK | Radius 5; neue Vorlage «… (angepasst)» in der Palette |
| ☐ | Vorlage mit zu grossem Wert (Maximum setzen, darüber eingeben) | Bauplan meldet Bereich, OK gesperrt |
| ☐ | Bei jeder Fehlermeldung | Text notieren: ________ |

| ☐ | Zwei flache Bleche nebeneinander. Vorlage mit 1 Flansch 90° 25 mm und **Versatz 5**, an beiden Blechen anwenden | Beide Flansche sitzen 5 mm weiter innen, zwischen den Flanschen 10 mm Luft; in der Zeitleiste je Skizze «Versatz +5 mm» und Extrusion |
| ☐ | Gleiche Vorlage mit **Versatz −5** | Blech wird je 5 mm verlängert, Flansch sitzt aussen; Abstand der Flansche 10 mm kleiner |
| ☐ | Versatz an runder Kante | Meldung «nur an geraden Kanten», nichts gebaut |

## 6. Eigene 3D-Details (10 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Neue Komponente, darin ein kleines Detail; Benutzerparameter z. B. `SD_Laenge` anlegen und im Feature verwenden | – |
| ☐ | **3D-Detail erfassen**: Komponente, gerade Anschlusskante, Parameter ankreuzen, Name → OK | «Gespeichert … Version 1» |
| ☐ | Palette → 3D-Details | Detail in der Liste |
| ☐ | Anderes Bauteil: **3D-Detail anwenden**, Zielkante wählen | Passung «✓ passt» bzw. Gründe |
| ☐ | Wert ändern → Vorschau → OK | Detail sitzt an der Kante, Meldung nennt gesetzte Parameter |
| ☐ | «Um 180° wenden» | Detail andersherum |
| ☐ | Gekrümmte Zielkante wählen | lässt sich nicht wählen (nur gerade Kanten) |
| ☐ | **Kanten bearbeiten** an Kreis- oder Bogenkante mit einer Vorlage **aus reinen Umschlägen** (`U+ 7`) | Umschlag folgt der Kontur, keine Schlitze/Lappen; Strg+Z nimmt alles zurück – sonst die Meldung wörtlich notieren |
| ☐ | Dieselbe Kante mit einer Vorlage mit **Flansch** (`90 25`) | Fusion nimmt den Flansch **oder** meldet «Fusion lehnt den Flansch an dieser runden Kante ab» mit seiner Antwort; nichts halb gebaut |
| ☐ | **3D-Detail anwenden** mit Haken «Ins bestehende Modell integrieren» an Falzende (Blech) | Zeitverlauf: Basis-Feature + Kombinieren, keine neue Komponente, Position/Ausrichtung stimmt, Strg+Z nimmt alles zurück; Abwicklung danach prüfen |
| ☐ | Dasselbe mit Detail, das den Körper nicht berührt | klare Meldung, Modell unverändert |

## 7. Rundblech (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Rundblech / Umformung**: Scheibe r 100, Rand 20 → OK | Drehkörper; «Herstellbar: nicht beurteilbar», Rohling Ø 240 |
| ☐ | Im Materialprofil Stauchen max. z. B. 20 % mit Quelle eintragen, erneut | «Herstellbar: ja» bzw. «nein» nach Grenzwert |
| ☐ | Kragen r 50, Höhe 10 | nur Beurteilung «gestreckt», kein Körper |
| ☐ | Kegel r 100 / 50, Höhe 100 → OK | Drehkörper, Abwicklung Kreisringsektor |
| ☐ | Scheibe r 100, Rand 20, «flach» und «dxf» anhaken → OK | flacher Körper mit sichtbarer Biegelinie, DXF im Exportordner |
| ☐ | Aus dem flachen Körper eine Zeichnung ableiten | Biegekante in der Zeichnung sichtbar |

## 8. Abwicklung, DXF und Werkstattblatt (8 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Abwicklung & DXF**, Blechkörper aus Block 5 (noch ohne Abwicklung: feststehende Fläche wählen) → OK | Ordner öffnet sich, `Nr_…dxf` und `…_werkstattblatt.html` |
| ☐ | DXF in einem CAD-Programm öffnen | Kontur und Biegelinien, Masse stimmen |
| ☐ | Werkstattblatt öffnen | Teilenummer, Material, Vorlage + Version, **Querschnitt mit Massen**, **Abwicklung mit Biegelinien**, Biegeliste |
| ☐ | Werkstattblatt nach Export | Zeichnung der Abwicklung (aus DXF) sichtbar, Biegelinien gestrichelt |
| ☐ | Zwei Körper gleichzeitig | beide exportiert, Zusammenfassung «2 von 2» |
| ☐ | Normaler Volumenkörper | «✗ … kein Blechkörper» |

## 9. Stückliste, Etiketten, Zuschnitt (8 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Einstellungen → Etikettenbogen: Masse Ihres Bogens eintragen | «Belegt … von 210 × 297 mm» bzw. «Passt nicht auf A4» |
| ☐ | **Stückliste & Zuschnitt**: 2–3 Blechkörper, Stück 2, Objekt, Auftrag → OK | Ordner mit `stueckliste.csv/.html`, `etiketten.html`, `zuschnittplan.svg/.csv/.dxf`, `bericht.txt` |
| ☐ | Befehl erneut ausführen | **gleiche** Teilenummern; Objekt/Auftrag vorausgefüllt |
| ☐ | `stueckliste.csv` in Excel öffnen | Spalten richtig, Umlaute richtig |
| ☐ | `etiketten.html` drucken (Ränder: keine, 100 %) auf Etikettenbogen | Etiketten sitzen auf den Feldern |
| ☐ | `zuschnittplan.svg` ansehen | keine Überlappungen, Teile beschriftet |

## 9a. Aufträge als Ordner (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Neuer Auftrag**: Nummer 99999, Objekt «Testweg 1, Bern», Jahr → OK | Meldung «Ordner angelegt», im Datenfenster Stammordner/Jahr/«99999 Testweg 1, Bern» mit Modelle, Pläne, Export |
| ☐ | Denselben Auftrag nochmals anlegen | Hinweis «gab es schon», keine doppelten Ordner |
| ☐ | Einstellungen → Aufträge: Jahresordner aus, Unterordner ändern → speichern, neuen Auftrag anlegen | Struktur entsprechend den Einstellungen |
| ☐ | Dokument im Ordner «Modelle» eines Auftrags speichern, **Stückliste & Zuschnitt** öffnen | Auftrag und Objekt sind aus dem Ordnernamen vorbelegt |
| ☐ | Testordner wieder löschen (von Hand im Datenfenster) | – |

## 10. Sicherung, Wiederherstellung, Update (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Palette → Sicherung → **Sicherung erstellen** | erscheint in der Liste |
| ☐ | Eine Vorlage löschen, dann die Sicherung **Wiederherstellen** | Rückfrage; Vorlage wieder da |
| ☐ | **Update simulieren:** Add-in stoppen, Ordner `SpenglerDigital` löschen und aus dem ZIP neu kopieren, starten | Vorlagen, Materialien, Einstellungen **alle noch da** |
| ☐ | Palette → Sicherung → **Protokoll öffnen** | Textdatei öffnet sich |

## 11. Konto, Abgleich und Updates (10 Min.) – ab 0.4.0

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Palette → Register **Konto** → mit App-Benutzername und Passwort anmelden | «Angemeldet als …, Firma …», Recht «dürfen Vorlagen ändern» (Admin) |
| ☐ | Falsches Passwort versuchen | «Benutzername oder Passwort falsch.» |
| ☐ | **Jetzt abgleichen** | Bericht: Vorlagen/Materialien «in die App hochgeladen» |
| ☐ | Eine Vorlage ändern und speichern | oben «✓ mit der App abgeglichen» |
| ☐ | Zweiter PC (oder zweites Windows-Konto): Add-in installieren, anmelden | dieselben Vorlagen und Materialien erscheinen |
| ☐ | Mit einem **Mitarbeiter**-Konto anmelden, Vorlage ändern | Hinweis «nur auf diesem PC», in der App unverändert |
| ☐ | Fusion ohne Internet starten (WLAN aus) | Add-in startet normal, kein Fehler; nach Wiederverbindung «Jetzt abgleichen» |
| ☐ | **Nach Updates suchen** | Rückfrage «Version x.y.z verfügbar» (nur wenn eine neuere bereitliegt) → Ja → «installiert (2 Dateien)» → Add-in stoppen/ausführen → Hilfe → Fähigkeiten zeigt die neue Version |
| ☐ | Abmelden | Anmeldemaske; Vorlagen bleiben lokal |

## 12. Tests in der Palette (3 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Palette → Register **Tests**: einen Punkt mit ✓ abhaken, bei einem anderen ✗ mit Notiz, bei einem dritten – | Farbe wechselt, Fortschritt oben zählt mit; Zeile zeigt «gesendet» (wenn angemeldet) bzw. «nur lokal» |
| ☐ | Ohne Anmeldung abhaken, dann anmelden, «nicht gesendete Ergebnisse senden» | Meldung «n Ergebnis(se) gesendet» |

## 13. Rückmeldung

| ☐ | Was schicken |
|---|---|
| ☐ | Datei `…\SpenglerDigitalCAD\protokoll\spengler_cad.log` |
| ☐ | Bildschirmfotos aus Block 2 und alle Fehlermeldungen |
| ☐ | Fusion-Version und Betriebssystem |
| ☐ | Notizen: was war unklar, umständlich oder fehlt? |

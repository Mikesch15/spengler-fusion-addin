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
| ☐ | Register SPENGLER ansehen | Vier Gruppen «1 · Auftrag», «2 · Konstruieren», «3 · Fertigung», «Verwaltung»; jeder Befehl hat ein eigenes, scharfes Symbol (auch im dunklen Fusion-Design) |
| ☐ | **Start / Übersicht** | Liste mit ✅/⚠️ (Konto, Material, Vorlagen, Auftrag, Projekt in der App); «Nächster Schritt» ist vorgewählt |
| ☐ | Ohne aktiven Auftrag **Kanten bearbeiten** starten | Der Befehl öffnet nicht; Hinweis «kein Auftrag aktiv … Jetzt dorthin wechseln?»; «Ja» startet «Auftrag wählen» |

## 2. Selbsttest und Fähigkeiten (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | SPENGLER → Hilfe → **Fusion-Fähigkeiten prüfen** | **Versionsnummer = installierte Version** und richtiger Ladeordner; Liste mit ✓/✗ – **Bildschirmfoto** |
| ☐ | Hilfe → **Selbsttest in neuem Dokument** | neues Dokument; ✓ Einheiten, ✓ Rundblech (Ø ca. 200.7 mm), ✓ 3D-Detail (Ursprung ca. (0, 100, 0) mm, «neu beim Import: SD_H_1», «Original SD_H unverändert») – **Bildschirmfoto** |
| ☐ | Testdokument ohne Speichern schliessen | – |
| ☐ | Kanten bearbeiten öffnen, noch nichts wählen | oben gelbe Ampel «Blechkörper wählen»; nach Körper + Kante grün «Bereit: …»; Kurzinfo unter «Vorlage» – **Bildschirmfoto** |
| ☐ | Kanten bauen, dann Zeitleiste ansehen | eine Gruppe «Spengler: <Vorlage>»; Strg+Z nimmt sie ganz zurück; Meldung nennt das Material des Auftrags |
| ☐ | Kanten bearbeiten nochmals öffnen | zuletzt benutzte Vorlage steht oben (↻), Material des Auftrags ist vorgewählt |
| ☐ | Auftrag-Wahl zurücksetzen (Einstellungen → Aufträge) und «Kanten bearbeiten» öffnen | Sperre mit Knopf «Jetzt beheben: Auftrag wählen öffnen» |
| ☐ | SPENGLER → Verwaltung → **Live-Test** → «Test starten» (Haken «Ergebnis senden» an), 1–2 Min. nichts anklicken | Meldung «x ok, y Warnungen, z Fehler»; Bericht als Testpunkt 97.002 in der App-Datenbank und in `livetest.txt` – **dieses Ergebnis genügt**, die Einzelprüfungen der Blöcke 5/8 müssen dafür nicht von Hand gemacht werden |
| ☐ | Hilfe: Themen durchklicken, «Bedienungsanleitung (PDF) öffnen» | Texte erscheinen, PDF öffnet |

**Live-Test der Blechgeometrie (ab 0.4.49) – so starten und zurückmelden:** Ein beliebiges Dokument offen lassen (es wird nicht verändert). SPENGLER → Verwaltung → **Live-Test** → Haken «Ergebnis senden» an → «Test starten». 2–4 Minuten nichts anklicken; Fusion öffnet und schliesst dabei eigene Testdokumente ungespeichert. **Erwartet:** je Schritt ✓ (PASS) oder ✗ (FAIL) mit Zahlen: Grundblech 1.0 und 0.7 mm in eigener Komponente (Regel und gemessene Dicke = Soll), ungültiges Profil/Dicke abgelehnt ohne Reste, Flansch, Gehrung an 2 Eckkanten, Umschlag je Kante (echter Saum), Versatz ±5, Rückbau nach provoziertem Fehler (genau der eingeschleuste Fehler, Zustand vorher = nachher inkl. Occurrences, Komponenten, Parameter, Blechregeln), Rückbau des 3D-Detail-Imports in jeder Phase, Abwicklung L- und U-Blech mit DXF (mm, 1 Kontur), Gehrungsecke mit gemessenem Eckspalt, Doppelfalz-Testprofil, gekrümmte Testkörper (Bogenkante, Zylinder, Teilzylinder, Kegel, gerolltes Blech R20, Kugelband: Normalenwinkel ≤ 0.5°, Detail-Abstand = 2 mm, Abwickelbarkeit). «Fusion lehnt ab – bleibt nicht unterstützt» ist bei Bogen-/Zylinderkanten das erwartete Ergebnis; «Fusion HAT gebaut» bitte mit Bildschirmfoto melden. **Prototypen (ab Korrekturauftrag 5.11.):** gerolltes Zylinderblech (Konturflansch), Flansch und Umschlag an der geraden Mantelkante (geprüft entlang der GANZEN Kante), Versatz als Bogenlänge, Abwicklung/DXF des Zylinderblechs, Teilkegel-Grenzen, Torus, Übergang Zylinder–Kegel. Schlägt «gerolltes Blech» fehl, stehen alle Fusion-Antworten im Bericht – bitte vollständig zurückmelden. **Kantenwerkzeug, eigene Geometrie (Testpaket, Branch `ccr-26e82854-8ygnzg`):** Die Schritte «KANTENWERKZEUG eigen: …» im Live-Test erzeugen alles selbst (Testdokumente, Test-Blech 100 × 60 × 1 mm, Zylindersegment R100/90°/80 mm). PASS-Kriterien: Aufkantung/Falz/Doppelfalz – Volumen = Querschnitt × 100 mm (±0.1 %), Höhe auf 0.01 mm, Abwickelbarkeit «mathematisch abwickelbar» (im Bericht als Kennwert «exakt» geführt); Prototyp 2 – Rückvergleich ok (Volumenabweichung ≤ 0.01 mm³ bzw. 1e-5 relativ, Radien 1/2/100/101 mm vorhanden), DXF-Masse auf 0.01 mm, 1 Kontur; Negativfälle – Ablehnung mit dem genannten Grund und ohne Reste; Rückbau – genau der eingeschleuste Fehler, Zustand unverändert. Der Bericht landet als 97.002 in der App und als `livetest.txt` im Datenordner; zusätzlich bitte im Werkzeug «Kanten bearbeiten» einmal von Hand Bauweise «Eigene Geometrie» an einer geraden Blechkante ausprobieren (Bildschirmfoto Bauplan + Ergebnis). **Pflicht-Live-Tests nach Korrektur 0.4.49** (für jeden: Fusion-Version + Betriebssystem, Testgeometrie, Parameter, erwartet/tatsächlich, Bildschirmfoto, Status bestanden/fehlgeschlagen/nicht durchgeführt in den Bericht): (1) planare Kante Flansch – Live-Schritte «Flansch 90°» und «KANTENWERKZEUG eigen: Aufkantung»; (2) Umschlag/Doppelumschlag – «Umschlag 10 mm», «KANTENWERKZEUG eigen: Aufkantung + Doppelfalz»; (3) unbekannte Fläche – in Fusion nicht gezielt erzeugbar, nur als Stub-Test vorhanden → im Bericht «nicht durchgeführt (nicht provozierbar)»; (4) Zylinder-Mantelkante – «KANTENWERKZEUG eigen: Prototyp 2» (Testmodus, im normalen Betrieb gesperrt); (5) Blechstatus vor/nach eigener Geometrie und (6) native Abwicklung danach und (7) DXF mit Konturprüfung – alle drei im Schritt «KANTENWERKZEUG eigen: Aufkantung» (isSheetMetal vorher/nachher, Abwicklung, DXF); (8) erzwungener Fehler – «KANTENWERKZEUG eigen: Rückbau» (nach Extrusion, in der Abwicklungs- und in der DXF-Prüfung). Ein bestandener Live-Test ist KEINE Fertigungsfreigabe; Zuschnittlängen sind theoretisch, bis eine Probebiegung sie bestätigt. **Ohne Release** (Entwicklungsstand im Branch): Ordner `SpenglerDigital` aus dem Branch wie bei der Grundinstallation in den Add-in-Ordner kopieren (vorher den bisherigen Ordner sichern), Fusion neu starten. **Fehlerbilder:** ✗ mit «gemessen … statt …» (falsche Dicke), «liegt nicht in der Zielkomponente», «Rückbau UNVOLLSTÄNDIG», «Kontur(en) statt 1». **Zurückmelden:** nichts weiter nötig, wenn «Ergebnis senden» an war (Testpunkt 97.002); sonst `livetest.txt` aus dem Datenordner schicken, bei ✗ zusätzlich ein Bildschirmfoto der Meldung.

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
| ☐ | Zwei zusammenstossende Kanten eines Blechs, Vorlage Flansch 90° 25 mm mit Versatz 5 (und −5) | Gemeinsamer Flansch mit Gehrung an der Ecke, beide Flansche um 5 mm versetzt, nur eine Skizze «Versatz» und eine Extrusion |
| ☐ | Versatz an runder Kante | Meldung «nur an geraden Kanten», nichts gebaut |
| ☐ | Zwei Bleche nebeneinander. **Kanten bearbeiten**: zuerst Blech A wählen, dann eine Kante von Blech B anklicken | Kante von B wird nicht übernommen bzw. Plan meldet «liegt nicht auf dem gewählten Körper»; Kantenfeld ist vor der Körperwahl gesperrt |

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

## 9b. Auftrag wählen, Export, Listen (8 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Auftrag wählen**: Suchfeld «Sonne», Auftrag wählen, Haken «Dokument im Ordner Modelle speichern» → OK | Meldung «Aktiver Auftrag …», Dokument liegt im Ordner «Modelle» des Auftrags |
| ☐ | Dasselbe nochmals mit dem schon dort liegenden Dokument | Meldung «liegt schon im Ordner» |
| ☐ | Einstellungen → Aufträge: «Exporte auf dem PC» auf einen Testordner setzen, speichern; **Abwicklung & DXF** | Dateien liegen in `Basis/Jahr/Nummer Objekt/Export/<Datum>` |
| ☐ | Teile im Werkstattblatt/Stückliste | Teilenummern wie `17642-01` |
| ☐ | **Stückliste & Zuschnitt** mit «Abkantliste» | `abkantliste.html` mit Biegefolge je Teil; Prüfung zeigt Warnungen (z. B. Schenkel unter 10 mm) |
| ☐ | In einem zweiten Dokument desselben Auftrags «Stückliste & Zuschnitt» mit «Bestellliste für den ganzen Auftrag» | `bestellliste.txt` nennt beide Dokumente |
| ☐ | Register **Berichte**: Änderungsprotokoll → Aktualisieren, nach einer Vorlagenänderung | Eintrag mit Zeit, Benutzer, Aktion |
| ☐ | Eine Fehlermeldung auslösen (z. B. Umschlag an ungeeigneter Kante), Berichte → Fehlerberichte laden | Bericht mit Protokollauszug erscheint |

## 9c. Status, Kalkulation, Mappe, Reste (10 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Auftrag wählen**, Status «In Arbeit» setzen → OK; Befehl nochmal öffnen | Hinter dem Auftrag steht «[In Arbeit]»; die App-Info zum Auftrag erscheint (falls dort vorhanden) |
| ☐ | Einstellungen → Kalkulation: Name eines Stundensatzes aus der App (z. B. Spengler) eintragen, speichern; **Stückliste & Zuschnitt** mit «Kalkulation» | `kalkulation.html` mit Stundensatz «App: …», Arbeitszeit und Kosten |
| ☐ | Materialprofil: «Preis je kg» und Dichte eintragen, erneut | Spalte «Material» in der Kalkulation gefüllt |
| ☐ | «Auftragsmappe» anhaken | `auftragsmappe.html` mit Deckblatt und Abschnitten; im Browser Strg+P zeigt eine Seite je Abschnitt |
| ☐ | Kantenvorlage öffnen → «Profilzeichnung öffnen» | Seite mit Querschnitt, Massen und Winkeln öffnet sich |
| ☐ | **Abwicklung & DXF** mit «Teilenummer in die DXF schreiben»; DXF in einem CAD öffnen | Teilenummer als Text in der Mitte, Kontur unverändert |
| ☐ | Register **Reste**: Rest erfassen (gleiches Material und Dicke wie ein Teil, grösser als das Teil); **Stückliste & Zuschnitt** | «Passende Reststücke» nennt das Teil |
| ☐ | Fehlermeldung auslösen, Register **Berichte → Fehlerberichte laden** | Bericht mit Bildschirmfoto und Protokoll |
| ☐ | Nach dem Update (neue Version) | Testpunkt 97.001 (Selbsttest) erscheint in der App-Datenbank |

## 9d. Vorlage aus Profil lernen (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Dokument mit einem Profil aus 2–3 Flanschen/Falzen (z. B. «Winkelfalz 35») öffnen, **Vorlage aus Profil lernen** | Liste der Schritte in Zeitleistenreihenfolge, mit gelesenen Werten (Winkel, mm) |
| ☐ | Name eingeben, OK | Meldung mit Kurzschrift; Vorlage erscheint in der Palette (Kategorie «Gelernt») |
| ☐ | Vorlage im Editor öffnen | Winkel und Längen stimmen mit dem Profil überein; Vorschau prüfen, Richtungen (Vorzeichen) falls nötig ändern |
| ☐ | Dokument ohne Flansche öffnen, Befehl starten | Meldung «keine Flansch- oder Saum-Features gefunden» |

## 9e. CAD ↔ App (8 Min.) – braucht die App-Version mit «Teile aus dem CAD»

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | Testauftrag, der es in der App als Projekt mit gleicher Auftragsnummer gibt; Teile mit Vorlage bauen; **Stückliste & Zuschnitt** mit «Teile an die App senden» | Bericht: «App: n Teil(e) gesendet (Auftrag «…»)» |
| ☐ | In der App das Projekt öffnen, Cockpit → Massaufnahmen | Unter der Liste «Teile aus dem CAD» mit Teilnummer, Zuschnitt, Material, Vorlage |
| ☐ | «Als Massaufnahme übernehmen», Material wählen, speichern | Neue Massaufnahme «Freies Profil» mit den Schenkeln; Summe der Masse = Abwicklungsbreite; Teil zeigt «übernommen» und «Massaufnahme öffnen» |
| ☐ | Zuschnitt und Werkstattansicht der App für diese Massaufnahme ansehen | Masse und Zuschnitt erscheinen wie bei einer selbst erfassten Massaufnahme |
| ☐ | Im CAD dasselbe Teil nochmals senden | Kein doppeltes Teil in der App (wird überschrieben) |
| ☐ | In der App eine Massaufnahme «Freies Profil» im Testauftrag anlegen; im CAD **Vorlage aus App-Massaufnahme** | Liste der Massaufnahmen; Vorlage mit den Biegungen entsteht (erster Schenkel entfällt) |
| ☐ | In der App an der Massaufnahme «Freies Profil» des Testprojekts **«An CAD senden»**, Länge 1500, 2 Stück | Bestätigung; im Projekt-Cockpit Box «An das CAD gesendet» mit «wartet auf das CAD» |
| ☐ | **Andere Ablage** → «– neue Ablage anlegen –», Name «Test-Ablage», Ordner `Test/Ablage`, Haken «Dokument speichern» und «aktiv» | Ordner `Test/Ablage` im Fusion-Projekt, Dokument liegt dort; Meldung «aktive Ablage»; Start zeigt «Aktive Ablage: Test-Ablage» |
| ☐ | Bei aktiver Ablage **Kanten bearbeiten** und **Stückliste & Zuschnitt** (ohne Auftrag) | Befehle öffnen ohne Sperre; Export im Ordner `…/Test-Ablage/…`; «App: keine Auftragsnummer – nichts gesendet» |
| ☐ | «Auftrag wählen» für einen Testauftrag | Die Ablage ist nicht mehr aktiv (Start zeigt den Auftrag) |
| ☐ | Palette → Register **Projekt**, Testprojekt wählen | Kopf (Kunde, Status, Hinweis, nächster Termin), Massaufnahmen mit Werkstattstand, «CAD und Werkstatt», Termine, Rapporte, Dateien, Offerten – **Bildschirmfoto** |
| ☐ | In der Projektkarte den **Projektstatus** ändern, «In der App ändern», Rückfrage mit Ja; in der App nachsehen | Status in der App geändert; in der Karte neu geladen. Danach in der App den Status anders setzen und im CAD (mit alter Karte) nochmals ändern → Meldung «inzwischen anderswo geändert», nichts überschrieben |
| ☐ | **Hinweis** ändern, dann eine Zeile **ergänzen** | Hinweis steht in der App im Projekt (Cockpit); die ergänzte Zeile trägt Datum, Namen und «(CAD)» |
| ☐ | **+ Termin hinzufügen** (Titel, Beginn 10.11.2026, 07:30, Ort), dann bei diesem Termin **Ändern** | Termin steht in der App unter Termine am Projekt; Änderung wird übernommen; ein Outlook-Termin hat keinen «Ändern»-Knopf |
| ☐ | In der Projektkarte bei einer Massaufnahme mit Foto «📷 Fotos/Skizzen», Bild antippen, **In Fusion einfügen** | Bild erscheint, antippen vergrössert; im Fusion-Dokument gibt es ein Referenzbild (Canvas) – Lage/Grösse einstellbar |
| ☐ | In der App eine Massaufnahme weiterschalten (rüsten/montieren) oder eine neue anlegen, dann im CAD **Start** | Zeile «🔔 Neu aus der App: …» und «Projekt: Kunde · Status …»; in der Projektkarte «Neu seit dem letzten Mal» |
| ☐ | Dateien: «Öffnen» bei einem Plan in der Projektkarte | Datei liegt unter Exportordner/App-Dateien/<Auftrag> und öffnet sich |
| ☐ | Im CAD **Blech aus Massaufnahme** | Ganz oben «📤 aus der App: … – 1500 mm × 2 Stück», Länge 1500 vorbelegt; nach OK Blech gebaut, Meldung «In der App als gebaut vermerkt», in der App «✔ im CAD gebaut» |
| ☐ | Im CAD **Blech aus Massaufnahme** (Testauftrag mit Massaufnahme) (Konstruieren), Massaufnahme «Freies Profil» wählen, Länge prüfen, OK | Neue Komponente mit Grundblech (Breite = erster Schenkel) und den Kanten der App; Zeitleisten-Gruppe «Spengler: …»; Hinweis bei abweichender Blechregel – **Bildschirmfoto** |
| ☐ | Palette → Register **Skizze**: mit Stift/Finger/Maus ein Winkelprofil zeichnen (Blech, 90° hoch, 90° zurück), dann in der Tabelle einen Wert ändern | Längen/Winkel rasten ein, Tabelle und Kurzschrift stimmen, Zuschnittbreite erscheint mit Material; Stift/Finger funktionieren (Tablet) – **Bildschirmfoto** |
| ☐ | Skizze benennen, «Als Kantenvorlage übernehmen», speichern | Vorlage erscheint unter Kantenvorlagen; auf eine Kante angewendet entsteht das gezeichnete Profil |
| ☐ | Palette → Register **Bauteile** → «Neues Bauteil erstellen»: Name, Verlauf *Grundrissverlauf*, Beispiel `3000 L90 2000 L90 3000 L90 2000 L90`, Haken «Ring», Breite `Mauer+2*Ue`, Kante am Verlauf `90 Tropf U+ 8`, «Parameter erkennen», Standardwerte 300 / 35 / 40, Speichern | Vorschau zeigt Ring (blaue Kante am Verlauf, orange Gegenkante) und den Querschnitt; Bauteil steht in der Liste |
| ☐ | **Bauteil erstellen** (Konstruieren), dieses Bauteil, Haken «Geschlossener Ring» | Ampel grün «Bereit: Breite 380 mm, 4 Strecken (Ring) …»; nach OK Blech als Rahmen mit Flansch und Umschlag an der Verlaufskante, Ecken auf Gehrung – **Bildschirmfoto** der Ecken |
| ☐ | Dasselbe mit offenem Verlauf `3000 L90 2000` (Haken «Ring» aus) und Seite «rechts» | Winkelförmiges Blech; Kantenfolge an beiden Strecken der Verlaufskante gemeinsam, Gehrung an der Ecke |
| ☐ | Bauteil mit Verlauf *gerade* und Länge 2000 | Ebenes Streifenblech mit den Kantenfolgen |

## 9f. Aufträge App ↔ Fusion abgleichen (5 Min.)

| ☐ | Schritt | Erwartet |
|---|---|---|
| ☐ | **Aufträge abgleichen** | Dialog: Projekte der App ohne Ordner und Ordner ohne Projekt, Zahl «in beiden», Abweichungen |
| ☐ | Nur einen Eintrag aus «App → Ordner» angehakt lassen, OK | Ordner `Stamm/Jahr/Nummer Objekt` mit Unterordnern entsteht in Fusion |
| ☐ | Einen Testordner `99998 Abgleich Test, Bern` in Fusion anlegen, abgleichen, nur diesen anhaken | Projekt «99998» erscheint in der App (Titel = Objekt) |
| ☐ | Nochmals abgleichen | Beide Einträge sind jetzt «in beiden» |
| ☐ | **Neuer Auftrag** mit Haken «Auch als Projekt in der App anlegen», Nummer 99997 | Meldung «App: Projekt 99997 … angelegt»; gleiche Nummer nochmals → «gibt es schon» |
| ☐ | Palette → Register **Aufträge** | Alle Aufträge mit Ordner ✓/–, App ✓/–, Fertigung, Teile «gefertigt/gesamt», Hinweise; Suche und Filter funktionieren |
| ☐ | In der Liste einen Fertigungsstatus ändern, dann «Aktiv» bei einem Auftrag | Status steht in der App/Auftrag wählen; Zeile wird als aktiv markiert (●) |
| ☐ | Testprojekte in der App wieder löschen/archivieren | – |
| ☐ | **Stückliste & Zuschnitt** mit «Dateien am Projekt in der App ablegen»; in der App Projekt → Cockpit → Dateien | «CAD – Stückliste …», «CAD – Auftragsmappe …» usw. sind da und lassen sich öffnen; Meldung «App-Dateien am Projekt: n neu» |
| ☐ | Dasselbe nochmals ausführen | Meldung «… ersetzt», keine doppelten Dateien in der Liste |

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


## Live-Tests Kantenwerkzeug (Tests 1–6) – vorbereitet, NICHT durchgeführt

Für jeden Test erfassen: Voraussetzungen/Ausgangszustand · Bedienungsschritte · erwartetes Ergebnis · tatsächliches Ergebnis · **bestanden / nicht bestanden
/ nicht durchführbar** · Fusion-Version (Hilfe → Über) und Betriebssystem · bei Fehlern Bildschirmfoto und Protokoll (Palette → Sicherung → «Protokoll
öffnen»). Alle Tests nur in einer **eigenen Testdatei** bzw. einer gespeicherten Kopie, nie im Kundenmodell. Add-in-Version: 0.4.53 oder neuer.

**Vorbereitung (für alle Tests):** Materialprofil mit Dicke 1.0 mm, Innenradius 1.0 mm und K-Faktor (z. B. 0.44) anlegen; Auftrag wählen (falls
«Auftrag erforderlich» eingestellt ist); Vorlage mit genau einem Flansch 90° / 20 mm (Kurzschrift im Expertenmodus z. B. `90 20`).

**Test 1 – Ausgangskörper.** Voraussetzung: neues Dokument, «Blech aus Massaufnahme» bzw. Fusion-Blech: Basisflansch 100 × 60 mm, Blechregel 1.0 mm.
Schritte: (1) Datei speichern als «LT-Kantenwerkzeug-1»; (2) Körper anklicken → Eigenschaften: Blechkörper ja, Dicke 1.0 mm notieren; (3) im Browser
nachsehen, ob unter der Komponente eine «Abwicklung» (Flat Pattern) existiert – notieren (für Test 4 soll KEINE vorhanden sein). Erwartet: gültiger
Blechkörper 1.0 mm, keine Abwicklung. Bestanden: beides zutreffend; nicht bestanden: kein Blechkörper oder andere Dicke.

**Test 2 – Eigene Geometrie an gerader Kante.** Voraussetzung: Test 1. Schritte: (1) SPENGLER → «Kanten bearbeiten»; (2) Körper wählen, dann die
obere lange Aussenkante (gerade, an der ebenen Oberseite); (3) Vorlage «90 20», Material aus der Vorbereitung; (4) **Bauweise: «Eigene Geometrie»**;
(5) Bauplan lesen: «Analyse … gerade Kante auf eben Fläche … mathematisch abwickelbar … Zuschnitt THEORETISCH»; (6) Vorschau einschalten und ansehen;
(7) OK. Erwartet: Vorschau zeigt eine Aufkantung nach oben über die ganze Kantenlänge; Ergebnisbericht ohne Fehler, mit den Zeilen «Blechkörper bleibt
Fusion-Blech; native Abwicklung … und DXF streng geprüft» und «temporäre Prüf-Abwicklung entfernt und Entfernung geprüft»; Körper danach weiterhin
Blechkörper (Eigenschaften). Bestanden: alles zutreffend. Nicht bestanden: Fehlermeldung, Körper kein Blech mehr, oder Bericht ohne diese Zeilen.
Nicht durchführbar: Bauweise-Auswahl fehlt (falsche Version) – Version prüfen.

**Test 3 – Native Abwicklung und DXF.** Voraussetzung: Test 2 bestanden. Schritte: (1) SPENGLER → «Abwicklung & DXF», Körper wählen, DXF an;
(2) Ausgabeordner öffnen, Änderungszeit der DXF notieren (muss jetzt sein); (3) Bericht lesen: «Abwicklung … (Fusion-Blechregel, theoretischer
Zuschnitt …)», «DXF ✓»; (4) DXF in einem unabhängigen Viewer/CAD öffnen (z. B. eDrawings, LibreCAD, DWG TrueView): Aussenmasse messen und mit dem
Bericht vergleichen, Kontur geschlossen, keine doppelten Linien, Biegelinie(n) vorhanden. Erwartet: neue Datei, Masse im Viewer = Bericht (± 0.1 mm),
eine geschlossene Aussenkontur. Hinweis: Die STRENGE Prüfung lief bereits in Test 2 (Zeile «DXF streng geprüft»); der Export hier nutzt die normale
Prüfung. DXF-Datei dem Testprotokoll beilegen. Bestanden / nicht bestanden entsprechend.

**Test 4 – Prüf-Abwicklung wird entfernt.** Teil A (keine Abwicklung vorher): nach Test 2 im Browser prüfen, dass KEINE Abwicklung unter der Komponente
steht (die interne Prüf-Abwicklung muss weg sein). Teil B (Abwicklung vorher vorhanden): neue Testdatei wie Test 1, dann in Fusion selbst eine Abwicklung
erzeugen (Blech → Abwicklung erstellen, Fläche oben), zurück ins Modell, dann Test 2 wiederholen. Erwartet A: keine Abwicklung; B: die eigene Abwicklung
existiert weiterhin (nicht gelöscht) und zeigt die neue Aufkantung. Fehlerfall: Meldet das Werkzeug «Prüf-Abwicklung liess sich nicht entfernen … FEHLGESCHLAGEN»,
ist der Test **nicht bestanden** – Bildschirmfoto und Protokoll senden.

**Test 5 – Rückbau bei DXF-Prüffehler.** Der Testfehler `eigen_validierung_dxf` lässt sich nicht über die Oberfläche auslösen; er läuft im
automatischen Live-Test. Schritte: SPENGLER → Verwaltung → Live-Test, «Ergebnis senden» an, starten, 3–5 Minuten nichts anklicken. Im Bericht den
Schritt «KANTENWERKZEUG eigen: Rückbau» suchen; Zeile `eigen_validierung_dxf: eingeschleuster Fehler ausgelöst; Zustand unverändert; Rückbau gemeldet ok`.
Erwartet: genau diese Zeile (✓ PASS). Nicht bestanden: «ANDERER Fehler», «VERÄNDERT», «NICHT VOLLSTÄNDIG MESSBAR» oder «UNVOLLSTÄNDIG». Bestehende
Objekte des Testdokuments bleiben erhalten (Zustandsvergleich im Bericht).

**Test 6 – Rückbau bei Löschfehler der Prüf-Abwicklung.** Ab 0.4.53 im automatischen Live-Test enthalten (über die Oberfläche nicht auslösbar). Schritte
wie Test 5; im Bericht den Schritt «KANTENWERKZEUG eigen: Rückbau» suchen, Zeile `eigen_pruefabwicklung_loeschen: eingeschleuster Fehler ausgelöst;
Zustand unverändert; Rückbau gemeldet ok`. Erwartet: Vorgang als fehlgeschlagen gewertet, Prüf-Abwicklung und neue Features entfernt, keine Abwicklung
unter der Komponente. Nicht bestanden: «VERÄNDERT» (z. B. Abwicklung zurückgeblieben) oder «UNVOLLSTÄNDIG» ohne Meldung des Restobjekts. Hinweis: Die
Teststelle löst den Fehler unmittelbar VOR dem Löschen aus; ein echtes «deleteMe() meldet False» von Fusion lässt sich live nicht erzwingen (nur Attrappen-Test).

**Abgabe:** Bericht 97.002 (automatisch bei «Ergebnis senden») bzw. `livetest.txt` aus dem Datenordner, dazu je Test 1–4 eine Zeile «bestanden / nicht
bestanden / nicht durchführbar», Fusion-Version, Betriebssystem, Bildschirmfotos und die DXF aus Test 3. Ein bestandener Live-Test ist KEINE
Fertigungsfreigabe.

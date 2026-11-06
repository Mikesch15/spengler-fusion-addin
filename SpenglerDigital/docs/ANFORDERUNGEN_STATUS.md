# Spengler Digital CAD – Anforderungsliste mit Status

**Aktueller Stand: Abschnitt «AKTUELLER STAND – Spengler-Kantenwerkzeug (Version 0.4.77)» ganz am Ende; alle Abschnitte davor sind HISTORISCH (5. 11. 2026, Branch `ccr-26e82854-8ygnzg`, nach 0.4.49, NICHT veröffentlicht).** Die älteren Abschnitte (auch «Nachtauftrag») sind Verlauf.

Stand 29.10.2026 · Programmstand 0.4.2 (geprüft wurde 0.4.0 inkl. der Korrekturen in 0.4.2) · Grundlage: Projektauftrag
«SPENGLER DIGITAL CAD – MASTER-AUFTRAG», Quellcode im Repo `Spengler-Digital-CAD`, Branch `claude/new-session-ux68bs`, Testanleitung.

## Statuswerte

| Kürzel | Bedeutung |
|---|---|
| **AUTO** | umgesetzt und automatisiert getestet (ohne Fusion; reine Rechnung/Datenlogik) |
| **LIVE** | in Fusion live getestet (vom Anwender, Fusion 2706.1.17, Windows) |
| **TEIL** | teilweise umgesetzt – oder Code vorhanden, aber die Ausführung in Fusion ist NICHT live geprüft |
| **NEIN** | nicht umgesetzt |

Regel: Eine Funktion, die Fusion-API-Aufrufe braucht, steht höchstens auf **TEIL**, solange sie nicht live geprüft ist –
auch wenn ihre Entscheidungslogik mit nachgebauten Fusion-Objekten getestet ist («Logik-Test»). Ein bestandener Test mit
Attrappe oder Nachbau beweist nur, dass das Add-in richtig entscheidet, nicht dass Fusion es so ausführt.

Live geprüft wurde bisher nur (Anwender, 29.10.2026): Start und Werkzeugleiste, Fähigkeitsprüfung (alle 9 API-Funktionen
vorhanden), Selbsttest (Einheiten 25 mm = 2.5 cm, Drehkörper Ø 200.70 mm, .f3d-Export/-Import, Ausrichtung per Matrix
(0, 100, 0) mm, Benutzerparameter setzen). Dabei gefunden und behoben: Palette-URL (0.3.1), Parameter-Umbenennung beim
Import (0.3.1), alter Code im Speicher nach Update (0.3.2). Die Palette selbst, alle Kantenbefehle, Abwicklung, DXF,
Konto/Abgleich und Updates sind in Fusion noch NICHT geprüft.

## 1–3 Arbeitsweise, Bestandsaufnahme, keine Vorlagen

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Zusammenhängendes Add-in statt Test-Add-ins | AUTO | ein Add-in, 8 Befehle; Start/Stop mit Attrappe getestet; Start **LIVE** |
| Repository/Prototyp/CAD-Logik/Zuschnitt analysiert | AUTO | Abschlussbericht 0.2.0 Kap. 1 |
| Fusion-API anhand Dokumentation geprüft | TEIL | help.autodesk.com in der Sandbox gesperrt; nur Suchergebnisse (EdgeFlangeInput = «Preview»). Eigenschaftsnamen von Flansch/Saum unbekannt |
| Produktive Vorlagenbibliothek beim ersten Start leer | AUTO | test_templates (System- und Benutzerbibliothek leer, keine Profile im Code) |
| Keine Standardmasse / Testdaten nur in Fixtures | AUTO | Prototyp-Bausteine nur `tests/fixtures/…TESTDATEN.json` |

## 4 Eigene parametrische 3D-Vorlagen

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Detail in Fusion modellieren, Anschlusskante + lokales KS festlegen, Variablen markieren, speichern (geführtes Authoring) | TEIL | Befehl «3D-Detail erfassen»; Rahmen-/Prüflogik AUTO; Ausführung in Fusion nicht live |
| Vorlage auf kompatible Kante anwenden, ausrichten, Variablen setzen | TEIL | Selbsttest **LIVE**: Export/Import/Ausrichtung/Parameter; Befehl «3D-Detail anwenden» selbst nicht live |
| Vorschau und Eignungsprüfung vor dem Anwenden | TEIL | Passungsprüfung AUTO (test_validation); Vorschau in Fusion nicht live |
| Bearbeitbare Fusion-Features / gültige Blechgeometrie im Zielbauteil | TEIL | «3D-Detail anwenden» integriert standardmässig: Basis-Feature + «Kombinieren» im Zeitverlauf, keine Komponente; Detailmasse eingefroren (keine Parametrik/Feature-Neuerzeugung). Logik-Test AUTO; **Fusion-Verhalten nicht live geprüft** (Weltlage der Kopie, Join auf Blechkörper, Abwicklung danach) |
| Kopieren, umbenennen, exportieren ohne Original zu ändern | AUTO | test_templates, test_cloud (Geometrie wird mitkopiert) |
| Unterscheidung fest/variabel/Referenzen/Version | AUTO | Datenmodell detailvorlage, test_validation |
| Keine Behauptung automatischer Parametrisierung | AUTO | Hilfetexte/Handbuch sagen das ausdrücklich |

## 5 Hauptmodule / Bedienung

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Live-Test in Fusion (Test-Blech, Flansch, Umschlag, Gehrung, Versatz, Abwicklung, DXF; Bericht 97.002) | NEIN | Befehl Verwaltung → Live-Test, nicht live geprüft; Test-Blech über createBaseFlangeInput (Annahme) |
| Bedienung 0.4.35 (Ampel, Kurzinfo, Zeitleisten-Gruppe, Material pro Auftrag, Beheben-Knopf, Fehlerhilfe, Tagessicherung, Dunkelmodus) | NEIN | Logik AUTO getestet; Fusion-Teile (Timeline-Gruppe, Textfelder, Beheben-Knopf) nicht live |
| Blech aus App-Massaufnahme (Grundblech + Kantenfolge) | NEIN | Logik AUTO; Grundblech über createBaseFlangeInput (Annahme), Kantenfolge wie «Kanten bearbeiten» |
| Auftragsübersicht (Palette) | TEIL | Logik + Browsertest AUTO; Ordner-Lesen/Abfragen der App nicht live |
| Bauteilvorlagen mit Grundrissverlauf/Ring (Editor in der Palette, Befehl «Bauteil erstellen») | NEIN | Geometrie, Parameter, Speicher, Sync, Editor AUTO getestet; Fusion: Grundblech aus Grundriss (createBaseFlangeInput), Kantenzuordnung, gemeinsamer Bau mit Gehrung nicht live – der Live-Test prüft L-Form und Ring |
| Profil von Hand skizzieren (Palette, Zeichenfeld mit Einrasten, Tabelle, Übernahme als Kantenvorlage) | TEIL | Logik + Browsertest (Maus) AUTO; Stift/Finger in der Fusion-Palette nicht live |
| Profil aus der App an das CAD senden (App v3.425, Tabelle cad_profil_auftraege; Add-in: Liste in «Blech aus Massaufnahme», «gebaut») | NEIN | Add-in-Seite getestet gegen Test-Datenbank; App-Prüfstand AUTO; nicht live |
| Projektkarte im CAD (Palette «Projekt», nur lesen), Fotos/Skizzen ansehen und als Referenzbild einfügen, «Neu»-Meldung, Werkstattstand der CAD-Teile | TEIL | Auswertung, Abfragen (Test-Datenbank), Palette (Browsertest), Start-Übersicht AUTO; Canvas-Einfügen (Live-Test-Schritt) und echte App-Daten nicht live |
| Ablagen: Modelle ohne Kundenauftrag in frei gewähltem Fusion-Ordner, Befehle ohne Auftrag, eigener Exportordner | TEIL | Logik, Start, Kontext, Exportordner AUTO (Attrappe); Ordner anlegen/Dokument speichern in Fusion nicht live |
| Änderungen an der App aus dem CAD: Projektstatus (nur wenn unverändert), Hinweis (ersetzen/ergänzen), Termine anlegen/ändern, Fertigungsstatus – alle mit Rückfrage | TEIL | Logik, Prüfung nach App-Regeln, Cloud-Aufrufe (Test-Datenbank, Rechte, veraltete Karte) und Palette AUTO; gegen die echte App nicht live |
| Eigene Gruppe in Fusion | LIVE | Befehle in Fusion erreichbar (Hilfe → Fähigkeiten/Selbsttest benutzt); Anordnung der 3 Gruppen nicht ausdrücklich bestätigt |
| A Kanten bearbeiten: Einzel-/Mehrfachauswahl, Vorlage, Parameter, Vorschau, ungeeignete Kanten, Ergebnisprüfung | TEIL | Bauplan/Eignung AUTO (test_operation_plan), Ablauf/Rückbau als Logik-Test; in Fusion nicht live |
| B 3D-Details anwenden | TEIL | siehe Kap. 4 |
| C Vorlagen verwalten (neu, bearbeiten, duplizieren, umbenennen, löschen, Kategorien, Favoriten, Import/Export, Versionen) | AUTO | test_templates, test_palette inkl. **Browsertest der echten Palette**; Palette in Fusion nicht live bestätigt |
| Aufträge als Ordner (Neuer Auftrag, Ableitung Nummer/Objekt) | AUTO/NEIN-LIVE | Logik und Nachbau getestet; Fusion-Daten-API nicht live |
| D Rundblech/Umformwerkzeuge | TEIL | Beurteilung AUTO; Drehkörper **LIVE** (Selbsttest); Falze an gekrümmten Rändern NEIN (Kap. 8) |
| E Abwicklung, DXF, Zeichnungen, Material, Zuschnitt | TEIL | siehe Kap. 10–12 |
| F Einstellungen, Backup/Restore, Hilfe | AUTO | test_migrations, test_validation, test_palette; Hilfe-Dialog in Fusion **LIVE** |
| Standard-/Expertenmodus mit derselben Engine | AUTO | template_engine; Browsertest Expertenmodus |

## 6 Geometrieadapter und Kanten-Engine

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Alle Fusion-Aufrufe in einem Adapter | AUTO | `geometry/fusion_adapter.py` (+ `edge_resolver.py`); UI ohne Geometrielogik |
| Kante analysieren / Eignung | TEIL | Logik-Test (Stirnfläche ≈ Dicke → Aussenkante); in Fusion nicht live |
| Kantenreferenz zuverlässig auflösen (entityToken, kein Raten) | TEIL | Logik-Test (0 oder 2 Treffer → Abbruch); Fusion-Verhalten nicht live |
| Flansch erzeugen | TEIL | Nach Autodesk-Doku (EdgeFlangeInput: angle, isFlipped, bendRadiusOverride.setOverride; API ab Oktober 2026 – in Fusion 2705.1.30 **nicht vorhanden**). Logik-Test AUTO; Höhenbezug Standard «Aussenflächen» – nicht live geprüft |
| Umschlag erzeugen | TEIL | Nach Autodesk-Doku: createHemFeatureInput() ohne Argumente, setFlatHem (ohne Radius) bzw. setOpenHem (Spalt = 2 × Radius, Annahme). Live-Test 30.10.: die alte Aufrufform (Eigenschaften setzen) scheiterte an Fusion 2705.1.30; neue Form nicht live geprüft |
| Neue Kante nach jedem Schritt bestimmen (nicht nur «am weitesten entfernt») | TEIL | Logik-Test: Parallelität, volle Länge, Abstandsfenster, Mehrdeutigkeit → Abbruch. Welche der beiden Endkanten (oben/unten) für Folgeschritte richtig ist, ist NICHT bewiesen |
| Ausschnitte/Freistellungen erzeugen | NEIN | Ecken/Freistellungen macht Fusion nach Blechregel |
| Abwicklung erstellen/aktualisieren | TEIL | Logik-Test Masse; `createFlatPattern` nicht live |
| Geometrie validieren | TEIL | Körper nach dem Bauen neu aufgelöst (Fix 0.4.2), `isValid`/`isSolid`; nicht live |
| Abbrechen/Rückgängig (Validieren → Plan → Vorschau → Bestätigung → Operation → Prüfung → Rückbau) | TEIL | Logik-Test Rückbau inkl. Meldung bei unvollständigem Rückbau (Fix 0.4.2); ein Rückgängig-Schritt je Befehl ist Fusion-Verhalten, nicht live |

## 7 Standard-/Expertenmodus, Vorlageneditor

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Standardmodus: Vorlage, Felder mit Einheiten, Warnungen | TEIL | Palette AUTO; Dialog «Kanten bearbeiten» in Fusion nicht live |
| Expertenmodus: Operationen hinzufügen/ändern/löschen/umordnen, Radien, Kurzschrift | AUTO | Browsertest; test_templates |
| Abhängigkeiten/Freistellungen/Parameterbeziehungen | TEIL | Ausdrücke mit Parametern und t/ri/k AUTO; Freistellungen NEIN |
| Versionierte strukturierte Vorlagen, Benutzer- und Projektbibliothek, Systemvorlagen leer | AUTO | test_templates |

## 8 Rundbleche, gekrümmte Ränder, Werkstattumformung

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| **Durchgehende Flansche/Umschläge an runden Blechkanten (Kreis, Bogen) ohne Einschnitte/Lappen** | **TEIL** | **Flansch an runden Kanten:** Fusions EdgeFlange-API nennt in der Doku nur lineare Aussenkanten; es wird trotzdem versucht und Fusions Antwort gemeldet (Live-Test steht aus). **Umschlag (Saum) an Kreis/Bogen:** in der API nicht auf gerade Kanten beschränkt, Folge-Kante koaxial, Hinweis bei Schlitzen – Logik-Test AUTO, **nicht live geprüft**. Ellipse/Spline abgelehnt. |
| (Alt) Einzel-/Doppelfalze an runden Kanten als Drehkörper | **NEIN** | Fusion-Flansch nur an geraden Kanten. Ersatz: Scheibe mit aufgebogenem Rand und Kegel als **Drehkörper (kein Fusion-Blechkörper)**; kein Umschlag/Falz an gekrümmten Rändern, kein Anwenden auf bestehende gekrümmte Blechkanten |
| Fälle Scheibe / Kragen / Kegel unterscheiden | AUTO | test_forming |
| Fertigungsabsicht Stauchen/Strecken/manuell/Empfehlung | AUTO | test_forming |
| konstruierbar / abwickelbar / herstellbar getrennt | AUTO | herstellbar nur mit eigenem Grenzwert |
| Keine Einschnitte ohne Freigabe; warnen statt heimlich ändern | AUTO | es werden nie Einschnitte erzeugt |
| Umformzonen markieren | TEIL | als Radiusbereich im Text; nicht im Modell markiert |
| Zuschnitt DXF + flacher Körper (Rundblech) | AUTO | nur Logik/DXF getestet; Fusion-Körper nicht live |
| Drehkörper in Fusion | LIVE | Selbsttest Ø 200.70 mm; Befehl «Rundblech» selbst nicht live |

## 9 Doppelfalzabschluss als Benutzervorlage

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Kein mitgelieferter Doppelfalzabschluss | AUTO | |
| Eigenes 3D-Modell als Vorlage, Falzende erkennen, ausrichten, Variablen, Vorschau | TEIL | über 3D-Detail-Workflow (Kap. 4); Falzende-Erkennung = gerade Zielkante wählen; nicht live |
| Kollisionen prüfen | TEIL | nur Begrenzungsrahmen-Überschneidung, kein Volumentest |
| Ergebnis und Abwicklung prüfen | NEIN | Detail wird nicht mit Blech vereinigt, daher keine Abwicklung des Gesamtteils |

## 10 Abwicklung, DXF, Fertigungszeichnungen

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Fusion-Blechabwicklung bevorzugen, Status prüfen | TEIL | `createFlatPattern`/`flatPattern` nicht live; Masse-Logik AUTO (Fix 0.4.2: Lage unabhängig) |
| Abwickelbarkeit vs. werkstattgerechte Umformbarkeit | AUTO | Rundblech-Beurteilung |
| DXF der Abwicklung (Fusion-Exporter), Erfolg nur wenn Datei existiert | TEIL | Logik-Test «Fusion meldet Erfolg ohne Datei → Fehler»; Export selbst nicht live |
| Biegelinien auf separaten konfigurierbaren Layern | TEIL | Fusion-DXF: Layer bestimmt Fusion (nicht konfigurierbar); eigener Zuschnittplan-DXF: Layer konfigurierbar, mit ezdxf geprüft |
| Einheiten/Skalierung, Dateinamen, Einzel-/Sammelexport | TEIL | Zuschnittplan-DXF 1:1 mm mit ezdxf geprüft; Fusion-DXF nicht live |
| Konturen auf ungültige/doppelte Segmente prüfen | TEIL | Prüffunktion vorhanden und getestet, wird aber NICHT auf die Fusion-DXF angewendet |
| Zeichnungen automatisch aus Bauteilen | NEIN | Fusion-Zeichnungs-API nicht genutzt; stattdessen Werkstattblatt (HTML) |
| Werkstattblatt: Masse, Material, Dicke, Kennung, Biegehinweise | AUTO | test_forming/test_parts_list (Rechnung + HTML); aus echten Bauteilen nicht live |

## 11 Zuschnittoptimierung (Port der App, js/29)

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Bestehende Logik analysiert und portiert | AUTO | 13 Referenzfälle gegen das echte App-JavaScript identisch |
| Mehrere Teile gemeinsam, Formate, Material/Dicke, Teilekennzeichnung | AUTO | test_nesting, test_parts_list |
| Rotation nur wenn erlaubt | AUTO | Einstellung |
| Verschnitt/Materialverbrauch | AUTO | |
| Plan visualisieren/exportieren (SVG, CSV, DXF) | AUTO | DXF mit ezdxf geprüft |
| Überlappungen prüfen, Rand-/Mindestabstände | AUTO | |
| **Rollenmischung (ebaRollenMischung)** | **NEIN** | |
| **Mischen verschiedener Breiten im selben Abschnitt (ebaMischeAbschnitte, «Trittbrett»)** | **NEIN** | |
| **Zu lange Stücke mit Nahtüberlappung teilen (ebaBlecheGeteilt)** | **NEIN** | zu lange Stücke werden nur gemeldet |
| **Reststücke / Restelager (js/42, Vorabzug aus Resten)** | **NEIN** | |
| **Materialbilanz (Schnittfuge, verwertbare/zu kleine Reste, js/33)** | **NEIN** | |
| **Normlängen-Plan für Stangenware (raNormPlan, js/28)** | **NEIN** | |
| **Spaltband-/Coil-Vorrang beim Materialbedarf (kern/zuschnitt.js)** | **NEIN** | gewählt wird das Format mit der kleinsten Blechfläche |
| Echte Abwicklungskonturen statt Rechtecke | NEIN | Rechtecke (umschliessendes Rechteck) |

## 12 Material- und Zuschnittberechnung

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Benutzerdefinierte Materialprofile, keine erfundenen Werte | AUTO | Bibliothek leer; K-Faktor aus Probebiegung (Port kern/materialien.js) |
| Fläche, Teile, Verbrauch, Gewicht (Schätzung), Ausnutzung, Sammelübersicht | AUTO | test_nesting, test_parts_list |
| Aus echten Fusion-Abwicklungen | TEIL | nicht live |

## 13–15 Hilfe, PDF-Anleitung, Logo

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Kontexthilfe, Tooltips, deutsche Texte | AUTO | Hilfethemen im Browsertest; Hilfe-Dialog **LIVE** |
| PDF-Anleitung (16 Kapitel), erzeugt und lesbar | AUTO | per pdftotext/Seitenbild geprüft; HTML-Fassung für Updates |
| Logo unter assets/logo, Icons daraus | AUTO | Dateien erzeugt; ob die Symbole in Fusion richtig erscheinen, wurde nicht ausdrücklich bestätigt |

## 16 Updatesicherheit und Benutzerdaten

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Benutzerdaten ausserhalb des Programmordners | AUTO / LIVE | Ordner `%APPDATA%\SpenglerDigitalCAD` beim Anwender vorhanden |
| Updates überschreiben keine Benutzerdaten | AUTO | Updater schreibt nur in erlaubte Programmpfade (Pfadprüfung getestet) |
| Backup vor Migration, schemaVersion, Migration validiert, bei Fehler unverändert | AUTO | test_migrations (inkl. Gegenprobe «Datei unverändert») |
| Manuelles Backup/Restore | AUTO | test_migrations; Fix 0.4.2: Restore setzt Abgleichstand zurück (Gegenprobe: Test scheitert am alten Code) |
| Import/Export dokumentiertes Format | AUTO | Handbuch Kap. 14 |
| Neuere Versionen nicht verändern | AUTO | Vorlagen, Materialien, Einstellungen, Abgleich (Schutz 0.4.2) |
| Löschen nur mit Bestätigung | AUTO | Papierkorb |
| Vorlage ↔ erzeugtes Bauteil getrennt versioniert | TEIL | Attribut mit Vorlagen-ID/-Version am Feature; nicht live |
| Automatische Updates per Klick | TEIL | Updater AUTO (nur geänderte Dateien, sha256, Sicherung, Rückbau, Manipulation erkannt); Test-Update 0.4.1 liegt bereit; in Fusion nicht live |

## 17–21 Struktur, Datenmodelle, Tests, Logging, Geometriekontrolle

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Ordnerstruktur (angepasst: Paket `spengler_cad/`) | AUTO | Begründung im Abschlussbericht |
| Datenmodelle A–F mit schemaVersion | AUTO | `core/models.py` |
| Einheiten eindeutig, mm ↔ cm | AUTO / LIVE | test_geometrie; Selbsttest 25 mm = 2.5 cm **LIVE** |
| Tests ohne Fusion | AUTO | 121 Tests, siehe Abschlussbericht |
| Fusion-Integrationstests | TEIL | Selbsttest im Add-in (**LIVE**) + Testanleitung; Kantenbefehle offen |
| Diagnoseprotokoll (Version, Fusion-Version, Befehl, Vorlage, Fehler) | AUTO / LIVE | Protokolldatei beim Anwender vorhanden |
| Vorschau/Bestätigung, nicht raten, keine Einschnitte, keine automatischen Löschungen | TEIL | Logik AUTO; Vorschau in Fusion nicht live |

## Zusatz (vom Anwender beauftragt)

| Anforderung | Status | Nachweis / Bemerkung |
|---|---|---|
| Vorschaubild je Vorlage, Werkstattblatt mit Bemassung, Stückliste, Etiketten, Teilenummern | AUTO (Teilenummern TEIL) | test_parts_list, Browsertest; Teilenummern-Attribute nicht live |
| Anbindung Spengler-Digital-App: Konto, Abgleich, Rechte, Konflikte, offline | TEIL | gegen Supabase-Nachbau AUTO (18 Tests), Datenbankregeln **gegen die echte Datenbank** 13/13 geprüft; Anmeldung/Abgleich aus Fusion nicht live |
| Datenbankmigration eingespielt | AUTO | Probelauf + Nachprüfung in der echten Datenbank |


## Zum Besprechen: richtige Verbindung zur Spengler-Digital-App (Stand 31.10.2026, noch nichts umgesetzt)
Gewünscht vom Anwender («erstmal merken, später besprechen»). Die App hat bereits Tabellen, die das Add-in heute nur teilweise nutzt:
- **Reststücke** (`reststuecke`): Die Reste im Add-in sind lokal, mit denselben Feldnamen – Ziel: Reste der App im Add-in sehen und verbrauchen, im Add-in erfasste Reste dort speichern, Reservierungen (`material_reservierungen`) beachten.
- **Aufträge** (`projects`, Auftragsnummer `order_no`): heute nur gelesen (Info in «Auftrag wählen»). Offen: Auftrag aus dem Add-in in der App anlegen/Status in der App setzen, Ordnerstruktur ↔ Projekt abgleichen. Der Fertigungsstatus des Add-ins liegt getrennt in `cad_auftragsstatus`.
- **Stundensätze** (`rates`): werden gelesen (nur mit Berechtigung «rates»); offen, ob auch Material-/Lagerpreise (`materials`, `lagerbestand`) für die Kalkulation übernommen werden.
- **Änderungsverlauf** (`audit_log`): das Add-in führt ein eigenes Protokoll (`cad_aenderungen`); offen, ob es in den App-Verlauf soll.
- Berechtigungen: Die App steuert Zugriffe über `has_permission(...)`; das Add-in muss das bei neuen Zugriffen beachten.


### Stand der App-Verbindung (1. 11. 2026)
- CAD → App: Tabelle `cad_teile` (neu), Teile mit Zuschnitt und `app_data` (Freies Profil); App-Seite `js/104-cad-teile.js` auf Branch `claude/cad-teile-aus-dem-cad` (Anzeige im Cockpit, Übernahme über `measurementAlsVorlage()`, Verknüpfung `measurement_id`). Noch nicht auf `main`, Version nicht erhöht.
- App → CAD: Massaufnahmen «Freies Profil»/«Dachrandblech» lesen und als Kantenvorlage übernehmen (nur Schenkel und Winkel).
- Noch offen: Material der App automatisch zuordnen (heute von Hand), Reste (`reststuecke`), Rückmeldung des App-Status (gerüstet/erledigt) ins CAD, andere Massaufnahme-Arten.
- Aufträge abgleichen (1. 11. 2026): Projekte der App ↔ Auftragsordner in Fusion über die Auftragsnummer, beide Richtungen mit Auswahl; Add-in schreibt in `projects` (nur INSERT wie die App; Verlauf über deren Trigger). Offen: Status/Kunde/Titel abgleichen, Änderungen am Objekt synchron halten, automatisches Abgleichen beim Start.

### Stabilisierung 0.4.48 (4. 11. 2026) – Status je Funktion
Legende: A = in Fusion live bestätigt, B = nur mit Fusion-Stub/Fake-Cloud getestet (Logik geprüft, Fusion-Aufruf nicht), C = nicht getestet, D = bekannt problematisch.
- Basisflansch aus Rechteck/L-Grundriss, gemeinsamer Flansch an 2 Kanten, Bildschirmfoto, Rundblech, 3D-Detail: **A** (Live-Test 97.002, 0.4.42).
- Flansch auf Test-Blech ±90°/45°/135°, Radius, Winkelfalz, Umschlag, Gehrung (Flansch/Winkelfalz/Umschlag), Abwicklung, DXF, Referenzbild, Ordnerliste, Bauteil L/Ring: **B** – der Live-Test ab 0.4.48 misst die Geometrie (Richtung, Höhe, Volumen) und bewertet sie; erster Lauf mit Messung steht aus.
- Versatz ±: **D** – Fusion lehnte die versetzte Kante ab («edge is not suitable for a sheet metal flange»); Ersatzkante seit 0.4.44, nie live gesehen. Der Live-Test misst ihn als Unterschied zum Bau ohne Versatz.
- Projektkarte lesen/schreiben (Status, Hinweis, Termine), Aufträge, Profil aus der App: **B** (Fake-Supabase); Schreiben nur mit Rückfrage, Termin-Änderung nur mit den gelesenen Werten (bedingter PATCH, bei Konflikt wird nichts überschrieben).
- Änderungen: A Zeitzone der Projektkarte (`_zeit()`, Neu-Vergleich); B Termin-Konfliktschutz; C Rückbau des Bauteils bei Abbruch (`abbruch_mit_rueckbau`); D DXF-Prüfung (`dxf_pruefung`, Export meldet fehlerhafte DXF nicht als Erfolg); F Live-Test-Bericht nur seit Teststart, Benutzerpfade/E-Mail maskiert; G messender Live-Test (`core/livetest_messung.py`).
- Offen: Umschlag-Varianten geometrisch bewerten, Mehrfachkanten-Fallback, innerHTML-Prüfung der Palette (19 Stellen ohne `esc(` in derselben Zeile), Fehlermeldungen bei Offline/fehlenden Tabellen.

### Geometrie-Stabilisierung 0.4.49 (4. 11. 2026) – Stand je Funktion
Kennzeichnung: **LIVE** = in Fusion bestätigt · **TEIL** = Logik mit Attrappen geprüft, Fusion-Lauf steht aus · **UNGETESTET**. Seit 0.4.42 lief kein Live-Test; alles unten ist **TEIL**, bis der Live-Test 0.4.49 vorliegt.
- **Grundblech** (`blech_aus_profil`): Regel mit Soll-Dicke (Design-Kopie per `addByCopy`, Bibliothek unverändert), `activeSheetMetalRule` vor `createBaseFlangeInput(profil)` (ohne Distanz), Zielkomponente aktiviert und zurückgestellt, Körper in Zielkomponente / gemessene Dicke / Blechkörper geprüft, Rückbau. **TEIL** (Basisflansch an sich LIVE seit 0.4.42, damals ohne Dickenregel).
- **Flansch / Gehrung**: Kreis/Bogen vor dem Modellieren abgelehnt, Gruppe geprüft (ein Körper, gerade, Kette), nach dem Bau kontrolliert (isMiteredCorners, Körper, Volumen); kein stiller Einzelkanten-Rückfall, nur nach Rückfrage. **TEIL**. Grenze: feine Spalte an der Ecke erkennt die Volumenprüfung nicht.
- **Umschlag**: genau eine Kante je Saum-Feature, 179°-Ersatz entfernt, jede Variante geometrisch kontrolliert (zweite Lage per Volumen, kein Zusatzkörper), Gruppe je Kante mit Rückbau. **TEIL**.
- **Versatz**: zentraler Rückbau (`Rueckbau`, `entfernen_bericht` prüft `deleteMe()`), Versatz entfernt eigene Skizze/Extrusion bei Fehler. **TEIL**; Versatz selbst weiter **offen** (Fusion lehnte die versetzte Kante live ab).
- **Abwicklung / DXF**: Voraussetzungen geprüft, feste Flächenwahl, Export mit Ordnerprüfung, alte Datei gilt nie als Export, DXF-Gegenprobe inkl. Konturzahl. **TEIL**.
- **Tests**: `run_all.py` = Unit-/Stub-Tests (so gekennzeichnet, auch im Release-Protokoll); Live-Test um Dicke 0.7/1.0, Zielkomponente, ungültige Eingaben, provozierten Rückbau, Abwicklung mit zwei Biegungen erweitert.
- **Verhaltensänderungen (mit dem Anwender abgestimmt 4.11.)**: Bau ohne Gehrung nur nach Ja; Umschlag-Ersatz über Flansch entfernt; runde Kanten für Flansch/Umschlag abgelehnt (Vorlagen «gekrümmt» damit derzeit nicht anwendbar – offen).

#### Fusion-API: kritische Aufrufe (Stand Autodesk-Doku laut Websuche 4.11.2026; Doku-Seiten aus der Sandbox nicht abrufbar, deshalb nicht im Wortlaut geprüft)
| API | wofür | Preview | seit | Verhalten bei Fehlen |
|---|---|---|---|---|
| `FlangeFeatures.createBaseFlangeInput(profile)` / `BaseFlangeInput` | Grundblech | **ja** | Preview-Stand 2025/26 | Abbruch mit Meldung, nichts gebaut |
| `FlangeFeatures.createEdgeFlangeInput(edges, distance)` / `EdgeFlangeInput` | Flansch, Gehrung | **ja** | API Okt. 2026 (laut Code-Kommentar) | Abbruch mit Meldung |
| `HemFeatures.createHemFeatureInput()`, `setFlatHem/setOpenHem(edge, …)` | Umschlag (eine Kante) | **ja** (Blech-API) | Sept. 2025 (laut Code-Kommentar) | Abbruch mit Meldung |
| `Component.activeSheetMetalRule` | Regel setzen | nein | Nov. 2022 | – |
| `SheetMetalRules.addByCopy(rule, name)`, `SheetMetalRule.thickness.expression` | Regel mit Soll-Dicke | nein (nicht als Preview bekannt) | Nov. 2022 | Abbruch, kein Grundblech mit falscher Dicke |
| `Occurrence.activate`, `Design.activateRootComponent`, `Design.activeOccurrence` | Zielkomponente aktivieren | nein | alt | Abbruch, wenn Aktivierung `False` meldet |
| `Component.createFlatPattern(face)`, `ExportManager.createDXFFlatPatternExportOptions` | Abwicklung/DXF | nein (nicht als Preview bekannt) | alt | Abbruch mit Meldung |
Alle Preview-Aufrufe liegen nur in `geometry/fusion_adapter.py` und werden vor dem Aufruf mit `hasattr` geprüft; «Fähigkeiten prüfen» und der Live-Test listen sie (`fusion_capabilities.py`). Ein unkontrollierter geometrischer Ersatz (z. B. 179°-Flansch statt Saum) wird nicht mehr verwendet.

## Nachtauftrag Geometrie und gekrümmte Flächen (5. 11. 2026) – Verlauf, ersetzt durch den Abschnitt «Korrekturauftrag» unten
Branch `ccr-26e82854-8ygnzg`, Ausgangsbasis 0.4.49 (HEAD `bb4254c`). **Kein Release, Version unverändert 0.4.49.** Seit 0.4.42 lief kein Fusion-Live-Test.

**Statuswerte (je Funktion):** implementiert, nicht live getestet · live getestet auf ebener Geometrie · live getestet auf gekrümmter Geometrie · eingeschränkt unterstützt · nicht unterstützt.

| Funktion | Status |
|---|---|
| Grundblech (Regel mit Soll-Dicke, Zielkomponente, Rückbau; Bögen im Profil) | Basisflansch an sich live getestet auf ebener Geometrie (0.4.42); Dicke/Komponente/Bögen: implementiert, nicht live getestet |
| Flansch, ebene gerade Kante | Flansch an sich live getestet auf ebener Geometrie (0.4.42, Protokoll); Kontrollen: implementiert, nicht live getestet |
| Mehrkantflansch mit Gehrung | eingeschränkt unterstützt (Kette gerader Kanten); Eckspalt-Messung implementiert, nicht live getestet |
| Umschlag (eine Kante je Saum, Mindestlänge, Kontrolle) | implementiert, nicht live getestet |
| Doppelfalz (Aufkantung + 2 Umschläge) | eingeschränkt unterstützt, nur als Live-Test-Fall; nicht live getestet |
| Versatz (Biegelinie, nur ebene Blechfläche) | implementiert, nicht live getestet; Fusion lehnte die versetzte Kante früher live ab (offen) |
| Abwicklung/DXF eben | implementiert, nicht live getestet (DXF-Gegenprobe inkl. Konturzahl) |
| Abwicklung gerolltes Blech (Biegezone Zylinder) | eingeschränkt unterstützt; nicht live getestet |
| Abwicklung doppelt gekrümmt | nicht unterstützt (wird erkannt und abgelehnt, keine Näherung) |
| 3D-Detail eben (atomarer Import, Interferenz, Abstand) | Import/Ausrichtung live getestet auf ebener Geometrie (Selbsttest 0.4.42); Rückbau/Interferenz/Abstand: implementiert, nicht live getestet |
| 3D-Detail auf Zylinder/Kegel (starr tangential, Abstand) | eingeschränkt unterstützt; nicht live getestet |
| 3D-Detail an Krümmung anpassen | nicht unterstützt (kein ungefragtes Verformen) |
| Flansch/Umschlag an gekrümmter Kante, auf Zylinder/Kegel | nicht unterstützt; Live-Test fragt Fusion ausdrücklich an |

**Unterstützungsmatrix (aus `core/unterstuetzung.py` erzeugt – implementiert ≠ live getestet; «Prototyp» ist im normalen Bau gesperrt):**

<!-- AUTO:matrix -->
| Bearbeitung | Fläche | gerade Kante | Kreisbogen | Kreis | Ellipse | Spline/freie Kurve | Kette aus Linien und Bögen |
|---|---|---|---|---|---|---|---|
| Grundblech | eben | implementiert | implementiert | implementiert | implementiert | implementiert | implementiert |
| Grundblech | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | eben | eingeschränkt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | eben | eingeschränkt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Zylinder | Prototyp (gesperrt) | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Abwicklung / DXF | eben | implementiert | implementiert | implementiert | implementiert | implementiert | implementiert |
| Abwicklung / DXF | Zylinder | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | Kegel | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | einfach gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Abwicklung / DXF | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail starr | eben | implementiert | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Zylinder | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Kegel | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | einfach gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | doppelt gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Freiform | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail an Fläche angepasst | eben | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Zylinder | Prototyp (gesperrt) | Prototyp (gesperrt) | Prototyp (gesperrt) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |

Grenzen und Gründe (gekrümmte Fälle):
- **Grundblech / Zylinder** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / Kegel** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / einfach gekrümmt** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / doppelt gekrümmt** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / Freiform** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Flansch / Zylinder** (nicht unterstützt): Fusion lehnt den Flansch an der Mantelkante eines gerollten Blechs ab (Live 0.4.60) – Bauweise «eigene Geometrie» verwenden
- **Flansch / Zylinder** (nicht unterstützt): Flansch entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Flansch / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Flansch / einfach gekrümmt** (nicht unterstützt): Flansch auf einfach gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Flansch / doppelt gekrümmt** (nicht unterstützt): Flansch auf doppelt gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Flansch / Freiform** (nicht unterstützt): Flansch auf Freiform: keine eindeutige, mathematisch abwickelbare Geometrie
- **Mehrkantflansch mit Gehrung / Zylinder** (nicht unterstützt): Fusion lehnt schon die Einzelkante an der Mantellinie ab (Live 0.4.60)
- **Mehrkantflansch mit Gehrung / Zylinder** (nicht unterstützt): Mehrkantflansch mit Gehrung entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Mehrkantflansch mit Gehrung / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Mehrkantflansch mit Gehrung / einfach gekrümmt** (nicht unterstützt): Mehrkantflansch mit Gehrung auf einfach gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Mehrkantflansch mit Gehrung / doppelt gekrümmt** (nicht unterstützt): Mehrkantflansch mit Gehrung auf doppelt gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Mehrkantflansch mit Gehrung / Freiform** (nicht unterstützt): Mehrkantflansch mit Gehrung auf Freiform: keine eindeutige, mathematisch abwickelbare Geometrie
- **Umschlag / Zylinder** (nicht unterstützt): Fusion lehnt den Umschlag an der Mantelkante eines gerollten Blechs ab (Live 0.4.60) – Bauweise «eigene Geometrie» verwenden
- **Umschlag / Zylinder** (nicht unterstützt): Umschlag entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Umschlag / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Umschlag / einfach gekrümmt** (nicht unterstützt): Umschlag auf einfach gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Umschlag / doppelt gekrümmt** (nicht unterstützt): Umschlag auf doppelt gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Umschlag / Freiform** (nicht unterstützt): Umschlag auf Freiform: keine eindeutige, mathematisch abwickelbare Geometrie
- **Doppelfalz / Zylinder** (nicht unterstützt): Fusion lehnt schon die Einzelkante an der Mantellinie ab (Live 0.4.60)
- **Doppelfalz / Zylinder** (nicht unterstützt): Doppelfalz entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Doppelfalz / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Doppelfalz / einfach gekrümmt** (nicht unterstützt): Doppelfalz auf einfach gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Doppelfalz / doppelt gekrümmt** (nicht unterstützt): Doppelfalz auf doppelt gekrümmt: keine eindeutige, mathematisch abwickelbare Geometrie
- **Doppelfalz / Freiform** (nicht unterstützt): Doppelfalz auf Freiform: keine eindeutige, mathematisch abwickelbare Geometrie
- **Versatz / Zylinder** (Prototyp (gesperrt)): gerade Kante parallel zur Zylinderachse: Versatz als Bogenlänge entlang des Mantels (Drehschnitt/-anfügung um die Achse, geometrisch eindeutig)
- **Versatz / Zylinder** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / Kegel** (nicht unterstützt): Kegel: tangentialer Versatz einer Mantellinie ist eine Drehung um die Spitze, Normal- und Radialrichtung unterscheiden sich – noch nicht umgesetzt
- **Versatz / einfach gekrümmt** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / doppelt gekrümmt** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / Freiform** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Abwicklung / DXF / Zylinder** (eingeschränkt): mathematisch abwickelbar; nur wenn Fusion den Körper als Blech abwickelt
- **Abwicklung / DXF / Kegel** (eingeschränkt): mathematisch abwickelbar; nur wenn Fusion den Körper als Blech abwickelt
- **Abwicklung / DXF / einfach gekrümmt** (eingeschränkt): mathematisch abwickelbar; Fusion entscheidet, kein eigener Nachweis
- **Abwicklung / DXF / doppelt gekrümmt** (nicht unterstützt): Gausssche Krümmung ≠ 0 – nicht verzerrungsfrei abwickelbar, keine DXF
- **Abwicklung / DXF / Freiform** (nicht unterstützt): Abwickelbarkeit nicht nachgewiesen – keine DXF; Näherung ist ein eigener, noch fehlender Modus
- **3D-Detail starr / Zylinder** (eingeschränkt): starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen
- **3D-Detail starr / Kegel** (eingeschränkt): starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen
- **3D-Detail starr / einfach gekrümmt** (eingeschränkt): starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen
- **3D-Detail starr / doppelt gekrümmt** (eingeschränkt): starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen
- **3D-Detail starr / Freiform** (eingeschränkt): starr tangential am Ankerpunkt (lokale Normale/Tangente), nicht verformt; Abstand/Kontakt wird gemessen
- **3D-Detail an Fläche angepasst / Zylinder** (Prototyp (gesperrt)): nur Vorlagen mit Anschlussradius-Parameter: der Radius wird auf den Zylinderradius gesetzt (keine freie Verformung)
- **3D-Detail an Fläche angepasst / Zylinder** (nicht unterstützt): keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt
- **3D-Detail an Fläche angepasst / Kegel** (nicht unterstützt): keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt
- **3D-Detail an Fläche angepasst / einfach gekrümmt** (nicht unterstützt): keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt
- **3D-Detail an Fläche angepasst / doppelt gekrümmt** (nicht unterstützt): keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt
- **3D-Detail an Fläche angepasst / Freiform** (nicht unterstützt): keine definierte Verformungsrichtung (Kegel/doppelt gekrümmt/Freiform) – Detail wird nicht ungefragt verformt
<!-- /AUTO:matrix -->

**Machbarkeit gekrümmter Fälle (aus `core/unterstuetzung.py` erzeugt):**

<!-- AUTO:machbarkeit -->
| Bearbeitung | Fläche | gerade Kante | Bogen/Kreis | Fusion-nativ | eindeutig | Abwickelbarkeit (math.) | Live-Test |
|---|---|---|---|---|---|---|---|
| Grundblech | Zylinder | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | Kegel | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | einfach gekrümmt | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | Freiform | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | Zylinder | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Zylinder | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | Zylinder | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | Kegel | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | Freiform | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Zylinder | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | Zylinder | Prototyp (gesperrt) | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | mathematisch abwickelbar | nötig |
| Versatz | Kegel | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | nein | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | Freiform | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | nein | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Abwicklung / DXF | Zylinder | eingeschränkt | eingeschränkt | FlatPattern | ja | mathematisch abwickelbar | nötig |
| Abwicklung / DXF | Kegel | eingeschränkt | eingeschränkt | FlatPattern | ja | mathematisch abwickelbar | nötig |
| Abwicklung / DXF | einfach gekrümmt | eingeschränkt | eingeschränkt | FlatPattern | ja | mathematisch abwickelbar | nötig |
| Abwicklung / DXF | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | FlatPattern | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| Abwicklung / DXF | Freiform | nicht unterstützt | nicht unterstützt | FlatPattern | ja | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail starr | Zylinder | eingeschränkt | eingeschränkt | Import + Transform | ja | mathematisch abwickelbar | nötig |
| 3D-Detail starr | Kegel | eingeschränkt | eingeschränkt | Import + Transform | ja | mathematisch abwickelbar | nötig |
| 3D-Detail starr | einfach gekrümmt | eingeschränkt | eingeschränkt | Import + Transform | ja | mathematisch abwickelbar | nötig |
| 3D-Detail starr | doppelt gekrümmt | eingeschränkt | eingeschränkt | Import + Transform | ja | nicht abwickelbar | nötig |
| 3D-Detail starr | Freiform | eingeschränkt | eingeschränkt | Import + Transform | ja | nicht abwickelbar | nötig |
| 3D-Detail an Fläche angepasst | Zylinder | Prototyp (gesperrt) | Prototyp (gesperrt) | Benutzerparameter | ja | mathematisch abwickelbar | nötig |
| 3D-Detail an Fläche angepasst | Kegel | nicht unterstützt | nicht unterstützt | Benutzerparameter | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Benutzerparameter | ja | mathematisch abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Benutzerparameter | nein | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | Freiform | nicht unterstützt | nicht unterstützt | Benutzerparameter | nein | nicht abwickelbar | Live-Anfrage (Ablehnung bestätigen) |
<!-- /AUTO:machbarkeit -->

**Fusion-API-Risiken:** Blech-Features (BaseFlange, EdgeFlange, Hem) sind Preview-API und werden vor dem Aufruf mit `hasattr` geprüft; neu genutzt und
nicht live bestätigt: `SurfaceEvaluator.getCurvature/getFirstDerivative/parametricRange`, `CurveEvaluator.getTangent`, `MeasureManager.measureMinimumDistance`,
`Design.createInterferenceInput/analyzeInterference`, `sketchArcs.addByThreePoints`, `RevolveFeatures` mit Teilwinkel. Fehlt eine dieser Funktionen,
wird verständlich abgebrochen (Interferenz: ausdrücklich gekennzeichnete Grobprüfung).
**BaseFeature-/Kombinieren-Integration** eines 3D-Details friert die Detailgeometrie ein: die parametrische Feature-Historie des Details bleibt NICHT erhalten.

## HISTORISCH – Korrekturauftrag gekrümmte Flächen – Status je Funktion (5. 11. 2026, Stand 0.4.49)
Ausgangs-Commit `dc50a15`. **Kein Release, Version 0.4.49 unverändert, main nicht berührt.** Statuswerte: NICHT IMPLEMENTIERT · IMPLEMENTIERT – NICHT LIVE GETESTET ·
LIVE GETESTET – TECHNISCH BESTANDEN · FACHLICH IM CAD GEPRÜFT · FÜR PRODUKTIVE ANWENDUNG FREIGEGEBEN. Seit 0.4.42 lief **kein** Fusion-Live-Test; kein Punkt
ist «fachlich geprüft» oder «freigegeben». Grundlage der Live-Angaben: Live-Test 97.002 (0.4.42, Fusion 2706.1.17).

| Funktion | eben | Zylinder | Kegel | doppelt gekrümmt / Freiform |
|---|---|---|---|---|
| Grundblech (Soll-Dicke, Zielkomponente, Bögen) | LIVE GETESTET – TECHNISCH BESTANDEN (Basisflansch 0.4.42); Dicke/Komponente/Bögen: IMPLEMENTIERT – NICHT LIVE GETESTET | gerolltes Segment: IMPLEMENTIERT – NICHT LIVE GETESTET (Prototyp) | NICHT IMPLEMENTIERT (per API nicht erzeugbar) | NICHT IMPLEMENTIERT |
| Flansch | LIVE GETESTET – TECHNISCH BESTANDEN (0.4.42); Kontrollen: IMPLEMENTIERT – NICHT LIVE GETESTET | gerade Mantelkante: IMPLEMENTIERT – NICHT LIVE GETESTET (Prototyp, gesperrt); Bogenkante: NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT |
| Mehrkant + Gehrung | IMPLEMENTIERT – NICHT LIVE GETESTET | NICHT IMPLEMENTIERT (erst nach Einzelkanten-Prototyp) | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT |
| Umschlag | IMPLEMENTIERT – NICHT LIVE GETESTET | gerade Mantelkante: IMPLEMENTIERT – NICHT LIVE GETESTET (Prototyp, gesperrt) | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT |
| Doppelfalz | IMPLEMENTIERT – NICHT LIVE GETESTET (Kantenfolge) | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT |
| Versatz | IMPLEMENTIERT – NICHT LIVE GETESTET (früher live abgelehnt, offen) | Bogenlänge an gerader Mantelkante: IMPLEMENTIERT – NICHT LIVE GETESTET (Prototyp, gesperrt) | NICHT IMPLEMENTIERT (Normal ≠ radial, nicht definiert umgesetzt) | NICHT IMPLEMENTIERT |
| Abwicklung / DXF | IMPLEMENTIERT – NICHT LIVE GETESTET (Prüfungen); unsichere Erkennung nur im Prüfmodus «Fusion entscheidet» | IMPLEMENTIERT – NICHT LIVE GETESTET | IMPLEMENTIERT – NICHT LIVE GETESTET (nur wenn Fusion den Körper abwickelt) | abgelehnt (keine exakte DXF) |
| 3D-Detail starr (Modus A) | LIVE GETESTET – TECHNISCH BESTANDEN (Import/Ausrichtung, Selbsttest 0.4.42); Rückbau/Interferenz: IMPLEMENTIERT – NICHT LIVE GETESTET | IMPLEMENTIERT – NICHT LIVE GETESTET | IMPLEMENTIERT – NICHT LIVE GETESTET | IMPLEMENTIERT – NICHT LIVE GETESTET |
| 3D-Detail anpassen (Modus B) | – | IMPLEMENTIERT – NICHT LIVE GETESTET (Prototyp, gesperrt; Anschlussradius-Parameter) | NICHT IMPLEMENTIERT | NICHT IMPLEMENTIERT |

**Grenzen (nachvollziehbar):** Kegel – ein gerolltes Kegelblech lässt sich per API nicht erzeugen (kein Lofted-Flange bekannt), deshalb nichts prüfbar;
die lokale Normale am Kegel ist nicht radial (Halbwinkel) – ein «Versatz» muss vorher fachlich als Normal-, Radial- oder Tangentialversatz festgelegt
werden. Doppelt gekrümmt (Kugel, Torus) – Gausssche Krümmung ≠ 0, keine verzerrungsfreie Abwicklung; Flansch/Umschlag ohne eindeutige Geometrie. Freiform –
Abwickelbarkeit nur über Stichproben, ausgefallene Punkte = unsicher; Bearbeitungen nicht definiert. Prototypen sind im normalen Bau GESPERRT und
werden erst nach bestandenem Live-Test (und fachlicher Prüfung) in `core/unterstuetzung.py` freigegeben.

## HISTORISCH – Spengler-Kantenwerkzeug – Status (5. 11. 2026, Stand 0.4.49 vor Veröffentlichung; überholt)
Ausgangs-HEAD `46ba14e`. Kein Release, Version 0.4.49, main unberührt. EIN Werkzeug: das bestehende «Kanten bearbeiten» (Befehls-ID unverändert, Vorlagen
und Kurzschrift unverändert kompatibel) mit Bauweise *Fusion-Blechfunktion* oder *Eigene Geometrie*. «Abwicklung & DXF» bleibt separat und nutzt für
Profilteile die eigene Abwicklung. **Fusion-Live-Tests: 0 ausgeführt** – alles unten ist höchstens IMPLEMENTIERT – NICHT LIVE GETESTET.

| Funktion | Status |
|---|---|
| Aufkantung / Einfachfalz / Doppelfalz als EIN Profil (eigene Geometrie, ebene gerade Kante) | IMPLEMENTIERT – NICHT LIVE GETESTET |
| Dasselbe an gerader Mantelkante Zylinder/Kegel (Prototyp 2/5) | IMPLEMENTIERT – NICHT LIVE GETESTET, gesperrt (Prototypen-Schalter) |
| Eigene Abwicklung + DXF + Rückvergleich 2D/3D für Profilteile | IMPLEMENTIERT – NICHT LIVE GETESTET |
| Analyse je Kante im Bauplan (Kantenart, Fläche, Klasse a–e, Abwicklungsaussicht) | IMPLEMENTIERT – NICHT LIVE GETESTET |
| Gehrung zwischen eigenen Profilen | NICHT IMPLEMENTIERT (Klasse b, zu prototypisieren) |
| Versatz in der eigenen Profilkette | NICHT IMPLEMENTIERT (nativ vorhanden) |
| Aufkantung an Kreisbogen-/Kreiskante | NICHT IMPLEMENTIERT – mathematisch nicht verzerrungsfrei abwickelbar (Klasse d); Alternativen nur als bewusste Variante |
| Ellipse / Spline / Kette aus Linien und Bögen | NICHT IMPLEMENTIERT (d bzw. c) |

**Mathematische Machbarkeit und Wahl des ersten Prototyps:**

<!-- AUTO:prototyp -->
| Nr. | Kandidat | Flächen | mathematisch abwickelbar | Fertigung | eigener Aufbau | Abwicklung/Validierung |
|---|---|---|---|---|---|---|
| 1 | Kreisbogenkante auf ebener Grundfläche, 90°-Aufkantung | Grundfläche eben (K = 0), Biegezone Torusabschnitt (K ≠ 0), Schenkel Zylinder (K = 0) | **nein** | Bördeln/Aufhalsen mit Streckung bzw. Stauchung des Randes – oder segmentiert mit Einschnitten | möglich (Drehung des Querschnitts um die Kreisachse), aber Ergebnis nicht verzerrungsfrei abwickelbar | keine verzerrungsfreie Abwicklung; Alternative: Zargenstreifen (Zylinder, abwickelbar) + Naht oder Freistellungen – nur als bewusst gewählte Variante |
| 2 | Gerade Mantelkante eines zylindrischen Blechsegments | Grundfläche Zylinder (K = 0), Biegezone Zylinder mit Achse = Kante (K = 0), Schenkel eben (K = 0) | ja | Rundbiegen des Segments, Abkanten an der geraden Kante – Spenglerpraxis (z. B. Rinnen-/Rohrhalbschalen mit Abkantung) | möglich: Querschnitt (Kreisbögen + Linien) senkrecht zur Kante, Extrusion entlang der Kante | theoretischer Zuschnitt: Länge = Σ Schenkel + Σ (ri + k·t)·|α| (Segment selbst: (R + k·t)·φ), Breite = Kantenlänge; Rückvergleich über Volumen und Radien |
| 3 | Gekrümmte (Kreis-)Kante auf zylindrischer Fläche (Stirnkante eines Rohrs) | Grundfläche Zylinder (K = 0), Biegezone Torusabschnitt (K ≠ 0), Schenkel Kreisring/Kegel (K = 0) | **nein** | Bördeln mit Streckung (Kragen) – nicht verzerrungsfrei | möglich (Drehkörper), aber nicht verzerrungsfrei abwickelbar | keine verzerrungsfreie Abwicklung |
| 4 | Kreisförmige Kante eines flachen Rundblechs (Ronde mit Rand) | Ronde eben (K = 0), Biegezone Torus (K ≠ 0), Rand Zylinder (K = 0) | **nein** | Drücken/Bördeln, Rand streckt/staucht | möglich (Drehkörper, vorhanden: «Rundblech»), nicht verzerrungsfrei abwickelbar | keine verzerrungsfreie Abwicklung; Rundblech-Werkzeug weist Umformung aus |
| 5 | Gerade Mantellinie eines konischen Blechs | Grundfläche Kegel (K = 0), Biegezone Zylinder um die Mantellinie (K = 0), Schenkel eben (K = 0) | ja | Kegel rollen, an der Mantellinie abkanten | Profil entlang der Mantellinie möglich (Tangentialebene längs der Mantellinie konstant); das konische Grundblech selbst lässt sich nicht als Querschnitts-Extrusion bauen | mathematisch abwickelbar (Kegelabwicklung Kreisringsektor + Profil-Zugabe); eigene Kegelabwicklung noch nicht umgesetzt |

**Erster Prototyp: Nr. 2 – Gerade Mantelkante eines zylindrischen Blechsegments.** Begründung: alle Flächen K = 0 (mathematisch abwickelbar), Grundsegment und Aufkantung entstehen aus EINEM Querschnitt (Kreisbögen + Linien) senkrecht zur geraden Kante, die eigene Abwicklung ist damit geschlossen rechenbar und über Volumen/Radien gegen das 3D-Modell prüfbar. Nr. 1 (Bogenkante auf ebenem Blech) ist wegen der Torus-Biegezone NICHT verzerrungsfrei abwickelbar und wird nicht als Erfolg umgesetzt; als konstruktive Sondervarianten kommen nur bewusst wählbare Segmentierung/Freistellung oder ein separater Zargenstreifen in Frage.
Beispiel Torus-Biegezone (Kreiskante R 500 mm, ri 1 mm, t 1 mm): max |K| = 2.00e-03 1/mm² ≫ Toleranz 1e-09.
<!-- /AUTO:prototyp -->

**Support-Matrix Kante × Fläche × Bearbeitung (nativ / eigene Geometrie / Klasse):**

<!-- AUTO:kantenwerkzeug -->
| Bearbeitung | Fläche | Kante | nativ (Fusion) | eigene Geometrie | Klasse |
|---|---|---|---|---|---|
| Flansch | eben | gerade Kante | implementiert | eingeschränkt | a |
| Flansch | eben | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Flansch | eben | Kreis | nicht unterstützt | nicht unterstützt | d |
| Flansch | eben | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | eben | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | eben | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Flansch | Zylinder | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Flansch | Zylinder | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Flansch | Zylinder | Kreis | nicht unterstützt | nicht unterstützt | d |
| Flansch | Zylinder | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | Zylinder | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | Zylinder | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Flansch | Kegel | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Flansch | Kegel | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Flansch | Kegel | Kreis | nicht unterstützt | nicht unterstützt | d |
| Flansch | Kegel | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | Kegel | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | Kegel | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Flansch | einfach gekrümmt | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Flansch | einfach gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Flansch | einfach gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Flansch | einfach gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | einfach gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | einfach gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Flansch | doppelt gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Flansch | doppelt gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Flansch | doppelt gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | d |
| Flansch | doppelt gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | doppelt gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | doppelt gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Flansch | Freiform | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Flansch | Freiform | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Flansch | Freiform | Kreis | nicht unterstützt | nicht unterstützt | d |
| Flansch | Freiform | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Flansch | Freiform | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Flansch | Freiform | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | eben | gerade Kante | implementiert | eingeschränkt | a |
| Umschlag | eben | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Umschlag | eben | Kreis | nicht unterstützt | nicht unterstützt | d |
| Umschlag | eben | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | eben | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | eben | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | Zylinder | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Umschlag | Zylinder | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Zylinder | Kreis | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Zylinder | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Zylinder | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Zylinder | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | Kegel | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Umschlag | Kegel | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Kegel | Kreis | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Kegel | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Kegel | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Kegel | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | einfach gekrümmt | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Umschlag | einfach gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Umschlag | einfach gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Umschlag | einfach gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | einfach gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | einfach gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | doppelt gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Umschlag | doppelt gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Umschlag | doppelt gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | d |
| Umschlag | doppelt gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | doppelt gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | doppelt gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Umschlag | Freiform | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Freiform | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Freiform | Kreis | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Freiform | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Freiform | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Umschlag | Freiform | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | eben | gerade Kante | eingeschränkt | eingeschränkt | a |
| Doppelfalz | eben | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | eben | Kreis | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | eben | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | eben | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | eben | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | Zylinder | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Doppelfalz | Zylinder | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Zylinder | Kreis | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Zylinder | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Zylinder | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Zylinder | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | Kegel | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Doppelfalz | Kegel | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Kegel | Kreis | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Kegel | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Kegel | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Kegel | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | einfach gekrümmt | gerade Kante | nicht unterstützt | Prototyp (gesperrt) | b |
| Doppelfalz | einfach gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Doppelfalz | einfach gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Doppelfalz | einfach gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | einfach gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | einfach gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | doppelt gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | doppelt gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | doppelt gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | doppelt gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | doppelt gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | doppelt gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Doppelfalz | Freiform | gerade Kante | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Freiform | Kreisbogen | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Freiform | Kreis | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Freiform | Ellipse | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Freiform | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | d |
| Doppelfalz | Freiform | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | c |
| Mehrkantflansch mit Gehrung | eben | gerade Kante | eingeschränkt | nicht unterstützt | a |
| Mehrkantflansch mit Gehrung | eben | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | eben | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | eben | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | eben | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | eben | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Zylinder | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Kegel | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | Kreis | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Mehrkantflansch mit Gehrung | Freiform | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | eben | gerade Kante | implementiert | nicht unterstützt | a |
| Versatz | eben | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | eben | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | eben | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | eben | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | eben | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Zylinder | gerade Kante | Prototyp (gesperrt) | nicht unterstützt | e |
| Versatz | Zylinder | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Zylinder | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | Zylinder | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | Zylinder | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | Zylinder | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | Kegel | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | einfach gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | doppelt gekrümmt | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | gerade Kante | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | Kreisbogen | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | Kreis | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | Ellipse | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | Spline/freie Kurve | nicht unterstützt | nicht unterstützt | e |
| Versatz | Freiform | Kette aus Linien und Bögen | nicht unterstützt | nicht unterstützt | e |

Klassen: **a** native Fusion-Operation unterstützt; **b** eigene, mathematisch abwickelbare Geometrie möglich; **c** nur mit konstruktiver Änderung (Freistellung/Segmentierung); **d** mathematisch nicht verzerrungsfrei abwickelbar; **e** technisch ungeklärt. «implementiert» heisst NICHT live getestet.
<!-- /AUTO:kantenwerkzeug -->

**Parametrik und Editierbarkeit:** native Bauweise – Fusion-Features (Flansch/Saum) mit ihren Parametern, nachträglich in Fusion änderbar. Eigene Geometrie –
Konstruktionsebene «an der Kante» + nicht bemasste Skizze + Extrusion (Vereinigen): in der Zeitleiste nachvollziehbar, aber NICHT vollständig parametrisch
(Masse über erneutes Anwenden); Referenz auf die Kante über die Ebene; ändert sich vorgelagerte Geometrie, kann die Ebene die Kante verlieren (Fusion meldet
das in der Zeitleiste). Das Profil des Teils steht als Attribut am Körper (für die eigene Abwicklung); wird der Körper danach anders verändert, verweigert
die eigene Abwicklung über den Rückvergleich die Ausgabe.

### HISTORISCH – Korrektur nach Review (5. 11. 2026, veröffentlicht in 0.4.50)
- Unbekannte/nicht lesbare Flächen: werden in allen Pfaden «unbekannt» (mit Diagnose) und abgelehnt – kein Rückfall auf «eben» mehr. STUB-GETESTET.
- Eigene Geometrie am Fusion-Blechkörper: wird nur übernommen, wenn danach isSheetMetal gilt, eine native Prüf-Abwicklung entsteht und die DXF die
  Konturprüfung besteht; am Profilteil nur, wenn die eigene Abwicklung das GANZE Teil beschreibt. Sonst Ablehnung/Rückbau. Ob Fusion die Blechsemantik
  nach dem Join tatsächlich behält: **NICHT VERIFIZIERT** (nur im Live-Test feststellbar) – bis dahin gilt die eigene Geometrie als ungetestet.
- Prototypen: im Produktionsmodus gesperrt; kein Schalter in Dialog oder Einstellungen; nur Entwickler-Override `SPENGLER_CAD_EXPERIMENTELL` für exakt
  benannte Fälle mit Warnung.
- Begriffe: «mathematisch abwickelbar» (Geometrie) · «theoretischer Zuschnitt» (Modell ri + k·t, Werte angegeben) · «praktisch verifiziert» (nur nach
  Probebiegung) – nichts in diesem Stand ist praktisch verifiziert.
- Konturprüfung: Berührung/kollineare Überlappung (0.01 mm), adaptive Bogenteilung (Sehnenfehler ≤ 0.005 mm). Kollision mit dem BESTEHENDEN Körper wird
  über den Soll-Volumenzuwachs der Extrusion erkannt (Überlappung → zu kleiner Zuwachs → Ablehnung).
- Produktiv freigegeben: keine neue Funktion. Eigene Geometrie an ebener gerader Kante ist bedienbar, aber IMPLEMENTIERT – NICHT LIVE GETESTET.

## AKTUELLER STAND – Spengler-Kantenwerkzeug (Version 0.4.77)

- **0.4.77 – Quetschfalte: «Tasche» getrennt, Ecke bis zum Wandende gefüllt (Anwender nach Live 0.4.76):** Die Falte war mit der Wand verschmolzen («nur verdickt»), die Lücke
  in der Ecke blieb (Spalt grösser als die Blechdicke). Neu: die zwei Lagen sind EIGENE Körper «Quetschfalte Lage 1/2» (Neuer Körper, anliegend, nicht verschmolzen,
  Lage 2 mit gerundeten Faltkanten); die Ecke wird im Blechkörper bis zu den gemessenen Wandenden gefüllt (L-Grundriss bei 90°, über die ganze Höhe).
  Fusions Abwicklung bleibt gesperrt. NICHT live geprüft.

- **0.4.76 – Quetschfalte: erster Test am echten Modell (Live 0.4.74):** gebaut, aber «nicht gefaltet, nur verdickt» und Spalt/Loch in der Ecke. Neu: Länge der
  Aufkantungen wird geprüft (Falte ragte über das Wandende); **Ecksäule über die ganze Höhe** schliesst den Spalt der Stossecke (nur senkrechte
  Aufkantungen), **gerundete Faltkanten** an Faltlinie und Ecklinie (Radius 1.5 t, kosmetisch – scheitert die Rundung, bleibt der Rest); Sperre der
  Fusion-Abwicklung zusätzlich über eine Markierung an der Komponente. Anwender: Falte über die GANZE Höhe der Aufkantung; eigene Abwicklung in drei Stufen
  (1 eigene Abwicklung normaler Teile als Gegenprobe neben Fusion, 2 Quetschfalte einrechnen, 3 DXF/Werkstattblatt des ganzen Teils). NICHT live geprüft.

- **0.4.71 – QUETSCHFALTE an der Ecke zweier Aufkantungen (Anwender 6. 11. 2026, Variante a):** Befehl «Quetschfalte an Ecke» (Konstruieren). Auswahl: je eine
  ebene Fläche der beiden Aufkantungen (Innen- oder Aussenseite) + Richtung «hinten rechts/links» (Blick von der Sichtseite: Wand 2 liegt rechts). Höhen,
  Aufkantungswinkel, Kantenwinkel und Blechdicke liest das Add-in aus dem Modell. Rechnung `core/quetschfalte.py`: Überschuss-Sektor ψ = 360° − β − γ1 − γ2,
  Faltlinie an der Winkelhalbierenden (180°), Seiten gleich lang (A0 = C0), rechnerisches Falten mit Schliessprüfung; asymmetrische Ecken/ungleiche Höhen
  werden abgelehnt. Das Teil wird verändert: zwei dreieckige Platten (Blechdicke) auf der AUSSENseite der gewählten Aufkantung (Machbarkeit live
  bestätigt 0.4.70: Platte anfügen, Körper gültig, Fusion-Blech erhalten). Ausgabe: DXF des Zuschnitt-Ausschnitts der Ecke + zwei SVG-Zeichnungen in
  `%APPDATA%\SpenglerDigitalCAD\Quetschfalte`. **Fusions Abwicklung ist auf Teilen mit Quetschfalte gesperrt** (Absturzgefahr 0.4.67). Fehler der ersten
  Zeichnung behoben: Ansicht war spiegelverkehrt, «hinten rechts» = Wand 2 (per Vektorrechnung belegt). NICHT live geprüft (Live-Test-Schritt «QUETSCHFALTE:
  Ecke zweier Aufkantungen bauen»). Offen: Falz-Ausschnitte des Doppelfalzes, Dachneigung/asymmetrische Ecken, Biegezugaben und Lagendicke im Zuschnitt,
  Abwicklung des GANZEN Teils mit Quetschfalte.

- **AUSSENMASS live BESTÄTIGT (Live 0.4.68, Fusion 2706.1.17):** Flansche mit Biegung innen und Kantenabbild bauen; die Abwicklungen aus Fusion
  stimmen exakt mit der Aussenmass-Rechnung (L-Blech 78.26, zwei Biegungen 96.52, gerolltes Blech R20 90.11 mm). Offen/behoben in 0.4.69: Volumenkontrolle
  der Gehrung und des Flansch-Messschritts rechnet jetzt NETTO nach Aussenmass (`flansch_volumen_pro_laenge`; Biegung innen schneidet den Flanschfuss
  zurück – Winkelfalz 135° lieferte 36 % von L × h × t, Formel 37 %); Abwicklungs-Erwartung wieder nach Aussenmass. Zylinder-Versatz: neue Kante
  weiterhin nicht gefunden, Diagnose mit Abstand je Drehrichtung ergänzt. Machbarkeitstest Quetschfalte: vorsorglich GESPERRT (Fusion-Absturz 0.4.67).
  Offen: Rückschnitt des Grundblechs bei der eigenen Geometrie.

- **0.4.66 – Aussenmass erneut (Biegung innen):** Zugriffe auf die Kante NACH dem Bau laufen über ein Abbild, das VOR dem Bau gemacht wird
  (`_abbild`; Einzelkante, Gruppe mit Gehrung, Live-Test). Lage «innen» ist wieder Standard. Live 0.4.65: Flansch 90° Höhe 20.0 mm, Grundriss +2.0 mm
  (Biegung ab Kante) – der Live-Test prüft, dass der Grundriss jetzt gleich bleibt. NICHT live geprüft; bei Rückfall wieder «ab Kante» (STANDARD_LAGE).
  Live 0.4.65 sonst: 43 ok, 3 Warnungen (Stossecke 1.00 mm, fachlich zulässig), 1 Fehler (Zylinder-Versatz: neue Mantelkante nicht gefunden – offen).

- **0.4.62 – AUSSENMASS (Anwender 6. 11. 2026: «unsere Masse sind immer Aussenmasse»):** Fusion-Flansch ohne Angabe in der Vorlage: Höhe aussen,
  Biegung innen (Aussenfläche bündig mit der Kante; Teil aussen so gross wie das Grundblech) – lässt sich das nicht einstellen, wird nicht gebaut.
  Zugabe/Zuschnitt (Palette, Bauplan, Werkstattblatt) und eigene Geometrie: Schenkel bis zur ÄUSSEREN virtuellen Kante ((ri + t)·tan(α/2)).
  **0.4.63: Lage «innen» wieder zurückgestellt** – Live 0.4.62: Fusion schneidet dabei das Grundblech zurück, die gewählte Kante wird ungültig
  («thisASMEdge»), 8 Flansch-Schritte scheiterten. Native Flansche wieder «ab Kante» (Höhe aussen bleibt); Live-Test meldet das offene Aussenmass
  als Warnung. Lösung: Kantenabbild vor dem Bau, dann «innen» als Standard.
  Offen: eigene Geometrie schneidet das Grundblech noch nicht zurück (Biegung ab Kante, Teil um (ri + t) grösser – wird im Ergebnis gemeldet).
  Live 0.4.61: 43 ok; Eckspalt einzeln 1.41 / gemeinsam 1.00 mm erklärt die +11 mm³; Spalt-Ecke nach Vorgabe zulässig. Neu gebaute Kanten
  liegen gegenüber ≤ 0.4.61 um (ri + t) anders; bestehende Modelle unverändert. Nicht live geprüft.

- **Live 0.4.59 / 0.4.60:** Rückbau (beide Schritte) und Abstandsmessung Zylinder/Kegel live bestanden. Gehrung: Fusion baut eine Stossecke, keine
  45°-Gehrung (0.4.60 misst den Spalt). Gerolltes Blech: Ursache API-Verwendung (Profile statt Kurven), 0.4.60 mit offenem Profil – nicht live geprüft.
  Abwicklungs-Erwartung nach Fusion-Konvention (Biegung ausserhalb der Kante, Höhe aussen; live exakt). Fachlich offen: Massbezug, Eckform
  (siehe `docs/BERICHT_STABILISIERUNG_0459.md`, Nachtrag).

- **0.4.59 – Fehleranalyse/Stabilisierung (Bericht: `docs/BERICHT_STABILISIERUNG_0459.md`):** Live 0.4.57: alle Kantenwerkzeug-Schritte bestanden,
  Tests 2 und 3 von Hand bestanden. Offen und in 0.4.59 diagnostisch vorbereitet, NICHT live geprüft: Rückbau «unvollständig» (Restobjekt
  unbekannt; Regeln jetzt über die Regel-Liste nachgewiesen, alle Proben laufen), Gehrungsecke (Flächensuche am Körper, Diagnose, isMiteredCorners an
  der Eingabe), gerolltes Blech (Proxy/Path, API-Signaturen im Bericht; Folgetests NICHT GETESTET ohne Testkörper), Abstandsmessung (Occurrence →
  Körper; nicht messbar = Fehler). Cloud-Bericht jetzt vollständig (Details zuerst).

- **Live 0.4.55/0.4.56 (5. 11. 2026):** Test 2 (eigene Geometrie, Aufkantung 90°/20 an der Kante) in Fusion **bestanden**. Test 3 **nicht bestanden**:
  das Löschen der per API erzeugten Prüf-Abwicklung (FlatPattern.deleteMe) beschädigt die Komponente – `Component.flatPattern` wirft danach «res»,
  `createFlatPattern` meldet «already exists», Stückliste scheitert. **Ab 0.4.57 wird keine Prüf-Abwicklung mehr angelegt oder gelöscht**: eine
  vorhandene Abwicklung wird nachgeführt und ihre DXF streng geprüft; ohne Abwicklung steht im Bericht «native Abwicklung NICHT geprüft». Beschädigte
  Komponenten werden erkannt und mit Abhilfe gemeldet (Abwicklung im Browser löschen). Teststelle `eigen_pruefabwicklung_loeschen` entfällt (Test 6).
- **Doppelfalz = Stehfalz** (Anwender 5. 11. 2026): Umschlag + Umschlag gleicher Richtung legt das umgeschlagene Ende samt Umschlag nochmals um 180°
  um (Paket; äussere Biegung Innenradius 2·r₁ + t + r₂, innere Biegung r₂ konzentrisch, Rest des ersten Umschlags bleibt). Die Länge des zweiten
  Umschlags ist die umgelegte Höhe. Nur Bauweise «eigene Geometrie»; nativ wird vorher abgelehnt. Gegenrichtung bleibt Z-Profil. Nicht live geprüft.

- **Live-Test 97.002 mit 0.4.53 (Fusion 2706.1.17, 5. 11. 2026):** 13 ok, 2 Warnungen, 10 Fehler, 21 übersprungen. Ursache der Fehler und aller
  Übersprungenen: In einem frischen Dokument wirft `designSheetMetalRules.count` «InternalValidationError : smDataRoot» – kein Grundblech, also auch
  keine Folgeschritte (Kantenwerkzeug, Rückbau-Tests 5/6 NICHT gelaufen). Behebung in 0.4.54: Rückfall über eine Bibliotheksregel (legt die
  Blechdaten an), sonst klare Meldung – nicht live geprüft. Offen: «Abstand Detail↔Fläche nicht messbar» bei Zylinder- und Kegelschale.
- **Branch:** `ccr-26e82854-8ygnzg`. **Bearbeitungs-HEAD:** `172d7c3` (Release 0.4.52); dieser Stand wird als **0.4.53** veröffentlicht.
- **Veröffentlicht:** 0.4.50 (Kantenwerkzeug, Absicherungen), 0.4.51 (strenge DXF-Prüfung, Prüf-Abwicklung, Begriffe), 0.4.52 (Doku), 0.4.53 (Review-Vorschläge
  a–d: Biegelinien-Ebenen, doppelte Bögen/Kreise, Kreuzungen, Live-Teststelle Löschfehler). main unverändert.
- **Unit-/Stub-Tests:** 510 bestanden, 0 fehlgeschlagen, 1 übersprungen (ezdxf fehlt) – ohne Fusion, mit Attrappen.
- **Fusion-Live-Tests:** NICHT DURCHGEFÜHRT (0). Vorbereitet: Testanleitung, Abschnitt «Live-Tests Kantenwerkzeug (Tests 1–6)».
- **Fertigungsprüfung:** NICHT DURCHGEFÜHRT (0). Alle Zuschnittlängen sind theoretisch.
- **Produktiv freigegeben:** keine Funktion des Kantenwerkzeugs der Bauweise «eigene Geometrie». Bedienbar (an ebener gerader Kante), aber
  IMPLEMENTIERT – NICHT LIVE GETESTET. Prototypen (gekrümmte Flächen) im Produktionsmodus gesperrt (nur Entwickler-Override).

**Korrekturen aus dem letzten Review (0.4.51):**
1. *Strenge DXF-Prüfung nur für die interne Validierung:* `dxf_pruefung.pruefe_streng()` wird ausschliesslich in `_native_abwicklung_absichern()`
   verwendet (nach eigener Geometrie am Fusion-Blechkörper). Der normale Export «Abwicklung & DXF» nutzt weiter `pruefe()` (offene Konturen/doppelte
   Linien nur als Hinweis) – unverändert.
2. *Begriffe:* «mathematisch abwickelbar» (Geometrie, Gausssche Krümmung 0) · «theoretischer Zuschnitt» (Modell ri + k·t, Innenradius und K-Faktor des
   Materialprofils werden angegeben) · «praktisch verifiziert» (nur nach dokumentierter Probebiegung – liegt nicht vor).
3. *Temporäre Prüf-Abwicklung:* nach der Prüfung gelöscht und geprüft (deleteMe-Ergebnis, Objekt ungültig, `Component.flatPattern` leer); misslingt
   das, gilt der Vorgang als fehlgeschlagen und der Rückbau versucht es erneut und meldet den Rest. Eine vorher vorhandene Abwicklung wird nie gelöscht.

**Was `pruefe_streng()` prüft – und was nicht (Stand Code 0.4.51):**
- Geprüft: Datei lesbar; mindestens ein Element (Linie, Bogen, Kreis, Polylinie); Aussenmasse (Begrenzungsrahmen aller Elemente) gleich den
  erwarteten Massen ± 1 mm; `$INSUNITS` = mm – fehlt die Angabe, wird mm nur akzeptiert, wenn der Massvergleich in mm passt; keine offenen Enden (jeder
  Endpunkt gerade Anzahl, Raster 0.01 mm); keine doppelten Linien (gleiche Endpunkte); keine Verzweigung (kein Endpunkt mit mehr als zwei Enden); keine
  teilweise überlappenden kollinearen LINIEN; keine doppelten oder überlappenden Bögen/Kreise (gleiches Zentrum und gleicher Radius ± 0.001 mm,
  überlappender Winkelbereich); keine Elemente, die sich kreuzen oder berühren, ohne einen gemeinsamen Endpunkt zu haben (Bögen fein polygonisiert,
  Sehnenfehler ≤ 5 µm, Berührtoleranz 5 µm; blosse Annäherung zählt erst ab 1 mm vom gemeinsamen Endpunkt, damit tangential anschliessende Bögen
  keinen Fehlalarm geben); keine Spline/Ellipse (werden nicht gelesen → «nicht sicher prüfbar» → Ablehnung); genau eine Kontur bildet den
  Gesamtrahmen, weitere Konturen liegen mit ihrem Rahmen vollständig innerhalb.
- NICHT geprüft bzw. Grenzen: kein vollständiger CAD-Topologie-Nachweis. Kreuzungen eines Elements MIT SICH SELBST (z. B. eine verschlungene
  Polylinie) und Berührungen näher als 1 mm am gemeinsamen Endpunkt zweier Elemente werden nicht erkannt. Innenkonturen (Löcher) werden nach Lage
  und Kreuzungsfreiheit beurteilt, ihre Form nicht weiter. Biegelinien werden über den Ebenennamen erkannt (Muster bend/bieg/fold, ohne
  Gross-/Kleinschreibung; «kante» seit 0.4.53 entfernt, damit Kontur-Ebenen wie «Aussenkante» nicht mehr übergangen werden); andere Namen führen
  absichtlich zur Ablehnung (sie erscheinen als offene Kontur). Die Änderung des Musters wirkt auch auf die Hinweise der normalen Exportprüfung und die
  DXF-Vorschau (Ebenen «BIEGUNG_…» gelten jetzt als Biegelinie).
  Der Massvergleich gegen die von Fusion gelieferte Abwicklung ist eine Plausibilitätskontrolle, kein unabhängiger Nachweis der gesamten Geometrie.

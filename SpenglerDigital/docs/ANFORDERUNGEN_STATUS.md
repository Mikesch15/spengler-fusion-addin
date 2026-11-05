# Spengler Digital CAD – Anforderungsliste mit Status

**Aktueller Stand: Abschnitt «Korrekturauftrag gekrümmte Flächen – Status je Funktion» am Ende (5. 11. 2026, Branch `ccr-26e82854-8ygnzg`, nach 0.4.49, NICHT veröffentlicht).** Die älteren Abschnitte (auch «Nachtauftrag») sind Verlauf.

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

| Bearbeitung | Fläche | gerade Kante | Kreisbogen | Kreis | sonstige Kurve |
|---|---|---|---|---|---|
| Grundblech | eben | implementiert | implementiert | implementiert | implementiert |
| Grundblech | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Grundblech | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Zylinder | Prototyp (gesperrt) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | eben | eingeschränkt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkantflansch mit Gehrung | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Zylinder | Prototyp (gesperrt) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | eben | eingeschränkt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Zylinder | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | eben | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Zylinder | Prototyp (gesperrt) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Abwicklung / DXF | eben | implementiert | implementiert | implementiert | implementiert |
| Abwicklung / DXF | Zylinder | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | Kegel | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | einfach gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| Abwicklung / DXF | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Abwicklung / DXF | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail starr | eben | implementiert | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Zylinder | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Kegel | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | einfach gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | doppelt gekrümmt | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail starr | Freiform | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail an Fläche angepasst | eben | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Zylinder | Prototyp (gesperrt) | Prototyp (gesperrt) | Prototyp (gesperrt) | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Kegel | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | einfach gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| 3D-Detail an Fläche angepasst | Freiform | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |

Grenzen und Gründe (gekrümmte Fälle):
- **Grundblech / Zylinder** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / Kegel** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / einfach gekrümmt** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / doppelt gekrümmt** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Grundblech / Freiform** (nicht unterstützt): Grundblech entsteht eben; gekrümmte Bleche als gerolltes Segment (Prototyp im Live-Test) oder Rundblech (Drehkörper, kein Blech)
- **Flansch / Zylinder** (Prototyp (gesperrt)): gerade Kante parallel zur Achse eines gerollten Blechsegments, Fusion-native EdgeFlange; gesperrt bis Live-Test
- **Flansch / Zylinder** (nicht unterstützt): Flansch entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Flansch / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Flansch / einfach gekrümmt** (nicht unterstützt): Flansch auf einfach gekrümmt: keine eindeutige, exakte Geometrie
- **Flansch / doppelt gekrümmt** (nicht unterstützt): Flansch auf doppelt gekrümmt: keine eindeutige, exakte Geometrie
- **Flansch / Freiform** (nicht unterstützt): Flansch auf Freiform: keine eindeutige, exakte Geometrie
- **Mehrkantflansch mit Gehrung / Zylinder** (nicht unterstützt): erst nach bestandenem Einzelkanten-Prototyp
- **Mehrkantflansch mit Gehrung / Zylinder** (nicht unterstützt): Mehrkantflansch mit Gehrung entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Mehrkantflansch mit Gehrung / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Mehrkantflansch mit Gehrung / einfach gekrümmt** (nicht unterstützt): Mehrkantflansch mit Gehrung auf einfach gekrümmt: keine eindeutige, exakte Geometrie
- **Mehrkantflansch mit Gehrung / doppelt gekrümmt** (nicht unterstützt): Mehrkantflansch mit Gehrung auf doppelt gekrümmt: keine eindeutige, exakte Geometrie
- **Mehrkantflansch mit Gehrung / Freiform** (nicht unterstützt): Mehrkantflansch mit Gehrung auf Freiform: keine eindeutige, exakte Geometrie
- **Umschlag / Zylinder** (Prototyp (gesperrt)): gerade Kante parallel zur Achse eines gerollten Blechsegments, Fusion-native Hem; gesperrt bis Live-Test
- **Umschlag / Zylinder** (nicht unterstützt): Umschlag entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Umschlag / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Umschlag / einfach gekrümmt** (nicht unterstützt): Umschlag auf einfach gekrümmt: keine eindeutige, exakte Geometrie
- **Umschlag / doppelt gekrümmt** (nicht unterstützt): Umschlag auf doppelt gekrümmt: keine eindeutige, exakte Geometrie
- **Umschlag / Freiform** (nicht unterstützt): Umschlag auf Freiform: keine eindeutige, exakte Geometrie
- **Doppelfalz / Zylinder** (nicht unterstützt): erst nach bestandenem Einzelkanten-Prototyp
- **Doppelfalz / Zylinder** (nicht unterstützt): Doppelfalz entlang einer Kreiskante eines Zylinders: Fusion-API nur gerade Kanten; Live-Anfrage im Test
- **Doppelfalz / Kegel** (nicht unterstützt): kein gerolltes Kegelsegment per API erzeugbar (kein Lofted-Flange in der API bekannt) – nicht prüfbar, nicht freigegeben
- **Doppelfalz / einfach gekrümmt** (nicht unterstützt): Doppelfalz auf einfach gekrümmt: keine eindeutige, exakte Geometrie
- **Doppelfalz / doppelt gekrümmt** (nicht unterstützt): Doppelfalz auf doppelt gekrümmt: keine eindeutige, exakte Geometrie
- **Doppelfalz / Freiform** (nicht unterstützt): Doppelfalz auf Freiform: keine eindeutige, exakte Geometrie
- **Versatz / Zylinder** (Prototyp (gesperrt)): gerade Kante parallel zur Zylinderachse: Versatz als Bogenlänge entlang des Mantels (Drehschnitt/-anfügung um die Achse, exakt)
- **Versatz / Zylinder** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / Kegel** (nicht unterstützt): Kegel: tangentialer Versatz einer Mantellinie ist eine Drehung um die Spitze, Normal- und Radialrichtung unterscheiden sich – noch nicht umgesetzt
- **Versatz / einfach gekrümmt** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / doppelt gekrümmt** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Versatz / Freiform** (nicht unterstützt): kein eindeutig definierter Versatz für diese Geometrie
- **Abwicklung / DXF / Zylinder** (eingeschränkt): exakt abwickelbar; nur wenn Fusion den Körper als Blech abwickelt
- **Abwicklung / DXF / Kegel** (eingeschränkt): exakt abwickelbar; nur wenn Fusion den Körper als Blech abwickelt
- **Abwicklung / DXF / einfach gekrümmt** (eingeschränkt): mathematisch abwickelbar; Fusion entscheidet, kein eigener Nachweis
- **Abwicklung / DXF / doppelt gekrümmt** (nicht unterstützt): Gausssche Krümmung ≠ 0 – keine exakte Abwicklung, keine DXF als exakt
- **Abwicklung / DXF / Freiform** (nicht unterstützt): Abwickelbarkeit nicht nachgewiesen – keine DXF als exakt; Näherung ist ein eigener, noch fehlender Modus
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

**Machbarkeit gekrümmter Fälle (aus `core/unterstuetzung.py` erzeugt):**

| Bearbeitung | Fläche | gerade Kante | Bogen/Kreis | Fusion-nativ | eindeutig | exakt | Live-Test |
|---|---|---|---|---|---|---|---|
| Grundblech | Zylinder | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | Kegel | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | einfach gekrümmt | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Grundblech | Freiform | nicht unterstützt | nicht unterstützt | BaseFlange (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | Zylinder | Prototyp (gesperrt) | nicht unterstützt | EdgeFlange (Preview) | ja | exakt | nötig |
| Flansch | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Flansch | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Zylinder | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Mehrkantflansch mit Gehrung | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange mehrere Kanten | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | Zylinder | Prototyp (gesperrt) | nicht unterstützt | Hem (Preview) | ja | exakt | nötig |
| Umschlag | Kegel | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Umschlag | Freiform | nicht unterstützt | nicht unterstützt | Hem (Preview) | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Zylinder | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Kegel | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Doppelfalz | Freiform | nicht unterstützt | nicht unterstützt | EdgeFlange + Hem | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | Zylinder | Prototyp (gesperrt) | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | exakt | nötig |
| Versatz | Kegel | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | nein | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Versatz | Freiform | nicht unterstützt | nicht unterstützt | Extrude/Revolve (Schnitt/Anfügen) | nein | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Abwicklung / DXF | Zylinder | eingeschränkt | eingeschränkt | FlatPattern | ja | exakt | nötig |
| Abwicklung / DXF | Kegel | eingeschränkt | eingeschränkt | FlatPattern | ja | exakt | nötig |
| Abwicklung / DXF | einfach gekrümmt | eingeschränkt | eingeschränkt | FlatPattern | ja | exakt | nötig |
| Abwicklung / DXF | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | FlatPattern | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| Abwicklung / DXF | Freiform | nicht unterstützt | nicht unterstützt | FlatPattern | ja | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail starr | Zylinder | eingeschränkt | eingeschränkt | Import + Transform | ja | exakt | nötig |
| 3D-Detail starr | Kegel | eingeschränkt | eingeschränkt | Import + Transform | ja | exakt | nötig |
| 3D-Detail starr | einfach gekrümmt | eingeschränkt | eingeschränkt | Import + Transform | ja | exakt | nötig |
| 3D-Detail starr | doppelt gekrümmt | eingeschränkt | eingeschränkt | Import + Transform | ja | nicht exakt | nötig |
| 3D-Detail starr | Freiform | eingeschränkt | eingeschränkt | Import + Transform | ja | nicht exakt | nötig |
| 3D-Detail an Fläche angepasst | Zylinder | Prototyp (gesperrt) | Prototyp (gesperrt) | Benutzerparameter | ja | exakt | nötig |
| 3D-Detail an Fläche angepasst | Kegel | nicht unterstützt | nicht unterstützt | Benutzerparameter | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | einfach gekrümmt | nicht unterstützt | nicht unterstützt | Benutzerparameter | ja | exakt | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | doppelt gekrümmt | nicht unterstützt | nicht unterstützt | Benutzerparameter | nein | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |
| 3D-Detail an Fläche angepasst | Freiform | nicht unterstützt | nicht unterstützt | Benutzerparameter | nein | nicht exakt | Live-Anfrage (Ablehnung bestätigen) |

**Fusion-API-Risiken:** Blech-Features (BaseFlange, EdgeFlange, Hem) sind Preview-API und werden vor dem Aufruf mit `hasattr` geprüft; neu genutzt und
nicht live bestätigt: `SurfaceEvaluator.getCurvature/getFirstDerivative/parametricRange`, `CurveEvaluator.getTangent`, `MeasureManager.measureMinimumDistance`,
`Design.createInterferenceInput/analyzeInterference`, `sketchArcs.addByThreePoints`, `RevolveFeatures` mit Teilwinkel. Fehlt eine dieser Funktionen,
wird verständlich abgebrochen (Interferenz: ausdrücklich gekennzeichnete Grobprüfung).
**BaseFeature-/Kombinieren-Integration** eines 3D-Details friert die Detailgeometrie ein: die parametrische Feature-Historie des Details bleibt NICHT erhalten.

## Korrekturauftrag gekrümmte Flächen – Status je Funktion (5. 11. 2026, AKTUELL)
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
werden. Doppelt gekrümmt (Kugel, Torus) – Gausssche Krümmung ≠ 0, keine exakte Abwicklung; Flansch/Umschlag ohne eindeutige Geometrie. Freiform –
Abwickelbarkeit nur über Stichproben, ausgefallene Punkte = unsicher; Bearbeitungen nicht definiert. Prototypen sind im normalen Bau GESPERRT und
werden erst nach bestandenem Live-Test (und fachlicher Prüfung) in `core/unterstuetzung.py` freigegeben.

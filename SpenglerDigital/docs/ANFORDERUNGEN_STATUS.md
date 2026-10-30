# Spengler Digital CAD – Anforderungsliste mit Status

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

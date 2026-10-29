# Abschlussbericht – Prüfung von Spengler Digital CAD 0.4.0, Korrekturen in 0.4.2

Stand 29.10.2026 · Repo `Spengler-Digital-CAD`, Branch `claude/new-session-ux68bs`, Ordner `fusion/SpenglerDigital`
Anforderungsliste mit Status: `docs/ANFORDERUNGEN_STATUS.md` · Vorgeschichte: `docs/ABSCHLUSSBERICHT_0.2.0.md`

## 1. Was geprüft wurde

Quellcode aller Module, Testanleitung, ursprünglicher Projektauftrag. Schwerpunkt wie beauftragt: Flansch, Umschlag,
Vorschau, Kantenauflösung, Rückbau bei Fehlern, Abwicklung, DXF, Sicherungen, Updates, Cloud-Synchronisierung.
Benutzerdaten wurden nicht verändert, keine Funktion wurde entfernt.

## 2. Gefundene und behobene Fehler (0.4.2)

| # | Bereich | Fehler | Behebung | Nachweis |
|---|---|---|---|---|
| 1 | Abwicklung | Masse nur aus X/Y des Begrenzungsrahmens. Liegt die Abwicklung nicht in XY, wäre die Blechdicke als Breite gemeldet worden (Stückliste, Etiketten, Zuschnitt falsch) | alle drei Ausdehnungen, kleinste = Dicke | Test scheitert am alten Code (Gegenprobe) |
| 2 | Kanten bearbeiten | Ergebnisprüfung benutzte die Körper-Referenz von VOR dem Bauen; in Fusion wird sie oft ungültig → falsche Meldung «Körper ist ungültig» möglich | Körper über entityToken neu auflösen; nicht auffindbar → Hinweis statt falscher Meldung | Logik-Test; in Fusion nicht live |
| 3 | Rückbau | Schlug das Löschen der bereits erzeugten Schritte fehl, wurde trotzdem «entfernt» gemeldet | Rückbau-Ergebnis wird ausgewertet; sonst Meldung «nicht vollständig entfernt – Strg+Z» | Test scheitert am alten Code |
| 4 | Rückbau | Fehlermeldung nannte bei «neue Kante nicht gefunden» den falschen Schritt | Meldung «Nach Schritt n (Kante für Schritt n+1 suchen)» | Test scheitert am alten Code |
| 5 | Abgleich | Mitarbeiter ohne Änderungsrecht: bei Konflikt wurde die eigene lokale Änderung **überschrieben** (Datenverlust) | lokale Fassung bleibt als lokale Kopie | Test scheitert am alten Code |
| 6 | Sicherung/Abgleich | Nach dem Wiederherstellen einer alten Sicherung hätte der nächste Abgleich die neueren Fassungen **in der App überschrieben** | Abgleichstand wird beim Wiederherstellen verworfen → Konflikt-Kopie statt Überschreiben; kein Auto-Abgleich direkt nach dem Wiederherstellen | Test scheitert am alten Code |
| 7 | Updates | Zweites «Nach Updates suchen» ohne Neustart meldete «0 Dateien installiert» | Meldung «bereits installiert – Add-in neu starten» | Test: nach Installation nichts mehr nötig |
| 8 | Start | Abgleich/Update-Prüfung beim Start mit 15 s Zeitlimit je Anfrage → Fusion-Start konnte bei schlechtem Netz lange hängen | 6 s beim Start | Code-Durchsicht |
| – | Abgleich | (Schutz, kein nachgewiesener Fehler) Datensätze aus einer neueren Add-in-Version werden nie mit älteren Fassungen überschrieben | Schutzlogik | Test |

## 3. Geprüft, ohne Fehler gefunden – aber NICHT in Fusion bestätigt

- **Flansch:** Werte und Einheiten («25 mm», «45 deg») korrekt; fehlt in Fusion die Eigenschaft für Winkel ≠ 90°, Richtung «nach
  hinten» oder Radius, wird abgebrochen statt mit falschem Wert gebaut. **Offen:** tatsächliche Eigenschaftsnamen der
  Preview-API und der Höhenbezug von Fusion (aussen, innen oder Blechmitte – die Kurzschrift misst auf Blechmitte bis zur
  virtuellen Kante; Abweichung bis ca. t/2 + Radius möglich).
- **Umschlag:** beide Aufrufformen (ohne Argumente + Kante setzen; mit Kante als Argument) getestet; Spalt = 2 × Radius ist eine
  Annahme. **Offen:** Verhalten in Fusion.
- **Vorschau:** baut in `executePreview` dieselben Features, Fusion verwirft sie selbst; `isValidResult = False` erzwingt Neubau
  beim OK. **Offen:** in Fusion nicht gesehen.
- **Kantenauflösung:** entityToken; 0 oder mehrere Treffer → Abbruch. Neue Aussenkante: parallel, volle Länge, Abstandsfenster,
  Mehrdeutigkeit → Abbruch. **Offen:** welche der beiden Endkanten (Ober-/Unterseite) Fusion für Folgeschritte braucht.
- **DXF:** Zuschnittplan-DXF mit unabhängigem Leser (ezdxf 1.4.5) geprüft: R12, 0 Fehler, 1:1 in mm. Fusion-DXF der Abwicklung:
  Erfolg nur, wenn die Datei existiert (Logik-Test). **Offen:** Export in Fusion.
- **Sicherungen:** Prüfsummen, Rückbau bei Fehler, keine Wiederherstellung ohne Bestätigung – getestet.
- **Updates:** nur geänderte Dateien, sha256, Pfade ausserhalb des Programmordners abgelehnt, Manipulation erkannt, Daten- und
  Programmsicherung, Rückbau – getestet. **Offen:** in Fusion.
- **Cloud:** Datenbankregeln in der echten Datenbank 13/13 (Probe-Transaktion, zurückgenommen); Client gegen Nachbau.
  **Offen:** Anmeldung/Abgleich aus Fusion (aus der Sandbox ist Supabase per HTTPS nicht erreichbar).

## 4. Tatsächlich ausgeführte automatische Tests (29.10.2026)

Befehl: `python3 fusion/SpenglerDigital/tests/run_all.py` → **121 Tests, 0 Fehler, 0 Ausfälle, 0 übersprungen**
(ezdxf und Node/Playwright waren vorhanden, daher liefen auch DXF-Leser- und Browsertest). Zusätzlich
`python3 fusion/test_kurzschrift.py` → bestanden; `pyflakes` ohne Befund.

| Datei | Tests | Art |
|---|---|---|
| test_cloud | 18 | Anmeldung, Abgleich zwei PCs, Konflikt, Löschen, Rechte, Firmen, Geometrie, offline, Restore, Updater – gegen **Supabase-Nachbau** |
| test_fusion_logik | 21 | **neu**: Flansch, Umschlag, neue Aussenkante, Rückbau, Abwicklungsmasse, DXF-Erfolgsprüfung, Kantenbeschreibung, Kantenauflösung, Teilenummern – mit **nachgebauten Fusion-Objekten** |
| test_templates | 14 | Vorlagen, Bibliothek leer, Versionen, Import/Export |
| test_nesting | 13 | Zuschnitt gegen 13 Referenzfälle aus dem echten App-JavaScript, DXF mit ezdxf |
| test_migrations | 10 | Migration ohne Datenverlust, Sicherung/Wiederherstellung |
| test_parts_list | 8 | Zeichnungen, Vorschau, Stückliste, Etiketten |
| test_validation | 8 | Material, Einstellungen, Detailvorlagen, Ausrichtung, Parameterzuordnung, Palette-URL |
| test_forming | 7 | Rundblech, Werkstattblatt |
| test_operation_plan | 6 | Bauplan, Kanteneignung |
| test_geometrie | 5 | Biegerechnung gegen JS-Referenz, K-Faktor, Einheiten |
| test_short_syntax | 5 | Kurzschrift |
| test_import_fusion | 4 | Syntax, Import aller Module, Start/Stop, Dialogaufbau mit **Attrappe** |
| test_palette | 2 | Palette-Backend; **echte HTML-Palette in Chromium** inkl. Anmeldung gegen Nachbau |

Gegenprobe: 6 der neuen Tests wurden gegen den Code von 0.4.0 ausgeführt und scheitern dort wie erwartet.

## 5. In Fusion live getestet (vom Anwender)

Fusion 2706.1.17, Windows: Add-in-Start, Fähigkeitsprüfung (9/9 vorhanden), Selbsttest (Einheiten, Drehkörper, .f3d
Export/Import, Ausrichtung, Benutzerparameter). Mehr nicht.

## 6. Noch offene Anforderungen (Auszug, vollständig in ANFORDERUNGEN_STATUS.md)

- **Durchgehende Flansche, Umschläge, Einzel- und Doppelfalze an gekrümmten/runden Blechkanten ohne Einschnitte/Lappen:
  NICHT umgesetzt.** Vorhanden ist nur die Beurteilung (stauchen/strecken, konstruierbar/abwickelbar/herstellbar) und ein
  Drehkörper für Scheibe mit Rand und Kegel – kein Fusion-Blechkörper, keine Falze, kein Anwenden auf vorhandene gekrümmte Kanten.
  Möglicher Weg (zu prüfen): Querschnitt-Sweep entlang der gekrümmten Kante als Volumenkörper, mit eigener Abwicklungsrechnung
  und Kennzeichnung «kein Fusion-Blech».
- **Zuschnittoptimierung – fehlende Teile der App:** Rollenmischung, Mischen verschiedener Breiten im selben Abschnitt
  («Trittbrett»), Teilen zu langer Stücke mit Nahtüberlappung, Reststücke/Restelager, Materialbilanz (Schnittfuge, Reste),
  Normlängen für Stangenware, Spaltband-/Coil-Vorrang; Verschachtelung echter Konturen statt Rechtecke.
- Eigene Ausschnitte/Freistellungen und Eckregeln (Gehrung, Saum an Saum) – nicht umgesetzt.
- 3D-Detail mit dem Blechkörper vereinigen und als bearbeitbare Features integrieren – nicht umgesetzt.
- Automatische Fusion-Zeichnungen – nicht umgesetzt (Werkstattblatt als Ersatz).
- Konturprüfung der Fusion-DXF, konfigurierbare Layer in der Fusion-DXF – nicht umgesetzt.

## 7. Erforderliche Live-Tests in Fusion (kurz, Reihenfolge)

1. Version prüfen (Hilfe → Fähigkeiten: 0.4.2 bzw. nach Update), Palette öffnet sich.
2. Konto anmelden, «Jetzt abgleichen», «Nach Updates suchen».
3. Kanten bearbeiten an einer Grundlasche: `90 25`, dann `90 H U+ u`. **Masse in Fusion nachmessen** (Höhenbezug!), Vorschau sichtbar,
   Strg+Z nimmt alles in einem Schritt zurück. Protokollzeilen `EdgeFlangeInput eigenschaften=…`, `HemFeatureInput eigenschaften=…` schicken.
4. Ungeeignete Kante (Biegekante, Volumenkörper) → gesperrt mit Grund.
5. Abwicklung & DXF (mit/ohne vorhandene Abwicklung), DXF in CAD öffnen.
6. Stückliste & Zuschnitt, Etiketten drucken.
7. 3D-Detail erfassen/anwenden, zweimal im selben Dokument.
8. Mitarbeiter-Konto, offline-Start, Sicherung wiederherstellen.
Ausführlich: `docs/Testanleitung.pdf`.

## 8. Lieferung

- ZIP `SpenglerDigitalCAD_0.4.2.zip` = Programmstand dieses Berichts und **neue Grundinstallation** (Basis-Dateiliste
  `fusion/releases/basis.json` jetzt 0.4.2). Bitte 0.4.2 von Hand installieren (statt 0.4.0).

## 9. Update-Kanal in der App (Datenbank)

- Test-Update **0.4.3** veröffentlicht (nur Versionsnummer, 2 Dateien, Prüfsummen in der Datenbank kontrolliert). Gegen das ZIP
  0.4.2 geprüft: genau diese 2 Dateien würden ersetzt.
- Test-Update 0.4.1 abgeschaltet (`aktiv = false`, nicht gelöscht).
- Wer noch 0.4.0 installiert hat: das Update auf 0.4.3 bricht mit «Update unvollständig … bitte ZIP von Hand» ab und verändert
  nichts (so getestet) – dann ZIP 0.4.2 von Hand installieren.
- Keine Benutzerdaten in der Datenbank verändert (cad_daten unverändert).

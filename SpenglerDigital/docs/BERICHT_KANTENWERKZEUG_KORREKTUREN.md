# Bericht: Korrekturen am Kantenwerkzeug nach Review 0.4.49

Branch `ccr-26e82854-8ygnzg` · Ausgangs-Commit `3d6044b` (geprüft: sauber, 471 Stub-Tests grün) · Version 0.4.49 unverändert · kein Release, kein Merge, main
nicht berührt. **Fusion-Live-Tests: 0 durchgeführt** (kein Fusion in der Arbeitsumgebung). **Fertigungsprüfungen: 0.**

## Korrekturen je Phase
| Phase | Commit | Konkrete Korrektur |
|---|---|---|
| 1 | `9c4299a` | `kante_beschreiben` setzte bei Lesefehler «eben» → jetzt `flaechentyp_kante`: «unbekannt» + Diagnose bei Fehler in `edge.faces`/`face.area`, keiner Fläche, unbekanntem Fusion-Typ; Flächenzahl/Aussenkanten-Erkennung fehlertolerant (None statt Absturz). `operation_plan`: Standard «unbekannt» statt «eben» (3 Stellen) und ausdrückliche Ablehnung mit Diagnose in jeder Bauweise. `flaechentyp`/`bezugsflaeche` protokollieren Lesefehler. 3D-Detail lehnt unbekannte Bezugsfläche ab. Palette-Trockenlauf setzt «eben» ausdrücklich (gedachte Kante, kein Rückfall). |
| 2 | `c6eba94` | `eigene_folge`: vor dem Bau Ablehnung, wenn weder Fusion-Blechkörper noch Profilteil mit Kante am Profilende. Nach dem Bau am Blechkörper `_native_abwicklung_absichern`: `isSheetMetal` muss gelten, native (Prüf-)Abwicklung, DXF-Export und Konturprüfung; neue Prüf-Abwicklung wird danach entfernt, bei jedem Fehler gehört sie zum Rückbau. Am Profilteil: Profil fortschreiben + eigene Abwicklung des ganzen Teils mit Rückvergleich, sonst Rückbau. Neue Teststellen `eigen_validierung_abwicklung`, `eigen_validierung_dxf`. |
| 3 | `2b065ea` | Prototypen-Schalter in Dialog und Einstellung (`geometrie.prototypenFreigegeben`) entfernt; alte Werte wirkungslos. Neuer Entwickler-Override `SPENGLER_CAD_EXPERIMENTELL` (`core/experimentell.py`) nur für exakt benannte Prototyp-Fälle, ungültige Einträge ignoriert, Warnung mit Bestätigung vor der Ausführung, Hinweis im Dialog. |
| 4 | `d43bf84` | «exakt» aus Meldungen/Bauplan/Export/Matrix/Analyse entfernt; Begriffe A mathematisch abwickelbar, B theoretischer Zuschnitt (k, ri angegeben), C praktisch verifiziert (nur nach Probebiegung). Berechnungen unverändert. |
| 5 | `8aed2e9` | Konturprüfung: Berührung und kollineare Überlappung (Abstand < 0.01 mm zwischen entlang des Umrisses entfernten Teilen), adaptive Bogenteilung (Sehnenfehler ≤ 0.005 mm; vorher bis 0.03 mm bei R 100 – mögliche falsche Freigabe), keine Fehlalarme in engen Biegungen. |
| 6/7 | dieser Commit | Testanleitung (8 Pflicht-Live-Tests mit Zuordnung), Statusdokument, dieser Bericht. |

## Neue/geänderte Tests (Unit/Stub)
`test_unbekannte_flaechen.py` (neu: fehlende Info, Lesefehler faces/area, unbekannter Typ, Diagnose, ebene Fläche unverändert, kante_beschreiben),
`test_prototyp_sperre.py` (neu: Standard gesperrt, Override exakt, ungültige Werte, unzulässige Kombination, Einstellungsdatei wirkungslos),
`test_grundblech_regel.py` (Blechsemantik/Prüf-Abwicklung/DXF), `test_profil_engine.py` (Begriffe, Kontur: Berührung, Überlappung, Toleranzgrenze,
kleinster und grosser Radius), `test_operation_plan.py` (Testkante mit ausdrücklich ebener Fläche), `test_kantenwerkzeug_matrix.py` (Begriffe).

## Testergebnisse
| Stufe | Ergebnis |
|---|---|
| Unit-/Stub-Tests (`tests/run_all.py`) | 492, 0 Fehler, 1 übersprungen (ezdxf fehlt) |
| Fusion-Live-Tests | 0 – nicht durchgeführt (keine Fusion-Umgebung). Pflichttests 1–8 sind als Live-Schritte vorbereitet (Testanleitung); Nr. 3 (unbekannte Fläche) ist in Fusion nicht gezielt erzeugbar und nur als Stub-Test vorhanden |
| Fertigungsprüfung | 0 |

## Freigabestand
- **Produktiv freigegeben (neu):** nichts. Bestehende native planare Workflows unverändert (Regressionstests grün).
- **Bedienbar, aber IMPLEMENTIERT – NICHT LIVE GETESTET:** eigene Geometrie an ebener gerader Kante (am Fusion-Blechkörper nur mit nachgewiesener nativer
  Abwicklung, sonst Rückbau).
- **Gesperrt (nur Entwickler-Override):** gerade Mantelkante auf Zylinder/Kegel (eigen und nativ), Umschlag auf Zylinder, Versatz am Zylinder, Detail an
  Zylinder anpassen.
- **Nicht unterstützt:** Kreisbogen-/Kreis-, Ellipsen-, Spline-Kanten, doppelt gekrümmte/Freiform-/unbekannte Flächen.

## Nachweise zu Blechkörper, Abwicklung und DXF nach eigener Geometrie
- Ob ein Fusion-Blechkörper nach dem Join der eigenen Geometrie ein gültiger Blechkörper bleibt: **NICHT VERIFIZIERT.** Der Code prüft es jetzt vor der
  Übernahme (`isSheetMetal`, native Abwicklung, DXF); fällt die Prüfung negativ aus, wird zurückgebaut – das ist die sichere Seite, kein Nachweis.
- Native Abwicklung und DXF nach eigener Geometrie: **NICHT VERIFIZIERT** (Live-Schritt «KANTENWERKZEUG eigen: Aufkantung» prüft genau das).

## Offene Risiken und nicht durchgeführte Prüfungen
- Alle Fusion-Aufrufe der eigenen Geometrie und der Absicherung sind ungetestet; denkbar ist, dass Fusion nach dem Join `isSheetMetal` verliert – dann
  lehnt das Werkzeug die eigene Geometrie an Blechkörpern immer ab (sicher, aber ohne Nutzen).
- Die Prüf-Abwicklung wird wieder gelöscht; schlägt das Löschen fehl, bleibt sie stehen (im Bericht vermerkt).
- Zuschnittlängen sind theoretisch (Modell ri + k·t); ohne Probebiegung keine Aussage zur Fertigungsgenauigkeit.
- Pflichttest 3 (unbekannte Fläche) live nicht provozierbar.

## Anleitung für die Live-Prüfung
Siehe Testanleitung, Abschnitt «Pflicht-Live-Tests nach Korrektur 0.4.49»: Branch-Stand einspielen, SPENGLER → Verwaltung → Live-Test mit «Ergebnis
senden», je Test Fusion-Version/OS, Ergebnis und Bildschirmfoto festhalten.

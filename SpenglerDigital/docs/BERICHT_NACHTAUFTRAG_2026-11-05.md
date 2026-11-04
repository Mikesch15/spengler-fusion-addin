# Abschlussbericht XXL-Nachtauftrag – Geometrie, gekrümmte Flächen, 3D-Details

**Branch** `ccr-26e82854-8ygnzg` · **Ausgangs-HEAD** `bb4254c` (Release 0.4.49) · **Version unverändert 0.4.49 – kein Release, main nicht berührt.**
**Wichtig:** Keine der Änderungen wurde in Fusion ausgeführt. Alle Tests unten sind Unit-/Stub-Tests mit Attrappen. Fusion-Live-Tests: **NICHT GETESTET**
(aus der Entwicklungsumgebung nicht möglich); sie sind als Live-Test-Schritte vorbereitet und laufen beim Anwender über SPENGLER → Verwaltung → Live-Test.

## Commits je Phase
| Phase | Commit | Inhalt |
|---|---|---|
| 0 | – | Bestand: HEAD `bb4254c`, Arbeitsbaum sauber, 407 Stub-Tests grün |
| 1 | `de32e12` | Rückbau-Proben (genau der eingeschleuste Fehler, Zustand inkl. Occurrences/Komponenten/Parameter/Blechregeln/Canvases), atomarer 3D-Detail-Import, Gehrungsecke geometrisch gemessen, Bericht PASS/FAIL/NICHT GETESTET |
| 2 | `fcb98c6` | Zentrale Geometrie-Referenz, Unterstützungsmatrix, lokaler Rahmen aus Normale, Kantenrahmen mit Normale am Ankerpunkt |
| 3–5 | `995dde8` | Versatz nur auf ebenen Blechflächen (erklärt), Fusion-Anfrage an gekrümmten Kanten nur im Live-Test, Umschlag-Mindestlänge, Bögen im Profil/Drehkörper |
| 6–7 | `434a0d9` | Abwickelbarkeit vor der Abwicklung, Rücknahme neuer Abwicklung bei Exportfehler, Volumen-Interferenz, Abstandsmessung, Abstand entlang Normale, gekrümmte Auswahl (starr) |
| 8 | `1ab4179` | Live-Testkörper gekrümmt + Doppelfalz |
| 9–10 | `2cc72f2` | Negativtest Radius, Doku-Synchrontest, Statusdokument, Handbuch, Testanleitung |

## Geänderte Dateien (Kurzbeschreibung)
- `geometry/fusion_adapter.py` – `detail_einsetzen` (atomar), `parameter_entfernen`, `ecke_daten`/`gehrung_eckspalt`, `referenz_aus_fusion`, `flaechentyp`, Krümmung, `kantenrahmen` mit Normale am Ankerpunkt (auch Bogenkanten), Versatz nur eben + `versatz_text`, `fusion_fragen` für Flansch/Umschlag, Umschlag-Mindestlänge, negativer Radius abgelehnt, Bögen in `blech_aus_profil`/`drehkoerper` (+ Teilwinkel), `abwickelbarkeit_koerper`/`_gauss_max`, `kollision_pruefen` (Interferenz) und `abstand_mm`, `quader_komponente`, `occurrence_von`, öffentliche Testfehler-Stellen.
- `core/geometrie_referenz.py` (neu) – Referenz, Klassen A/B/C, Veraltet-Prüfung, analytische Normalen, Abwickelbarkeit, Versatzdefinition.
- `core/unterstuetzung.py` (neu) – Matrix Bearbeitung × Geometrieklasse; Quelle für Eignung und Doku.
- `core/gehrung.py` (neu) – Gehrungsflächen erkennen, Eckspalt bewerten.
- `core/operation_plan.py` – gekrümmte Kanten über die Matrix; `details/frames.py` – `rahmen_aus_normale`.
- `core/livetest_bericht.py` – PASS / PASS mit Hinweis / FAIL / NICHT GETESTET.
- `commands/detail_generator_command.py` – atomares Einsetzen, Abstand, Interferenz/Abstandsmeldung, Bogenkanten und Zylinder-/Kegelflächen wählbar.
- `commands/export_command.py` – neu erzeugte Abwicklung bei Fehler entfernt.
- `diagnostics/live_test.py`, `diagnostics/live_test_gekruemmt.py` (neu) – Rückbau-, Import-, Gehrungs-, Doppelfalz- und gekrümmte Live-Schritte.
- Tests: `test_gehrung_import.py`, `test_geometrie_referenz.py` (neu), Ergänzungen in `test_grundblech_regel.py`, `test_fusion_logik.py`, `test_livetest.py`, `fake_fusion_blech.py`.
- Doku: `ANFORDERUNGEN_STATUS.md` (aktueller Abschnitt + Matrix), `Benutzerhandbuch.md`, `Testanleitung.md`, PDFs/HTML.

## Tests
- **Stub/Unit (ohne Fusion):** 432 Tests, 0 Fehler, 1 übersprungen (ezdxf fehlt). Davon neu: Referenz/Normalen/Abwickelbarkeit/Versatz/Matrix, Gehrungsflächen/Eckspalt, atomarer Detail-Import in jeder Phase, Bögen im Profil, Versatz-Ablehnung auf Zylinder, Umschlag-Mindestlänge, Kugel nicht abwickelbar, Interferenz-Rückfall, Abwicklungs-Rücknahme, negativer Radius, Doku-Synchronität.
- **Fusion-Live:** NICHT GETESTET. Grund: kein Fusion in der Entwicklungsumgebung. Vorbereitet: siehe Testanleitung, Abschnitt Live-Test.

## Statusmatrix (implementiert ≠ live getestet; Live-Stand: überall «nicht live getestet» ausser den 0.4.42-Ergebnissen)
| Funktion | eben | gekrümmte Kante | Zylinder | Kegel | Freiform |
|---|---|---|---|---|---|
| Grundblech | implementiert (Basisflansch live 0.4.42) | implementiert (Bögen im Profil) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Flansch | implementiert (live 0.4.42) | nicht unterstützt (Fusion-Anfrage im Live-Test) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Mehrkant + Gehrung | eingeschränkt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Umschlag | implementiert | nicht unterstützt (Fusion-Anfrage) | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Doppelfalz | eingeschränkt (Live-Test-Fall) | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Versatz | implementiert | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |
| Abwicklung/DXF | implementiert | implementiert | eingeschränkt (gerolltes Blech) | eingeschränkt | nicht unterstützt (erkannt) |
| 3D-Detail starr | implementiert (Import live 0.4.42) | eingeschränkt | eingeschränkt | eingeschränkt | eingeschränkt |
| 3D-Detail anpassen | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt | nicht unterstützt |

## Bekannte Einschränkungen und Risiken
- Alles Neue ist ungeprüft gegen die echte Fusion-API; besonders `getCurvature`-Einheiten/Rückgabeform, `measureMinimumDistance` zwischen Flächen, Interferenz-API, Bögen im Basisflansch-Profil, Teilwinkel-Drehung.
- Gehrungsflächen-Suche ist eine Heuristik (Normale in Blechebene, gleicher Winkel zu beiden Kanten); im Bau nur Hinweis, im Live-Test PASS/FAIL. Selbstüberschneidung erkennt nur Fusions `isValid`/`isSolid`.
- Flansch/Umschlag an gekrümmten Kanten und auf Zylinder/Kegel sind nicht umgesetzt – die Live-Anfrage liefert erst die Fakten. Vorlagen «gekrümmt» bleiben dadurch blockiert.
- Keine Näherungsabwicklung (Priorität 3). Versatz an der versetzten Kante: früheres Live-Problem weiterhin offen.
- Doppelte Testklassen in `test_fusion_logik.py` (älter, eine Variante läuft nie) – unverändert.

## Nächste Schritte
1. Live-Test auf 0.4.49+Branch-Stand ausführen (erst nach einem Release über den Release-Knopf, den der Anwender freigibt).
2. Ergebnisse der Fusion-Anfragen an Bogen-/Zylinderkanten auswerten → Matrix (`core/unterstuetzung.py`) gezielt freigeben oder Alternativstrategie (z. B. Konturflansch) prüfen.
3. Gehrungsflächen-Heuristik anhand echter Live-Werte schärfen; danach im Bau als harte Prüfung verwenden.
4. Detail «an Krümmung anpassen» und Näherungsabwicklung mit Verzerrungsangabe nur nach eigener Fachentscheidung.

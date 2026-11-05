# Abschlussbericht Korrektur- und Erweiterungsauftrag «gekrümmte Flächen»

**Branch** `ccr-26e82854-8ygnzg` · **Ausgangs-Commit** `dc50a15` (wie im Auftrag) · **End-Commit:** dieser Bericht (siehe `git log`)
**Version unverändert 0.4.49 – kein Release, kein Merge, main nicht berührt.**

## Wichtigste Aussage vorab
In dieser Arbeitsumgebung läuft kein Fusion. **Echte Fusion-Live-Tests: 0 ausgeführt.** Alle Zahlen unten sind Unit-/Stub-Tests (Python-Attrappen). Damit ist
**Abschlusskriterium 4 (mindestens ein live getesteter Prototyp auf zylindrischer Geometrie) NICHT erfüllt**: Die Prototypen (Flansch, Umschlag, Versatz auf dem
gerollten Zylinderblech, Abwicklung/DXF) sind implementiert und als Live-Testschritte vorbereitet, im normalen Bau aber gesperrt, bis der Live-Test
bestanden ist. Ohne Release muss der Branch-Stand für den Live-Test von Hand in Fusion eingespielt werden (Testanleitung).

## Commits
| Commit | Phase | Kurzbeschreibung |
|---|---|---|
| `dd4bb65` | 1A | Matrix nach Flächenklasse UND Kantentyp; gerade Kante auf Zylinder ≠ eben; Sperre im Adapter vor jedem Feature; Einschränkungen im Bauplan |
| `dcb7e14` | 1B | Abwickelbarkeit konservativ («unsicher» statt «exakt»), Gauss-Stichprobe mit Ausfallzählung/Einheit, Prüfmodus «Fusion entscheidet» |
| `087b5e5` | 1C | Rückbau-Proben: nicht messbar = FAIL, anderer Fehler = FAIL, Konstruktionsobjekte; Teststufe/Aussagekraft im Bericht |
| `cd21365` | 1D | neu angelegte Blechregel wird zurückgebaut; Teststelle nach jedem Folgeschritt; Live-Rückbau ebener Flansch |
| `009f3c3` | 2 | Machbarkeitstabelle; Orientierung entlang der ganzen Kante |
| `c2537bb` | 3–5 | Prototypen gerolltes Zylinderblech, Flansch/Umschlag an gerader Mantelkante, Versatz als Bogenlänge; Kegel-/Torus-/Übergangs-Tests |
| `83f1359` | 6 | Detail-Erfassung mit Referenz/Krümmung/Anschlussradius; Modus A starr / B anpassen (Prototyp); Integration zurückgenommen bei Blechverlust |
| `50ca108` | 7/8 | Abwicklung + DXF des Zylinderblechs (Live); Testkörper 1–10 vollständig |
| `5c019ce` | 9 | Status (5 Stufen), Grenzen, Testanleitung, Handbuch |

## Geänderte Dateien
`core/unterstuetzung.py` (neu aufgebaut), `core/geometrie_referenz.py`, `core/operation_plan.py`, `core/livetest_messung.py`, `details/detail_validation.py`,
`geometry/fusion_adapter.py`, `commands/detail_generator_command.py`, `commands/export_command.py`, `diagnostics/live_test.py`, `diagnostics/live_test_gekruemmt.py`,
Tests (`fusion_stub`, `test_fusion_logik`, `test_gehrung_import`, `test_geometrie_referenz`, `test_grundblech_regel`, `test_livetest_messung`), Doku (Status,
Handbuch, Testanleitung, PDFs/HTML, dieser Bericht).

## Phasen
- **Vollständig (Code + Stub-Tests):** 1A, 1B, 1C, 1D, 2, 9.
- **Implementiert, Live-Nachweis offen:** 3 (Flansch Zylinder), 4 (Umschlag Zylinder), 5 (Versatz Zylinder), 6 (Modus B), 7 (Abwicklung Zylinder), 8 (Testkörper).
- **Technisch nicht möglich / bewusst nicht umgesetzt:** Flansch/Umschlag an Kreisbogenkanten (Fusion-API nur gerade Kanten; Live-Anfrage vorbereitet),
  alles auf Kegelblech (per API nicht erzeugbar), Versatz auf Kegel (Definition Normal/Radial/Tangential nötig), doppelt gekrümmt/Freiform (nicht exakt),
  Modus B auf Kegel/Freiform (keine definierte Verformungsrichtung), Mehrkant/Gehrung auf Zylinder (erst nach Einzelkanten-Prototyp), Näherungsabwicklung.

## Tests
| Stufe | Anzahl | Ergebnis |
|---|---|---|
| Unit-/Stub-Tests (`tests/run_all.py`) | 448 (Start 432) | 0 Fehler, 1 übersprungen (ezdxf fehlt) |
| Echte Fusion-Live-Tests | 0 | NICHT AUSGEFÜHRT – kein Fusion verfügbar; Fusion-Version daher keine |
| Fachlich im CAD geprüft | 0 | – |
Vorbereitete Live-Schritte (neu/erweitert): Rückbau (ebener Flansch, neue Komponente + neue Regel, Versatz, Gruppe, Import), Prototyp Flansch/Umschlag/Versatz/
Abwicklung am Zylinderblech (je Positiv-, Negativ-, Grenz- und Rückbaufall), Teilkegel-Grenzen, Torus, Übergang Zylinder–Kegel.

## Risiken und Einschränkungen
- **Konturflansch per API**: unklar dokumentiert (Preview); `blech_gerollt` probiert mehrere Aufrufformen. Klappt keine, sind alle Zylinder-Prototypen
  nicht prüfbar – der Bericht enthält dann Fusions Antworten.
- Neue, nie live gelaufene API-Aufrufe: `ConstructionAxes.setByCylinderOrConeOrTorus`, `ConstructionPlanes.setByTwoEdges`, Drehschnitt mit Winkel aus Bogenlänge,
  `CurveEvaluator.getParameterExtents/getPointAtParameter`, `addByCenterStartSweep`.
- Die Fusion-Attrappe liefert jetzt stabile Konstanten (für Flächentyp-Vergleiche) – ändert keine produktive Logik.
- Gehrungsflächen-Heuristik und Prüfung «entlang der Kante» sind Annahmen, bis Live-Werte vorliegen.

## Empfehlung für den nächsten Schritt
1. Branch-Stand in Fusion einspielen (von Hand oder per freigegebenem Release) und den Live-Test laufen lassen.
2. Bericht 97.002 auswerten: zuerst «gerolltes Blech» (ob der Konturflansch per API geht), dann Flansch/Umschlag/Versatz am Zylinder.
3. Nur bestandene Prototypen fachlich im CAD prüfen und danach in `core/unterstuetzung.py` von «prototyp» auf «eingeschraenkt» stellen.
4. Für den Kegel vorher fachlich festlegen, welcher Versatz gemeint ist (Normal-, Radial- oder Tangentialversatz).

# Bericht – Fehleranalyse und Stabilisierung ab 0.4.58 (Stand 0.4.59, 5. 11. 2026)

Grundlage: Live-Test 97.002 mit 0.4.57 (Fusion 2706.1.17). Ein Live-Lauf mit 0.4.58 lag bei der Bearbeitung **nicht** vor. Alle Änderungen sind mit
Unit-/Stub-Tests (Attrappen) geprüft, **nicht in Fusion**. Ursachen, die nur Fusion zeigen kann, sind ausdrücklich als «offen» bzw. «Annahme»
gekennzeichnet.

## Gefundene Ursachen

| Prio | Befund | Ursache | Sicherheit |
|---|---|---|---|
| alle | Details im Cloud-Bericht fehlten | Der Bericht stand VOR dem Protokoll und wurde von vorne auf 19 000 Zeichen gekürzt – bei langem Protokoll ging der Bericht verloren; die Notiz enthielt je Schritt nur die erste Zeile, ein langer Schritt (gerolltes Blech) füllte die 4000 Zeichen | sicher (Code) |
| 1 | «Rückbau gemeldet UNVOLLSTÄNDIG» bei unverändertem Zustand | Welches Objekt: **offen** (erst der nächste Live-Bericht nennt es). Belegt: `t_rueckbau` brach bei der ERSTEN fehlgeschlagenen Probe ab – unklar, ob die Root-Probe (1.0 mm) oder die Probe «neue Komponente, neue Regel 0.65 mm» betroffen war, die Gruppenprobe lief gar nicht. Wahrscheinlichste Ursache (Annahme): eine Blechregel, deren Löschung über `isValid` nicht belastbar nachweisbar ist (Zustand unverändert = Regel tatsächlich weg) | teils |
| 2 | Gehrungsflächen 0 gefunden, isMiteredCorners=None, +11 mm³ / +2 Flächen | Gesucht wurde nur unter `feature.faces`; ob Fusion die Gehrungsflächen dort liefert, ist offen. `isMiteredCorners` wurde am FEATURE gelesen (gibt Fusion nicht heraus), gesetzt wird es an der EINGABE. Ursache der 11 mm³: **offen** – Volumen/Flächenzahl beweisen keine Gehrung | teils |
| 3 | Gerolltes Blech (4 Tests) | `Path.create` auf eine native Skizzenkurve in einer aktivierten Unterkomponente → «getObjectPath» (vermutlich API-Verwendung: Proxy fehlte); `createContourFlangeInput` verlangt (Liste?, distance) – erstes Argument als `std::vector<…>`, keine der übergebenen Formen passte (Signatur unbekannt); `createBaseFlangeInput` nimmt nur Profile (für einen offenen Bogen ungeeignet) | teils |
| 4 | «Abstand Detail↔Fläche nicht messbar» | `measureMinimumDistance` bekam eine **Occurrence** – der MeasureManager misst BRep-Objekte; die Ausnahme wurde verschluckt. Betraf auch den Hinweis in «3D-Detail einsetzen» | sicher (Code), Wirkung nicht live geprüft |

## Geänderte Dateien und Änderungen

| Datei | Änderung |
|---|---|
| `core/livetest_bericht.py` | `cloud_notiz` (jeder auffällige Schritt bekommt Platz, mit Folgezeilen), `cloud_protokoll` (vollständige Details zuerst, Protokoll nur im Restplatz, dessen Ende) – Tabellengrenzen 4000 / 20 000 unverändert |
| `commands/livetest_command.py` | nutzt die beiden Funktionen |
| `diagnostics/live_test.py` | `proben_sammeln`: alle Rückbau-Proben laufen, Ergebnis gesammelt; Proben benannt (Root 1.0 mm / neue Komponente 0.65 mm); Zustand zusätzlich mit Konstruktionspunkten, Abwicklungen (unlesbar = nicht messbar) und Blechregel-NAMEN; `_Uebersprungen` (NICHT GETESTET, nie bestanden); Gehrung: ohne geometrisch nachgewiesene Gehrungsflächen höchstens Warnung, `isMiteredCorners` an Feature UND Eingabe gemeldet |
| `geometry/fusion_adapter.py` | `_loeschen`: Blechregeln über die Liste der Design-Regeln nachgewiesen (nicht über isValid), Meldung nennt Regelname und «wird noch verwendet»; `LETZTE_FLANSCH_EINGABE` (isMiteredCorners an der Eingabe zurückgelesen); `gehrung_eckspalt`: Rückfall auf ebene Körperflächen in Eckennähe (60 mm), einheitlich mm, Diagnose der eckennahen Flächen; `blech_gerollt`: Proxy-Kurve, Path-Formen, Signatur der API-Methoden im Bericht, klare Meldung «Ursache offen: API-Verwendung oder nicht unterstützt»; `_signatur`; `abstand_mm`: Occurrence → Körper-Proxys, Fläche → Proxy, Gründe statt verschluckter Ausnahme |
| `core/gehrung.py` | `diagnose()` – Abstand und Winkel der eckennahen ebenen Flächen |
| `diagnostics/live_test_gekruemmt.py` | neuer Schritt «Testkörper gerolltes Blech (Konturflansch)»; abhängige Prototyp-Tests NICHT GETESTET mit Verweis, wenn der Testkörper fehlt; leere Komponente wird bei Fehlschlag entfernt; «Abstand nicht messbar» = FEHLER («NICHT verifiziert») statt «PASS mit Hinweis» |
| `tests/test_rueckbau_0459.py` | 14 neue Tests (Regel-Nachweis, Proben sammeln, Cloud-Bericht, Zustand, Gehrungsdiagnose, Fixture-Übersprung, Signatur, Abstandsmessung) |

## Tests

- Unit-/Stub-Tests: **529 bestanden, 0 fehlgeschlagen, 1 übersprungen** (ezdxf fehlt) – ohne Fusion.
- Fusion-Live-Tests mit 0.4.59: **0** (noch nicht gelaufen). Fertigungsprüfung: 0.

## In Fusion noch durchzuführen

1. Live-Test mit «Ergebnis senden» – liefert erstmals den vollständigen Bericht. Daraus: Restobjekt des Rückbaus (P1), Diagnose der Gehrungsecke
   und isMiteredCorners an der Eingabe (P2), API-Signaturen und Antworten zum Konturflansch (P3), Abstandsmessung (P4).
2. Abnahme P1: «Rückbau bei provoziertem Fehler» und «KANTENWERKZEUG eigen: Rückbau» mehrfach hintereinander grün, Zustand inkl. Regelnamen und
   Abwicklungen gleich; zusätzlich Browser ansehen.
3. Danach je Fehlergruppe die eigentliche Korrektur (sie hängt vom Bericht ab).

## Einschränkungen (unverändert offen)

- P1: Das konkrete Restobjekt ist nicht bekannt; die Regel-Nachweis-Änderung behebt nur den wahrscheinlichsten Fall.
- P2: Die Ursache der 11 mm³ ist nicht geklärt; die Gehrung gilt erst als verifiziert, wenn die Gehrungsflächen gefunden und der Spalt gemessen ist.
- P3: Das gerollte Blech per Konturflansch funktioniert weiterhin nicht; die vier Prototyp-Tests werden ohne Testkörper als NICHT GETESTET gemeldet.
  Ob «nicht unterstützt» oder «falsch aufgerufen», entscheidet erst die Signatur aus Fusion.
- P4: Ob der MeasureManager die Proxys annimmt, ist nicht live geprüft.

## Auswirkungen auf Bestehendes

- Kantenwerkzeug und bestehende Blechmodelle: keine Änderung an der Geometrie-Erzeugung. Geändert ist das Löschen von Blechregeln im Rückbau
  (strenger Nachweis; eine Regel, die nachweislich noch da ist, wird weiterhin als Fehler gemeldet) und die Gehrungsprüfung im gemeinsamen Flansch
  (nur Hinweistext, verwirft kein Ergebnis).
- «3D-Detail einsetzen»: der Abstandshinweis kann jetzt erscheinen (vorher nie messbar).
- Live-Test: andere Bewertung – fehlende Abstandsmessung = Fehler, fehlender Testkörper = NICHT GETESTET, Gehrung ohne Flächennachweis = Warnung.
  Die Zahlen sind deshalb nicht direkt mit 0.4.57 vergleichbar.

# Abschlussbericht XXL-Auftrag «Einheitliches Spengler-Kantenwerkzeug» (v2 inkl. Review-Ergänzung)

**Branch** `ccr-26e82854-8ygnzg` · **Ausgangs-HEAD** `46ba14e` (geprüft: sauber, 448 Stub-Tests grün) · **End-HEAD:** dieser Bericht (`git log`) ·
**Version 0.4.49 unverändert – kein Release, kein Merge, main unberührt.**

## Wichtigste Aussage vorab
**Echte Fusion-Live-Tests: 0 ausgeführt** (kein Fusion in der Arbeitsumgebung). Alles ist höchstens «implementiert + Stub-getestet»; nichts ist
Fusion-live-getestet oder fachlich/fertigungstechnisch verifiziert. Die Abnahmekriterien 11 (eigene Abwicklung durch Rückvergleich validiert) und 14
(Live-Tests mit Fusion-Version) sind damit **nicht erfüllt**; das Testpaket dafür liegt bereit.

## Commits
| Commit | Inhalt |
|---|---|
| `b592042` | Matrix nativ / eigene Geometrie / Klassen a–e, Kanten Ellipse/Kette; mathematische Machbarkeitsanalyse, Wahl Prototyp 2; Statustabellen aus dem Code |
| `fc70900` | Profil-Engine (Querschnitt, Selbstschnitt, eigene Abwicklung, Rückvergleich 2D/3D) |
| `a46c526` | Adapter: Profilteil, Profil an gerader Kante, eigene Abwicklung; Vor-/Nachprüfungen, Rückbau |
| `b8eeb53` | «Kanten bearbeiten» erweitert: Bauweise, Prototypen-Schalter, Analyse im Bauplan, atomar über alle Kanten; Abwicklung & DXF mit eigener Abwicklung |
| `9101875` | Live-Testpaket eigene Geometrie |
| `f2e9dc0` | Handbuch, Testanleitung, Statusdokument |

## Ein Werkzeug
Kein neuer Befehl: das bestehende **«Kanten bearbeiten»** (ID, Vorlagen, Kurzschrift, Vorschau, Bauplan, Rückbau unverändert) ist das Kantenwerkzeug.
Erreichbar in EINER Oberfläche: Aufkantung, Einfachfalz (Umschlag), Doppelfalz (Folge), Gehrung (nativ, mehrere Kanten), Versatz (nativ), Ketten über die
Vorlage. Neu: **Bauweise «Eigene Geometrie»** – der ganze Querschnitt als ein Profil entlang der geraden Kante, inkl. Aufkantung + Falz/Doppelfalz in einem
Arbeitsgang. «Abwicklung & DXF» bleibt separat.

## Mathematische Verfahren
- Abwickelbarkeit über die Gausssche Krümmung jeder entstehenden Fläche (`core/machbarkeit_gekruemmt.py`); Biegezone an einer Kreiskante = Torus,
  K = cos θ / (r (R + r cos θ)) ≠ 0 → nicht exakt (Toleranz |K| < 1e-9 1/mm² trennt Rundung von echter Krümmung).
- Prismatisches Profil: Querschnitt aus Linien/Kreisbögen (Offset ± t/2 der Blechmitte, `core/bend_geometry` wiederverwendet), Extrusion entlang einer
  geraden Kante, deren Flächennormale längs der Kante konstant ist (Mantellinie: Tangentialebene konstant) – geprüft an 7 Punkten, Grenze 0.05°.
- Abwicklung: L = Σ gerade Schenkel + Σ (ri + k·t)·|α|; Rückvergleich: V₃D = t·W·Mittellinie exakt, Modellabweichung ΔV = t·W·Σ(k − ½)·t·|α|; Radien 3D gegen
  ri und ri + t je Biegung; DXF-Gegenprobe der Masse auf 0.01 mm.
- Selbstschnitt: Polygonisierung des Querschnitts (3°) und Kreuzungstest nicht benachbarter Segmente.

## Support-Matrix und Abwicklungsstatus
Vollständig im Statusdokument (automatisch aus `core/unterstuetzung.py`). Kurz: eben/gerade – nativ und eigen (b); Zylinder/Kegel gerade Mantelkante – eigen
Prototyp (b, gesperrt); Kreisbogen/Kreis auf eben/Zylinder/Kegel – Klasse d (Torus); Ellipse/Spline – d; Kette – c; doppelt gekrümmt/Freiform – d;
unbekannt – e. Abwicklung: eigene exakte Abwicklung nur für Profilteile der eigenen Geometrie; sonst Fusion-Abwicklung mit den bisherigen Prüfungen.

## Tests
| Stufe | Ergebnis |
|---|---|
| Unit-/Stub-Tests | 471 (Start 448), 0 Fehler, 1 übersprungen (ezdxf) |
| Fusion-Live | 0 ausgeführt – Testpaket vorbereitet (Schritte «KANTENWERKZEUG eigen: …»), Fusion-Version: keine |
| fachlich im CAD | 0 |

## Offene Punkte, Risiken
- Alle Fusion-Aufrufe der eigenen Geometrie sind ungetestet: `setByDistanceOnPath` (Ebene an der Kante), Skizze mit Dreipunkt-Bögen, Profilwahl über die
  Fläche, Join-Extrusion, Attribute am Körper. Möglicher Fehlerpunkt: die Richtung der Skizzenebene (abgefangen über Volumenprüfung beider Richtungen).
- Gehrung zwischen eigenen Profilen, Versatz in der Profilkette, Kegelgrundblech, konstruktive Varianten für Bogenkanten (Segmentierung/Freistellung,
  Zargenstreifen) – nicht umgesetzt.
- Eigene Geometrie ist nicht voll parametrisch (unbemasste Skizze + Extrusion).
- Der Prototypen-Schalter ist eine Bedienentscheidung; er darf erst nach bestandenem Live-Test benutzt werden.
- Masse der eigenen Geometrie auf Blechmitte bis virtuelle Kante – unterscheidet sich vom Standard-Höhenbezug der nativen Fusion-Funktion.

## Testpaket für den Anwender
1. Branch `ccr-26e82854-8ygnzg` (dieser Commit) einspielen: Ordner `SpenglerDigital` sichern und ersetzen, Fusion neu starten (oder Release freigeben).
2. SPENGLER → Verwaltung → Live-Test, «Ergebnis senden» an, starten; 3–5 Minuten nichts anklicken.
3. PASS/FAIL je Schritt im Bericht 97.002 bzw. `livetest.txt`; Kriterien in der Testanleitung (Abschnitt Kantenwerkzeug).
4. Zusätzlich von Hand: «Kanten bearbeiten», Bauweise «Eigene Geometrie», gerade Kante eines Blechs, Vorlage mit Aufkantung + Umschlag → Bauplan und
   Ergebnis fotografieren; danach «Abwicklung & DXF» auf ein Profilteil.

## Empfehlung
Zuerst den Live-Test laufen lassen. Bestehen die Schritte «KANTENWERKZEUG eigen» und Prototyp 2, die eigene Geometrie auf ebenen Kanten fachlich im CAD prüfen
und dann die Gehrung zwischen eigenen Profilen (Schnitt an der Winkelhalbierenden) als nächsten Baustein angehen.

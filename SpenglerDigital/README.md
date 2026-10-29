# Spengler Digital CAD – Add-in für Autodesk Fusion (Version 0.4.2)

Eigene Kantenvorlagen (Flansch-/Umschlagfolgen) und eigene 3D-Detailvorlagen auf Blechkanten anwenden,
Rundbleche ohne Einschnitte beurteilen und modellieren, Abwicklung/DXF, Werkstattblatt,
Material- und Zuschnittberechnung (Rechnung aus der Spengler-Digital-App).

**Wichtig:** Dieses Add-in wurde automatisch getestet, aber noch **nicht in Fusion selbst**.
Bitte zuerst die Testanleitung `docs/Testanleitung.pdf` durchgehen.

## Installation (Windows und macOS)

1. ZIP `SpenglerDigitalCAD_0.4.2.zip` entpacken. Es entsteht der Ordner `SpenglerDigital`.
2. Den Ordner an einen festen Ort kopieren, z. B.
   - Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SpenglerDigital`
   - macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/SpenglerDigital`
   (jeder andere Ort geht auch, dann in Schritt 3 «verknüpfen»).
3. Fusion → **Dienstprogramme → Add-Ins → Skripte und Add-Ins** (Shift+S) → Register **Add-Ins**.
   Steht «SpenglerDigital» nicht in der Liste: **+** → «Script oder Add-In von meinem Gerät» → Ordner wählen.
4. «SpenglerDigital» wählen → **Ausführen**, Häkchen **Beim Start ausführen** setzen.
5. Im Arbeitsbereich **Konstruktion** erscheint das Register **SPENGLER** mit den Gruppen
   «Kanten & Details», «Fertigung» und «Verwaltung».

Ein früher installierter Prototyp 0.1 hat dieselbe Add-in-ID und wird ersetzt (vorher stoppen).

## Erster Start

- Die Vorlagenbibliothek und die Materialbibliothek sind **leer**. Es gibt bewusst keine mitgelieferten Profile.
- Zuerst **Verwaltung → Vorlagen & Einstellungen → Materialien**: eigenes Materialprofil anlegen
  (Dicke Pflicht; Innenradius/K-Faktor/Dichte/Tafeln/Rollen optional).
- Dann **Kantenvorlagen → Neue Vorlage erstellen**.
- **Hilfe → Selbsttest in neuem Dokument** prüft die Fusion-API-Wege und schreibt das Protokoll.

## Benutzerdaten – Updates sicher

Vorlagen, 3D-Detailgeometrie, Materialien, Einstellungen, Sicherungen und Protokoll liegen **nicht** im
Add-in-Ordner, sondern hier:

- Windows: `%APPDATA%\SpenglerDigitalCAD`
- macOS: `~/Library/Application Support/SpenglerDigitalCAD`

**Update:** Add-in stoppen, Ordner `SpenglerDigital` durch die neue Version ersetzen, Add-in starten.
Wichtig: Danach muss `SpenglerDigital.py` direkt im Ordner liegen, den Fusion verwendet (kein Ordner im Ordner, nicht in einen
neuen Ordner entpacken). Kontrolle: **Hilfe → Fusion-Fähigkeiten prüfen** zeigt Versionsnummer und Ladeordner.
Beim Start prüft das Add-in das Datenformat; vor jeder Umstellung entsteht automatisch eine Sicherung in
`…\SpenglerDigitalCAD\sicherungen`. Schlägt eine Umstellung fehl, bleiben die Daten unverändert.

**Sicherung/Wiederherstellung:** Vorlagen & Einstellungen → Register **Sicherung**.

**Spengler-Digital-App (ab 0.4.0):** Vorlagen & Einstellungen → Register **Konto** → mit dem App-Konto anmelden.
Dann werden Vorlagen, 3D-Details und Materialprofile mit allen PCs der Firma abgeglichen, und Updates kommen
nach Rückfrage automatisch (nur geänderte Dateien, vorher Sicherung). Die erste Installation je PC bleibt von Hand.
Datenbank-Grundlage: `supabase/v_cad_addin_grundlagen.sql`; Updates veröffentlichen: `fusion/werkzeug/release_sql.py`.

## Ordner

| Ordner | Inhalt |
|---|---|
| `SpenglerDigital.py`, `.manifest` | Einstiegspunkt für Fusion |
| `spengler_cad/core` | Kurzschrift, Ausdrücke, Biegerechnung, Modelle, Prüfungen, Bauplan |
| `spengler_cad/geometry` | Geometrieadapter – einzige Stelle mit Fusion-Geometrieaufrufen |
| `spengler_cad/details` | 3D-Detailvorlagen: Prüfung, Koordinatensysteme |
| `spengler_cad/forming` | Rundbleche, Stauchen/Strecken, Kegel |
| `spengler_cad/manufacturing` | Zuschnitt (Port aus der App), Material, DXF, Werkstattblatt |
| `spengler_cad/storage` | Pfade, Vorlagen, Materialien, Einstellungen, Sicherung, Migration |
| `spengler_cad/commands`, `ui`, `palette` | Fusion-Befehle, Hilfetexte, HTML-Palette |
| `templates/system` | Systemvorlagen – produktiv leer |
| `assets` | Logo und Symbole |
| `docs` | Benutzerhandbuch (PDF, Markdown), Austauschformat |
| `tests` | automatische Tests, Referenzfälle, Live-Testliste |

## Tests ohne Fusion

```
python3 tests/run_all.py
```
Python 3.9 oder neuer, keine Zusatzpakete. Der Browsertest der Palette läuft nur, wenn Node und Playwright vorhanden sind.

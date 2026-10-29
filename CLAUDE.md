# Spengler Digital CAD – Fusion-Add-in (Python). Kurz und auf Deutsch antworten, tokensparend arbeiten.

- Paket `SpenglerDigital/spengler_cad/` (core, storage, manufacturing, forming, details, geometry, commands, ui);
  Fusion-Aufrufe NUR in `geometry/fusion_adapter.py`. Jede neue Fusion-Funktion als «nicht live geprüft» kennzeichnen.
- Keine mitgelieferten Vorlagen/Materialien; Benutzerdaten in %APPDATA%\SpenglerDigitalCAD, nie ändern ohne Freigabe.
- Prüfen: `python3 SpenglerDigital/tests/run_all.py | tail -2`; Doku-PDF/HTML: `python3 SpenglerDigital/docs/handbuch_pdf.py` (nur wenn Doku geändert).
- Nie ganz lesen: `docs/*.md`, `fusion_adapter.py`, `palette/vorlagen.js` – grep + Ausschnitt.
- Stand/Offenes: `SpenglerDigital/docs/ANFORDERUNGEN_STATUS.md` (nur gezielt lesen).
- Updates: Version in `spengler_cad/__init__.py` + `SpenglerDigital.manifest`; `python3 werkzeug/release_sql.py release <v> "<Text>"`
  → SQL per Supabase ausführen → `… bestaetigen <v>`. ZIP-Grundinstallation = `releases/basis.json`.
- Cloud: Supabase der Spengler-Digital-App (Repo Spengler---Digital-V1 nur bei Bedarf anhängen, z. B. Zuschnitt `js/29`).
- Jede Antwort endet mit Statusblock (✅ Fertig / ⏳ Läuft / ❓ Von dir). Kein PR ohne Auftrag.

# Spengler Digital CAD – Fusion-Add-in

Fusion-360-Add-in (Python) für Spenglerarbeiten, verbunden mit der Web-App «Spengler-Digital» (Supabase).

## Welcher Stand ist aktuell?

- **Aktiver Entwicklungsstand: Branch `ccr-26e82854-8ygnzg`.** Releases (Release-Knopf, `release.yml`) und Updates kommen von dort.
- **`main` ist veraltet** (Stand 0.4.7) und wird bewusst nicht angefasst. Ein Pull Request nach `main` erfolgt erst auf ausdrücklichen Auftrag nach der Stabilisierung.

## Aufbau

- `SpenglerDigital/spengler_cad/` – Paket (core, storage, manufacturing, forming, details, geometry, commands, ui). Fusion-Aufrufe nur in `geometry/fusion_adapter.py`.
- `SpenglerDigital/tests/` – Tests ohne Fusion (`python3 SpenglerDigital/tests/run_all.py`). Stub-Tests sind **keine** echten Fusion-Live-Tests.
- Live-Test in Fusion: Befehl «Live-Test» im Add-in; der Bericht geht an die eigene Firma (`cad_testergebnisse`).
- Doku: `SpenglerDigital/docs/` (Benutzerhandbuch, Testanleitung, `ANFORDERUNGEN_STATUS.md`).

## Daten

Benutzerdaten liegen unter `%APPDATA%\SpenglerDigitalCAD`. Es werden keine Vorlagen oder Materialien mitgeliefert.

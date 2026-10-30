# Release-Knopf

Neue Version veröffentlichen, ohne lokale Werkzeuge: GitHub → **Actions** → **Release veröffentlichen** → **Run workflow** →
Version (z. B. `0.4.6`) und Kurztext eintragen → **Run workflow**.

Der Ablauf (`werkzeug/veroeffentlichen.py`) bricht bei jedem Fehler ab und legt den Release-Eintrag – ab dem jedes Add-in das Update
sieht – erst ganz zuletzt an: Version prüfen → Tests → Version setzen → geänderte Dateien einzeln hochladen → Prüfsummen in der
Datenbank kontrollieren → Release-Eintrag → `releases/hochgeladen.json` nachführen. Danach committet der Knopf Version, Testplan und
`hochgeladen.json` in den Zweig, auf dem er lief.

Einmalig nötig: Supabase-Zugriffstoken als GitHub-Geheimnis `SUPABASE_ACCESS_TOKEN` (Settings → Secrets and variables → Actions).
Ein Token gilt für das ganze Supabase-Konto – nur im GitHub-Geheimnis ablegen, nie ins Repository.

Von Hand (ohne GitHub): `SUPABASE_ACCESS_TOKEN=… python3 werkzeug/veroeffentlichen.py 0.4.6 "Text"`.

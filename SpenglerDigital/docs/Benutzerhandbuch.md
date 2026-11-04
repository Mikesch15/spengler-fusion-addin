# Spengler Digital CAD – Bedienungsanleitung

Add-in für Autodesk Fusion · Version 0.4.2 · Stand 29.10.2026

> **Prüfstand dieser Version:** Die Rechenteile (Kurzschrift, Vorlagen, Bauplan, Zuschnitt, Material, Umformung, Sicherung, Migration) sind automatisch getestet. Die Bedienung in Fusion selbst ist **noch nicht in Fusion getestet**. Funktionen, die davon abhängen, sind mit **[nicht in Fusion geprüft]** markiert.

## 1. Installation und erster Start

1. ZIP-Datei entpacken; es entsteht der Ordner `SpenglerDigital`.
2. Ordner z. B. nach `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\` (Windows) bzw. `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` (macOS) kopieren.
3. In Fusion **Dienstprogramme → Add-Ins → Skripte und Add-Ins** (Shift+S), Register **Add-Ins**. Fehlt «SpenglerDigital» in der Liste: **+** und den Ordner wählen.
4. **Ausführen** und **Beim Start ausführen** ankreuzen.
5. Im Arbeitsbereich **Konstruktion** erscheint das Register **SPENGLER**.

Beim ersten Start legt das Add-in den Benutzerdatenordner an (siehe Kapitel 14). Danach empfiehlt sich **Hilfe → Selbsttest in neuem Dokument**: Er prüft in einem neuen, leeren Dokument die Fusion-Funktionen, die das Add-in benutzt, und schreibt das Ergebnis ins Protokoll.

## 2. Werkzeugleiste und Befehle

Register **SPENGLER**, vier Gruppen **in der Reihenfolge der Arbeit** (jeder Befehl hat ein eigenes Symbol):

| Gruppe | Befehl | Zweck |
|---|---|---|
| 1 · Auftrag | **Start / Übersicht** | Zeigt, was eingerichtet ist (Konto, Material, Vorlagen, aktiver Auftrag, Projekt in der App, Dokument im Auftragsordner) und schlägt den **nächsten Schritt** vor – mit Sprung dorthin |
| | Neuer Auftrag | Auftragsordner (Jahr, Unterordner) in Fusion und auf Wunsch das Projekt in der App anlegen |
| | Auftrag wählen | Vorhandenen Auftrag aktiv setzen, Status, Dokument im Auftragsordner speichern |
| | Aufträge abgleichen | Projekte der App und Auftragsordner in Fusion gegeneinander abgleichen |
| 2 · Konstruieren | Kanten bearbeiten | Zuerst den Blechkörper wählen, dann Kantenvorlage auf seine Kanten anwenden |
| | 3D-Detail erfassen / anwenden | Eigenes 3D-Blechdetail als Vorlage speichern bzw. ansetzen |
| | Rundblech / Umformung | Rundbleche, Kragen, Kegel: Beurteilung, Drehkörper, Zuschnitt |
| | Vorlage aus Profil lernen / aus App-Massaufnahme | Kantenvorlage aus einem vorhandenen Profil bzw. einer Massaufnahme der App |
| 3 · Fertigung | Abwicklung & DXF | Fusion-Abwicklung, DXF-Export, Werkstattblatt |
| | Stückliste & Zuschnitt | Teilenummern, Stückliste, Abkantliste, Kalkulation, Zuschnittplan, Mappe, Teile und Dateien an die App |
| Verwaltung | Vorlagen & Einstellungen | Palette: Vorlagen, 3D-Details, Materialien, Einstellungen, Reste, Berichte, Sicherung, Konto |
| | Hilfe | Hilfethemen, diese Anleitung, Fähigkeitsprüfung, Selbsttest |

**Fehlbedienung vermeiden:** Befehle, die für einen Auftrag arbeiten (**Kanten bearbeiten, Abwicklung & DXF, Stückliste & Zuschnitt, Rundblech**), öffnen sich nicht ohne **aktiven Auftrag**. Stattdessen erklärt Fusion, was fehlt, und bietet «Jetzt dorthin wechseln?» an (Auftrag wählen bzw. Vorlagen & Einstellungen). Dasselbe gilt für fehlendes Materialprofil oder fehlende Kantenvorlage. Wer das nicht will, schaltet es unter Einstellungen → Aufträge → «Sicherheit» ab. Hilfe, Einstellungen und alle Auftragsbefehle sind immer frei.

Fehlt in Ihrer Fusion-Version die API für eigene Register, erscheinen die Befehle in den Panels **Blech → Erstellen** bzw. **Volumenkörper → Erstellen**.

## 3. Leere Vorlagenbibliothek

Die Vorlagenbibliothek ist beim ersten Start **leer**. Es werden bewusst keine Ortgänge, Traufen, Falze, Säume oder Standardmasse mitgeliefert – Sie legen jede Vorlage passend zu Ihrer Werkstatt selbst an. Auch die Materialbibliothek ist leer; das Add-in erfindet keine Radien, K-Faktoren oder Dichten.

Bibliotheksebenen:

- **Benutzerbibliothek** – Ihre Vorlagen im Benutzerdatenordner.
- **Projektbibliothek** (optional) – ein Ordner, der unter *Einstellungen → Projektbibliothek* eingetragen ist, z. B. auf einem Netzlaufwerk.
- **Systemvorlagen** – im Add-in-Ordner, produktiv leer und schreibgeschützt.

## 4. Eigene Kanten- und Operationsvorlagen

*Vorlagen & Einstellungen → Kantenvorlagen → Neue Vorlage erstellen.*

Eine Kantenvorlage besteht aus:

- **Name, Beschreibung, Kategorie, Favorit**
- **Parametern** – Name (z. B. `H`), Bezeichnung, Einheit (mm, deg oder ohne), Standardwert, Minimum, Maximum, variabel ja/nein
- **Operationen** – Folge ab der Kante: Flansch (Winkel, Länge, optional Radius) oder Umschlag (±180°, Länge)
- **Anschluss und Grenzen** (Expertenmodus) – Kantentyp, Dickenbereich, Mindestkantenlänge, Einschnitte ausdrücklich erlauben

**Schritt für Schritt:** Im Abschnitt **Schritte** der Vorlage legen Sie mit **+ Flansch** und **+ Umschlag** jeden Schritt einzeln an und tragen Winkel, Länge und optional den Radius in die Tabelle ein (Zahlen, Parameternamen wie `H` oder Ausdrücke). Winkel + = zur Sichtseite, − = nach hinten. Die **Vorschau** darüber zeichnet nach jeder Änderung den Querschnitt neu; Pfeile verschieben Schritte, ✕ löscht sie. Die Kurzschrift bleibt als Alternative erhalten und folgt der Tabelle.

Die schnellste Eingabe ist die **Kurzschrift**:

| Eingabe | Bedeutung |
|---|---|
| `90 25` | 90° zur Sichtseite abkanten, Schenkel 25 mm |
| `-90 30` | 90° nach hinten |
| `U+ 7` / `U- 7` | Umschlag 180° zur Sichtseite / nach hinten, 7 mm |
| `90r5 20` | Innenradius 5 mm für diese Biegung |
| `90 H U+ u+4*t` | Parameter `H`, `u`; `t` = Blechdicke, `ri` = Innenradius, `k` = K-Faktor aus dem Materialprofil |
| `{w} 20` | Winkel als Ausdruck |

**Mass und Lage (Schrittetabelle):** *Mass* legt fest, worauf die Schenkellänge zielt: aussen, innen oder tangential (Fusion: Höhenbezug). *Lage* sagt, wo der Flansch an der Bestandsfläche ansetzt: **benachbart** (an der Kante, Fusion «StartEdge»), innen, aussen oder tangential (Fusion: Biegeposition). «Standard» lässt Fusions Voreinstellung. Beim **Flansch** wird die gewählte Lage genau so verlangt (lehnt Fusion sie ab, kommt eine Meldung). Beim **Umschlag** sind nach Fusion nur benachbart und tangential zulässig; «innen»/«aussen» werden versucht, bei Ablehnung geht das Add-in automatisch auf benachbart/tangential weiter (steht im Protokoll). Ein freier «Versatz ±» ist in der Fusion-Flansch-API nicht vorgesehen. Vorschau und Abwicklung rechnen immer theoretisch mit der Blechmitte. **Versatz (mm):** verschiebt die Biegung von der Startkante weg: **+ nach innen** (das Blech wird um diesen Betrag zurückgeschnitten, es entsteht «Luft»), **− nach aussen** (das Blech wird um diesen Betrag verlängert). Beispiel: zwei aneinanderliegende Bleche je mit 90° 25 mm und Versatz 5 → 10 mm Abstand zwischen den Flanschen. Fusions Flansch-Werkzeug kann die Biegung nicht frei verschieben; das Add-in schneidet bzw. verlängert deshalb das Blech vorher mit einem Streifen (Skizze «Versatz …» und Extrusion in der Zeitleiste). Nur an geraden Kanten. Zusammenstossende Kanten (Gehrung): alle Streifen entstehen in einer Skizze und einer Extrusion, beim Verlängern wird die Ecke aufgefüllt, danach baut Fusion den gemeinsamen Flansch mit Gehrung an den versetzten Kanten (gilt für den Versatz im ersten Schritt). Vorschau und Abwicklung rechnen ohne Versatz. Nicht in Fusion geprüft. **Biegeradius:** Ohne eigenen Radius in der Vorlage gilt der Innenradius des Materialprofils (Flansch); der Umschlag ist ein Saum (zuerst «offen» mit Spalt = Blechdicke, wie im Fusion-Dialog); der **Radius** der Vorlage ist beim Umschlag der **Abstand** zwischen den Lagen (wie «Abstand» im Fusion-Dialog Falz, Typ Offen); ohne Angabe gilt der Innenradius des Materialprofils, sonst die Blechdicke. Beim Umschlag probiert das Add-in mehrere Lagen/Richtungen durch und protokolliert die Versuche. Nicht in Fusion geprüft.

Nach «übernehmen» werden neue Parameternamen automatisch als Parameter angelegt; Werte und Bereiche tragen Sie selbst ein. Unter der Kurzschrift zeigt die **Vorschau** den Querschnitt mit den Standardwerten: das bestehende Blech gestrichelt, die Kante grün, Schenkelmasse und Biegungen B1, B2 … Sie aktualisiert sich beim Tippen. Ist unter «Prüfen» ein Testmaterial gewählt (sonst das Standardmaterial), zeichnet sie mit dessen Dicke und Innenradius; ohne Material als Skizze mit 1 mm Dicke. Fehlt einem Parameter der Standardwert, steht statt des Bildes der Grund. Dasselbe Bild erscheint verkleinert in der Vorlagenliste. **Prüfen & Trockenlauf** zeigt Fehler, die Folge mit den Standardwerten und – wenn Innenradius und K-Faktor im Material stehen – die theoretische Abwicklungszugabe.

Speichern: Jede inhaltliche Änderung erhöht die **Vorlagenversion**; frühere Versionen bleiben erhalten (*Versionen*). **Duplizieren** erzeugt eine unabhängige Kopie, **Umbenennen** ändert nur den Namen, **Löschen** verschiebt die Vorlage nach Bestätigung in den Papierkorb (wiederherstellbar unter *Sicherung*).

## 5. Eigene 3D-Vorlagen und Anschlussreferenzen [nicht in Fusion geprüft]

Für Details, die sich nicht als Flanschfolge beschreiben lassen (z. B. Ihren eigenen Doppelfalzabschluss mit Unter-/Oberfalz, Endlasche und Freistellungen), gibt es einen geführten Erfassungsablauf:

1. Detail in einer **eigenen Komponente** modellieren.
2. Masse, die später veränderbar sein sollen, als **Fusion-Benutzerparameter** anlegen (Ändern → Parameter ändern) und in den Features verwenden.
3. **3D-Detail erfassen**: Komponente wählen, die **Anschlusskante** (gerade Kante, an der das Detail später ansetzt) und optional eine **Bezugsfläche** (bestimmt die Z-Richtung). Name, Kategorie, Beschreibung eingeben und die **variablen Parameter** ankreuzen.

Gespeichert werden die Komponente als Fusion-Archiv (.f3d), das lokale Koordinatensystem der Anschlusskante (Ursprung = Kantenanfang, X = Kantenrichtung, Z = Normale der Bezugsfläche), die Kantenlänge, die Blechdicke aus der Blechregel, die variablen und festen Parameter und die Namen der Zeitachsen-Features.

**Grenzen:** Beliebige Körper werden nicht automatisch parametrisiert. Veränderbar ist nur, was Sie als Benutzerparameter angelegt und angekreuzt haben.

## 6. Variable Parameter

- **Variable Parameter** erscheinen beim Anwenden als Eingabefeld mit Einheit; Bereichsgrenzen werden geprüft.
- **Feste Parameter** behalten den gespeicherten Wert (in der Parameterliste das Häkchen «variabel» entfernen).
- **Materialwerte** `t`, `ri`, `k` kommen immer aus dem gewählten Materialprofil. Fehlt ein benötigter Wert, wird nicht gebaut.

## 7. Vorlagen auf Kanten und Falzenden anwenden [nicht in Fusion geprüft]

**Zuerst der Blechkörper:** Im Befehl «Kanten bearbeiten» wählst du zuerst den **Blechkörper**, dann seine Kanten. Das Kantenfeld ist erst nach der Körperwahl aktiv; Kanten eines anderen Körpers werden aus der Auswahl genommen bzw. abgelehnt. So gelten die Kanten eindeutig für ein Blech, auch wenn mehrere Bleche nebeneinander liegen. Nicht in Fusion geprüft.

**Grundblech (Blech aus Massaufnahme, Bauteil erstellen):** Das Blech entsteht in einer neuen Komponente mit **genau der Dicke des Materials**: Das Add-in nimmt eine Blechregel des Dokuments mit dieser Dicke oder legt eine Kopie «Spengler 0.70 mm» an (Bibliotheks- und Standardregeln bleiben unverändert) und setzt sie vor dem Bauen. Danach wird geprüft, dass der Körper in der neuen Komponente liegt und die gemessene Dicke stimmt – sonst wird abgebrochen und alles zurückgebaut. Eine neu angelegte Blechregel bleibt im Dokument und wird beim nächsten Mal wiederverwendet.

**Gekrümmte Geometrie (Stand 5. 11. 2026, nicht live getestet):** Versatz nur an Kanten **ebener** Blechflächen (auf Zylinder/Kegel wird er mit Begründung abgelehnt; im Bericht steht, was der Versatz bedeutet: Biegelinie in der Blechebene, lokale Richtung). Abwicklung/DXF nur für exakt abwickelbare Körper (eben, Zylinder, Kegel) – Kugel-, Torus- und Freiformflächen werden erkannt und abgelehnt, es wird nie eine verzerrte Abwicklung als exakt ausgegeben. Flansch und Umschlag an gekrümmten Kanten unterstützt das Add-in (noch) nicht; der Live-Test fragt Fusion dazu an.

**Kanten bearbeiten:** Eine oder mehrere Aussenkanten eines Blechkörpers wählen (nur gerade Kanten – Kreis/Bogen werden seit 0.4.49 vor dem Bauen abgelehnt, weil Fusions Flansch- und Saum-Schnittstelle nur gerade Kanten beschreibt), Vorlage und Material wählen, Werte eingeben. Der **Bauplan** im Dialog zeigt die Folge, die geeigneten Kanten und alle Warnungen. Ungeeignete Kanten (Ellipse/Spline, kein Blechkörper, Biegezone, falsche Dicke, zu kurz) werden mit Grund genannt; dann ist OK gesperrt. Mit **Vorschau** zeigt Fusion das Ergebnis vor der Bestätigung.

Ablauf beim OK: Kante neu auflösen → Flansch/Umschlag Schritt für Schritt → nach jedem Schritt die neue Aussenkante bestimmen (gerade, parallel, gleich lang, in plausibler Entfernung; bei Mehrdeutigkeit Abbruch statt Raten) → Körper prüfen. Schlägt ein Schritt fehl, werden die bereits erzeugten Schritte dieser Kante wieder entfernt. Der ganze Befehl ist ein Rückgängig-Schritt (Strg+Z). Jedes erzeugte Feature trägt die Vorlagen-ID und -Version als Attribut; spätere Vorlagenänderungen verändern bestehende Bauteile nicht.

**3D-Detail anwenden:** Detailvorlage wählen, Zielkante (Falzende) und optional Bezugsfläche wählen, Werte eingeben. Die **Passung** prüft Kantentyp, Kantenlänge, Blechdicke und Wertebereiche. Mit «Um 180° wenden» wird die Richtung umgekehrt. Beim OK wird das Detail importiert, an der Kante ausgerichtet und die Parameter werden gesetzt. Standardmässig (Haken «Ins bestehende Modell integrieren») wird es danach in den Zielkörper übernommen (siehe Kapitel 16); ohne Haken bleibt es eine **eigene Komponente**. Die Kollision wird als echte Volumenüberschneidung geprüft; geht das in der Fusion-Version nicht, steht ausdrücklich «nur GROBE Vorprüfung (Begrenzungsrahmen)» im Bericht. Der Abstand Detail ↔ Zielkörper wird gemessen und gemeldet. **Abstand zur Fläche:** verschiebt das Detail entlang der lokalen Flächennormale (nur ohne Integration). **Gekrümmte Flächen (Zylinder, Kegel) und Bogenkanten:** das Detail wird **starr tangential** angesetzt (lokale Normale und Tangente am Kantenanfang) und nie an die Krümmung angepasst oder verformt. Geht beim Einsetzen etwas schief (Import, Ausrichtung, Parameter, Integration), werden Import und neue Parameter vollständig zurückgenommen.

## 8. Standard- und Expertenmodus

Beide Modi benutzen dieselbe Rechen-Engine.

- **Standardmodus:** Vorlage wählen und die wenigen variablen Werte eingeben.
- **Expertenmodus** (Häkchen in Palette und Dialog): Operationen hinzufügen, ändern, löschen und umordnen, Radien je Biegung, Anschluss/Grenzen/Einschnitt-Freigabe. In «Kanten bearbeiten» kann die Folge für eine Ausführung angepasst und optional als neue Vorlage gespeichert werden – das Original bleibt unverändert.

## 9. Rundbleche und Werkstattumformung

Für Rundbleche als Drehkörper (kein Fusion-Blech) gibt es den Befehl **Rundblech / Umformung**:

| Fall | Was passiert mit dem Rand | Modell |
|---|---|---|
| Scheibe mit aufgebogenem Rand | wird gestaucht | Drehkörper |
| Kragen an rundem Ausschnitt | wird gestreckt | nur Beurteilung |
| Kegelstumpf / konischer Übergang | abwickelbar, keine Umformung | Drehkörper |

Das Add-in unterscheidet klar:

- **konstruierbar** – lässt sich modellieren bzw. rechnen;
- **abwickelbar** – ohne Dehnung in die Ebene abwickelbar (nur Kegel/Zylinder);
- **herstellbar** – mit dem gewählten Verfahren (Stauchen/Schweifen, Strecken/Schweifen, manuell, automatische Empfehlung). Das wird **nur** beurteilt, wenn im Materialprofil ein **eigener Grenzwert** (Stauchen/Strecken in %) mit Quelle hinterlegt ist. Sonst steht «nicht beurteilbar».

Die angegebene Dehnung ist die reine Umfangsänderung (Geometrie) – keine Garantie: Falten, Rückfederung und Wanddickenänderung sind nicht gerechnet. Einschnitte oder Lappen werden **nie** automatisch erzeugt. Der Drehkörper ist kein Fusion-Blechkörper; Zuschnittdurchmesser und Kegelabwicklung sind theoretisch.

**Zuschnitt ausgeben:** Mit «flach» entsteht zusätzlich ein flacher Körper (Rohling) mit sichtbaren Biegelinien (Skizze, Fläche geteilt) – daraus lässt sich eine Fusion-Zeichnung ableiten. Mit «dxf» wird der Zuschnitt (Layer ZUSCHNITT, BIEGELINIE) in den Exportordner geschrieben. Scheibe: Kreis + Biegekreis; Kegel/Zylinder: Kreisringsektor bzw. Rechteck; Kragen: nur Loch und Biegekreis (kein Körper). Nicht in Fusion geprüft.

## 10. Abwicklung und DXF [nicht in Fusion geprüft]

**Abwicklung & DXF:** Blechkörper wählen. Hat die Komponente noch keine Abwicklung, erzeugt Fusion sie; die feststehende Fläche wählst du oder das Add-in nimmt nach fester Regel die grösste ebene Fläche (Oberseite zuerst). Vorher wird geprüft: gültiger Blechkörper in dieser Komponente, Fläche eben und am richtigen Körper. Eine vorhandene Abwicklung wird verwendet. Das Add-in liest das umschliessende Rechteck der Abwicklung und exportiert die DXF mit dem **Fusion-Exporter** (Ebenen und Biegelinien legt Fusion fest). Dateiname nach Muster `{bauteil}_{material}_{dicke}mm`, Ablage in einem Ordner mit Datum/Uhrzeit (Einzel- und Sammelexport). Erfolg wird nur gemeldet, wenn Fusion den Export ausgeführt und die Datei neu geschrieben hat (eine alte Datei gleichen Namens wird vorher entfernt) und die DXF-Gegenprobe (Masse, mm, Kontur) passt. «Abwickelbar» in Fusion heisst noch nicht «werkstattgerecht umformbar» (siehe Kapitel 9).

## 10a. Aufträge als Ordner in Fusion [nicht in Fusion geprüft]

Befehl **Neuer Auftrag** (Register SPENGLER → Fertigung): Auftragsnummer, Objekt (z. B. «Nägeligasse 1a, Bern») und Jahr eingeben. Das Add-in legt im aktiven Fusion-Projekt `Stammordner / Jahr / «17642 Nägeligasse 1a, Bern»` mit den Unterordnern (Standard: Modelle, Pläne, Export) an. Vorhandene Ordner werden wiederverwendet, nichts wird gelöscht oder umbenannt.

Einstellungen (Vorlagen & Einstellungen → Einstellungen → «Aufträge»): Stammordner (Projekt oder Ordner darin, Standard «Projekte»), Jahresordner ein/aus, Unterordner (Komma getrennt).

**Ableiten:** Liegt das aktive Dokument in einem Ordner nach dem Muster «Nummer Objekt» (mindestens 3 Ziffern, dann Leerzeichen), übernehmen **Stückliste & Zuschnitt**, Etiketten und das Werkstattblatt Auftragsnummer und Objekt automatisch aus dem Ordnernamen. Ohne passenden Ordner gelten die zuletzt verwendeten Angaben. Das Dokument speicherst du selbst im Ordner «Modelle» (die Fusion-Schnittstelle legt Dateien nicht automatisch dort ab).

### Auftrag wählen, speichern, Export, Listen [nicht in Fusion geprüft]

- **Auftrag wählen** (Register SPENGLER → Fertigung): Liste der vorhandenen Aufträge (neueste Nummer zuerst, mit Suchfeld). Der gewählte Auftrag ist «aktiv» für Stückliste, Etiketten, Werkstattblatt und Export. Mit dem Haken wird das offene Dokument im Ordner «Modelle» des Auftrags gespeichert (ungespeichert: Speichern; liegt es woanders: eine Kopie, die Originaldatei bleibt). Den Haken gibt es auch bei **Neuer Auftrag**. Namen der Ordner für Modelle/Pläne/Export: Einstellungen → Aufträge.
- **Export in den Auftrag:** Ist in den Einstellungen ein *Basisordner auf dem PC* eingetragen, landen DXF, Werkstattblätter und Listen in `Basis/Jahr/«Nummer Objekt»/Export/<Datum_Uhrzeit>`; ohne Basisordner im allgemeinen Exportordner.
- **Teilenummer mit Auftragsnummer:** Teile heissen z. B. `17642-01` (Einstellungen → Aufträge, abschaltbar). Intern bleibt es die laufende Nummer.
- **Prüfung vor dem Export** (Abwicklung & DXF sowie Stückliste & Zuschnitt): Warnungen (nie ein Abbruch) zu fehlendem Material, fehlender Teilenummer oder Abwicklung, doppelten Nummern, zu kurzen Schenkeln und zu kleinen Innenradien. Schwellen: Einstellungen → «Prüfung vor Export» (Standard 10 mm und 1 × Dicke).
- **Abkantliste:** Haken in «Stückliste & Zuschnitt» → `abkantliste.html`: je Teil Biegefolge mit Winkel, Schenkel, Innenradius (zum Drucken oder als PDF aus dem Browser). Nur für Teile, die mit «Kanten bearbeiten» entstanden sind.
- **Bestellliste für den ganzen Auftrag:** Jedes Mal, wenn «Stückliste & Zuschnitt» läuft, merkt sich das Add-in die Teile dieses Dokuments unter der Auftragsnummer. Mit dem Haken «Bestellliste für den ganzen Auftrag» werden die Teile **aller** bisher ausgewerteten Dokumente des Auftrags zusammengerechnet (`bestellliste.txt`: Fläche, Gewicht, Tafelbedarf je Material). Neuere Stände eines Dokuments ersetzen die älteren.
- **Berichte** (Register in der Palette): *Fehlerberichte* – jede Fehlermeldung im Add-in schickt Meldung und Protokollauszug automatisch an die eigene Firma (angemeldet nötig); hier lassen sie sich nachlesen. *Änderungsprotokoll* – wer wann welche Vorlage/welches Material gespeichert, kopiert, umbenannt, gelöscht oder importiert hat (nur dieser PC).

### Status, Kalkulation, Mappe, Profilzeichnung, Beschriftung, Reste [nicht in Fusion geprüft]

- **Fertigungsstatus:** In **Auftrag wählen** steht hinter jedem Auftrag sein Status (Offen, In Arbeit, Gefertigt, Geliefert). Dort lässt er sich setzen; ein neuer Auftrag beginnt «Offen». Der Status liegt in der Spengler-Digital-App (Tabelle `cad_auftragsstatus`) und gilt für alle PCs der Firma. Darunter steht, was die App zu diesem Auftrag kennt (Name, Kunde, Status in der App – nur gelesen, die App-Daten werden vom Add-in nie geändert). Ohne Anmeldung funktioniert die Liste, nur ohne Status.
- **Kalkulation** (Haken in «Stückliste & Zuschnitt» → `kalkulation.html`): Arbeitszeit je Teil = Rüstzeit + Biegungen × Minuten + Zuschnittumfang × Minuten (+ Zuschlag), mal **Stundensatz aus der App** (Einstellungen → Kalkulation: Name des Satzes, z. B. «Spengler»; der Satz muss in der App sichtbar sein, sonst von Hand eintragen). Material: nur wenn im Materialprofil Dichte und **Preis je kg** stehen. Die Zeiten sind Annahmen (Standard 5 min Rüsten, 1.5 min je Biegung, 2 min je m Umfang), bitte an die Werkstatt anpassen; die Kalkulation ersetzt keine Offerte.
- **Auftragsmappe** (Haken): Stückliste, Abkantliste, Kalkulation, Zuschnittplan und die zuletzt erzeugten Werkstattblätter des Auftrags in einer Datei `auftragsmappe.html` mit Deckblatt, je Abschnitt eine Seite. Drucken oder als PDF speichern mit Strg+P im Browser.
- **Profilzeichnung:** Im Editor einer Kantenvorlage der Knopf «Profilzeichnung öffnen»: grosser Querschnitt mit Schenkelmassen, Biegungen und Winkeln und eine Tabelle, als druckbare Seite (Dicke aus dem gewählten Material, sonst Skizze mit 1 mm).
- **Beschriftung:** In «Abwicklung & DXF» schreibt der Haken «Teilenummer in die DXF schreiben» die Teilenummer als Text in die Mitte des Zuschnitts (Layer «Text» der Einstellungen); die Kontur bleibt unverändert.
- **Reste** (Register in der Palette): Reststücke erfassen (Material, Dicke, Breite × Länge, Anzahl). «Stückliste & Zuschnitt» nennt Teile, die in einen Rest gleicher Dicke und gleichen Materials passen (Drehen nach Einstellung). Die Reste liegen vorerst nur auf diesem PC; die Felder entsprechen den Reststücken der App für eine spätere Verbindung.
- **Vorlage aus Profil lernen** (Register SPENGLER → Kanten & Details): liest die Flansch- und Saum-Features des offenen Dokuments in der Reihenfolge der Zeitleiste (nur **Werte**: Winkel, Länge, Radius; nichts wird verändert) und legt daraus eine Kantenvorlage an. Du wählst die Schritte per Haken und gibst Namen und Kategorie ein. Konturflansche werden nicht gelesen. Die Richtung der Schritte nach dem ersten lässt sich aus den Werten nicht ablesen und steht zunächst gleich wie beim ersten Schritt – bitte in der Vorschau des Editors prüfen; ebenso das Mass (Bezug aussen/innen/tangential wird nicht gelesen). Nicht in Fusion geprüft: Welche Werte Fusion für diese Features tatsächlich liefert, steht im Protokoll («Profil lesen»).
- **App als Zentrale – Teile an die App senden** (Haken in «Stückliste & Zuschnitt», Standard an, nur angemeldet): Jedes Teil geht mit Teilnummer, Material, Dicke, Zuschnitt (Breite × Länge), Stückzahl, Vorlage und den Schenkeln samt Winkeln in die Tabelle `cad_teile` der Spengler-Digital-App; die Zuordnung zum Projekt läuft über die Auftragsnummer. Erneutes Senden überschreibt dasselbe Teil. In der App stehen sie im Projekt unter den Massaufnahmen als «Teile aus dem CAD»; **«Als Massaufnahme übernehmen»** öffnet eine neue Massaufnahme «Freies Profil» mit diesen Werten – nach dem Speichern rechnen Zuschnitt, Rüstliste und Werkstattansicht mit der App-eigenen Logik wie bei einer selbst erfassten Massaufnahme (Material in der App noch wählen). Der erste Schenkel ist das bestehende Blech und so lang, dass die Summe der Masse der Abwicklungsbreite des CAD entspricht. (App-Seite: Branch `claude/cad-teile-aus-dem-cad` im App-Repository, erst nach dem Zusammenführen sichtbar.)
- **Dateien am Projekt in der App ablegen** (Haken in «Stückliste & Zuschnitt», Standard an, angemeldet, Auftragsnummer = Projektnummer in der App): Stückliste (HTML und CSV), Abkantliste, Kalkulation, Bestellliste, Zuschnittplan (SVG und CSV) und Auftragsmappe landen in der Ablage **Dateien** des Projekts im Cockpit der App, benannt «CAD – Stückliste 18162.html» usw. Beim erneuten Ausführen wird die Datei mit gleichem Namen **ersetzt** (keine Duplikate). Dazu braucht das Konto in der App das Recht «Projekte bearbeiten»; höchstens 50 MB je Datei. Die DXF-Dateien und Werkstattblätter bleiben vorerst lokal (die Werkstattblätter stecken in der Auftragsmappe).
- **Vorlage aus App-Massaufnahme** (Register SPENGLER → Kanten & Details): liest die Massaufnahmen «Freies Profil» und «Dachrandblech» des aktiven Auftrags aus der App (nur lesen) und legt aus Schenkeln und Winkeln eine Kantenvorlage an; der erste Schenkel (bestehendes Blech) entfällt. Winkel 180° wird zum Umschlag; Richtung und Mass bitte im Editor prüfen.
- **Aufträge abgleichen** (Register SPENGLER → Fertigung, angemeldet): vergleicht die Projekte der App mit den Auftragsordnern in Fusion über die **Auftragsnummer** (App `order_no` = Ordner «Nummer Objekt»). Die Liste zeigt, was auf einer Seite fehlt: Projekte der App ohne Ordner → Ordner anlegen (Jahresordner aus dem Anlagedatum des Projekts, mit den Unterordnern der Einstellungen); Ordner in Fusion ohne Projekt → Projekt in der App anlegen (Nummer, Objekt = Ordnername, Titel = Objekt; wie beim Anlegen in der App, den Titel kannst du dort ändern). Alles ist vorangehakt, nimm raus, was du nicht willst (z. B. Testprojekte). Abweichendes Objekt bei gleicher Nummer wird nur gemeldet, nie überschrieben; archivierte Projekte und Nummern ohne ≥ 3 Ziffern werden übersprungen. Auch **Neuer Auftrag** legt auf Wunsch (Haken, Standard an) das Projekt in der App an, falls es die Nummer dort noch nicht gibt. Die App führt den Verlauf der angelegten Projekte selbst; dafür braucht das Konto in der App das Recht «Projekte».
- **Gehrung bei mehreren Schritten:** Zusammenhängende Kanten werden **Schritt für Schritt gemeinsam** gebaut: jeder Flansch und auch jeder Umschlag als ein Feature über alle Kanten, damit Fusion alle Ecken auf Gehrung schneidet. Fusions Saum-Werkzeug nimmt über die Schnittstelle nur eine Kante; ein Umschlag an mehreren Kanten wird deshalb **je Kante als eigener, echter Saum** gebaut (die Ecken sind dann nicht auf Gehrung geschnitten – das steht im Bericht). Einen 179°-Flansch als Ersatz gibt es seit 0.4.49 nicht mehr. Nach dem Bauen wird kontrolliert (Gehrung laut Fusion, gültiger Körper, Volumen passt); fällt die Kontrolle durch oder klappt ein gemeinsamer Schritt nicht, wird **alles zurückgebaut**. Beim OK fragt das Add-in dann: «Stattdessen je Kante OHNE Gehrung bauen?» – nur bei Ja wird je Kante gebaut, und der Bericht sagt «OHNE Gehrung (Ecke stumpf)». In der Vorschau wird nie ohne Gehrung gebaut.
- **Protokoll senden** (Register Berichte): Wenn etwas nicht wie erwartet geht, aber keine Fehlermeldung kam, kurz die Notiz eintippen und «Protokoll senden» – die letzten Protokollzeilen gehen an die eigene Firma (siehe auch Fehlerberichte).
- **Selbsttest nach Update:** Nach jedem Update prüft das Add-in einmal, welche Fusion-Funktionen in deiner Fusion-Version vorhanden sind (Flansch, Saum, Extrusion, Daten-Ordner …) und meldet das Ergebnis als Testpunkt 97.001 an die eigene Firma.
- **Bedienung & Sicherheit (0.4.35):**
  - **Ampel im Dialog «Kanten bearbeiten»:** oben zeigt ein Satz in Grün/Gelb/Rot, was jetzt fehlt oder warum es nicht geht («Schritt 1: Blechkörper wählen», «Bereit: 2 Kanten (100 mm, 60 mm), Winkelfalz, Alu 1.0»).
  - **Kurzinfo:** Beschreibung und Kurzschrift der gewählten Vorlage stehen direkt im Dialog. **Zuletzt benutzte** Vorlagen stehen oben (↻), danach Favoriten (★).
  - **Material pro Auftrag:** Das Material wird einmal gewählt (beim ersten Bauen) und gilt dann für Kanten, Stückliste/Zuschnitt und Rundblech des Auftrags als Vorgabe.
  - **Rückgängig als Gruppe:** Alles, was «Kanten bearbeiten» baut, steht in der Zeitleiste als eine Gruppe «Spengler: <Vorlage>»; ein Strg+Z nimmt alles zurück.
  - **Fehlermeldungen mit Lösung:** Typische Fusion-Fehler (z. B. SM_GENERIC_FAILURE, Biegezone, kein Auftrag) erklären, was man tun kann.
  - **Gesperrte Befehle** zeigen einen Knopf «Jetzt beheben» (öffnet z. B. «Auftrag wählen»). Die **Start-Übersicht** zeigt den Ablauf Auftrag › Material › Kanten › Prüfen & Zuschnitt › App.
  - **Prüfung vor dem Zuschnitt** meldet zusätzlich: Blechdicke passt nicht zum Material, Körper ist kein Blech.
  - **Vorschau** der Vorlage im Editor zeigt jetzt den Versatz (die Biegung rückt nach innen/aussen). Die Palette hat einen **Dunkelmodus** (folgt dem System).
  - **Tägliche Sicherung:** Beim Start sichert das Add-in einmal pro Tag automatisch die Vorlagen und Einstellungen (die letzten 20 bleiben).
  - **OK-Knöpfe** heissen überall nach dem, was passiert («Kanten bauen», «Auftrag anlegen» …). Tastenkürzel setzt Fusion selbst: Taste **S** (Suche) und «Spengler» tippen; eigene Kürzel bietet die Fusion-Schnittstelle nicht an.
- **Profil von Hand skizzieren** (Palette → Register «Skizze»): Mit Stift, Finger oder Maus ein Profil auf das Zeichenfeld zeichnen (Ziehen oder Klicken von Punkt zu Punkt). Der **erste Strich ist das bestehende Blech**, jeder weitere Strich wird ein **Flansch** (Drehung nach links = +, nach rechts = −); eine Drehung von ≥ 170° wird ein **Umschlag**. Längen und Winkel **rasten** auf das gewählte Raster ein (Länge frei/1/5/10 mm, Winkel 1/5/15/45/90°, Kästchengrösse 5–100 mm). Die Tabelle rechts zeigt Länge und Winkel jedes Strichs und lässt sich genau nachtippen (auch Striche löschen oder mit «+ Strich» ergänzen). Mit gewähltem Material steht darunter die **theoretische Zuschnittbreite**. «Als Kantenvorlage übernehmen» öffnet die Skizze im Editor der Kantenvorlagen zum Prüfen und Speichern; die **Kurzschrift** lässt sich auch in ein Bauteil einfügen. Radius und Versatz ergänzt du im Editor.
- **Bauteile mit Grundrissverlauf** (Palette → Register «Bauteile», Befehl **Bauteil erstellen** in Konstruieren): Eine Bauteilvorlage baust du selbst im Add-in. Sie besteht aus
  - **Verlauf:** *gerade* (beim Bauen gibst du nur die Länge ein) oder *Grundrissverlauf*: Strecken mit Richtungswechseln, z. B. `3000 L90 2000 L90 3000 L90 2000 L90` (Zahl = Länge in mm, `L90` = nach links, `R45` = nach rechts). Ein Verlauf, der am Anfang wieder ankommt, kann als **geschlossener Ring** gebaut werden (Gebäude, Kamin, Schacht). Das Blech liegt links oder rechts vom Verlauf.
  - **Breite** des Blechs quer zum Verlauf als Zahl oder Ausdruck mit Parametern (z. B. `Mauer+2*Ueberstand`; `t` = Blechdicke).
  - **Kantenfolgen** in Kurzschrift wie bei den Kantenvorlagen für die **Kante am Verlauf**, die **Gegenkante** und die beiden **Stirnseiten** (z. B. `90 Tropf U+ 8`). Namen darin werden zu Parametern; Beschriftung, Einheit, Standardwert und Grenzen trägst du in der Parametertabelle ein. Die Vorschau zeigt die Draufsicht (Band mit beiden Kanten) und den Querschnitt jeder Seite.
  
  Beim Bauen entsteht zuerst das ebene Blech aus dem Grundriss, dann bekommen die zusammenhängenden Kanten ihre Kantenfolge **gemeinsam** (Fusion schneidet die Ecken auf Gehrung). Alles liegt als eine Gruppe in der Zeitleiste (ein Strg+Z). Bauteilvorlagen werden wie die Kantenvorlagen versioniert, gesichert und mit der App abgeglichen. Einschränkung: Versatz, Massbezug und Lage gibt es in der Kurzschrift nicht; ein Flansch mit Schenkel `Tropf` ist 90°, `U+` ein Umschlag.
- **Auftragsübersicht** (Palette → Register «Aufträge»): alle Aufträge auf einen Blick – Ordner in Fusion, Projekt in der App, Fertigungsstatus, Teile (gefertigt/gesamt) und letzte Änderung. Suche nach Nummer/Objekt, Filter nach Status oder «Mit Hinweis» (z. B. «Kein Ordner in Fusion», «Projekt fehlt in der App», «Alle Teile gefertigt – Status auf Gefertigt setzen?»). Der Status lässt sich direkt in der Liste ändern (wird in der App gespeichert), «Aktiv» macht einen Auftrag zum aktiven Auftrag. Ohne Anmeldung zeigt die Liste nur die Ordner.
- **Andere Ablage – Modelle ohne Kundenauftrag** (Register SPENGLER → Auftrag): Für ein Wettbewerbs-, Muster- oder Eigenmodell (z. B. die Schweizermeisterschaft) legst du eine **Ablage** an: Name und Fusion-Ordner im aktiven Projekt, z. B. `Wettbewerbe/Schweizermeisterschaft` (oder einen vorhandenen Ordner aus der Liste übernehmen). Fehlende Ordner werden angelegt, das aktuelle Dokument wird dort gespeichert, und die Ablage wird **aktiv**: Alle Befehle (Kanten bearbeiten, Abwicklung, Stückliste …) arbeiten dann **ohne Auftrag**, Exporte liegen im eigenen Ordner (`<Lokale Basis>/<Ablage>/Export` bzw. `<Exportordner>/<Ablage>`), Teilenummern sind einfach 01, 02 …, und es wird nichts in die App gesendet. Liegt ein Dokument im Ordner einer Ablage, erkennt das Add-in sie von selbst. Wählst du später einen Auftrag, ersetzt dieser die aktive Ablage. Eine Ablage lässt sich über den Haken «aus der Liste entfernen» wieder streichen (der Fusion-Ordner bleibt).
- **Projektkarte – alles zum Projekt im CAD** (Palette → Register **Projekt**, angemeldet): Projekt wählen (vorbelegt mit dem aktiven Auftrag), dann steht alles aus der App da: Kunde, Status, Hinweis, Zuteilung, nächster Termin; die **Massaufnahmen** mit Art, Titel, Werkstattstand (✎ in Bearbeitung … ✓ gerüstet, montiert) und den Daten der Stufen; **CAD und Werkstatt** (deine CAD-Teile und die mit «An CAD senden» geschickten Aufträge mit dem Stand der verknüpften Massaufnahme, z. B. «Gerüstet (gerüstet 3.11.2026)»); **Termine**, **Rapporte** (Stunden, Personen, Arbeiten), **Dateien**, **Offerten** und **Leistungen**.
  - **Fotos und Skizzen der Massaufnahme:** «📷 Fotos/Skizzen» lädt die Bilder (antippen = gross). **In Fusion einfügen** legt ein Bild als Referenzbild (Canvas) ins aktive Dokument, Lage und Grösse stellst du dort ein; **Speichern** legt es unter Exportordner → «App-Dateien/<Auftrag>» ab. Dateien des Projekts (Pläne, PDF) öffnen sich mit «Öffnen» ebenso.
  - **In der App ändern und ergänzen** (immer mit Rückfrage, nichts passiert ohne dein Ja):
    - **Projektstatus** (Offen / In Arbeit / Abgeschlossen / Storniert) und der **Fertigungsstatus** des Auftrags lassen sich direkt in der Karte setzen. Der Projektstatus wird nur geändert, wenn er in der App noch so steht, wie die Karte ihn zeigt – hat jemand ihn inzwischen geändert, meldet das CAD es und überschreibt nichts.
    - **Hinweis:** «Hinweis speichern» ersetzt den Hinweis im Projekt (leer = löschen), «Ergänzen» hängt eine Zeile mit Datum und Namen an («4.11.2026 Mike (CAD): Gerüst bestellt»). Ist das Projekt inzwischen anderswo geändert worden, wird nicht überschrieben.
    - **Termine:** «+ Termin hinzufügen» legt einen Termin am Projekt an (Titel, Beginn/Ende als 4.11.2026, Uhrzeiten, Ort, Notiz – geprüft nach den Regeln der App); «Ändern» bearbeitet einen in der App angelegten Termin. Termine aus Outlook, Google oder Kalender-Abos lassen sich nur dort ändern. Löschen gibt es im CAD nicht.
    - Alle Änderungen brauchen das Recht «Projekte bearbeiten» in der App (für Termine zusätzlich das eingeschaltete Modul «Termine»). Fehlt es, meldet das CAD das, statt still nichts zu tun. In der App steht der Änderer wie bei jeder Änderung im Änderungsprotokoll.
  - **Neu seit dem letzten Mal:** Oben steht, was seit dem letzten Ansehen neu ist (neue Massaufnahmen, Werkstatt-Schritte, Rapporte, Dateien, Termine) und wie viele Aufträge aus der App auf das CAD warten. Dieselbe Zeile (🔔) und eine Kurzinfo zum Projekt stehen in der **Start-Übersicht** des Add-ins.
- **Profile aus der App senden** (App ab v3.425): In der App gibt es an einer Massaufnahme «Freies Profil» im Projekt-Cockpit den Knopf **«An CAD senden»** (Länge in mm und Stückzahl). Im Add-in steht der Auftrag dann in **Blech aus Massaufnahme** ganz oben («📤 aus der App: Name – Länge × Stück»), mit der Länge schon eingetragen. Nach dem Bauen wird er in der App als «im CAD gebaut» vermerkt. Die Schenkel werden beim Senden kopiert; spätere Änderungen an der Massaufnahme ändern einen gesendeten Auftrag nicht. Bei mehreren Stück baut das Add-in ein Bauteil (in Fusion kopieren). In der App lässt sich ein offener Auftrag zurückziehen.
- **Blech aus Massaufnahme** (Register SPENGLER → Konstruieren): erzeugt aus einer Massaufnahme «Freies Profil» oder «Dachrandblech» des aktiven Auftrags (nur lesen) ein Bauteil: Grundblech mit Breite = erster Schenkel und Länge aus der App (änderbar) und auf Wunsch die Kantenfolge (Flansche/Umschläge). Das Material wird gewählt; passt die Blechregel in Fusion nicht zur Dicke, steht ein Hinweis. Alles landet als eine Gruppe in der Zeitleiste. Richtung und Masse bitte mit der Massaufnahme vergleichen.
- **Live-Test** (Register SPENGLER → Verwaltung): prüft die Fusion-Funktionen des Add-ins **automatisch** – Test-Blech, Flansch (Winkel, Radius, nach hinten), Winkelfalz, Umschlag, Gehrung an Eckkanten, Versatz ±, Abwicklung, DXF, Bildschirmfoto, Rundblech, 3D-Detail. Alles läuft in neuen Testdokumenten, die danach ohne Speichern geschlossen werden; deine Dokumente bleiben unberührt. Dauer 1–2 Minuten, Fusion reagiert dabei nicht. Seit 0.4.48 **misst** er das Ergebnis (Volumen, Ausdehnung) und bewertet Richtung, Höhe und Volumen der Flansche und Umschläge, Versatz und Radius als Unterschied zum Bau ohne, und prüft die DXF-Datei der Abwicklung; geometrisch Falsches zählt als ✗ Fehler. Der Bericht enthält nur Protokollzeilen seit Teststart, Benutzerpfade und E-Mail-Adressen sind maskiert. Das Ergebnis (✓ ok, ⚠ auffällig, ✗ Fehler, je Schritt mit Zahlen) geht als Testpunkt 97.002 an die eigene Firma und liegt als `livetest.txt` im Datenordner. Sinnvoll nach jedem Update und nach jeder Fusion-Aktualisierung.
- **Fehlerbericht mit Bild:** Jede Fehlermeldung schickt zusätzlich ein kleines Bildschirmfoto der Ansicht mit (Register Berichte zeigt es an). Das Änderungsprotokoll im Register Berichte ist jetzt für alle PCs der Firma gemeinsam (angemeldet).

## 11. Fertigungszeichnungen

Fusion bietet per API keine zuverlässige automatische Zeichnungserstellung mit Ansichten. Das Add-in erstellt deshalb ein **Werkstattblatt** (HTML, druckbar) mit Logo, Bauteilkennung, Material, Dicke, Vorlage und Version, Abwicklungsmassen aus Fusion sowie – für Bauteile aus «Kanten bearbeiten» mit Innenradius/K-Faktor im Material – Teilenummer, Objekt/Auftrag sowie – für Bauteile aus «Kanten bearbeiten» mit Innenradius/K-Faktor im Material – **Querschnitt mit Schenkelmassen und Biegungen**, **Abwicklung der Kante mit Biegelinien** (Masse ab Biegebeginn) und **Biegeliste**. Alles daraus ist als *theoretisch* gekennzeichnet (Blechmitte, K-Faktor des Materialprofils); die Zeichenlogik stammt aus dem CAD-Programm. Normgerechte Fusion-Zeichnungen erstellen Sie weiterhin im Arbeitsbereich Zeichnung.

## 12. Materialberechnung

**K-Faktor aus Probebiegung** (Palette → Materialien → Materialprofil öffnen): Streifen genau zuschneiden, **eine** 90°-Biegung mit dem Innenradius des Profils biegen, beide Schenkel **aussen** messen. Zuschnitt, a und b eintragen → «K-Faktor berechnen». Dicke und Innenradius kommen aus den Feldern des Profils. Ist das Ergebnis plausibel (0.1–0.6), lässt es sich mit einem Klick übernehmen; danach «Speichern». Die Rechnung ist dieselbe wie im CAD-Programm. Der K-Faktor gilt für die theoretische Abwicklung des Add-ins; für die Fusion-Abwicklung denselben Wert in der Fusion-Blechregel eintragen.

**Stückliste & Zuschnitt**: Blechkörper mit Fusion-Abwicklung wählen, Material, Stück je Teil, Objekt und Auftrag eingeben (werden für das nächste Mal gemerkt) und die gewünschten Ausgaben ankreuzen:

- **Teilenummern**: Jeder Körper bekommt eine Nummer, die als Attribut am Körper im Fusion-Dokument gespeichert wird. Vorhandene Nummern bleiben; ein neuer Körper erhält die nächste freie Nummer im Dokument. Dieselbe Nummer steht auf Stückliste, Etikett, Werkstattblatt und im DXF-Dateinamen.
- **Stückliste** als `stueckliste.csv` (Excel: Semikolon, Umlaute korrekt) und `stueckliste.html` (drucken): Nr, Teil, Material, Dicke, Zuschnitt × Länge, Stück, Laufmeter, Fläche, Gewicht, Summe je Material. Fläche aus der Fusion-Abwicklung; fehlt sie, das umschliessende Rechteck (mit * markiert). Ohne Dichte im Materialprofil kein Gewicht.
- **Etiketten** als `etiketten.html`: eins pro Stück (Objekt, Auftrag, Teil mit Nummer und i/n, Blech, Mass) im A4-Bogenformat aus *Einstellungen → Etikettenbogen* (Spalten, Zeilen, Etikettgrösse, Ränder, Abstände – vom Bogen des Herstellers ablesen; die Palette zeigt, ob der Bogen auf A4 passt). Im Browser drucken mit **Seitenränder: keine** und **Skalierung 100 %**.
- **Materialbedarf & Zuschnittplan** wie unten.

Die Materialberechnung ermittelt je Material: Anzahl Teile, Abwicklungsfläche (aus Fusion, sonst Rechteck – dann als obere Schätzung markiert), Gewicht (nur mit Dichte; Fläche × Dicke × Dichte, **Schätzwert**), Materialverbrauch und Ausnutzung des besten Lagerformats. Ergebnis: `bericht.txt` im Exportordner (wird nach dem Befehl geöffnet).

## 13. Zuschnittoptimierung

Die Rechnung ist aus der **Spengler-Digital-App** übernommen (gleiche Logik, gegen Referenzfälle aus der App getestet):

- Teile werden als **Streifen ihrer Abwicklungsbreite** aus Rolle oder Tafel geschnitten; Streifen je Abschnitt = ⌊(B + f) / (A + f)⌋.
- Je Breite wird die **kleinste Streifenzahl** gesucht (zuerst gierig, dann exakte Suche ab der Untergrenze); die Schnittfuge liegt zwischen zwei Stücken.
- Rolle mit mehreren Streifen nebeneinander: jeder Abschnitt nur so lang wie sein längstes Stück.
- Bestes Format = kleinste Blechfläche.

Neu im Add-in: Randabstand je Tafelseite, **Drehen nur wenn erlaubt** (Einstellung), Überlappungs- und Randprüfung der Lage, Ausgabe als `zuschnittplan.svg`, `.csv` und `.dxf` (Layer einstellbar).

**Nicht übernommen** (und so ausgewiesen): Rollenmischung, Mischen verschiedener Breiten im selben Abschnitt, automatisches Teilen zu langer Stücke mit Nahtüberlappung, Restelager der App. Teile werden als Rechtecke verschachtelt, freie Konturen nicht.

## 14. Import/Export und Sicherung

**Benutzerdatenordner** (überlebt Updates):

- Windows: `%APPDATA%\SpenglerDigitalCAD`
- macOS: `~/Library/Application Support/SpenglerDigitalCAD`

Inhalt: `vorlagen/kanten`, `vorlagen/details` (+ `geometrie/*.f3d`), `vorlagen/versionen`, `vorlagen/papierkorb`, `materialien`, `einstellungen.json`, `datenformat.json`, `sicherungen`, `protokoll`, `export`.

**Vorlagen exportieren/importieren** (Palette, Kantenvorlagen): Austauschformat ist eine JSON-Datei:

```
{ "schemaVersion": 1, "typ": "bibliothek_export", "exportiert": "<Zeit>",
  "vorlagen": [ <Kantenvorlage oder Detailvorlage, vollständig> ],
  "geometrie": { "<relativer Pfad .f3d>": "<Base64>" } }
```

Beim Import werden bestehende Vorlagen nie überschrieben: gleiche ID → Import als Kopie mit neuer ID. Vorlagen aus einer neueren Programmversion werden abgelehnt statt verändert.

**Sicherung** (Palette → Sicherung): «Sicherung erstellen» schreibt eine ZIP-Datei mit allen Benutzerdaten und Prüfsummen. «Wiederherstellen» prüft die Datei, sichert den aktuellen Stand automatisch und ersetzt ihn erst dann.

**Konto & Abgleich mit der Spengler-Digital-App** (Palette → Register **Konto**): Mit demselben Benutzernamen und Passwort wie in der App anmelden. Danach werden Kantenvorlagen, 3D-Details (samt .f3d-Geometrie) und Materialprofile mit allen PCs der Firma abgeglichen – beim Start, nach jeder Änderung in der Palette und mit «Jetzt abgleichen». Oben in der Palette steht der Stand («✓ mit der App abgeglichen», «nur lokal …»).

- **Lokal zuerst:** Jede Änderung wird zuerst auf dem PC gespeichert. Ohne Internet arbeitet das Add-in normal weiter und gleicht später ab.
- **Rechte:** Ändern dürfen Konten mit dem App-Recht «Vorlagen ändern» (Standard: Admin; in der App pro Person einstellbar – es ist dasselbe Recht wie für die Massaufnahme-Vorlagen). Alle anderen sehen und benutzen die Vorlagen; eigene Änderungen bleiben dann auf ihrem PC und werden als «nur auf diesem PC» gemeldet.
- **Firmen getrennt:** Jede Firma sieht nur ihre eigenen Daten (Regeln der App-Datenbank).
- **Konflikt:** Haben zwei PCs dieselbe Vorlage geändert, gilt die Fassung aus der App; die eigene bleibt als Kopie «… (Konflikt TT.MM.)» erhalten und wird ebenfalls abgeglichen.
- **Löschen** verschiebt auf allen PCs in den Papierkorb; in der App wird nur markiert, frühere Fassungen bleiben dort gespeichert.
- Das **Passwort** wird nicht gespeichert, nur die Sitzung (`konto.json` im Benutzerdatenordner). «Abmelden» löscht sie.

## 15. Updates und Wiederherstellung

**Mit Anmeldung (ab 0.4.0):** Beim Start fragt das Add-in, wenn in der App eine neuere Version bereitliegt (oder Palette → Konto → «Nach Updates suchen»). Bei «Ja»: Benutzerdaten sichern → bisherige Programmdateien nach `…\SpenglerDigitalCAD\programm_sicherung\<Version>` kopieren → nur geänderte Dateien laden und per Prüfsumme kontrollieren → ersetzen. Danach das Add-in neu starten (Shift+S → Stoppen → Ausführen). Stimmt eine Prüfsumme nicht oder fehlt etwas, wird abgebrochen und nichts verändert. Die PDF-Anleitungen kommen nur mit dem ZIP; «Hilfe → Bedienungsanleitung öffnen» zeigt die stets aktuelle HTML-Fassung.

**Von Hand (ZIP), z. B. Erstinstallation auf einem neuen PC:**

1. Add-in stoppen (Skripte und Add-Ins → Stoppen).
2. Inhalt des ZIP in **denselben** Ordner kopieren und ersetzen (danach liegt `SpenglerDigital.py` direkt im Ordner). Der Benutzerdatenordner wird dabei nicht berührt.
3. Add-in starten und unter Hilfe → Fusion-Fähigkeiten Version und Ladeordner prüfen. Das Add-in prüft das Datenformat (`schemaVersion` je Datensatz):
   - Umstellung nötig → **automatische Sicherung**, Umstellung auf Kopien, Prüfung jedes Datensatzes, erst dann Übernahme.
   - Kritische Umstellung → Rückfrage vor dem Start.
   - Fehler → **keine Datei wird verändert**, Meldung mit Pfad der Sicherung.
   - Datensätze aus einer neueren Version → werden gelesen, aber nie überschrieben.
4. Zurück zum alten Stand: Palette → Sicherung → gewünschte Sicherung → Wiederherstellen.

## 16. Fehlerbehebung und bekannte Grenzen

**Protokoll:** Palette → Sicherung → «Protokoll öffnen» (Datei `protokoll/spengler_cad.log`). Bei Problemen bitte diese Datei schicken.

| Meldung | Ursache / Lösung |
|---|---|
| «Die Vorlagenbibliothek ist leer» | Zuerst unter Vorlagen & Einstellungen eine Vorlage anlegen. |
| «… FlangeFeatures.createEdgeFlangeInput fehlt» | Fusion aktualisieren; die Blech-API ist neu. |
| «… lässt sich nicht einstellen – abgebrochen» | Diese Fusion-Version kennt die Eigenschaft nicht; es wird nichts mit falschen Werten gebaut. Protokoll schicken. |
| «Neue Aussenkante ist mehrdeutig» | Folge in Einzelschritten anwenden (je Schritt eine Vorlage). |
| «… nur an geraden Kanten bauen» | Flansch und Umschlag gehen per Fusion-Schnittstelle nur an geraden Kanten; runde Kanten werden vor dem Bauen abgelehnt. Ellipse/Spline werden nicht bearbeitet. Für Rundbleche als Drehkörper den Befehl Rundblech verwenden. |
| «Materialwerte fehlen: ri, k» | Innenradius/K-Faktor im Materialprofil ergänzen oder die Vorlage ohne `ri`/`k` schreiben. |
| «Parameter nicht gefunden» (3D-Detail) | Der Benutzerparameter wurde beim Import umbenannt oder nicht übernommen; Parameter in Fusion prüfen. |

**Bekannte Grenzen dieser Version:**

- Die Fusion-Blech-API ist bei Autodesk «Preview». Flansch und Umschlag sind **nicht in Fusion geprüft**; die Eigenschaftsnamen werden gesucht und protokolliert.
- Freistellungen/Ecken erzeugt Fusion nach der Blechregel; eigene Freistellungen erzeugt das Add-in nicht.
- Flansche über die ganze Kantenlänge. Fusions Flansch-Schnittstelle (EdgeFlange, ab API Oktober 2026) nennt in der Dokumentation nur gerade Kanten. An Kreis-/Bogenkanten wird deshalb nichts versucht. Zusammenhängende Kanten bekommen den Flansch gemeinsam in einem Feature (Gehrung an den Ecken); klappt das nicht, wird zurückgebaut und nachgefragt, ob ohne Gehrung je Kante gebaut werden soll. Feine Spalte an der Gehrungsecke erkennt die Kontrolle nicht – bitte im Modell ansehen.
- 3D-Details: Benutzerparameter gelten im ganzen Dokument; zweimal dasselbe Detail mit verschiedenen Werten im selben Dokument ist nicht geprüft.
- Rundbleche als Drehkörper, nicht als Fusion-Blechkörper; Umformbarkeit nur mit eigenen Grenzwerten.
- Keine automatische Fusion-Zeichnung (Werkstattblatt statt dessen).
- Zuschnitt mit Rechtecken; Rollenmischung und Restelager der App nicht übernommen.
- Abgleich mit der App: Einstellungen (Zuschnitt, Etiketten, Export) bleiben je PC; abgeglichen werden Vorlagen, 3D-Details und Materialprofile.


**3D-Detail anwenden – Integration:** Mit Haken «Ins bestehende Modell integrieren» (Standard) wird das Detail als Basis-Feature plus «Kombinieren» in den Zielkörper übernommen, ohne eigene Komponente; ein Rückgängig-Schritt. Berührt das Detail den Körper nicht oder ändert es das Volumen nicht, wird alles zurückgenommen und der Grund gemeldet. Ohne Haken bleibt es eine eigene Komponente. Die Masse sind danach fest: die parametrische Feature-Historie des Details bleibt bei der Integration **nicht** erhalten. Nicht live geprüft.

## 17. Tests in Fusion abhaken

Palette → Register **Tests**: Die Testanleitung steht dort Punkt für Punkt. Pro Punkt **✓** (ok), **✗** (Fehler, mit Notiz – Meldungstext oder Messwert) oder **–** (übersprungen); nochmal klicken nimmt zurück. Die Ergebnisse werden auf diesem PC gespeichert (`testergebnisse.json` im Benutzerdatenordner) und, wenn Sie im Register Konto angemeldet sind, sofort an die Spengler-Digital-App übermittelt, damit die Entwicklung sie sieht. Bei ✗ wird zusätzlich der Protokollauszug (letzte Zeilen) mitgesendet; sonst werden keine Kundendaten übertragen. Ohne Netz oder Anmeldung bleibt alles lokal; **Nicht gesendete Ergebnisse senden** holt das nach.

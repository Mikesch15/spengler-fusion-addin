// Bedient die echte Palette (palette/vorlagen.html) im Browser. Fusion wird durch window.__testSenden ersetzt,
// das an das Python-Backend (test_palette.py) weiterleitet. Aufruf: node palette_browser_test.cjs <url>
const { chromium } = require("playwright");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const fehler = [];
  page.on("pageerror", (e) => fehler.push(e.message));
  await page.addInitScript(() => {
    window.__testSenden = async (aktion, daten) => {
      const r = await fetch("/senden", { method: "POST", body: JSON.stringify({ aktion, daten }) });
      return r.text();
    };
  });
  await page.goto(process.argv[2]);
  const pruefe = (b, t) => { if (!b) throw new Error("FEHLGESCHLAGEN: " + t); };
  await page.waitForFunction(() => document.getElementById("version").textContent.includes("Version"));
  pruefe(await page.isVisible("#vLeer"), "leere Bibliothek wird angezeigt");
  // Material anlegen
  await page.click("nav button[data-tab=materialien]");
  pruefe(await page.isVisible("#mLeer"), "leere Materialbibliothek");
  await page.click("#mNeu");
  await page.fill("#mName", "TEST Blech");
  await page.fill("#mT", "0.7"); await page.fill("#mRi", "1"); await page.fill("#mK", "0.4");
  await page.fill("#mTafeln", "1000x2000; 1250x2500");
  await page.fill("#mK", "");
  await page.fill("#mPz", "128.61"); await page.fill("#mPa", "50"); await page.fill("#mPb", "80");
  await page.click("#mPrech");
  await page.click("#mPueb");
  pruefe((await page.inputValue("#mK")) === "0.399", "K-Faktor aus Probe übernommen: " + await page.inputValue("#mK"));
  await page.fill("#mPz", "140"); await page.click("#mPrech");
  await page.waitForSelector("#meldung .fehler");
  await page.fill("#mK", "0.4");
  await page.click("#mSpeichern");
  await page.waitForSelector("#mListe tbody tr");
  pruefe((await page.textContent("#mListe")).includes("1000×2000"), "Tafelformat gespeichert");
  // Vorlage im Standardmodus per Kurzschrift
  await page.click("nav button[data-tab=vorlagen]");
  await page.click("#vNeu");
  await page.fill("#eName", "TEST Falz");
  await page.fill("#eKurz", "90 H U+ u+4*t");
  await page.click("#eKurzUeb");
  await page.waitForFunction(() => document.querySelectorAll("#pTab tbody tr").length === 2);
  pruefe(await page.isVisible("#oTab"), "Schritt-Tabelle auch im Standardmodus sichtbar");
  await page.fill('#pTab input[data-p="0"][data-f="default"]', "25");
  await page.fill('#pTab input[data-p="1"][data-f="default"]', "7");
  await page.waitForFunction(() => document.querySelector("#eVorschau svg") && document.querySelector("#eVorschau").textContent.includes("25"));
  await page.fill('#pTab input[data-p="0"][data-f="default"]', "40");
  await page.waitForFunction(() => document.querySelector("#eVorschau").textContent.includes("40"));
  await page.fill('#pTab input[data-p="0"][data-f="default"]', "25");
  await page.selectOption("#eMat", { label: "TEST Blech (0.7 mm)" });
  await page.waitForFunction(() => document.querySelector("#eVorschau").textContent.includes("Material TEST Blech"));
  await page.click("#ePruef");
  await page.waitForSelector("#ePruefErg .meldung");
  pruefe((await page.textContent("#ePruefErg")).includes("Vorlage ist gültig"), "Prüfung gültig: " + await page.textContent("#ePruefErg"));
  pruefe((await page.textContent("#ePruefErg")).includes("Abwicklungszugabe"), "Theorie angezeigt");
  await page.click("#eSpeichern");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("Version 1"));
  pruefe(await page.isVisible("#vListe tbody td.mini svg"), "Vorschaubild in der Vorlagenliste");
  if (process.env.BILDSCHIRMFOTO) await page.screenshot({ path: process.env.BILDSCHIRMFOTO, fullPage: true });
  // Expertenmodus: Operation ergänzen, umordnen, speichern → Version 2
  await page.click("#oNeu");
  await page.waitForFunction(() => document.getElementById("eVorschau").innerHTML.includes("<svg"));   // Vorschau zeichnet mit
  await page.click('button[data-oauf="2"]');
  pruefe((await page.inputValue("#eKurz")) === "90 H 90 10 U+ u+4*t", "Kurzschrift folgt Tabelle: " + await page.inputValue("#eKurz"));
  await page.click("#eSpeichern");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("Version 2"));
  // Duplizieren, Löschen (Bestätigung), Papierkorb
  await page.click("#eKopie");
  await page.waitForFunction(() => document.querySelectorAll("#vListe tbody tr").length === 2);
  await page.click("#eLoeschen");
  await page.waitForFunction(() => document.querySelectorAll("#vListe tbody tr").length === 1);
  // ungültige Vorlage wird abgelehnt
  await page.click("#vNeu");
  await page.fill("#eName", "");
  await page.click("#eSpeichern");
  await page.waitForSelector("#meldung .fehler");
  // Einstellungen + Sicherung
  await page.click("nav button[data-tab=einstellungen]");
  await page.waitForFunction(() => document.getElementById("sEpruef").textContent.includes("24 Etiketten pro Bogen"));
  await page.fill("#sEbr", "100");
  await page.waitForFunction(() => document.getElementById("sEpruef").textContent.includes("Passt nicht auf A4"));
  await page.click("#sSpeichern");
  await page.waitForSelector("#meldung .fehler");
  await page.fill("#sEbr", "70");
  await page.fill("#sFuge", "2");
  await page.click("#sSpeichern");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("gespeichert"));
  await page.click("nav button[data-tab=sicherung]");
  await page.click("#bSichern");
  await page.waitForFunction(() => document.querySelectorAll("#bListe button").length === 1);
  pruefe((await page.textContent("#pkListe")).includes("kv-"), "gelöschte Vorlage im Papierkorb");
  await page.click("#sicherung [data-hilfe=einstellungen]");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("Updates"));
  // Konto: anmelden, abgleichen, Änderung wird automatisch hochgeladen
  await page.click("nav button[data-tab=konto]");
  pruefe(await page.isVisible("#kAnmelden"), "Anmeldemaske sichtbar");
  await page.fill("#kBenutzer", "chef"); await page.fill("#kPasswort", "falsch"); await page.click("#kAnmelden");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("falsch"));
  await page.fill("#kPasswort", "geheim"); await page.click("#kAnmelden");
  await page.waitForFunction(() => document.getElementById("kWer").textContent.includes("Chef"));
  pruefe((await page.textContent("#kRecht")).includes("dürfen Vorlagen ändern"), "Recht angezeigt");
  pruefe((await page.inputValue("#kPasswort")) === "", "Passwortfeld geleert");
  await page.click("nav button[data-tab=vorlagen]");
  await page.click("#vListe tbody tr td:nth-child(3)");
  await page.fill("#eBeschr", "nach Anmeldung geändert");
  await page.click("#eSpeichern");
  await page.waitForFunction(() => document.getElementById("syncStatus").textContent.includes("abgeglichen"));
  // Register Tests: abhaken, mit Notiz Fehler melden, Übermittlung an die (nachgebaute) App
  await page.click("nav button[data-tab=tests]");
  await page.waitForSelector('.tpunkt[data-tid="0.1"]');
  await page.click('.tpunkt[data-tid="0.1"] [data-tstatus=ok]');
  await page.waitForFunction(() => document.querySelector('.tpunkt[data-tid="0.1"]').textContent.includes("gesendet"));
  await page.fill('.tpunkt[data-tid="0.2"] .tnotiz', "Meldung XY");
  await page.click('.tpunkt[data-tid="0.2"] [data-tstatus=fehler]');
  await page.waitForFunction(() => document.querySelector('.tpunkt[data-tid="0.2"]').classList.contains("s-fehler"));
  pruefe((await page.textContent("#tFortschritt")).includes("2 von"), "Fortschritt zählt: " + await page.textContent("#tFortschritt"));
  await page.click('.tpunkt[data-tid="0.1"] [data-tstatus=ok]');   // nochmal klicken = zurücknehmen
  await page.waitForFunction(() => document.querySelector('.tpunkt[data-tid="0.1"]').classList.contains("s-offen"));
  await page.click("nav button[data-tab=bauteile]");
  pruefe(await page.isVisible("#bLeer"), "keine Bauteile am Anfang");
  await page.click("#bNeu");
  await page.fill("#bName", "TEST Abdeckung");
  await page.selectOption("#bArt", "grundriss");
  await page.fill("#bBsp", "3000 L90 2000 L90 3000 L90 2000 L90");
  await page.check("#bRing");
  await page.fill("#bBreite", "Mauer+2*Ue");
  await page.fill("#bT_verlauf", "90 Tropf U+ 8");
  await page.click("#bErkennen");
  await page.waitForFunction(() => document.querySelectorAll("#bParam tbody tr input[data-f=default]").length === 3);
  const namen = await page.$$eval("#bParam tbody tr td:first-child", (l) => l.map((x) => x.textContent).join(","));
  pruefe(namen === "Mauer,Tropf,Ue", "Parameter erkannt: " + namen);
  await page.fill('#bParam input[data-bp="0"][data-f="default"]', "300");
  await page.fill('#bParam input[data-bp="1"][data-f="default"]', "35");
  await page.fill('#bParam input[data-bp="2"][data-f="default"]', "40");
  await page.waitForFunction(() => document.querySelector("#bVorschau svg") && document.querySelector("#bVorschau").textContent.includes("Ring"));
  await page.click("#bSpeichern");
  await page.waitForFunction(() => document.getElementById("meldung").textContent.includes("Bauteil gespeichert"));
  pruefe((await page.textContent("#btListe")).includes("TEST Abdeckung"), "Bauteil in der Liste");
  await page.click("nav button[data-tab=skizze]");
  const cv = await page.$("#skCanvas"); const bb = await cv.boundingBox();
  const pt = (x, y) => [bb.x + x * bb.width / 640, bb.y + y * bb.height / 400];
  const zieh = async (x, y) => { const [px, py] = pt(x, y); await page.mouse.move(px, py); await page.mouse.down(); await page.mouse.up(); };
  await zieh(100, 300); await zieh(300, 300); await zieh(300, 200); await zieh(260, 200);
  await page.waitForFunction(() => document.querySelectorAll("#skTab tbody tr input[data-f=laenge]").length === 3);
  const werte = await page.$$eval("#skTab tbody tr input", (l) => l.map((x) => x.value).join(","));
  pruefe(werte === "100,50,90,20,90", "Skizze eingerastet: " + werte);
  await page.fill('#skTab input[data-sk="1"][data-f="laenge"]', "35");
  await page.waitForFunction(() => document.getElementById("skInfo").textContent.includes("90 35 90 20"));
  await page.fill("#skName", "TEST Skizze");
  await page.click("#skVorlage");
  await page.waitForSelector("#editor", { state: "visible" });
  pruefe((await page.inputValue("#eName")) === "TEST Skizze", "Skizze als Vorlage im Editor");
  await page.click("nav button[data-tab=projekt]");
  await page.waitForTimeout(600);
  await page.evaluate(() => pkZeigen({kopf:{nummer:"18191",objekt:"Alpeneggstrasse 22, Bern",kunde:"Weyermann AG",status:"In Arbeit",hinweis:"Schlüssel beim Hauswart",zugeteilt:["Mike L"],archiviert:false},
    massaufnahmen:[{id:135,art:"Freies Profil",titel:"Stirn",zeichen:"✓",status:"Freigegeben",datum:"3.11.2026",stufen:["freigegeben 3.11.2026"],montage:"",pfade:["a.jpg"],cad_teile:1,cad_auftraege:1,archiviert:false}],
    cad:{teile:[{label:"18191-01",name:"Ortgang",stueck:2,material:"Alu",app:"in der App übernommen",werkstatt:"Gerüstet"}],auftraege:[{titel:"Stirn",laenge:3200,stueck:2,status:"wartet auf das CAD",gebaut:"",werkstatt:""}]},
    rapporte:[{datum:"19.10.2026",stunden:2.5,personen:["Mike"],material:1,arbeiten:["Messen"]}],termine:[{titel:"Montage",wann:"10.11.2026",ort:"Bern",mitarbeiter:[]}],naechster_termin:{titel:"Montage",wann:"10.11.2026",ort:"Bern"},
    dateien:[{name:"Plan.pdf",groesse:"2 KB",datum:"3.11.2026",pfad:"project-files/7/x.pdf"}],offerten:[{nr:"O-1",titel:"Dach",datum:"1.10.2026",gueltig_bis:"",positionen:4,pdf:""}],leistungen:[],
    zaehler:{massaufnahmen:1,aktiv:1},neu:{text:"1 Auftrag aus der App wartet"},hinweise:[]}));
  const pk = await page.textContent("#pkKarte");
  pruefe(pk.includes("Weyermann AG") && pk.includes("Alpeneggstrasse 22") && pk.includes("Schlüssel beim Hauswart") && pk.includes("Nächster Termin: Montage"), "Projektkopf mit Kunde, Hinweis und Termin");
  pruefe(pk.includes("Freies Profil") && pk.includes("Fotos/Skizzen (1)") && pk.includes("18191-01") && pk.includes("Werkstatt: Gerüstet") && pk.includes("wartet auf das CAD"), "Massaufnahmen, CAD-Teile mit Werkstattstand, gesendeter Auftrag");
  pruefe(pk.includes("Plan.pdf") && pk.includes("O-1") && pk.includes("19.10.2026"), "Dateien, Offerten, Rapporte");
  pruefe((await page.textContent("#pkNeu")).includes("1 Auftrag aus der App wartet"), "Hinweis «Neu seit dem letzten Mal»");
  await page.click("nav button[data-tab=auftraege]");
  await page.waitForFunction(() => document.getElementById("aSumme").textContent.includes("Aufträge"));
  pruefe((await page.textContent("#aListe")).includes("Keine Aufträge"), "Auftragsübersicht ohne Aufträge");
  pruefe((await page.textContent("#aInfo")).length > 10, "Hinweis in der Auftragsübersicht");
  pruefe(fehler.length === 0, "JS-Fehler: " + fehler.join("; "));
  await browser.close();
  console.log("BROWSERTEST OK");
})().catch((e) => { console.error(e.message); process.exit(1); });

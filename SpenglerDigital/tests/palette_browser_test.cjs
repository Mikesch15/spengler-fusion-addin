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
  pruefe(fehler.length === 0, "JS-Fehler: " + fehler.join("; "));
  await browser.close();
  console.log("BROWSERTEST OK");
})().catch((e) => { console.error(e.message); process.exit(1); });

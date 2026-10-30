// Spengler Digital CAD – Palette «Vorlagen & Einstellungen».
// Keine Geometrie und keine Speicherlogik hier: alles läuft über senden() an Python (spengler_cad/ui/palette_backend.py).
"use strict";
let Z = null;          // Zustand vom Backend
let V = null;          // Vorlage im Editor
let M = null;          // Material im Editor
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Fusion legt adsk.fusionSendData teils erst NACH dem load-Ereignis an – bis zu 10 s darauf warten, statt sofort aufzugeben.
async function verbindungAbwarten() {
  for (let i = 0; i < 50; i++) {
    if ((window.adsk && adsk.fusionSendData) || window.__testSenden) return;
    await new Promise((r) => setTimeout(r, 200));
  }
}
async function senden(aktion, daten) {
  const json = JSON.stringify(daten || {});
  let antwort;
  await verbindungAbwarten();
  if (window.adsk && adsk.fusionSendData) antwort = await adsk.fusionSendData(aktion, json);
  else if (window.__testSenden) antwort = await window.__testSenden(aktion, json);
  else throw new Error("Keine Verbindung zu Fusion (adsk.fusionSendData fehlt) – Palette bitte nur in Fusion öffnen, nicht im Browser; sonst Add-in neu starten.");
  const a = JSON.parse(antwort || "{}");
  if (!a.ok) throw new Error(a.fehler || "Unbekannter Fehler");
  if (a.abgleich) syncAnzeige(a.abgleich);
  return a.daten;
}
function meldung(text, art = "info") {
  $("meldung").innerHTML = text ? `<div class="meldung ${art}">${esc(text)}</div>` : "";
}
async function tun(fn, erfolg) {
  try { const r = await fn(); if (erfolg) meldung(erfolg, "ok"); return r; }
  catch (e) { meldung(e.message, "fehler"); return undefined; }
}
const frage = (text) => senden("frage", { text }).catch(() => false);
const zahlOderNull = (v) => (v === "" || v == null ? null : Number(String(v).replace(",", ".")));
const zahlOderText = (v) => { const s = String(v ?? "").trim(); if (s === "") return null; const n = Number(s.replace(",", ".")); return Number.isFinite(n) ? n : s; };

function syncAnzeige(s) {   // kleiner Hinweis oben: Ergebnis des automatischen Abgleichs nach einer Änderung
  const t = !s.ok ? "⚠ Abgleich: " + s.text : s.nur_lokal && s.nur_lokal.length ? "⚠ nur auf diesem PC: " + s.nur_lokal.join(", ")
    : s.konflikte && s.konflikte.length ? "⚠ Konflikt-Kopie: " + s.konflikte.join(", ") : "✓ mit der App abgeglichen";
  $("syncStatus").textContent = t;
  $("syncStatus").title = s.text || "";
}
async function zeigeKonto() {
  const k = await senden("konto");
  $("kAbgemeldet").style.display = k.angemeldet ? "none" : "block";
  $("kAngemeldet").style.display = k.angemeldet ? "block" : "none";
  const c = Z.einstellungen.cloud || {};
  $("kSyncStart").checked = c.syncOnStart !== false; $("kUpdStart").checked = c.updateCheckOnStart !== false;
  if (!k.angemeldet) { $("syncStatus").textContent = "nur lokal (nicht angemeldet)"; return; }
  const ko = k.konto;
  $("kWer").innerHTML = `Angemeldet als <b>${esc(ko.name || ko.benutzer)}</b> (${esc(ko.rolle)}) · Firma <b>${esc(ko.firma || "–")}</b>`;
  $("kRecht").textContent = ko.darf_aendern ? "Sie dürfen Vorlagen ändern – Änderungen gehen an alle PCs der Firma."
    : "Nur lesen: In der App ist «Vorlagen ändern» für Ihr Konto nicht freigegeben. Eigene Änderungen bleiben auf diesem PC.";
  if (k.letzterAbgleich) $("kBericht").innerHTML = `<div class="meldung info">Letzter Abgleich ${esc(k.letzterAbgleich.zeit)}:\n${esc(k.letzterAbgleich.text)}</div>`;
  if (!$("syncStatus").textContent || $("syncStatus").textContent.startsWith("nur lokal")) $("syncStatus").textContent = "angemeldet: " + (ko.firma || "");
}
async function laden() {
  Z = await senden("init");
  $("version").textContent = "Version " + Z.version;
  $("ordner").textContent = Z.datenordner;
  document.body.classList.toggle("experte", Z.einstellungen.ui.mode === "experte");
  $("experte").checked = Z.einstellungen.ui.mode === "experte";
  zeigeVorlagen(); zeigeDetails(); zeigeMaterialien(); zeigeEinstellungen(); zeigeSicherung();
  await zeigeKonto().catch((e) => meldung(e.message, "fehler"));
}
$("kAnmelden").onclick = async () => {
  const r = await tun(() => senden("anmelden", { benutzer: $("kBenutzer").value, passwort: $("kPasswort").value }));
  $("kPasswort").value = "";
  if (r) { await laden(); meldung("Angemeldet. " + r.abgleich.text, "ok"); }
};
$("kAbmelden").onclick = async () => {
  if (!(await frage("Abmelden? Die Vorlagen bleiben auf diesem PC, werden aber nicht mehr abgeglichen."))) return;
  await tun(() => senden("abmelden")); await laden(); meldung("Abgemeldet.", "ok");
};
$("kAbgleich").onclick = async () => {
  const r = await tun(() => senden("abgleichen"));
  if (r) { await laden(); meldung(r.text, r.fehler.length || r.konflikte.length ? "fehler" : "ok"); }
};
$("kUpdate").onclick = async () => { const r = await tun(() => senden("update_installieren")); if (r) meldung(r, "ok"); };
for (const [id, k] of [["kSyncStart", "syncOnStart"], ["kUpdStart", "updateCheckOnStart"]]) {
  $(id).addEventListener("change", async () => {
    Z.einstellungen.cloud = Object.assign(Z.einstellungen.cloud || {}, { [k]: $(id).checked });
    await tun(() => senden("einstellungen_speichern", { einstellungen: Z.einstellungen }), "Gespeichert.");
  });
}

// ------------------------------------------------------------------ Kantenvorlagen
function zeigeVorlagen() {
  const f = $("vFilter").value;
  $("vFilter").innerHTML = '<option value="">Alle Kategorien</option>' + Z.kategorien.map((k) => `<option ${k === f ? "selected" : ""}>${esc(k)}</option>`).join("");
  $("katListe").innerHTML = Z.kategorien.map((k) => `<option value="${esc(k)}">`).join("");
  const liste = Z.vorlagen.filter((v) => !f || v.category === f);
  $("vLeer").style.display = Z.vorlagen.length ? "none" : "block";
  $("vListe").style.display = Z.vorlagen.length ? "" : "none";
  $("vListe").querySelector("tbody").innerHTML = liste.map((v) => `<tr data-id="${esc(v.id)}" class="${V && V.id === v.id ? "gewaehlt" : ""}">
    <td><input type="checkbox" class="vWahl" value="${esc(v.id)}"></td><td>${v.favorite ? "★" : ""}</td>
    <td>${esc(v.name)}${v._nurLesen ? ' <span class="klein">(schreibgeschützt)</span>' : ""}${v._ebene !== "benutzer" ? ` <span class="klein">[${esc(v._ebene)}]</span>` : ""}</td>
    <td>${esc(v.category)}</td><td>${esc(v.version)}</td><td class="klein">${esc(kurzText(v.operations))}</td>
    <td class="mini" title="${esc(v._vorschauGrund || "")}">${v._vorschau || '<span class="klein">–</span>'}</td></tr>`).join("");
  const mats = Z.materialien.map((m) => `<option value="${esc(m.id)}">${esc(m.name)} (${m.thickness} mm)</option>`).join("");
  const alt = $("eMat").value;
  $("eMat").innerHTML = '<option value="">– ohne –</option>' + mats;
  $("eMat").value = Z.materialien.some((m) => m.id === alt) ? alt : (Z.einstellungen.defaultMaterialId || "");
}
function kurzText(ops) {
  return (ops || []).map((o) => {
    let w = o.typ === "umschlag" ? (String(o.winkel).trim().startsWith("-") ? "U-" : "U+") : (typeof o.winkel === "string" ? `{${o.winkel}}` : o.winkel);
    if (o.radius !== null && o.radius !== undefined && o.radius !== "") w += "r" + o.radius;
    return `${w} ${o.laenge}`;
  }).join(" ");
}
function oeffneEditor(v) {
  V = JSON.parse(JSON.stringify(v));
  $("editor").style.display = "block";
  $("eName").value = V.name || ""; $("eBeschr").value = V.description || ""; $("eKat").value = V.category || "";
  $("eFav").checked = !!V.favorite; $("eVersion").textContent = V.version ? `Version ${V.version}` : "";
  $("eKante").value = V.connection?.edgeType || "gerade";
  $("eTmin").value = V.constraints?.thicknessMin ?? ""; $("eTmax").value = V.constraints?.thicknessMax ?? "";
  $("eLmin").value = V.constraints?.edgeLengthMin ?? "";
  $("eCuts").checked = !!V.manufacturing?.cutsAllowed; $("eNotiz").value = V.metadata?.notes || "";
  $("eKurz").value = kurzText(V.operations);
  $("ePruefErg").innerHTML = "";
  for (const id of ["eSpeichern", "eUmben", "eLoeschen"]) $(id).disabled = !!V._nurLesen;
  zeigeParameter(); zeigeOps(); zeigeVorlagen(); vorschau();
}
let vorschauUhr = null;
function vorschau() {   // Querschnitt mit Standardwerten, leicht verzögert beim Tippen
  clearTimeout(vorschauUhr);
  vorschauUhr = setTimeout(async () => {
    if (!V) return;
    try {
      const r = await senden("vorschau", { vorlage: editorLesen(), materialId: $("eMat").value || null });
      $("eVorschau").innerHTML = r.svg ? r.svg + `<div class="klein">${r.material ? "Material " + esc(r.material) : "Skizze (ohne Materialprofil: t = 1 mm, Ri = t)"} · Standardwerte</div>`
        : `<span class="klein">Keine Vorschau: ${esc(r.grund)}</span>`;
    } catch (e) { $("eVorschau").innerHTML = `<span class="klein">Keine Vorschau: ${esc(e.message)}</span>`; }
  }, 250);
}
function zeigeParameter() {
  $("pTab").querySelector("tbody").innerHTML = V.parameters.map((p, i) => `<tr>
    <td><input data-p="${i}" data-f="name" value="${esc(p.name)}" size="6"></td>
    <td><input data-p="${i}" data-f="label" value="${esc(p.label)}" size="14"></td>
    <td><select data-p="${i}" data-f="unit">${["mm", "deg", ""].map((u) => `<option value="${u}" ${p.unit === u ? "selected" : ""}>${u || "–"}</option>`).join("")}</select></td>
    <td><input type="number" step="any" data-p="${i}" data-f="default" value="${p.default ?? ""}"></td>
    <td><input type="number" step="any" data-p="${i}" data-f="min" value="${p.min ?? ""}"></td>
    <td><input type="number" step="any" data-p="${i}" data-f="max" value="${p.max ?? ""}"></td>
    <td><input type="checkbox" data-p="${i}" data-f="variable" ${p.variable !== false ? "checked" : ""}></td>
    <td><button data-pdel="${i}">✕</button></td></tr>`).join("");
}
function zeigeOps() {
  $("oTab").querySelector("tbody").innerHTML = V.operations.map((o, i) => `<tr>
    <td>${i + 1}</td>
    <td><select data-o="${i}" data-f="typ"><option value="flansch" ${o.typ === "flansch" ? "selected" : ""}>Flansch</option><option value="umschlag" ${o.typ === "umschlag" ? "selected" : ""}>Umschlag</option></select></td>
    <td><input data-o="${i}" data-f="winkel" value="${esc(o.winkel)}" size="7"></td>
    <td><input data-o="${i}" data-f="laenge" value="${esc(o.laenge)}" size="9"></td>
    <td><input data-o="${i}" data-f="radius" value="${esc(o.radius ?? "")}" size="6"></td>
    <td>${o.typ === "umschlag" ? "" : `<select data-o="${i}" data-f="bezug">${[["", "Standard"], ["aussen", "aussen"], ["innen", "innen"], ["tangential", "tangential"]].map(([w, t]) => `<option value="${w}" ${(o.bezug || "") === w ? "selected" : ""}>${t}</option>`).join("")}</select>`}</td>
    <td><select data-o="${i}" data-f="lage">${[["", "Standard"], ["kante", "benachbart (Kante)"], ["innen", "innen"], ["aussen", "aussen"], ["tangential", "tangential"]].map(([w, t]) => `<option value="${w}" ${(o.lage || "") === w ? "selected" : ""}>${t}</option>`).join("")}</select></td>
    <td><button data-oauf="${i}">↑</button><button data-oab="${i}">↓</button><button data-odel="${i}">✕</button></td></tr>`).join("");
}
function editorLesen() {
  V.name = $("eName").value.trim(); V.description = $("eBeschr").value; V.category = $("eKat").value.trim() || "Ohne Kategorie";
  V.favorite = $("eFav").checked;
  V.connection = Object.assign(V.connection || {}, { edgeType: $("eKante").value });
  V.constraints = Object.assign(V.constraints || {}, { thicknessMin: zahlOderNull($("eTmin").value), thicknessMax: zahlOderNull($("eTmax").value), edgeLengthMin: zahlOderNull($("eLmin").value) });
  V.manufacturing = Object.assign(V.manufacturing || {}, { cutsAllowed: $("eCuts").checked });
  V.metadata = Object.assign(V.metadata || {}, { notes: $("eNotiz").value });
  return V;
}
document.addEventListener("input", (e) => {
  const t = e.target;
  if (V && t.closest && t.closest("#editor")) vorschau();
  if (t.dataset.p !== undefined) {
    const p = V.parameters[+t.dataset.p], f = t.dataset.f;
    p[f] = t.type === "checkbox" ? t.checked : ["default", "min", "max"].includes(f) ? zahlOderNull(t.value) : t.value;
  }
  if (t.dataset.o !== undefined) {
    const o = V.operations[+t.dataset.o], f = t.dataset.f;
    o[f] = f === "typ" ? t.value : (f === "bezug" || f === "lage") ? (t.value || undefined) : zahlOderText(t.value);
    if (f === "typ" && t.value === "umschlag") { o.winkel = 180; delete o.bezug; }   // Umschlag hat keinen Massbezug
    $("eKurz").value = kurzText(V.operations);
  }
});
document.addEventListener("change", (e) => { if (e.target.dataset.o !== undefined && e.target.dataset.f === "typ") zeigeOps(); });
document.addEventListener("click", async (e) => {
  const t = e.target;
  if (t.dataset.tab) {
    document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("aktiv", b === t));
    document.querySelectorAll("section").forEach((s) => s.classList.toggle("aktiv", s.id === t.dataset.tab));
    meldung("");
  }
  if (t.dataset.hilfe) meldung(await tun(() => senden("hilfe", { thema: t.dataset.hilfe })), "info");
  if (t.dataset.pdel !== undefined) { V.parameters.splice(+t.dataset.pdel, 1); zeigeParameter(); }
  if (t.dataset.odel !== undefined) { V.operations.splice(+t.dataset.odel, 1); zeigeOps(); $("eKurz").value = kurzText(V.operations); }
  for (const [k, d] of [["oauf", -1], ["oab", 1]]) {
    if (t.dataset[k] !== undefined) {
      const i = +t.dataset[k], j = i + d;
      if (j >= 0 && j < V.operations.length) { [V.operations[i], V.operations[j]] = [V.operations[j], V.operations[i]]; zeigeOps(); $("eKurz").value = kurzText(V.operations); }
    }
  }
  const zeile = t.closest("#vListe tbody tr");
  if (zeile && t.type !== "checkbox") oeffneEditor(Z.vorlagen.find((v) => v.id === zeile.dataset.id));
  const mz = t.closest("#mListe tbody tr");
  if (mz) oeffneMaterial(Z.materialien.find((m) => m.id === mz.dataset.id));
  if (t.dataset.dkopie) await tun(async () => { await senden("duplizieren", { id: t.dataset.dkopie, typ: "detailvorlage" }); await laden(); }, "Kopie erstellt.");
  if (t.dataset.dloesch && await frage("3D-Detailvorlage wirklich löschen? Sie wird in den Papierkorb verschoben.")) {
    await tun(async () => { await senden("loeschen", { id: t.dataset.dloesch, typ: "detailvorlage", bestaetigt: true }); await laden(); }, "In den Papierkorb verschoben.");
  }
  if (t.dataset.wieder && await frage("Sicherung «" + t.dataset.wieder + "» wiederherstellen? Der aktuelle Stand wird vorher automatisch gesichert.")) {
    await tun(async () => { await senden("wiederherstellen", { datei: t.dataset.wieder, bestaetigt: true }); await laden(); }, "Wiederhergestellt. Der vorherige Stand wurde gesichert.");
  }
  if (V && t.closest && t.closest("#editor") && (t.dataset.odel !== undefined || t.dataset.oauf !== undefined || t.dataset.oab !== undefined || t.dataset.pdel !== undefined)) vorschau();
  if (t.dataset.pk) await tun(async () => { await senden("papierkorb_zurueck", { datei: t.dataset.pk }); await laden(); }, "Wiederhergestellt.");
});
$("experte").addEventListener("change", async () => {
  Z.einstellungen.ui.mode = $("experte").checked ? "experte" : "standard";
  document.body.classList.toggle("experte", $("experte").checked);
  await tun(() => senden("einstellungen_speichern", { einstellungen: Z.einstellungen }));
});
$("vFilter").addEventListener("change", zeigeVorlagen);
$("vNeu").onclick = async () => { const v = await tun(() => senden("neue_vorlage", { name: "Neue Vorlage" })); if (v) { oeffneEditor(v); $("eName").select(); } };
$("pNeu").onclick = () => { V.parameters.push({ name: "", label: "", unit: "mm", default: null, min: null, max: null, description: "", variable: true }); zeigeParameter(); };
const schrittNeu = (op) => { V.operations.push(op); zeigeOps(); $("eKurz").value = kurzText(V.operations); vorschau(); };
$("oNeu").onclick = () => schrittNeu({ typ: "flansch", winkel: 90, laenge: 10, radius: null });
$("oNeuU").onclick = () => schrittNeu({ typ: "umschlag", winkel: 180, laenge: 7, radius: null });
$("eKurzUeb").onclick = async () => {
  const r = await tun(() => senden("kurzschrift", { text: $("eKurz").value }));
  if (!r) return;
  const alt = V.operations;   // Mass/Lage der bisherigen Schritte bleiben erhalten (die Kurzschrift kennt sie nicht)
  V.operations = r.operations.map((o, i) => (alt[i] && alt[i].typ === o.typ ? Object.assign(o, { bezug: alt[i].bezug, lage: alt[i].lage }) : o));
  for (const n of r.parameter) if (!V.parameters.some((p) => p.name === n)) V.parameters.push({ name: n, label: n, unit: "mm", default: null, min: null, max: null, description: "", variable: true });
  zeigeParameter(); zeigeOps(); vorschau();
  meldung(r.parameter.length ? "Übernommen. Neue Parameter bitte mit Wert/Bereich ergänzen: " + r.parameter.join(", ") : "Übernommen.", "ok");
};
$("ePruef").onclick = async () => {
  editorLesen();
  const r = await tun(() => senden("pruefen", { vorlage: V, materialId: $("eMat").value || null }));
  if (!r) return;
  let h = r.fehler.length ? `<div class="meldung fehler">${esc(r.fehler.join("\n"))}</div>` : '<div class="meldung ok">Vorlage ist gültig.</div>';
  if (r.warnungen.length) h += `<div class="meldung info">${esc(r.warnungen.join("\n"))}</div>`;
  if (r.aufgeloest) h += `<div class="meldung info">Mit Standardwerten: ${esc(r.aufgeloest)}${r.zugabe != null ? ` · Abwicklungszugabe theoretisch ${r.zugabe.toFixed(1)} mm` : ""}</div>`;
  if (!r.fehler.length) { const p = await tun(() => senden("bauplan_test", { vorlage: V, materialId: $("eMat").value || null })); if (p) h += `<div class="meldung info">${esc(p)}</div>`; }
  $("ePruefErg").innerHTML = h;
};
$("eSpeichern").onclick = async () => {
  editorLesen();
  const v = await tun(() => senden("speichern", { vorlage: V }));
  if (v) { await laden(); oeffneEditor(Z.vorlagen.find((x) => x.id === v.id) || v); meldung(`Gespeichert (Version ${v.version}).`, "ok"); }
};
$("eAbbrechen").onclick = () => { V = null; $("editor").style.display = "none"; zeigeVorlagen(); };
$("eKopie").onclick = async () => { if (!V.id || !Z.vorlagen.some((x) => x.id === V.id)) return meldung("Erst speichern, dann duplizieren.", "fehler");
  const v = await tun(() => senden("duplizieren", { id: V.id })); if (v) { await laden(); oeffneEditor(v); meldung("Kopie erstellt – das Original ist unverändert.", "ok"); } };
$("eUmben").onclick = async () => { const n = $("eName").value.trim(); const v = await tun(() => senden("umbenennen", { id: V.id, name: n })); if (v) { await laden(); oeffneEditor(v); meldung("Umbenannt.", "ok"); } };
$("eVers").onclick = async () => { const l = await tun(() => senden("versionen", { id: V.id })); if (l) meldung(l.length ? "Frühere Versionen:\n" + l.map((x) => `Version ${x.version} (${x.modified}): ${kurzText(x.operations)}`).join("\n") : "Keine früheren Versionen.", "info"); };
$("eLoeschen").onclick = async () => {
  if (!(await frage(`Vorlage «${V.name}» wirklich löschen?\nSie wird in den Papierkorb verschoben und kann unter «Sicherung» wiederhergestellt werden.`))) return;
  if (await tun(() => senden("loeschen", { id: V.id, bestaetigt: true }), "In den Papierkorb verschoben.") !== undefined) { V = null; $("editor").style.display = "none"; await laden(); }
};
$("vExport").onclick = async () => {
  const ids = [...document.querySelectorAll(".vWahl:checked")].map((c) => c.value);
  if (!ids.length) return meldung("Bitte zuerst Vorlagen ankreuzen.", "fehler");
  const n = await tun(() => senden("export_dialog", { ids })); if (n) meldung(`${n} Vorlage(n) exportiert.`, "ok");
};
$("vImport").onclick = async () => {
  const r = await tun(() => senden("import_dialog", {})); if (!r) return;
  await laden();
  meldung(`Importiert: ${r.importiert.length}, als Kopie: ${r.kopien.length}` + (r.abgelehnt.length ? `\nAbgelehnt:\n${r.abgelehnt.map((a) => a.join(": ")).join("\n")}` : ""), r.abgelehnt.length ? "fehler" : "ok");
};

// ------------------------------------------------------------------ 3D-Details
function zeigeDetails() {
  $("dLeer").style.display = Z.details.length ? "none" : "block";
  $("dListe").style.display = Z.details.length ? "" : "none";
  $("dListe").querySelector("tbody").innerHTML = Z.details.map((d) => `<tr><td>${esc(d.name)}</td><td>${esc(d.category)}</td><td>${esc(d.version)}</td>
    <td class="klein">${esc(d.parameters.map((p) => p.name).join(", "))}</td>
    <td><button data-dkopie="${esc(d.id)}">Duplizieren</button> <button class="gefahr" data-dloesch="${esc(d.id)}">Löschen…</button></td></tr>`).join("");
}

// ------------------------------------------------------------------ Materialien
function zeigeMaterialien() {
  $("mLeer").style.display = Z.materialien.length ? "none" : "block";
  $("mListe").style.display = Z.materialien.length ? "" : "none";
  $("mListe").querySelector("tbody").innerHTML = Z.materialien.map((m) => `<tr data-id="${esc(m.id)}"><td>${esc(m.name)}</td><td>${m.thickness}</td>
    <td>${m.innerRadius ?? "–"}</td><td>${m.kFactor ?? "–"}</td><td>${m.density ?? "–"}</td>
    <td class="klein">${esc((m.sheets || []).map((s) => s.join("×")).join(", "))}</td><td class="klein">${esc((m.coils || []).join(", "))}</td></tr>`).join("");
}
function oeffneMaterial(m) {
  M = JSON.parse(JSON.stringify(m));
  $("mEditor").style.display = "block";
  $("mName").value = M.name; $("mWerk").value = M.material || ""; $("mT").value = M.thickness;
  $("mD").value = M.density ?? ""; $("mRi").value = M.innerRadius ?? ""; $("mK").value = M.kFactor ?? "";
  $("mRegel").value = M.sheetMetalRule || ""; $("mHinw").value = M.notes || "";
  $("mTafeln").value = (M.sheets || []).map((s) => s.join("x")).join("; ");
  $("mRollen").value = (M.coils || []).join("; ");
  const g = M.formingLimits || {};
  $("mPz").value = $("mPa").value = $("mPb").value = ""; $("mPErg").innerHTML = "";
  $("mStau").value = g.shrinkMaxPercent ?? ""; $("mStr").value = g.stretchMaxPercent ?? ""; $("mQuelle").value = g.source || "";
}
$("mNeu").onclick = async () => { const m = await tun(() => senden("material_neu", { name: "Neues Material", dicke: 1 })); if (m) { m.thickness = ""; oeffneMaterial(m); } };
$("mSchliessen").onclick = () => { M = null; $("mEditor").style.display = "none"; };
$("mSpeichern").onclick = async () => {
  const liste = (s, n) => s.split(/[;,]/).map((x) => x.trim()).filter(Boolean).map(n);
  M.name = $("mName").value.trim(); M.material = $("mWerk").value; M.thickness = zahlOderNull($("mT").value);
  M.density = zahlOderNull($("mD").value); M.innerRadius = zahlOderNull($("mRi").value); M.kFactor = zahlOderNull($("mK").value);
  M.sheetMetalRule = $("mRegel").value; M.notes = $("mHinw").value;
  M.sheets = liste($("mTafeln").value, (x) => x.toLowerCase().split(/[x×*]/).map((y) => Number(y.trim())));
  M.coils = liste($("mRollen").value, Number);
  M.formingLimits = { shrinkMaxPercent: zahlOderNull($("mStau").value), stretchMaxPercent: zahlOderNull($("mStr").value), source: $("mQuelle").value };
  const m = await tun(() => senden("material_speichern", { material: M }), "Materialprofil gespeichert.");
  if (m) { await laden(); oeffneMaterial(m); }
};
$("mPrech").onclick = async () => {
  const r = await tun(() => senden("k_faktor", { zuschnitt: $("mPz").value, a: $("mPa").value, b: $("mPb").value, t: $("mT").value, ri: $("mRi").value }));
  if (!r) { $("mPErg").innerHTML = ""; return; }
  meldung("");
  $("mPErg").innerHTML = `<div class="meldung ${r.plausibel ? "ok" : "fehler"}">K-Faktor: <b>${r.k.toFixed(3)}</b> (Biegeverkürzung ${r.verkuerzung.toFixed(2)} mm)` +
    (r.plausibel ? ' <button id="mPueb">In K-Faktor übernehmen</button>' : "<br>" + esc(r.hinweis)) + "</div>";
  if (r.plausibel) $("mPueb").onclick = () => { $("mK").value = r.k.toFixed(3); meldung("K-Faktor eingetragen – mit «Speichern» sichern.", "ok"); };
};
$("mLoeschen").onclick = async () => {
  if (!M.id || !(await frage(`Materialprofil «${M.name}» wirklich löschen?`))) return;
  if (await tun(() => senden("material_loeschen", { id: M.id, bestaetigt: true }), "Gelöscht (Papierkorb).") !== undefined) { M = null; $("mEditor").style.display = "none"; await laden(); }
};

// ------------------------------------------------------------------ Einstellungen
function zeigeEinstellungen() {
  const e = Z.einstellungen;
  $("sMat").innerHTML = '<option value="">– keins –</option>' + Z.materialien.map((m) => `<option value="${esc(m.id)}" ${m.id === e.defaultMaterialId ? "selected" : ""}>${esc(m.name)}</option>`).join("");
  $("sProj").value = e.projectLibraryFolder || "";
  $("sFuge").value = e.nesting.kerf; $("sRand").value = e.nesting.margin; $("sDreh").checked = !!e.nesting.rotationAllowed;
  $("sLK").value = e.export.layerContour; $("sLT").value = e.export.layerText; $("sDN").value = e.export.fileNamePattern; $("sOrd").value = e.export.folder || "";
  $("sVerf").value = e.forming.defaultProcess;
  const l = e.labels;
  [["sEsp", "spalten"], ["sEze", "zeilen"], ["sEbr", "breite"], ["sEho", "hoehe"], ["sEob", "oben"], ["sEli", "links"], ["sEax", "abstandX"], ["sEay", "abstandY"]].forEach(([id, k]) => { $(id).value = l[k]; });
  etikettenPruefen();
}
function etikettenLesen() {
  const z = (id, ganz) => { const v = zahlOderNull($(id).value); return v === null ? null : (ganz && Number.isInteger(v) ? v : v); };
  return { spalten: z("sEsp", true), zeilen: z("sEze", true), breite: z("sEbr"), hoehe: z("sEho"), oben: z("sEob") ?? 0, links: z("sEli") ?? 0, abstandX: z("sEax") ?? 0, abstandY: z("sEay") ?? 0 };
}
async function etikettenPruefen() {
  try { const r = await senden("etiketten_pruefen", { labels: etikettenLesen() }); $("sEpruef").textContent = r.fehler.length ? "⚠ " + r.fehler.join(" ") : r.text; }
  catch (e) { $("sEpruef").textContent = "⚠ " + e.message; }
}
document.addEventListener("input", (e) => { if (e.target.id && e.target.id.startsWith("sE")) etikettenPruefen(); });
$("sSpeichern").onclick = async () => {
  const e = Z.einstellungen;
  e.defaultMaterialId = $("sMat").value || null; e.projectLibraryFolder = $("sProj").value.trim();
  e.nesting.kerf = zahlOderNull($("sFuge").value) ?? 0; e.nesting.margin = zahlOderNull($("sRand").value) ?? 0; e.nesting.rotationAllowed = $("sDreh").checked;
  e.export.layerContour = $("sLK").value || "ZUSCHNITT"; e.export.layerText = $("sLT").value || "TEXT"; e.export.fileNamePattern = $("sDN").value || "{bauteil}"; e.export.folder = $("sOrd").value.trim();
  e.forming.defaultProcess = $("sVerf").value;
  e.labels = etikettenLesen();
  if (await tun(() => senden("einstellungen_speichern", { einstellungen: e }), "Einstellungen gespeichert.")) await laden();
};

// ------------------------------------------------------------------ Sicherung
function zeigeSicherung() {
  $("bListe").innerHTML = Z.sicherungen.map((s) => `<tr><td>${esc(s)}</td><td><button data-wieder="${esc(s)}">Wiederherstellen…</button></td></tr>`).join("") || '<tr><td class="klein">keine</td></tr>';
  $("pkListe").innerHTML = Z.papierkorb.map((s) => `<tr><td>${esc(s)}</td><td>${s.startsWith("material_") ? "" : `<button data-pk="${esc(s)}">Zurückholen</button>`}</td></tr>`).join("") || '<tr><td class="klein">leer</td></tr>';
}
$("bSichern").onclick = async () => { const p = await tun(() => senden("sicherung", {})); if (p) { await laden(); meldung("Sicherung erstellt:\n" + p, "ok"); } };
$("bSichernUnter").onclick = async () => { const p = await tun(() => senden("sicherung_dialog", {})); if (p) meldung("Sicherung gespeichert:\n" + p, "ok"); };
$("bAusDatei").onclick = async () => { const p = await tun(() => senden("wiederherstellen_dialog", {})); if (p) { await laden(); meldung("Wiederhergestellt. Vorheriger Stand gesichert:\n" + p, "ok"); } };
$("bProto").onclick = () => tun(() => senden("protokoll", {}));

// ------------------------------------------------------------------ Tests
let T = null;
const tOffen = new Set(["0"]);
const tZeichen = { ok: "✓", fehler: "✗", uebersprungen: "–" };
function tFortschritt() {
  const alle = T.plan.flatMap((b) => b.punkte), e = T.ergebnisse;
  const n = (s) => alle.filter((p) => (e[p.id] || {}).status === s).length;
  const bearbeitet = alle.filter((p) => e[p.id] && e[p.id].status !== "offen").length;
  $("tFortschritt").textContent = `${bearbeitet} von ${alle.length} bearbeitet · ✓ ${n("ok")} · ✗ ${n("fehler")} · – ${n("uebersprungen")}`;
  const ungesendet = alle.filter((p) => e[p.id] && !e[p.id].gesendet).length;
  $("tSenden").style.display = ungesendet ? "" : "none";
  $("tSenden").textContent = `${ungesendet} nicht gesendete Ergebnisse senden`;
}
function zeigeTests() {
  if (!T) return;
  $("tListe").innerHTML = T.plan.map((b) => `<details class="tblock" data-block="${b.nr}" ${tOffen.has(String(b.nr)) ? "open" : ""}>
    <summary>${b.nr}. ${esc(b.titel)} <span class="klein">(${b.punkte.filter((p) => (T.ergebnisse[p.id] || {}).status && T.ergebnisse[p.id].status !== "offen").length}/${b.punkte.length})</span></summary>
    ${b.hinweis ? `<div class="klein" style="padding:4px 8px">${esc(b.hinweis)}</div>` : ""}
    ${b.punkte.map((p) => { const e = T.ergebnisse[p.id] || {}; return `<div class="tpunkt s-${e.status || "offen"}" data-tid="${p.id}">
      <div>${esc(p.text)}</div>${p.erwartet ? `<div class="klein">Erwartet: ${esc(p.erwartet)}</div>` : ""}
      <div class="zeile tstatus">${["ok", "fehler", "uebersprungen"].map((s) => `<button data-tstatus="${s}" class="${e.status === s ? "an-" + s : ""}" title="${s}">${tZeichen[s]}</button>`).join("")}
        <input class="tnotiz" placeholder="Notiz / Meldungstext / Messwert" value="${esc(e.notiz || "")}">
        <span class="klein">${e.status && e.status !== "offen" ? (e.gesendet ? "gesendet" : "nur lokal") : ""}</span></div></div>`; }).join("")}
  </details>`).join("");
  tFortschritt();
}
async function ladeTests() { try { T = await senden("testplan"); zeigeTests(); } catch (e) { $("tListe").textContent = "Testplan nicht lesbar: " + e.message; } }
async function testSpeichern(zeile, status) {
  const id = zeile.dataset.tid, p = T.plan.flatMap((b) => b.punkte).find((x) => x.id === id);
  const notiz = zeile.querySelector(".tnotiz").value;
  const r = await tun(() => senden("test_speichern", { test_id: id, text: p.text, status, notiz }));
  if (!r) return;
  T.ergebnisse[id] = r.ergebnis; zeigeTests();
  meldung(r.gesendet ? "" : "Gespeichert, noch nicht übermittelt: " + r.hinweis, r.gesendet ? "info" : "info");
}
$("tListe").addEventListener("click", (e) => {
  const b = e.target.closest("[data-tstatus]"); if (!b) return;
  const zeile = b.closest(".tpunkt"), alt = (T.ergebnisse[zeile.dataset.tid] || {}).status;
  testSpeichern(zeile, alt === b.dataset.tstatus ? "offen" : b.dataset.tstatus);   // nochmal klicken = zurücknehmen
});
$("tListe").addEventListener("change", (e) => {
  if (!e.target.classList.contains("tnotiz")) return;
  const zeile = e.target.closest(".tpunkt"), alt = (T.ergebnisse[zeile.dataset.tid] || {}).status;
  if (alt) testSpeichern(zeile, alt);   // Notiz ändern, Status behalten
});
$("tListe").addEventListener("toggle", (e) => { const d = e.target; if (d.dataset && d.dataset.block !== undefined) d.open ? tOffen.add(d.dataset.block) : tOffen.delete(d.dataset.block); }, true);
$("tSenden").onclick = async () => {
  const r = await tun(() => senden("tests_senden")); if (!r) return;
  T.ergebnisse = r.ergebnisse; zeigeTests();
  meldung(r.offen ? `${r.gesendet} gesendet, ${r.offen} noch offen: ${r.hinweis}` : `${r.gesendet} Ergebnis(se) gesendet.`, r.offen ? "fehler" : "ok");
};

window.addEventListener("load", () => tun(async () => { await laden(); await ladeTests(); }));

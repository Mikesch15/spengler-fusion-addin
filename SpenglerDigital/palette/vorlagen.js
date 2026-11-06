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
  $("kLtUpdate").checked = c.livetestAutoNachUpdate === true; $("kLtFern").checked = c.livetestAutoFern === true;
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
  zeigeVorlagen(); zeigeDetails(); zeigeMaterialien(); zeigeEinstellungen(); zeigeSicherung(); bListeZeigen();
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
for (const [id, k] of [["kSyncStart", "syncOnStart"], ["kUpdStart", "updateCheckOnStart"], ["kLtUpdate", "livetestAutoNachUpdate"], ["kLtFern", "livetestAutoFern"]]) {
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
    <td><input data-o="${i}" data-f="versatz" value="${esc(o.versatz ?? "")}" size="5" placeholder="0"></td>
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
    o[f] = f === "typ" ? t.value : (f === "bezug" || f === "lage") ? (t.value || undefined) : f === "versatz" ? (t.value.trim() ? zahlOderText(t.value) : undefined) : zahlOderText(t.value);
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
  const alt = V.operations;   // Mass/Lage/Versatz der bisherigen Schritte bleiben erhalten (die Kurzschrift kennt sie nicht)
  V.operations = r.operations.map((o, i) => (alt[i] && alt[i].typ === o.typ ? Object.assign(o, { bezug: alt[i].bezug, lage: alt[i].lage, versatz: alt[i].versatz }) : o));
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
  $("mD").value = M.density ?? ""; $("mP").value = M.pricePerKg ?? ""; $("mRi").value = M.innerRadius ?? ""; $("mK").value = M.kFactor ?? "";
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
  M.density = zahlOderNull($("mD").value); M.pricePerKg = zahlOderNull($("mP").value); M.innerRadius = zahlOderNull($("mRi").value); M.kFactor = zahlOderNull($("mK").value);
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
  const au = e.auftrag || { wurzelOrdner: "Projekte", jahresordner: true, unterordner: ["Modelle", "Pläne", "Export"] };
  $("sAWurzel").value = au.wurzelOrdner || ""; $("sAJahr").checked = !!au.jahresordner; $("sAUnter").value = (au.unterordner || []).join(", ");
  const ro = au.rollen || { modelle: "Modelle", plaene: "Pläne", export: "Export" };
  $("sAMod").value = ro.modelle; $("sAPla").value = ro.plaene; $("sAExp").value = ro.export;
  $("sAReq").checked = e.auftragErforderlich !== false;
  $("sALokal").value = au.lokalBasis || ""; $("sANr").checked = au.teilnummerMitAuftrag !== false;
  const ka = e.kalkulation || { stundensatzName: "", stundensatzManuell: null, ruestMinProTeil: 5, minProBiegung: 1.5, minProMeterZuschnitt: 2, zuschlagProzent: 0 };
  $("sKName").value = ka.stundensatzName || ""; $("sKMan").value = ka.stundensatzManuell ?? ""; $("sKRuest").value = ka.ruestMinProTeil;
  $("sKBieg").value = ka.minProBiegung; $("sKSchn").value = ka.minProMeterZuschnitt; $("sKZus").value = ka.zuschlagProzent;
  const pr = e.pruefung || { minSchenkel: 10, minRadiusFaktor: 1 };
  $("sPMin").value = pr.minSchenkel; $("sPRad").value = pr.minRadiusFaktor;
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
  e.auftrag = { wurzelOrdner: $("sAWurzel").value.trim(), jahresordner: $("sAJahr").checked, unterordner: $("sAUnter").value.split(",").map((x) => x.trim()).filter(Boolean),
    rollen: { modelle: $("sAMod").value.trim(), plaene: $("sAPla").value.trim(), export: $("sAExp").value.trim() }, lokalBasis: $("sALokal").value.trim(), teilnummerMitAuftrag: $("sANr").checked };
  e.kalkulation = { stundensatzName: $("sKName").value.trim(), stundensatzManuell: zahlOderNull($("sKMan").value), ruestMinProTeil: zahlOderNull($("sKRuest").value) ?? 5,
    minProBiegung: zahlOderNull($("sKBieg").value) ?? 1.5, minProMeterZuschnitt: zahlOderNull($("sKSchn").value) ?? 2, zuschlagProzent: zahlOderNull($("sKZus").value) ?? 0 };
  e.auftragErforderlich = $("sAReq").checked;
  e.pruefung = { minSchenkel: zahlOderNull($("sPMin").value) ?? 10, minRadiusFaktor: zahlOderNull($("sPRad").value) ?? 1 };
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


// ------------------------------------------------------------------ Berichte: Fehlerberichte und Änderungsprotokoll
$("fbLaden").onclick = async () => {
  const r = await tun(() => senden("fehlerberichte"));
  if (!r) return;
  $("fbListe").innerHTML = r.length ? r.map((b, i) => `<details><summary>${esc((b.geaendert_am || "").replace("T", " ").slice(0, 16))} · v${esc(b.addin_version || "?")} · ${esc((b.text || "").slice(0, 110))}</summary>
    ${b.bild ? `<img alt="Bildschirmfoto" style="max-width:100%;border:1px solid #888" src="data:image/jpeg;base64,${esc(b.bild)}">` : ""}
    <pre style="white-space:pre-wrap;font-size:11px">${esc(b.notiz || "")}\n\n${esc(b.protokoll || "")}</pre></details>`).join("") : "<p class='klein'>Keine Fehlerberichte.</p>";
};
async function aenderungenLaden() {
  const r = await tun(() => senden("aenderungen", { max: 200 }));
  if (!r) return;
  $("acListe").innerHTML = r.map((a) => `<tr><td>${esc((a.zeit || "").replace("T", " "))}</td><td>${esc(a.benutzer)}</td><td>${esc(a.aktion)}</td><td>${esc(a.name)}</td><td>${esc(a.version ?? "")}</td></tr>`).join("") || "<tr><td colspan='5'>Noch keine Änderungen.</td></tr>";
}
$("acLaden").onclick = aenderungenLaden;

$("eProfil").onclick = async () => {
  const r = await tun(() => senden("profilblatt", { vorlage: editorLesen(), materialId: $("eMat").value || null }));
  if (r) await tun(() => senden("datei_oeffnen", { pfad: r.pfad }), "Profilzeichnung geöffnet (Datei: " + r.pfad + ").");
};

// ------------------------------------------------------------------ Projektkarte (alles zum Projekt, nur lesen)
let PK = null;
async function pkListeLaden() {
  const r = await tun(() => senden("projekt_liste"));
  if (!r) return;
  const alt = $("pkWahl").value;
  $("pkWahl").innerHTML = r.projekte.map((p) => `<option value="${esc(p.nummer)}">${esc(p.nummer)} ${esc(p.objekt)}${p.kunde ? " – " + esc(p.kunde) : ""}</option>`).join("");
  $("pkWahl").value = [alt, r.aktiv].find((n) => n && r.projekte.some((p) => p.nummer === n)) || (r.projekte[0] || {}).nummer || "";
}
const pkZeile = (...teile) => teile.filter((x) => x !== undefined && x !== null && x !== "").join(" · ");
function pkAbschnitt(titel, anzahl, inhalt, offen) {
  return `<details class="tblock" ${offen ? "open" : ""}><summary>${esc(titel)} <span class="klein">(${anzahl})</span></summary><div style="padding:6px 10px">${inhalt || '<span class="klein">Nichts vorhanden.</span>'}</div></details>`;
}
function pkZeigen(k) {
  PK = k;
  const h = k.kopf;
  $("pkNeu").innerHTML = k.neu && k.neu.text ? `<div class="meldung info">🔔 Neu seit dem letzten Mal: ${esc(k.neu.text)}</div>` : "";
  const kopf = `<fieldset><legend>${esc(h.nummer)} ${esc(h.objekt)}</legend>
    <div>${pkZeile("Kunde: <b>" + esc(h.kunde || "–") + "</b>", h.archiviert ? "archiviert" : "")}</div>
    <div class="zeile"><label style="min-width:0">Projektstatus</label><select id="pkStatus" data-alt="${esc(h.status_key)}">${[["offen", "Offen"], ["in_arbeit", "In Arbeit"], ["abgeschlossen", "Abgeschlossen"], ["storniert", "Storniert"]].map(([w, t]) => `<option value="${w}"${w === h.status_key ? " selected" : ""}>${t}</option>`).join("")}</select>
      <button id="pkStatusSpeichern">In der App ändern</button>
      <label style="min-width:0">Fertigung (CAD)</label><select id="pkFertigung"><option value="">–</option>${[["offen", "Offen"], ["in_arbeit", "In Arbeit"], ["gefertigt", "Gefertigt"], ["geliefert", "Geliefert"]].map(([w, t]) => `<option value="${w}"${w === h.fertigung ? " selected" : ""}>${t}</option>`).join("")}</select><button id="pkFertigungSpeichern">Setzen</button></div>
    ${h.zugeteilt.length ? `<div class="klein">Zugeteilt: ${esc(h.zugeteilt.join(", "))}</div>` : ""}
    <div class="zeile" style="align-items:flex-start"><label style="min-width:0">Hinweis</label><textarea id="pkHinweis" rows="3" cols="46" data-updated="${esc(h.updated_at)}">${esc(h.hinweis_roh)}</textarea>
      <div><button id="pkHinweisSpeichern">Hinweis speichern</button><br><input id="pkHinweisNeu" size="26" placeholder="Zeile ergänzen …"><button id="pkHinweisErgaenzen">Ergänzen</button></div></div>
    ${k.naechster_termin ? `<div>Nächster Termin: <b>${esc(k.naechster_termin.titel)}</b>, ${esc(k.naechster_termin.wann)}${k.naechster_termin.ort ? ", " + esc(k.naechster_termin.ort) : ""}</div>` : ""}
    <div class="klein">${k.zaehler.massaufnahmen} Massaufnahmen, davon ${k.zaehler.aktiv} aktiv</div></fieldset>`;
  const ma = k.massaufnahmen.map((m) => `<div class="zeile" style="border-bottom:1px solid var(--rand);padding:4px 0"><div style="flex:1;min-width:200px">
      <b>${esc(m.art)}</b> ${esc(m.titel)}<div class="klein">${esc(pkZeile(m.zeichen + " " + m.status, m.datum, ...m.stufen, m.montage ? "Montage " + m.montage : "", m.cad_teile ? m.cad_teile + " CAD-Teil(e)" : "", m.cad_auftraege ? m.cad_auftraege + " an das CAD gesendet" : "", m.archiviert ? "archiviert" : ""))}</div></div>
      ${m.pfade.length ? `<button data-pkfotos="${esc(m.id)}">📷 Fotos/Skizzen (${m.pfade.length})</button>` : ""}</div><div id="pkF${esc(m.id)}"></div>`).join("");
  const cad = k.cad.teile.map((t) => `<div class="zeile"><b>${esc(t.label)}</b> ${esc(t.name)} <span class="klein">${esc(pkZeile(t.stueck + " Stück", t.material, t.app, t.werkstatt ? "Werkstatt: " + t.werkstatt : ""))}</span></div>`).join("")
    + k.cad.auftraege.map((a) => `<div class="zeile">📤 <b>${esc(a.titel)}</b> <span class="klein">${esc(pkZeile(a.laenge + " mm", a.stueck + " Stück", a.status, a.gebaut, a.werkstatt ? "Werkstatt: " + a.werkstatt : ""))}</span></div>`).join("");
  const rap = k.rapporte.map((r) => `<div class="zeile"><b>${esc(r.datum)}</b> <span class="klein">${esc(pkZeile(r.stunden + " h", r.personen.join(", "), r.material ? r.material + " Material" : "", r.arbeiten.join("; ")))}</span></div>`).join("");
  const ter = `<div class="zeile"><button id="pkTerminNeu">+ Termin hinzufügen</button></div><div id="pkTerminForm"></div>` + k.termine.map((t) => `<div class="zeile"><span style="flex:1"><b>${esc(t.titel)}</b> <span class="klein">${esc(pkZeile(t.wann, t.ort, t.mitarbeiter.join(", "), t.quelle !== "app" ? "aus " + t.quelle + " (nur in der App/Kalender änderbar)" : ""))}</span></span>${t.aenderbar ? `<button data-pktermin="${esc(t.id)}">Ändern</button>` : ""}</div>`).join("");
  const dat = k.dateien.map((f) => `<div class="zeile"><span style="flex:1">${esc(f.name)} <span class="klein">${esc(pkZeile(f.groesse, f.datum))}</span></span><button data-pkdatei="${esc(f.pfad)}" data-pkname="${esc(f.name)}">Öffnen</button></div>`).join("");
  const off = k.offerten.map((o) => `<div class="zeile"><b>${esc(o.nr)}</b> ${esc(o.titel)} <span class="klein">${esc(pkZeile(o.datum, o.gueltig_bis ? "gültig bis " + o.gueltig_bis : "", o.positionen + " Positionen", o.pdf))}</span></div>`).join("");
  const lei = k.leistungen.map((l) => `<div class="zeile">${esc(l.bezeichnung)} <span class="klein">${esc(pkZeile(l.status, l.menge != null ? l.menge + " " + l.einheit : "", l.ausgefuehrt != null ? "ausgeführt " + l.ausgefuehrt : ""))}</span></div>`).join("");
  $("pkKarte").innerHTML = kopf + pkAbschnitt("Massaufnahmen", k.massaufnahmen.length, ma, true) + pkAbschnitt("CAD und Werkstatt", k.cad.teile.length + k.cad.auftraege.length, cad, true)
    + pkAbschnitt("Termine", k.termine.length, ter, true) + pkAbschnitt("Rapporte", k.rapporte.length, rap) + pkAbschnitt("Dateien", k.dateien.length, dat)
    + pkAbschnitt("Offerten", k.offerten.length, off) + pkAbschnitt("Leistungen", k.leistungen.length, lei)
    + (k.hinweise.length ? `<div class="klein">${esc(k.hinweise.join(" · "))}</div>` : "");
  $("pkStand").textContent = "Stand " + new Date().toLocaleTimeString().slice(0, 5);
}
async function pkLaden() {
  const nr = $("pkWahl").value;
  if (!nr) return;
  const k = await tun(() => senden("projekt_karte", { nummer: nr }));
  if (k) pkZeigen(k);
}
async function pkFotos(mid) {
  const m = PK.massaufnahmen.find((x) => String(x.id) === String(mid));
  const box = $("pkF" + mid);
  if (!m || !box) return;
  box.innerHTML = '<span class="klein">Lädt…</span>';
  const r = await tun(() => senden("projekt_fotos", { pfade: m.pfade }));
  if (!r) { box.innerHTML = ""; return; }
  box.innerHTML = '<div class="zeile">' + r.bilder.map((b, i) => `<div style="text-align:center"><img src="${b.url}" data-pkgross="1" style="max-width:150px;max-height:120px;border:1px solid var(--rand);border-radius:6px;cursor:zoom-in"><div>
    <button data-pkfusion="${esc(b.pfad)}" data-pktitel="${esc(m.art + " " + m.titel)}" title="als Referenzbild in das aktive Fusion-Dokument legen">In Fusion einfügen</button>
    <button data-pkdatei="${esc(b.pfad)}" data-pkname="">Speichern</button></div></div>`).join("") + "</div>" + (r.fehler.length ? `<div class="klein">${esc(r.fehler.join(" · "))}</div>` : "");
}
// ---- Änderungen in der App: immer mit Rückfrage, danach wird die Karte neu geladen
async function pkAenderung(frageText, aktion, daten, erfolg) {
  if (!(await frage(frageText))) return false;
  const r = await tun(() => senden(aktion, daten), erfolg);
  if (r !== undefined) { await pkLaden(); meldung(erfolg, "ok"); return true; }
  return false;
}
function pkTerminForm(t) {
  const f = t || { id: "", titel: "", start: "", ende: "", start_zeit: "", ende_zeit: "", ort: "", notiz: "" };
  const tag = (iso) => (iso && /^\d{4}-\d\d-\d\d$/.test(iso) ? `${+iso.slice(8)}.${+iso.slice(5, 7)}.${iso.slice(0, 4)}` : iso || "");
  $("pkTerminForm").innerHTML = `<fieldset><legend>${f.id ? "Termin ändern" : "Neuer Termin"}</legend>
    <div class="zeile"><label>Titel</label><input id="ptTitel" size="34" value="${esc(f.titel)}"></div>
    <div class="zeile"><label>Beginn</label><input id="ptStart" size="11" placeholder="4.11.2026" value="${esc(tag(f.start))}"> <input id="ptStartZ" size="6" placeholder="07:30" value="${esc(f.start_zeit)}">
      <label style="min-width:0">Ende</label><input id="ptEnde" size="11" placeholder="wie Beginn" value="${esc(f.ende && f.ende !== f.start ? tag(f.ende) : "")}"> <input id="ptEndeZ" size="6" placeholder="16:00" value="${esc(f.ende_zeit)}"></div>
    <div class="zeile"><label>Ort</label><input id="ptOrt" size="34" value="${esc(f.ort || "")}"></div>
    <div class="zeile"><label>Notiz</label><input id="ptNotiz" size="50" value="${esc(f.notiz || "")}"></div>
    <div class="zeile"><button class="haupt" id="ptSpeichern" data-id="${esc(f.id)}">In der App speichern</button><button id="ptAbbrechen">Abbrechen</button></div></fieldset>`;
}
$("pkKarte").addEventListener("click", async (ev) => {
  const t = ev.target, k = PK; if (!k) return;
  const h = k.kopf;
  if (t.id === "pkStatusSpeichern") { const neu = $("pkStatus").value, alt = $("pkStatus").dataset.alt; if (neu === alt) return meldung("Der Status ist schon so gesetzt.", "info");
    return pkAenderung(`Projektstatus in der App von «${alt}» auf «${neu}» ändern?`, "projekt_status", { id: h.id, neu, alt }, "Projektstatus geändert."); }
  if (t.id === "pkFertigungSpeichern") { const s = $("pkFertigung").value; if (!s) return;
    return pkAenderung(`Fertigungsstatus von Auftrag ${h.nummer} auf «${s}» setzen?`, "auftrag_status", { nummer: h.nummer, status: s }, "Fertigungsstatus gesetzt."); }
  if (t.id === "pkHinweisSpeichern") { const x = $("pkHinweis").value;
    return pkAenderung(x.trim() ? "Den Hinweis im Projekt der App ersetzen?" : "Den Hinweis im Projekt der App LÖSCHEN?", "projekt_hinweis", { id: h.id, text: x, modus: "ersetzen", updated_at: $("pkHinweis").dataset.updated }, "Hinweis gespeichert."); }
  if (t.id === "pkHinweisErgaenzen") { const x = $("pkHinweisNeu").value.trim(); if (!x) return meldung("Bitte erst den Text zum Ergänzen eingeben.", "fehler");
    return pkAenderung("Diese Zeile zum Hinweis im Projekt der App ergänzen?\n\n" + x, "projekt_hinweis", { id: h.id, text: x, modus: "ergaenzen", alt: h.hinweis_roh, updated_at: $("pkHinweis").dataset.updated }, "Hinweis ergänzt."); }
  if (t.id === "pkTerminNeu") return pkTerminForm(null);
  if (t.dataset.pktermin) return pkTerminForm(k.termine.find((x) => String(x.id) === t.dataset.pktermin));
  if (t.id === "ptAbbrechen") { $("pkTerminForm").innerHTML = ""; return; }
  if (t.id === "ptSpeichern") {
    const termin = { titel: $("ptTitel").value, start_datum: $("ptStart").value, start_zeit: $("ptStartZ").value, ende_datum: $("ptEnde").value, ende_zeit: $("ptEndeZ").value, ort: $("ptOrt").value, notiz: $("ptNotiz").value };
    const alt = t.dataset.id ? (k.termine.find((x) => String(x.id) === t.dataset.id) || {}).roh : null;      // Werte, wie die Karte sie gelesen hat – Bedingung für das Ändern
    return pkAenderung(`Termin «${termin.titel}» (${termin.start_datum}) ${t.dataset.id ? "in der App ändern" : "in der App anlegen"}?`, "termin_speichern", { id: t.dataset.id || null, project_id: h.id, termin, alt }, t.dataset.id ? "Termin geändert." : "Termin angelegt.");
  }
});
$("pkLaden").onclick = pkLaden;
$("pkWahl").onchange = pkLaden;
$("pkKarte").addEventListener("click", async (ev) => {
  const t = ev.target;
  if (t.dataset.pkfotos) return pkFotos(t.dataset.pkfotos);
  if (t.dataset.pkgross) { const o = document.createElement("div"); o.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:99;display:flex;align-items:center;justify-content:center;cursor:zoom-out"; o.innerHTML = `<img src="${t.src}" style="max-width:96%;max-height:96%">`; o.onclick = () => o.remove(); document.body.appendChild(o); return; }
  if (t.dataset.pkfusion) { const r = await tun(() => senden("projekt_foto_fusion", { nummer: $("pkWahl").value, pfad: t.dataset.pkfusion, titel: t.dataset.pktitel }), "Als Referenzbild in Fusion eingefügt (Lage und Grösse in Fusion einstellen)."); return; }
  if (t.dataset.pkdatei) { const r = await tun(() => senden("projekt_datei", { nummer: $("pkWahl").value, pfad: t.dataset.pkdatei, name: t.dataset.pkname || undefined })); if (r) meldung(`Gespeichert: ${r.pfad}${r.geoeffnet ? " (geöffnet)" : ""}`, "ok"); }
});
document.querySelector('nav button[data-tab="projekt"]').addEventListener("click", async () => { if (!$("pkWahl").options.length) await pkListeLaden(); if (!PK && $("pkWahl").value) pkLaden(); });

// ------------------------------------------------------------------ Skizze (Profil von Hand zeichnen)
const SK = { rohe: [], ursprung: [0, 0], schenkel: [], start: 0, hover: null, lauf: 0 };
const SK_PX = 20;                                           // Pixel je Kästchen
const skMm = () => Number($("skM").value) / SK_PX;           // mm je Pixel
function skPos(ev) {
  const c = $("skCanvas"), r = c.getBoundingClientRect();
  const px = (ev.clientX - r.left) * c.width / r.width, py = (ev.clientY - r.top) * c.height / r.height;
  return { px, py, mm: [px * skMm(), (c.height - py) * skMm()] };
}
const skPx = (m) => [m[0] / skMm(), $("skCanvas").height - m[1] / skMm()];
function skInit() {
  $("skMat").innerHTML = '<option value="">– ohne (nur Skizze) –</option>' + Z.materialien.map((m) => `<option value="${esc(m.id)}">${esc(m.name)} (${m.thickness} mm)</option>`).join("");
  if (!$("skMat").value) $("skMat").value = Z.einstellungen.defaultMaterialId || "";
  skZeichnen();
}
function skZeichnen() {
  const c = $("skCanvas"), g = c.getContext("2d");
  g.clearRect(0, 0, c.width, c.height);
  g.strokeStyle = "#e3e8ee"; g.lineWidth = 1;
  for (let x = 0; x <= c.width; x += SK_PX) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, c.height); g.stroke(); }
  for (let y = 0; y <= c.height; y += SK_PX) { g.beginPath(); g.moveTo(0, y); g.lineTo(c.width, y); g.stroke(); }
  const pts = SK.rohe.map(skPx);
  g.lineCap = "round"; g.lineJoin = "round"; g.font = "12px Segoe UI, Arial";
  for (let i = 1; i < pts.length; i++) {
    g.strokeStyle = i === 1 ? "#8a949e" : "#1f78c1"; g.lineWidth = 4;
    g.beginPath(); g.moveTo(pts[i - 1][0], pts[i - 1][1]); g.lineTo(pts[i][0], pts[i][1]); g.stroke();
    const s = SK.schenkel[i - 1];
    if (s) {
      g.fillStyle = "#17496f"; g.fillText(String(s.laenge), (pts[i - 1][0] + pts[i][0]) / 2 + 6, (pts[i - 1][1] + pts[i][1]) / 2 - 6);
      if (i > 1) { g.fillStyle = "#b26a00"; g.fillText(s.winkel + "°", pts[i - 1][0] + 8, pts[i - 1][1] + 14); }
    }
  }
  g.fillStyle = "#17496f";
  pts.forEach((p, i) => { g.beginPath(); g.arc(p[0], p[1], i === 0 ? 6 : 4, 0, 7); g.fill(); });
  if (SK.hover && pts.length) {
    const l = pts[pts.length - 1];
    g.setLineDash([6, 5]); g.strokeStyle = "#f28c28"; g.lineWidth = 2; g.beginPath(); g.moveTo(l[0], l[1]); g.lineTo(SK.hover.px, SK.hover.py); g.stroke(); g.setLineDash([]);
    const m = SK.rohe[SK.rohe.length - 1];
    g.fillStyle = "#b26a00"; g.fillText(Math.round(Math.hypot(SK.hover.mm[0] - m[0], SK.hover.mm[1] - m[1])) + " mm", SK.hover.px + 8, SK.hover.py - 8);
  }
}
function skTabelle() {
  $("skTab").querySelector("tbody").innerHTML = SK.schenkel.map((s, i) => `<tr><td>${i + 1}${i === 0 ? " <span class='klein'>Blech</span>" : ""}</td>
    <td><input type="number" step="any" data-sk="${i}" data-f="laenge" value="${s.laenge}" style="width:72px"></td>
    <td>${i === 0 ? "–" : `<input type="number" step="any" data-sk="${i}" data-f="winkel" value="${s.winkel}" style="width:64px">`}</td>
    <td>${i === 0 ? "" : `<button data-skdel="${i}">✕</button>`}</td></tr>`).join("") || "<tr><td colspan='4' class='klein'>Noch nichts gezeichnet.</td></tr>";
}
function skInfo(r) {
  $("skInfo").innerHTML = r ? `<div>Summe der Striche ${esc(r.summe)} mm${r.zuschnitt ? ` · <b>Zuschnittbreite ca. ${esc(r.zuschnitt)} mm</b> (theoretisch, mit Material)` : ""}${r.zuschnitt_grund ? ` · ${esc(r.zuschnitt_grund)}` : ""}</div>
    <div>Kurzschrift ab Strich 2: <code>${esc(r.kurz || "–")}</code></div>${(r.hinweise || []).map((h) => `<div>${esc(h)}</div>`).join("")}` : "";
}
async function skAuswerten(daten) {   // gezeichnete Punkte oder Tabelle → eingerastetes Ergebnis, Zeichnung und Tabelle neu
  const lauf = ++SK.lauf;
  const r = await tun(() => senden("skizze_auswerten", Object.assign({ laengenraster: Number($("skL").value), winkelraster: Number($("skW").value), materialId: $("skMat").value || null }, daten)));
  if (!r || lauf !== SK.lauf) return r;
  SK.schenkel = r.schenkel; SK.start = r.start;
  SK.rohe = r.punkte.map((p) => [p[0] + SK.ursprung[0], p[1] + SK.ursprung[1]]);
  skZeichnen(); skInfo(r); return r;
}
function skNeu() { SK.rohe = []; SK.schenkel = []; SK.hover = null; SK.start = 0; skTabelle(); skZeichnen(); skInfo(null); }
$("skCanvas").addEventListener("pointerdown", (ev) => {
  ev.preventDefault(); $("skCanvas").setPointerCapture(ev.pointerId);
  const p = skPos(ev);
  if (!SK.rohe.length) { SK.ursprung = p.mm; SK.rohe = [p.mm]; SK.schenkel = []; skZeichnen(); }
  SK.hover = p; skZeichnen();
});
$("skCanvas").addEventListener("pointermove", (ev) => { if (SK.rohe.length) { SK.hover = skPos(ev); skZeichnen(); } });
$("skCanvas").addEventListener("pointerup", async (ev) => {
  const p = skPos(ev); SK.hover = null;
  if (SK.rohe.length === 1 && !SK.schenkel.length && Math.hypot(p.mm[0] - SK.rohe[0][0], p.mm[1] - SK.rohe[0][1]) / skMm() < 6) { skZeichnen(); return; }   // nur der Startpunkt
  const l = SK.rohe[SK.rohe.length - 1];
  if (Math.hypot(p.mm[0] - l[0], p.mm[1] - l[1]) / skMm() < 6) { skZeichnen(); return; }
  SK.rohe.push(p.mm);                                       // sofort merken: schnelle Striche gehen nicht verloren, die Antwort rastet sie dann ein
  skZeichnen();
  if (await skAuswerten({ punkte: SK.rohe })) skTabelle();
});
$("skCanvas").addEventListener("pointerleave", () => { SK.hover = null; skZeichnen(); });
$("skTab").addEventListener("input", (ev) => {
  const t = ev.target; if (t.dataset.sk === undefined) return;
  SK.schenkel[+t.dataset.sk][t.dataset.f] = t.value === "" ? "" : Number(t.value);
  clearTimeout(SK.uhr); SK.uhr = setTimeout(() => skAuswerten({ schenkel: SK.schenkel, start: SK.start }), 400);
});
$("skTab").addEventListener("click", async (ev) => {
  const i = ev.target.dataset.skdel; if (i === undefined) return;
  SK.schenkel.splice(+i, 1);
  if (await skAuswerten({ schenkel: SK.schenkel, start: SK.start })) skTabelle();
});
$("skPlus").onclick = async () => {
  if (!SK.schenkel.length) { SK.ursprung = [60, 60]; SK.schenkel = [{ laenge: 80, winkel: 0 }]; } else SK.schenkel.push({ laenge: 20, winkel: 90 });
  if (await skAuswerten({ schenkel: SK.schenkel, start: SK.start })) skTabelle();
};
$("skRueck").onclick = async () => {
  if (SK.schenkel.length <= 1) return skNeu();
  SK.schenkel.pop();
  if (await skAuswerten({ schenkel: SK.schenkel, start: SK.start })) skTabelle();
};
$("skLeer").onclick = skNeu;
for (const id of ["skL", "skW"]) $(id).onchange = () => { if (SK.rohe.length > 1) skAuswerten({ punkte: SK.rohe }); };
$("skM").onchange = skZeichnen;
$("skMat").onchange = () => { if (SK.schenkel.length) skAuswerten({ schenkel: SK.schenkel, start: SK.start }); };
$("skVorlage").onclick = async () => {
  const v = await tun(() => senden("skizze_vorlage", { schenkel: SK.schenkel, name: $("skName").value.trim(), kategorie: $("skKat").value.trim() }));
  if (v) { document.querySelector('nav button[data-tab="vorlagen"]').click(); oeffneEditor(v); meldung("Skizze als Kantenvorlage geöffnet – bitte prüfen und speichern.", "ok"); }
};
document.querySelector('nav button[data-tab="skizze"]').addEventListener("click", skInit);

// ------------------------------------------------------------------ Bauteile (Blech mit Breite, Verlauf und Kantenfolgen)
let B = null;
const B_SEITEN = ["verlauf", "gegen", "start", "ende"];
function bListeZeigen() {
  const l = Z.bauteile || [];
  $("bLeer").style.display = l.length ? "none" : "block";
  $("btListe").style.display = l.length ? "" : "none";
  $("btListe").querySelector("tbody").innerHTML = l.map((v) => `<tr data-bid="${esc(v.id)}" class="${B && B.id === v.id ? "gewaehlt" : ""}"><td>${v.favorite ? "★ " : ""}${esc(v.name)}</td>
    <td>${esc(v.category)}</td><td>${esc(v.version)}</td><td>${v.verlauf?.art === "grundriss" ? "Grundriss" : "gerade"}</td>
    <td class="klein">${B_SEITEN.filter((s) => (v._texte || {})[s]).map((s) => esc(s + ": " + v._texte[s])).join(" · ")}</td></tr>`).join("");
  $("bMat").innerHTML = '<option value="">– Skizze (t = 1 mm) –</option>' + Z.materialien.map((m) => `<option value="${esc(m.id)}">${esc(m.name)} (${m.thickness} mm)</option>`).join("");
  $("bMat").value = Z.einstellungen.defaultMaterialId || "";
}
function bOeffnen(v) {
  B = JSON.parse(JSON.stringify(v));
  $("bEditor").style.display = "block";
  $("bName").value = B.name || ""; $("bBeschr").value = B.description || ""; $("bKat").value = B.category || ""; $("bFav").checked = !!B.favorite;
  $("bVersion").textContent = B.version ? `Version ${B.version}` : "";
  $("bArt").value = B.verlauf?.art || "gerade"; $("bSeite").value = B.verlauf?.seite || "links"; $("bBsp").value = B.verlauf?.beispiel || "";
  $("bRing").checked = false; $("bBreite").value = B.breite || "";
  for (const s of B_SEITEN) $("bT_" + s).value = (B._texte || {})[s] || "";
  bArtZeigen(); bParamZeigen(); bListeZeigen(); bVorschau();
}
function bArtZeigen() {
  const g = $("bArt").value === "grundriss";
  $("bBspZeile").style.display = g ? "" : "none"; $("bBspHilfe").style.display = g ? "" : "none";
  $("bLaenge").disabled = g;
}
function bParamZeigen() {
  $("bParam").querySelector("tbody").innerHTML = (B.parameters || []).map((p, i) => `<tr>
    <td>${esc(p.name)}</td><td><input data-bp="${i}" data-f="label" value="${esc(p.label)}" size="16"></td>
    <td><select data-bp="${i}" data-f="unit">${["mm", "deg", ""].map((u) => `<option value="${u}" ${p.unit === u ? "selected" : ""}>${u || "–"}</option>`).join("")}</select></td>
    <td><input type="number" step="any" data-bp="${i}" data-f="default" value="${p.default ?? ""}"></td>
    <td><input type="number" step="any" data-bp="${i}" data-f="min" value="${p.min ?? ""}"></td>
    <td><input type="number" step="any" data-bp="${i}" data-f="max" value="${p.max ?? ""}"></td></tr>`).join("") || "<tr><td colspan='6' class='klein'>Noch keine Parameter – sie entstehen aus den Namen in Breite und Kantenfolgen.</td></tr>";
}
function bLesen() {
  B.name = $("bName").value.trim(); B.description = $("bBeschr").value; B.category = $("bKat").value.trim() || "Ohne Kategorie"; B.favorite = $("bFav").checked;
  B.verlauf = Object.assign({}, B.verlauf, { art: $("bArt").value, seite: $("bSeite").value, beispiel: $("bBsp").value.trim() });
  B.breite = $("bBreite").value.trim();
  const t = {}; for (const s of B_SEITEN) t[s] = $("bT_" + s).value.trim();
  return t;
}
async function bErkennen() {   // Kurzschrift → Operationen, Parameterliste abgleichen (Einstellungen der Parameter bleiben)
  const texte = bLesen();
  const v = await tun(() => senden("bauteil_erkennen", { vorlage: B, texte }));
  if (v) { B = v; bParamZeigen(); }
  return !!v;
}
let bUhr = null;
function bVorschau() {
  clearTimeout(bUhr);
  bUhr = setTimeout(async () => {
    if (!B) return;
    try {
      const texte = bLesen();
      const vorher = (B.parameters || []).map((p) => p.name).join(",");
      const v = await senden("bauteil_erkennen", { vorlage: B, texte }); B = v;
      if ((B.parameters || []).map((p) => p.name).join(",") !== vorher) bParamZeigen();      // Tabelle nur neu zeichnen, wenn sich die Namen ändern (sonst springt die Eingabe)
      const r = await senden("bauteil_vorschau", { vorlage: B, materialId: $("bMat").value || null, laenge: zahlOderNull($("bLaenge").value) || 1000, geschlossen: $("bRing").checked,
        verlauf: B.verlauf.beispiel, seite: B.verlauf.seite });
      $("bVorschau").innerHTML = r.grund ? `<span class="klein">Keine Vorschau: ${esc(r.grund)}</span>`
        : `<div class="zeile">${r.grundriss}${Object.values(r.querschnitte).map((q) => `<div>${q.svg || ""}<div class="klein">${esc(q.titel)}</div></div>`).join("")}</div><div class="klein">${esc(r.text)}</div>`;
      $("bMeld").textContent = (r.warnungen || []).join(" ");
    } catch (e) { $("bVorschau").innerHTML = `<span class="klein">Keine Vorschau: ${esc(e.message)}</span>`; }
  }, 450);
}
$("bNeu").onclick = async () => { const v = await tun(() => senden("neues_bauteil", { name: "Neues Bauteil" })); if (v) bOeffnen(v); };
$("btListe").addEventListener("click", (ev) => { const tr = ev.target.closest("tr[data-bid]"); if (tr) bOeffnen(Z.bauteile.find((x) => x.id === tr.dataset.bid)); });
$("bErkennen").onclick = async () => { if (await bErkennen()) { meldung("Parameter übernommen – Standardwerte bitte eintragen.", "ok"); bVorschau(); } };
$("bArt").onchange = () => { bArtZeigen(); bVorschau(); };
$("bEditor").addEventListener("input", (ev) => {
  const t = ev.target;
  if (t.dataset.bp !== undefined) {
    const p = B.parameters[+t.dataset.bp];
    p[t.dataset.f] = t.dataset.f === "label" || t.dataset.f === "unit" ? t.value : zahlOderNull(t.value);
  }
  bVorschau();
});
$("bEditor").addEventListener("change", (ev) => { if (ev.target.id === "bMat" || ev.target.id === "bRing" || ev.target.id === "bSeite") bVorschau(); });
$("bSpeichern").onclick = async () => {
  if (!(await bErkennen())) return;
  const v = await tun(() => senden("speichern", { vorlage: B }));
  if (v) { await laden(); bOeffnen(Z.bauteile.find((x) => x.id === v.id) || v); meldung(`Bauteil gespeichert (Version ${v.version}).`, "ok"); }
};
$("bAbbrechen").onclick = () => { B = null; $("bEditor").style.display = "none"; bListeZeigen(); };
$("bKopie").onclick = async () => {
  if (!B || !B.id || !Z.bauteile.some((x) => x.id === B.id)) return meldung("Erst speichern, dann duplizieren.", "fehler");
  const v = await tun(() => senden("duplizieren", { id: B.id, typ: "bauteilvorlage" })); if (v) { await laden(); bOeffnen(v); meldung("Kopie erstellt.", "ok"); }
};
$("bLoeschen").onclick = async () => {
  if (!B || !B.id || !Z.bauteile.some((x) => x.id === B.id)) return meldung("Dieses Bauteil ist noch nicht gespeichert.", "fehler");
  if (!(await frage(`Bauteil «${B.name}» wirklich löschen? Es wird in den Papierkorb verschoben.`))) return;
  if (await tun(() => senden("loeschen", { id: B.id, typ: "bauteilvorlage", bestaetigt: true }), "In den Papierkorb verschoben.") !== undefined) { B = null; $("bEditor").style.display = "none"; await laden(); }
};
document.querySelector('nav button[data-tab="bauteile"]').addEventListener("click", bListeZeigen);

// ------------------------------------------------------------------ Aufträge (Übersicht)
async function auftraegeLaden() {
  const r = await tun(() => senden("auftragsuebersicht"));
  if (!r) return;
  window._auftraege = r;
  auftraegeZeigen();
}
function auftraegeZeigen() {
  const r = window._auftraege; if (!r) return;
  const q = $("aSuche").value.trim().toLowerCase(), f = $("aFilter").value;
  const zeilen = r.zeilen.filter((x) => (!q || (x.nummer + " " + x.objekt).toLowerCase().includes(q)) && (!f || (f === "hinweis" ? x.hinweise.length : x.fertigung === f)));
  const s = r.summe;
  $("aSumme").textContent = `${s.alle} Aufträge · offen ${s.offen} · in Arbeit ${s.in_arbeit} · gefertigt ${s.gefertigt} · geliefert ${s.geliefert} · ohne Status ${s.ohne_status} · mit Hinweis ${s.mit_hinweis}`;
  $("aInfo").textContent = r.hinweise.length ? r.hinweise.join(" ") : "Status ändern: Liste in der Spalte «Fertigung». «Aktiv» macht den Auftrag zum aktiven Auftrag in Fusion.";
  $("aListe").innerHTML = zeilen.map((x) => `<tr${x.aktiv ? ' class="gewaehlt"' : ""}>
    <td>${x.aktiv ? "●" : `<button data-aaktiv="${esc(x.nummer)}" data-aobjekt="${esc(x.objekt)}" data-ajahr="${esc(x.jahr || "")}" title="zum aktiven Auftrag machen">Aktiv</button>`}</td>
    <td>${esc(x.nummer)}</td><td>${esc(x.objekt)}</td><td>${x.fusion ? "✓" : "–"}</td><td>${x.app ? "✓" : "–"}</td>
    <td><select data-astatus="${esc(x.nummer)}"><option value="">–</option>${r.status.map((s2) => `<option value="${s2[0]}"${s2[0] === x.fertigung ? " selected" : ""}>${esc(s2[1])}</option>`).join("")}</select></td>
    <td>${x.teile ? `${x.gefertigt}/${x.teile}` : "–"}</td><td class="klein">${esc((x.geaendert || "").slice(0, 16).replace("T", " "))}</td>
    <td class="klein">${esc(x.hinweise.join("; "))}</td></tr>`).join("") || "<tr><td colspan='9'>Keine Aufträge gefunden.</td></tr>";
}
$("aLaden").onclick = auftraegeLaden;
$("aSuche").oninput = auftraegeZeigen;
$("aFilter").onchange = auftraegeZeigen;
$("aListe").addEventListener("change", async (ev) => {
  const t = ev.target;
  if (t.dataset.astatus && t.value && await tun(() => senden("auftrag_status", { nummer: t.dataset.astatus, status: t.value }), "Status gespeichert.")) auftraegeLaden();
});
$("aListe").addEventListener("click", async (ev) => {
  const t = ev.target;
  if (t.dataset.aaktiv && await tun(() => senden("auftrag_aktiv", { nummer: t.dataset.aaktiv, objekt: t.dataset.aobjekt, jahr: t.dataset.ajahr ? Number(t.dataset.ajahr) : null }), "Aktiver Auftrag gesetzt.")) auftraegeLaden();
});
document.querySelector('nav button[data-tab="auftraege"]').addEventListener("click", auftraegeLaden);

// ------------------------------------------------------------------ Reste
async function resteLaden() {
  const r = await tun(() => senden("reste"));
  if (!r) return;
  $("rMatListe").innerHTML = (Z.materialien || []).map((m) => `<option value="${esc(m.name)}">`).join("");
  $("rListe").innerHTML = r.filter((x) => !x.verbraucht).map((x) => `<tr><td>${esc(x.material_name)}</td><td>${esc(x.staerke_mm)}</td><td>${esc(x.breite_mm)} × ${esc(x.laenge_mm)}</td>
    <td>${esc(x.anzahl)}</td><td class="klein">${esc(x.herkunft || "")} ${esc(x.notiz || "")}</td>
    <td><button data-rverb="${esc(x.id)}" title="als verbraucht markieren">verbraucht</button> <button data-rdel="${esc(x.id)}">✕</button></td></tr>`).join("") || "<tr><td colspan='6'>Keine Reste erfasst.</td></tr>";
  window._reste = r;
}
$("rSpeichern").onclick = async () => {
  const z = (id) => zahlOderNull($(id).value);
  const r = await tun(() => senden("rest_speichern", { rest: { material_name: $("rMat").value.trim(), staerke_mm: z("rT"), breite_mm: z("rB"), laenge_mm: z("rL"), anzahl: z("rN"), notiz: $("rNotiz").value.trim() } }), "Rest gespeichert.");
  if (r) { $("rB").value = $("rL").value = $("rNotiz").value = ""; await resteLaden(); }
};
$("rListe").addEventListener("click", async (ev) => {
  const t = ev.target;
  if (t.dataset.rdel && await frage("Rest wirklich löschen?")) { await tun(() => senden("rest_loeschen", { id: t.dataset.rdel })); await resteLaden(); }
  if (t.dataset.rverb) {
    const x = (window._reste || []).find((y) => y.id === t.dataset.rverb);
    if (x) { await tun(() => senden("rest_speichern", { rest: Object.assign({}, x, { verbraucht: true }) }), "Als verbraucht markiert."); await resteLaden(); }
  }
});
document.querySelector('nav button[data-tab="reste"]').addEventListener("click", resteLaden);
document.querySelector('nav button[data-tab="berichte"]').addEventListener("click", aenderungenLaden);

$("pSenden").onclick = async () => {
  if (await tun(() => senden("protokoll_senden", { notiz: $("pNotiz").value }), "Protokoll gesendet.")) $("pNotiz").value = "";
};

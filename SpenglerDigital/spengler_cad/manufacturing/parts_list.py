"""Auftrags-Stückliste und Etiketten.

Stückliste: Port von stueckliste/stuecklisteCsv aus kern/auftrag.js. Abweichung: liegt die echte
Abwicklungsfläche aus Fusion vor, wird sie für Fläche und Gewicht verwendet (sonst Zuschnitt × Länge
wie im CAD-Programm); die Quelle steht in jeder Zeile.
Etiketten: eins pro Stück auf A4-Bögen, Format aus den Einstellungen (wie im CAD-Programm), als
druckbare HTML-Seite (im Browser drucken – in Fusion steht keine PDF-Bibliothek zur Verfügung).

teile: [{'nr', 'name', 'material': {'name','thickness','density'}, 'breite' (Zuschnitt mm), 'laenge' (mm),
         'stueck', 'flaeche' (mm² je Stück oder None), 'notiz'}]
"""
import html

A4 = (210.0, 297.0)


def stueckliste(teile):
    zeilen = []
    for t in teile:
        stueck = max(0, int(round(t.get("stueck", 1) if t.get("stueck") is not None else 1)))
        m = t.get("material") or {}
        echt = t.get("flaeche") is not None
        je = (t["flaeche"] if echt else t["breite"] * t["laenge"]) / 1e6
        flaeche = je * stueck
        dichte = m.get("density")
        zeilen.append({"nr": t.get("nr", ""), "name": t["name"], "notiz": t.get("notiz") or "", "material": m.get("name") or "–",
                       "dicke": m.get("thickness"), "zuschnitt": t["breite"], "laenge": t["laenge"], "stueck": stueck,
                       "laufmeter": t["laenge"] / 1000.0 * stueck, "flaeche": flaeche, "flaecheQuelle": "Abwicklung" if echt else "Rechteck",
                       "gewicht": flaeche * (m.get("thickness") or 0) * dichte if dichte else None})
    je_mat = {}
    for z in zeilen:
        s = je_mat.setdefault(z["material"], {"material": z["material"], "stueck": 0, "laufmeter": 0.0, "flaeche": 0.0, "gewicht": 0.0, "gewichtVollstaendig": True})
        s["stueck"] += z["stueck"]
        s["laufmeter"] += z["laufmeter"]
        s["flaeche"] += z["flaeche"]
        if z["gewicht"] is None:
            s["gewichtVollstaendig"] = False
        else:
            s["gewicht"] += z["gewicht"]
    summe = {"stueck": sum(z["stueck"] for z in zeilen), "flaeche": sum(z["flaeche"] for z in zeilen),
             "gewicht": sum(z["gewicht"] or 0 for z in zeilen), "gewichtVollstaendig": all(z["gewicht"] is not None for z in zeilen)}
    return {"zeilen": zeilen, "jeMaterial": list(je_mat.values()), "summe": summe}


def _feld(v):
    if isinstance(v, bool):
        return "ja" if v else "nein"
    if isinstance(v, (int, float)):
        return ("%.3f" % v).rstrip("0").rstrip(".")
    if v is None:
        return ""
    s = str(v)
    return '"%s"' % s.replace('"', '""') if any(c in s for c in ';"\n') else s


def stueckliste_csv(liste, kopf=()):
    """CSV für Excel: Semikolon, Dezimalpunkt, BOM für Umlaute (wie kern/auftrag.js)."""
    zeile = lambda a: ";".join(_feld(x) for x in a)
    z = [zeile(k) for k in kopf]
    z.append(zeile(["Nr", "Teil", "Material", "Dicke mm", "Zuschnitt mm", "Länge mm", "Stück", "Laufmeter m", "Fläche m²", "Fläche aus", "Gewicht kg", "Notiz"]))
    for r in liste["zeilen"]:
        z.append(zeile([r["nr"], r["name"], r["material"], r["dicke"], round(r["zuschnitt"], 1), round(r["laenge"], 1), r["stueck"],
                        r["laufmeter"], r["flaeche"], r["flaecheQuelle"], r["gewicht"], r["notiz"]]))
    z.append("")
    z.append(zeile(["Summe je Material", "", "", "", "", "", "Stück", "Laufmeter m", "Fläche m²", "", "Gewicht kg"]))
    for s in liste["jeMaterial"]:
        z.append(zeile([s["material"], "", "", "", "", "", s["stueck"], s["laufmeter"], s["flaeche"], "", s["gewicht"] if s["gewichtVollstaendig"] else None]))
    return "﻿" + "\r\n".join(z) + "\r\n"


def stueckliste_html(liste, objekt="", auftrag="", datum="", logo=None, version=""):
    e = lambda s: html.escape("–" if s is None or s == "" else str(s))
    n = lambda v, f="%.3f": "–" if v is None else (f % v)
    z = ['<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Stückliste %s</title>' % e(auftrag or objekt),
         "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:14mm;color:#111;font-size:10pt}table{border-collapse:collapse;width:100%}"
         "td,th{border:1px solid #999;padding:3px 6px;text-align:left}td.z{text-align:right}th{background:#e6eef6}h1{font-size:16pt;margin:0}"
         ".hinweis{color:#8a5a00;font-size:8.5pt}</style></head><body>"]
    if logo:
        z.append('<img src="%s" alt="" style="height:44px;float:right">' % e(logo))
    z.append("<h1>Stückliste</h1><p>Objekt: <b>%s</b> · Auftrag: <b>%s</b> · %s</p>" % (e(objekt), e(auftrag), e(datum)))
    z.append("<table><tr><th>Nr</th><th>Teil</th><th>Material</th><th>Zuschnitt × Länge mm</th><th>Stück</th><th>Laufmeter m</th><th>Fläche m²</th><th>Gewicht kg</th><th>Notiz</th></tr>")
    for r in liste["zeilen"]:
        z.append("<tr><td>%s</td><td>%s</td><td>%s</td><td class=z>%.1f × %.1f</td><td class=z>%d</td><td class=z>%.2f</td><td class=z>%s%s</td><td class=z>%s</td><td>%s</td></tr>" % (
            e(r["nr"]), e(r["name"]), e(r["material"]), r["zuschnitt"], r["laenge"], r["stueck"], r["laufmeter"], n(r["flaeche"]),
            "" if r["flaecheQuelle"] == "Abwicklung" else "*", n(r["gewicht"], "%.2f"), e(r["notiz"]) if r["notiz"] else ""))
    z.append("</table><h2 style='font-size:12pt'>Summe je Material</h2><table><tr><th>Material</th><th>Stück</th><th>Laufmeter m</th><th>Fläche m²</th><th>Gewicht kg</th></tr>")
    for s in liste["jeMaterial"]:
        z.append("<tr><td>%s</td><td class=z>%d</td><td class=z>%.2f</td><td class=z>%.3f</td><td class=z>%s</td></tr>" % (
            e(s["material"]), s["stueck"], s["laufmeter"], s["flaeche"], n(s["gewicht"], "%.2f") if s["gewichtVollstaendig"] else "– (Dichte fehlt)"))
    z.append("</table><p class='hinweis'>* Fläche aus dem umschliessenden Rechteck (keine Fusion-Abwicklungsfläche). Gewicht = Fläche × Dicke × Dichte: Schätzwert.</p>")
    z.append("<p style='font-size:8pt;color:#666'>Spengler Digital CAD %s</p></body></html>" % e(version))
    return "\n".join(z)


# ---------------------------------------------------------------------------------------- Etiketten
def etiketten_pruefen(e):
    """Etikettenbogen prüfen → (fehler[], text). Gleiche Rechnung wie im CAD-Programm (etikettenPruefen)."""
    f = []
    for k in ("spalten", "zeilen"):
        if not (isinstance(e.get(k), int) and not isinstance(e.get(k), bool) and e[k] >= 1):
            f.append("Etiketten: %s muss eine ganze Zahl ab 1 sein." % k.capitalize())
    for k in ("breite", "hoehe"):
        if not (isinstance(e.get(k), (int, float)) and e[k] > 0):
            f.append("Etiketten: %s muss grösser als 0 sein." % ("Breite" if k == "breite" else "Höhe"))
    for k in ("oben", "links", "abstandX", "abstandY"):
        if not (isinstance(e.get(k), (int, float)) and e[k] >= 0):
            f.append("Etiketten: %s muss eine Zahl ≥ 0 sein." % k)
    if f:
        return f, ""
    b = e["links"] + e["spalten"] * e["breite"] + (e["spalten"] - 1) * e["abstandX"]
    h = e["oben"] + e["zeilen"] * e["hoehe"] + (e["zeilen"] - 1) * e["abstandY"]
    text = "Belegt %.1f × %.1f mm von 210 × 297 mm, %d Etiketten pro Bogen." % (b, h, e["spalten"] * e["zeilen"])
    if b > A4[0] + 0.5 or h > A4[1] + 0.5:
        f.append(text + " Passt nicht auf A4.")
    return f, text


def etiketten_html(liste, e, objekt="", auftrag=""):
    """Ein Etikett pro Stück. → (html, anzahl). Wirft ValueError bei ungültigem Bogenformat."""
    fehler, _ = etiketten_pruefen(e)
    if fehler:
        raise ValueError(" ".join(fehler))
    esc = lambda s: html.escape("–" if s is None or s == "" else str(s))
    etiketten = []
    for r in liste["zeilen"]:
        for i in range(r["stueck"]):
            teil = "%s%s%s" % ("%s · " % esc(r["nr"]) if r["nr"] != "" else "", esc(r["name"]),
                               " <small>%d/%d</small>" % (i + 1, r["stueck"]) if r["stueck"] > 1 else "")
            etiketten.append('<dl class="etikett"><dt>Objekt</dt><dd>%s</dd><dt>Auftrag</dt><dd>%s</dd><dt>Teil</dt><dd>%s</dd>'
                             '<dt>Blech</dt><dd>%s%s</dd><dt>Mass</dt><dd>%.1f × %.0f</dd></dl>' % (
                                 esc(objekt), esc(auftrag), teil, esc(r["material"]),
                                 " %g mm" % r["dicke"] if r["dicke"] else "", r["zuschnitt"], r["laenge"]))
    pro = e["spalten"] * e["zeilen"]
    stil = ("grid-template-columns:repeat(%d,%smm);grid-auto-rows:%smm;column-gap:%smm;row-gap:%smm;padding:%smm 0 0 %smm;"
            % (e["spalten"], e["breite"], e["hoehe"], e["abstandX"], e["abstandY"], e["oben"], e["links"]))
    boegen = ['<section class="bogen" style="%s">%s</section>' % (stil, "".join(etiketten[i:i + pro])) for i in range(0, len(etiketten), pro)]
    seite = ('<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Etiketten %s</title><style>'
             "@page{size:A4;margin:0}body{margin:0;font-family:Segoe UI,Arial,sans-serif}"
             ".bogen{display:grid;box-sizing:border-box;width:210mm;height:297mm;align-content:start;break-after:page}"
             ".bogen:last-child{break-after:auto}.etikett{margin:0;padding:3mm 4mm;font-size:9pt;display:grid;grid-template-columns:auto 1fr;"
             "gap:0 3mm;align-content:center;overflow:hidden;box-sizing:border-box}.etikett dt{color:#555;font-size:7pt;text-transform:uppercase}"
             ".etikett dd{margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
             "@media screen{body{background:#ccc}.bogen{background:#fff;margin:8mm auto}.etikett{outline:1px dashed #bbb}}"
             "</style></head><body>%s</body></html>" % (html.escape(auftrag or objekt or ""), "".join(boegen)))
    return seite, len(etiketten)

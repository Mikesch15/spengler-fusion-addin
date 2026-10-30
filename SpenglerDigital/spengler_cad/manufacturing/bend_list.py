"""Abkantliste für die Werkstatt: je Teil die Biegefolge (Winkel, Schenkel, Radius) aus der Vorlage, druckbar als HTML (→ PDF über den Browser)."""
import html


def abkantliste_html(teile, objekt="", auftrag="", datum="", version=""):
    """teile: [{'nr','name','material','dicke','operationen' ([{typ,winkel,laenge,radius}] oder None),'ri','stueck'}]"""
    e = lambda s: html.escape(str(s if s is not None else "–"))
    z = ['<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Abkantliste %s</title>' % e(auftrag or objekt),
         "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:14mm;color:#111}table{border-collapse:collapse;margin:4px 0 14px}"
         "td,th{border:1px solid #888;padding:3px 8px;text-align:left}h1{font-size:17pt}h2{font-size:12pt;margin:14px 0 2px;page-break-after:avoid}"
         ".hin{color:#8a5a00}@media print{h2{break-after:avoid}table{break-inside:avoid}}</style></head><body>",
         "<h1>Abkantliste</h1><p>Objekt: <b>%s</b> · Auftrag: <b>%s</b> · %s</p>" % (e(objekt), e(auftrag), e(datum))]
    ohne = []
    for t in teile:
        ops = t.get("operationen") or []
        kopf = "%s %s" % (e(t.get("nr")) if t.get("nr") not in (None, "") else "", e(t.get("name")))
        if not ops:
            ohne.append(t.get("name") or "Teil")
            continue
        z.append("<h2>%s <span style='font-weight:normal'>– %s, %s mm, %s Stück</span></h2>" % (kopf, e(t.get("material")), e(t.get("dicke")), e(t.get("stueck", 1))))
        z.append("<table><tr><th>Biegung</th><th>Art</th><th>Winkel</th><th>Schenkel mm</th><th>Innenradius mm</th></tr>")
        for i, op in enumerate(ops, 1):
            r = op.get("radius") if op.get("radius") is not None else t.get("ri")
            z.append("<tr><td>%d</td><td>%s</td><td>%g°</td><td>%.1f</td><td>%s</td></tr>" % (
                i, "Umschlag" if op.get("typ") == "umschlag" else "Abkanten", op.get("winkel", 0), op.get("laenge", 0),
                ("%.2f" % r) if isinstance(r, (int, float)) else "Material"))
        z.append("</table>")
    if ohne:
        z.append("<p class='hin'>Ohne Biegefolge (nicht mit «Kanten bearbeiten» erzeugt): %s</p>" % e(", ".join(ohne)))
    z.append("<p style='font-size:8pt;color:#666'>Erstellt mit Spengler Digital CAD %s. Winkel wie in der Vorlage (+ links / − rechts in Laufrichtung).</p></body></html>" % e(version))
    return "\n".join(z)

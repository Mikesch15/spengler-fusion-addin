"""Auftragsmappe: Stückliste, Abkantliste, Kalkulation, Zuschnittplan und Werkstattblätter in EINER HTML-Datei (je Abschnitt eine neue Seite) –
im Browser drucken oder als PDF speichern (Strg+P). Reine Logik."""
import html
import re


def ausschnitt(dokument):
    """(style, body) eines kompletten HTML-Dokuments; ohne <body> das ganze Stück."""
    stile = "\n".join(re.findall(r"<style[^>]*>.*?</style>", dokument, flags=re.S | re.I))
    m = re.search(r"<body[^>]*>(.*)</body>", dokument, flags=re.S | re.I)
    return stile, (m.group(1) if m else dokument)


def mappe_html(abschnitte, objekt="", auftrag="", datum="", version=""):
    """abschnitte: [(Titel, HTML-Dokument oder -Stück)] → ein Dokument mit Deckblatt und Inhaltsverzeichnis."""
    e = html.escape
    stile, teile = [], []
    for titel, dok in abschnitte:
        st, body = ausschnitt(dok)
        if st and st not in stile:
            stile.append(st)
        teile.append((titel, body))
    z = ['<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Auftragsmappe %s</title>' % e(auftrag or objekt),
         "<style>@media print{.neueSeite{page-break-before:always}}.deckblatt{font-family:Segoe UI,Arial,sans-serif;margin:30mm 16mm}"
         ".deckblatt h1{font-size:26pt}.deckblatt li{margin:4px 0}</style>"] + stile + ["</head><body>"]
    z.append('<div class="deckblatt"><h1>Auftragsmappe</h1><p style="font-size:14pt">Auftrag <b>%s</b><br>%s</p><p>%s</p><ol>%s</ol>'
             '<p style="font-size:8pt;color:#666">Spengler Digital CAD %s – zum Drucken oder als PDF speichern: Strg+P im Browser.</p></div>'
             % (e(auftrag or "–"), e(objekt or "–"), e(datum), "".join("<li>%s</li>" % e(t) for t, _ in teile), e(version)))
    for titel, body in teile:
        z.append('<div class="neueSeite" style="margin-top:8mm"><!-- %s -->%s</div>' % (e(titel), body))
    z.append("</body></html>")
    return "\n".join(z)

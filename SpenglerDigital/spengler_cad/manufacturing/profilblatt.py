"""Profilblatt einer Kantenvorlage: grosse Querschnittzeichnung mit Schenkelmassen, Biegungen und Winkeln plus Tabelle (HTML, druckbar).
Alle Masse theoretisch (Blechmitte, Biegerechnung der App); der Querschnitt beginnt an der bestehenden Kante («Kante»)."""
import html

from ..core import template_engine
from .drawing import kanten_profil, profil_svg


def profilblatt_html(vorlage, material=None, werte=None, objekt="", auftrag="", datum="", version=""):
    """→ (html, None) oder (None, Grund). Ohne Materialprofil: Skizze mit t = 1 mm und ri = t (ausdrücklich so beschriftet)."""
    e = html.escape
    skizze = material is None
    m = dict(material) if material else {"name": "Skizze (ohne Materialprofil)", "thickness": 1.0}
    if m.get("innerRadius") is None:
        m["innerRadius"] = m["thickness"]
    if m.get("kFactor") is None:
        m["kFactor"] = 0.5
    try:
        ops, _ = template_engine.aufloesen(vorlage, werte or {}, m)
        res, _ = kanten_profil(ops, m["thickness"], m["innerRadius"], m["kFactor"])
    except Exception as ex:
        return None, (str(ex).splitlines()[-1] if str(ex) else "Profil nicht berechenbar")
    z = ['<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Profil %s</title>' % e(vorlage.get("name", "")),
         "<style>body{font-family:Segoe UI,Arial,sans-serif;margin:14mm;color:#111}h1{font-size:18pt;margin:0 0 6px}table{border-collapse:collapse;margin-top:10px}"
         "td,th{border:1px solid #888;padding:3px 10px;text-align:left}.hin{color:#8a5a00;font-size:9pt}svg{max-width:100%;height:auto}</style></head><body>",
         "<h1>Profil: %s</h1>" % e(vorlage.get("name", "")),
         "<p>%s%sMaterial: <b>%s</b>, Dicke <b>%g mm</b>, Innenradius %g mm%s</p>" % (
             ("Objekt: <b>%s</b> · " % e(objekt)) if objekt else "", ("Auftrag: <b>%s</b> · " % e(auftrag)) if auftrag else "",
             e(m["name"]), m["thickness"], m["innerRadius"], " (Annahme für die Skizze)" if skizze or material.get("innerRadius") is None else ""),
         profil_svg(res, 760, 480, rand=40, schrift=14, dicke=m["thickness"], basis_segment=True, kante_a="Kante", kante_b=False),
         "<table><tr><th>Nr</th><th>Art</th><th>Winkel</th><th>Schenkel mm</th><th>Innenradius mm</th></tr>"]
    for i, op in enumerate(ops, 1):
        z.append("<tr><td>%d</td><td>%s</td><td>%g°</td><td>%g</td><td>%s</td></tr>" % (
            i, "Umschlag" if op["typ"] == "umschlag" else "Flansch", op["winkel"], op["laenge"],
            ("%g" % op["radius"]) if op.get("radius") is not None else "%g (Material)" % m["innerRadius"]))
    z.append("</table><p class='hin'>Masse theoretisch, bis Blechmitte; + Winkel = Biegung nach links, − nach rechts in Laufrichtung ab der Kante. "
             "Verbindlich sind die Fusion-Abwicklung und die Werkstattkontrolle.</p>")
    z.append("<p style='font-size:8pt;color:#666'>%s Spengler Digital CAD %s</p></body></html>" % (e(datum), e(version)))
    return "\n".join(z), None

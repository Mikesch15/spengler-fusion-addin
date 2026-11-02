#!/usr/bin/env python3
"""Erzeugt die Symbole der Werkzeugleiste und das Logo des Add-ins aus einfachen SVG-Zeichnungen (einheitlicher, flacher Stil).

Aufruf:  SP=<Ordner mit node_modules/playwright-core> python3 werkzeug/icons_erzeugen.py
Schreibt SVG nach werkzeug/icons/ (Quelle, nicht im Add-in-Paket) und PNG nach SpenglerDigital/assets/icons/<name>/ (16x16, 16x16@2x, 32x32, 32x32@2x,
jeweils auch -dark) sowie SpenglerDigital/assets/logo/ (logo_32/64/256/512.png). Die PNG werden eingecheckt; das Skript braucht nur, wer die Symbole ändert."""
import json
import math
import os
import subprocess
import sys

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUELLE = os.path.join(WURZEL, "werkzeug", "icons")
ZIEL = os.path.join(WURZEL, "SpenglerDigital", "assets", "icons")
LOGO = os.path.join(WURZEL, "SpenglerDigital", "assets", "logo")

BLAU, ORANGE, DUNKEL = "#1f78c1", "#f28c28", "#17496f"
S = 'fill="none" stroke="%s" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'


def svg(inhalt, farbe=BLAU, akzent=ORANGE):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
            '<g %s>%s</g></svg>') % (S % farbe, inhalt.replace("ACC", akzent).replace("INK", farbe))


def zahnrad(cx=16, cy=16, r1=12.0, r2=9.2, zaehne=8):
    pts = []
    for i in range(zaehne):
        a = 2 * math.pi * i / zaehne
        w = math.pi / zaehne * 0.55
        for ang, r in ((a - w, r2), (a - w * 0.6, r1), (a + w * 0.6, r1), (a + w, r2)):
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return "M" + " L".join("%.1f %.1f" % p for p in pts) + " Z"


ICONS = {
    # Auftrag
    "start": '<rect x="7" y="6" width="18" height="21" rx="2.5"/><path d="M12 6V4.5h8V6"/><path d="M11 14l2.4 2.4L18 12" stroke="ACC"/><path d="M11 21h10" /><path d="M11 24h6"/>',
    "auftrag_neu": '<path d="M4 9a2 2 0 0 1 2-2h6l3 3h11a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M16 14v8M12 18h8" stroke="ACC"/>',
    "auftrag_wahl": '<path d="M4 9a2 2 0 0 1 2-2h6l3 3h11a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M11 18.5l3.2 3.2L21 15" stroke="ACC"/>',
    "abgleich": '<path d="M6 13a10 10 0 0 1 17-4.5L26 11"/><path d="M26 5.5V11h-5.5" stroke="ACC"/><path d="M26 19a10 10 0 0 1-17 4.5L6 21"/><path d="M6 26.5V21h5.5" stroke="ACC"/>',
    # Konstruieren
    "kanten": '<path d="M3 24h15q5 0 5-5V8"/><path d="M23 8h-6q-2 0-2 2v2" stroke="ACC"/><path d="M3 28h15q9 0 9-9V6" opacity=".35"/>',
    "details": '<path d="M16 3.5l11 6v13l-11 6-11-6v-13z"/><path d="M5 9.5l11 6 11-6M16 15.5v13" /><path d="M16 3.5l11 6-11 6-11-6z" fill="ACC" fill-opacity=".25" stroke="ACC"/>',
    "rundblech": '<ellipse cx="16" cy="9" rx="7" ry="3"/><path d="M9 9l-5 14M23 9l5 14"/><path d="M4 23q12 7 24 0" stroke="ACC"/>',
    "lernen": '<path d="M3 24h8q3 0 3-3V10"/><path d="M14 10h-4" stroke="ACC"/><path d="M19 15h4"/><rect x="19" y="8" width="9" height="16" rx="1.5"/><path d="M21.5 12h4M21.5 16h4M21.5 20h2.5" stroke="ACC"/>',
    "app_vorlage": '<path d="M9 22a5.5 5.5 0 0 1 .7-10.9A7 7 0 0 1 23 12.5 4.8 4.8 0 0 1 22.5 22z"/><path d="M16 14v9m-3.5-3.5L16 23l3.5-3.5" stroke="ACC"/>',
    # Fertigung
    "abwicklung": '<rect x="4" y="7" width="24" height="18" rx="1.5"/><path d="M12 7v18M20 7v18" stroke="ACC" stroke-dasharray="2.5 2.5"/><path d="M8 16h-2.5m2.5 0l-1.6-1.6M8 16l-1.6 1.6" />',
    "stueckliste": '<rect x="4" y="5" width="24" height="22" rx="2"/><path d="M4 11h24" stroke="ACC"/><path d="M12 11v16M10 17h-2M10 22h-2M24 17h-8M24 22h-8" /><path d="M4 11h24V7a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2z" fill="ACC" fill-opacity=".2" stroke="none"/>',
    # Verwaltung
    "einstellungen": '<path d="%s"/><circle cx="16" cy="16" r="3.6" stroke="ACC"/>' % zahnrad(),
    "hilfe": '<circle cx="16" cy="16" r="12"/><path d="M12.3 12.6a3.9 3.9 0 1 1 5.3 3.6c-1.1.6-1.6 1.2-1.6 2.5" /><circle cx="16" cy="23" r="1.2" fill="ACC" stroke="ACC"/>',
}

LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a8fd6"/><stop offset="1" stop-color="#123f63"/></linearGradient></defs>
<rect x="4" y="4" width="120" height="120" rx="26" fill="url(#g)"/>
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 86h46q22 0 22-22V32" stroke="#fff" stroke-width="10"/>
<path d="M90 32H70q-8 0-8 8v6" stroke="#f9a23c" stroke-width="10"/>
<path d="M22 102h52q30 0 30-30V30" stroke="#fff" stroke-opacity=".28" stroke-width="5"/>
</g></svg>'''


def png_rendern(aufgaben):
    """aufgaben: [(svg_text, ziel_png, groesse_px)] → rendert mit Chromium (Playwright)."""
    sp = os.environ.get("SP", "/opt/node-tools")
    skript = (
        "const {chromium}=require(process.env.SP+'/node_modules/playwright-core');"
        "(async()=>{const a=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));"
        "const b=await chromium.launch({executablePath:process.env.CHROME||undefined,args:['--no-sandbox']});const p=await b.newPage();"
        "for(const [s,z,g] of a){await p.setViewportSize({width:g,height:g});"
        "await p.setContent('<body style=\"margin:0;background:transparent\">'+s.replace(/width=\"\\d+\" height=\"\\d+\"/,'width=\"'+g+'\" height=\"'+g+'\"')+'</body>');"
        "await p.screenshot({path:z,omitBackground:true,clip:{x:0,y:0,width:g,height:g}});}"
        "await b.close();})();")
    tmp = os.path.join(WURZEL, "werkzeug", "_rendern.json")
    js = os.path.join(WURZEL, "werkzeug", "_rendern.js")
    json.dump(aufgaben, open(tmp, "w", encoding="utf-8"))
    open(js, "w").write(skript)
    try:
        subprocess.run(["node", js, tmp], check=True, env=dict(os.environ, SP=sp))
    finally:
        for f in (tmp, js):
            if os.path.exists(f):
                os.remove(f)


def main():
    os.makedirs(QUELLE, exist_ok=True)
    aufgaben = []
    for name, inhalt in ICONS.items():
        hell, dunkel = svg(inhalt), svg(inhalt, farbe="#8fc6f0", akzent="#ffb454")
        open(os.path.join(QUELLE, name + ".svg"), "w", encoding="utf-8").write(hell)
        ordner = os.path.join(ZIEL, name)
        os.makedirs(ordner, exist_ok=True)
        for variante, text in (("", hell), ("-dark", dunkel)):
            for datei, px in (("16x16", 16), ("16x16@2x", 32), ("32x32", 32), ("32x32@2x", 64)):
                aufgaben.append((text, os.path.join(ordner, datei + variante + ".png"), px))
    open(os.path.join(QUELLE, "logo.svg"), "w", encoding="utf-8").write(LOGO_SVG)
    os.makedirs(LOGO, exist_ok=True)
    for px in (32, 64, 256, 512):
        aufgaben.append((LOGO_SVG, os.path.join(LOGO, "logo_%d.png" % px), px))
    # Gemeinsame Symbole (Rückfall / Add-in-Eintrag): das Logo
    for datei, px in (("16x16", 16), ("16x16@2x", 32), ("32x32", 32), ("32x32@2x", 64)):
        aufgaben.append((LOGO_SVG, os.path.join(ZIEL, datei + ".png"), px))
    png_rendern(aufgaben)
    print("%d Bilder erzeugt" % len(aufgaben))


if __name__ == "__main__":
    sys.exit(main())

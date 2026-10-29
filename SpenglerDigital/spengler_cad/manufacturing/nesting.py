"""Zuschnittoptimierung – Python-Port der bestehenden App-Rechnung (Spengler-Digital-V1, js/29-einlaufblech-aufnahme.js).

Übernommen (Logik 1:1, gegen Referenzfälle aus dem echten JavaScript getestet):
  ebaStreifenJeAbschnitt → streifen_je_abschnitt   floor((B + f) / (A + f))
  ebaRestBreite          → rest_breite            B − n·A − (n−1)·f
  ebaVerteile            → _verteile              exakte Suche mit Budget (Stücke auf k Streifen)
  ebaPackeInStreifen     → packe_in_streifen      gierig, dann kleinste Streifenzahl ab Untergrenze
  ebaPackeMehrereAbschnitte → packe_mehrere_abschnitte  (Rolle, ≥2 Streifen je Abschnitt)
  ebaFormatZeilen/ebaFormatPlan → format_plan     (ohne Rollenmischung, s. unten)
Modell der App: Teile werden als Streifen der Abwicklungsbreite A quer aus Rolle/Tafel (Breite B)
geschnitten; die Teile liegen längs im Streifen. Schnittfuge f fällt ZWISCHEN zwei Stücken an.

NICHT übernommen (bewusst, und so in der Oberfläche ausgewiesen):
  - Rollenmischung (v3.328, ebaRollenMischung) und Trittbrett-Mischung verschiedener Breiten (ebaMischeAbschnitte)
  - Teilen zu langer Stücke mit Nahtüberlappung (ebaBlecheGeteilt) – zu lange Stücke werden gemeldet
  - Reststücklager (js/42) – die Fusion-Seite kennt das Lager der App nicht
Zusätzlich (neu, nicht aus der App): Randabstand je Tafelseite, optional Drehen bei Tafeln,
Überlappungsprüfung der erzeugten Lage, SVG/CSV-Ausgabe.
Teile sind Rechtecke (Abwicklungsbreite × Länge). Freie Konturen werden NICHT verschachtelt.
"""

EPS = 1e-9


def streifen_je_abschnitt(B, A, fuge=0.0):
    if A <= 0 or B <= 0:
        return 0
    import math
    return int(math.floor((B + fuge) / (A + fuge)))


def rest_breite(B, A, n, fuge=0.0):
    if B <= 0 or A <= 0 or n < 1:
        return 0.0
    r = B - n * A - (n - 1) * fuge
    return r if r > 0 else 0.0


def _stueckliste(stuecke):
    return sorted([s for s in stuecke if s["laenge"] > 0], key=lambda s: -s["laenge"])


def _verteile(stuecke, k, L, fuge, budget):
    """Exakte Verteilung der (absteigend sortierten) Stücke auf k Streifen der Länge L.
    → Liste von Streifen, False (passt nicht) oder None (Budget aufgebraucht)."""
    if k < 1:
        return False if stuecke else []
    if stuecke and stuecke[0]["laenge"] > L + EPS:
        return False
    streifen = [{"stuecke": [], "rest": float(L)} for _ in range(k)]
    zustand = {"schritte": 0, "aus": False}
    grenze = budget or 200000

    def setze(i):
        if i >= len(stuecke):
            return True
        zustand["schritte"] += 1
        if zustand["schritte"] > grenze:
            zustand["aus"] = True
            return False
        roh = stuecke[i]["laenge"]
        gesehen = []
        for st in streifen:
            ln = roh + (fuge if st["stuecke"] else 0.0)
            if st["rest"] < ln - EPS:
                continue
            if st["rest"] in gesehen:
                continue
            gesehen.append(st["rest"])
            st["stuecke"].append(stuecke[i])
            st["rest"] -= ln
            if setze(i + 1):
                return True
            st["stuecke"].pop()
            st["rest"] += ln
            if zustand["aus"]:
                return False
        return False

    if setze(0):
        return streifen
    return None if zustand["aus"] else False


def packe_in_streifen(stuecke, L, fuge=0.0, budget=None):
    """Feste Streifenlänge L, kleinstmögliche Streifenzahl. stuecke: [{'nr', 'laenge', …}]"""
    st = _stueckliste(stuecke)
    if not st:
        return {"streifen": [], "optimal": True, "zuLang": []}
    if st[0]["laenge"] > L:
        return {"streifen": None, "optimal": True, "zuLang": [s for s in st if s["laenge"] > L]}
    gierig = []
    for s in st:
        ziel = next((g for g in gierig if g["rest"] >= s["laenge"] + fuge - EPS), None)
        if ziel:
            ziel["stuecke"].append(s)
            ziel["rest"] -= s["laenge"] + fuge
        else:
            gierig.append({"stuecke": [s], "rest": L - s["laenge"]})
    summe = sum(s["laenge"] for s in st)
    import math
    untergrenze = int(math.ceil(summe / L - EPS))
    for k in range(untergrenze, len(gierig)):
        v = _verteile(st, k, L, fuge, budget)
        if v is None:
            return {"streifen": gierig, "optimal": False, "zuLang": []}
        if v:
            return {"streifen": v, "optimal": True, "zuLang": []}
    return {"streifen": gierig, "optimal": True, "zuLang": []}


def packe_mehrere_abschnitte(stuecke, je_abschnitt, fuge=0.0, budget=None):
    """Rolle mit ≥2 Streifen je Abschnitt: jeder Abschnitt so lang wie sein längstes Stück (Regel der App)."""
    offen = _stueckliste(stuecke)
    if not offen:
        return {"abschnitte": [], "streifen": [], "optimal": True}
    abschnitte = []
    schritte, grenze, aus = 0, budget or 200000, False
    while offen:
        schritte += 1
        if schritte > grenze:
            aus = True
            break
        L = offen[0]["laenge"]
        lanes = [{"stuecke": [], "rest": L} for _ in range(max(1, je_abschnitt))]
        lanes[0]["stuecke"].append(offen.pop(0))
        lanes[0]["rest"] -= L
        i = 0
        while i < len(offen):
            s = offen[i]
            platziert = False
            for lane in lanes:
                kosten = s["laenge"] + (fuge if lane["stuecke"] else 0.0)
                if lane["rest"] >= kosten - EPS:
                    lane["stuecke"].append(s)
                    lane["rest"] -= kosten
                    offen.pop(i)
                    platziert = True
                    break
            if not platziert:
                i += 1
        nr = len(abschnitte) + 1
        abschnitte.append({"laenge": L, "streifen": [dict(l, abschnittLaenge=L, abschnittNr=nr) for l in lanes if l["stuecke"]]})
    streifen = [s for a in abschnitte for s in a["streifen"]]
    return {"abschnitte": abschnitte, "streifen": streifen, "optimal": not aus}


def _format_gruppe(g, fmt, fuge):
    """Eine Streifenbreite (Gruppe) auf einem Format (Rolle: laenge None, Tafel: [B, L])."""
    B, Lt = fmt["breite"], fmt.get("laenge")
    ist_rolle = Lt is None
    je = streifen_je_abschnitt(B, g["breite"], fuge)
    if je < 1:
        return {"schmal": True}
    if ist_rolle and je >= 2:
        mp = packe_mehrere_abschnitte(g["stuecke"], je, fuge)
        rl = sum(a["laenge"] for a in mp["abschnitte"])
        return {"je": je, "streifen": mp["streifen"], "optimal": mp["optimal"], "abschnitte": len(mp["abschnitte"]),
                "rollenLaenge": rl, "abschnittLaenge": max([a["laenge"] for a in mp["abschnitte"]] or [0]),
                "abschnittListe": mp["abschnitte"]}
    L = max(s["laenge"] for s in g["stuecke"]) if ist_rolle else Lt
    v = packe_in_streifen(g["stuecke"], L, fuge)
    if v["streifen"] is None:
        return {"lang": v["zuLang"], "laenge": L}
    streifen = v["streifen"]
    import math
    ab = int(math.ceil(len(streifen) / float(je)))
    if je == 1 and ist_rolle:
        rl = sum(max(0.0, L - s["rest"]) for s in streifen)
    else:
        rl = ab * L
    return {"je": je, "streifen": streifen, "optimal": v["optimal"], "abschnitte": ab, "rollenLaenge": rl, "abschnittLaenge": L}


def format_plan(gruppen, formate, fuge=0.0):
    """gruppen: [{'breite': A, 'stuecke': [{'nr','laenge',…}]}]; formate: [{'breite': B, 'laenge': L|None, 'text'}]
    → {'moeglich': [...sortiert, bestes zuerst], 'zuSchmal', 'zuKurz', 'bestes', 'netto' (m²)}"""
    gruppen = [g for g in gruppen if g.get("stuecke") and g.get("breite", 0) > 0]
    netto = sum(g["breite"] * s["laenge"] for g in gruppen for s in g["stuecke"]) / 1e6
    moeglich, zu_schmal, zu_kurz = [], [], []
    for f in formate:
        zeilen, flaeche, problem = [], 0.0, None
        for g in gruppen:
            r = _format_gruppe(g, f, fuge)
            if r.get("schmal"):
                problem = ("schmal", f)
                break
            if "lang" in r:
                problem = ("lang", {"format": f, "stuecke": r["lang"]})
                break
            r["breite"] = g["breite"]
            r["restBreite"] = rest_breite(f["breite"], g["breite"], r["je"], fuge)
            r["ungenutzteStreifen"] = r["abschnitte"] * r["je"] - len(r["streifen"]) if not (f.get("laenge") is None and r["je"] >= 2) else 0
            zeilen.append(r)
            flaeche += f["breite"] * r["rollenLaenge"] / 1e6
        if problem:
            (zu_schmal if problem[0] == "schmal" else zu_kurz).append(problem[1])
            continue
        moeglich.append({"format": f, "zeilen": zeilen, "flaeche": flaeche, "verschnitt": flaeche - netto,
                         "anteil": (flaeche - netto) / flaeche * 100 if flaeche > 0 else 0.0,
                         "rollenLaenge": sum(z["rollenLaenge"] for z in zeilen),
                         "optimal": all(z["optimal"] for z in zeilen)})
    moeglich.sort(key=lambda e: (e["flaeche"], e["rollenLaenge"], -e["format"]["breite"]))
    return {"moeglich": moeglich, "zuSchmal": zu_schmal, "zuKurz": zu_kurz, "bestes": moeglich[0] if moeglich else None, "netto": netto}


# ---------------------------------------------------------------------------- Fusion-Abwicklungen → Plan
def teile_gruppieren(teile, drehen_erlaubt=False, tafel_laengen=None):
    """teile: [{'name', 'breite' (quer zu den Biegelinien), 'laenge' (längs), 'stueck'}] → Gruppen je Breite.
    Drehen (Breite↔Länge) nur wenn erlaubt und das Teil sonst in keine Tafel passt."""
    gruppen = {}
    hinweise = []
    nr = 0
    max_l = max(tafel_laengen) if tafel_laengen else None
    for t in teile:
        b, l = float(t["breite"]), float(t["laenge"])
        if drehen_erlaubt and max_l is not None and l > max_l and b <= max_l:
            b, l = l, b
            hinweise.append("%s wurde gedreht (Länge %.0f mm passt sonst in keine Tafel)." % (t["name"], b))
        key = round(b, 1)
        g = gruppen.setdefault(key, {"breite": key, "stuecke": []})
        for _ in range(max(0, int(t.get("stueck", 1)))):
            nr += 1
            g["stuecke"].append({"nr": nr, "laenge": l, "name": t["name"]})
    return sorted(gruppen.values(), key=lambda g: -g["breite"]), hinweise


def formate_aus_material(material, rand=0.0):
    """Tafeln und Rollen aus dem Materialprofil; Randabstand verkleinert die nutzbare Fläche je Seite."""
    out = []
    for c in material.get("coils") or []:
        nb = c - 2 * rand
        if nb > 0:
            out.append({"breite": nb, "laenge": None, "text": "Rolle %g mm" % c, "brutto": [c, None]})
    for b, l in material.get("sheets") or []:
        nb, nl = b - 2 * rand, l - 2 * rand
        if nb > 0 and nl > 0:
            out.append({"breite": nb, "laenge": nl, "text": "Tafel %g × %g mm" % (b, l), "brutto": [b, l]})
    return out


# ---------------------------------------------------------------------------- Lage, Prüfung, Ausgabe
def lage(eintrag, fuge=0.0, rand=0.0):
    """Konkrete Rechtecke je Abschnitt/Tafel für Darstellung und Kollisionsprüfung.
    → [{'blatt': i, 'laenge': L, 'breite': B, 'rechtecke': [{'x','y','w','h','name','nr'}]}]"""
    f = eintrag["format"]
    blaetter = []
    for z in eintrag["zeilen"]:
        A, je = z["breite"], z["je"]
        if "abschnittListe" in z:
            abschnitte = [(a["laenge"], a["streifen"]) for a in z["abschnittListe"]]
        else:
            s = z["streifen"]
            abschnitte = [(z["abschnittLaenge"] if f.get("laenge") is not None or je > 1 else max(0.0, z["abschnittLaenge"] - st["rest"]), s[i:i + je])
                          for i, st in ((i, s[i]) for i in range(0, len(s), je))]
        for L, streifen in abschnitte:
            rechtecke = []
            for j, st in enumerate(streifen):
                x = rand + j * (A + fuge)
                y = rand
                for p in st["stuecke"]:
                    rechtecke.append({"x": x, "y": y, "w": A, "h": p["laenge"], "name": p.get("name", ""), "nr": p["nr"]})
                    y += p["laenge"] + fuge
            blaetter.append({"blatt": len(blaetter) + 1, "breite": (f.get("brutto") or [f["breite"]])[0],
                             "laenge": (f.get("brutto") or [None, None])[1] or L + 2 * rand, "rechtecke": rechtecke})
    return blaetter


def kollisionen(blaetter, fuge=0.0, rand=0.0):
    """Überlappungen und Randverletzungen finden → Liste von Texten (leer = in Ordnung)."""
    out = []
    for b in blaetter:
        r = b["rechtecke"]
        for i, a in enumerate(r):
            if a["x"] < rand - 1e-6 or a["y"] < rand - 1e-6 or a["x"] + a["w"] > b["breite"] - rand + 1e-6 or a["y"] + a["h"] > b["laenge"] - rand + 1e-6:
                out.append("Blatt %d: Teil %s ragt über den Rand." % (b["blatt"], a["nr"]))
            for c in r[i + 1:]:
                if a["x"] < c["x"] + c["w"] + fuge - 1e-6 and c["x"] < a["x"] + a["w"] + fuge - 1e-6 and \
                   a["y"] < c["y"] + c["h"] + fuge - 1e-6 and c["y"] < a["y"] + a["h"] + fuge - 1e-6:
                    out.append("Blatt %d: Teile %s und %s überlappen (inkl. Schnittfuge)." % (b["blatt"], a["nr"], c["nr"]))
    return out


def als_svg(blaetter, massstab=0.1):
    teile, y0 = [], 10.0
    breite = max([b["breite"] for b in blaetter] or [100]) * massstab + 20
    for b in blaetter:
        h = b["laenge"] * massstab
        teile.append('<rect x="10" y="%.2f" width="%.2f" height="%.2f" fill="#eef1f4" stroke="#333" stroke-width="0.6"/>' % (y0, b["breite"] * massstab, h))
        teile.append('<text x="10" y="%.2f" font-size="7" font-family="sans-serif">Blatt %d: %g × %g mm</text>' % (y0 - 2, b["blatt"], b["breite"], b["laenge"]))
        for r in b["rechtecke"]:
            teile.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#9fb4c7" stroke="#1d3557" stroke-width="0.4"/>'
                         % (10 + r["x"] * massstab, y0 + r["y"] * massstab, r["w"] * massstab, r["h"] * massstab))
            teile.append('<text x="%.2f" y="%.2f" font-size="5" font-family="sans-serif">%s</text>'
                         % (12 + r["x"] * massstab, y0 + r["y"] * massstab + 6, _xml("%s %s" % (r["nr"], r["name"]))))
        y0 += h + 18
    return '<svg xmlns="http://www.w3.org/2000/svg" width="%.0f" height="%.0f" viewBox="0 0 %.0f %.0f">%s</svg>' % (breite, y0, breite, y0, "".join(teile))


def als_csv(eintrag):
    z = ["Nr;Teil;Breite mm;Laenge mm;Streifen"]
    for g in eintrag["zeilen"]:
        for i, st in enumerate(g["streifen"], 1):
            for p in st["stuecke"]:
                z.append("%s;%s;%.1f;%.1f;%d" % (p["nr"], p.get("name", ""), g["breite"], p["laenge"], i))
    return "\n".join(z) + "\n"


def _xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

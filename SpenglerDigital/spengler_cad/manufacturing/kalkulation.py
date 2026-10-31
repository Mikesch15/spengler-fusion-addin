"""Kalkulation je Teil und Auftrag: Arbeitszeit × Stundensatz (aus der App) + Material (nur mit Preis je kg im Materialprofil).

Die Zeiten sind Annahmen aus den Einstellungen (Rüstzeit je Teil, Minuten je Biegung, Minuten je Meter Zuschnittumfang, Zuschlag) – keine
erfundenen Fertigungswerte: ohne eigene Eingabe gelten die Standardwerte der Einstellungen, die im Ergebnis ausdrücklich genannt werden.
Zuschnittumfang = Umfang des umschliessenden Rechtecks der Abwicklung (obere Schätzung). Reine Logik."""
import html


def standard():
    return {"stundensatzName": "", "stundensatzManuell": None, "ruestMinProTeil": 5.0, "minProBiegung": 1.5, "minProMeterZuschnitt": 2.0, "zuschlagProzent": 0.0}


def stundensatz_waehlen(einstellung, app_saetze):
    """→ (satz je Stunde oder None, Quelle-Text). Name in der App hat Vorrang vor dem handschriftlichen Wert."""
    k = dict(standard(), **(einstellung or {}))
    name = (k.get("stundensatzName") or "").strip().lower()
    for s in app_saetze or []:
        if name and str(s.get("name", "")).strip().lower() == name:
            return float(s["value"]), "App: %s" % s["name"]
    if k.get("stundensatzManuell") is not None:
        return float(k["stundensatzManuell"]), "von Hand eingetragen"
    if name:
        return None, "Stundensatz «%s» nicht in der App gefunden (oder keine Berechtigung/nicht angemeldet)" % k["stundensatzName"]
    return None, "kein Stundensatz gewählt (Einstellungen → Kalkulation)"


def kalkuliere(teile, einstellung, satz):
    """teile: [{'nr','name','stueck','breite','laenge','flaeche' (mm² oder None),'material' (Profil), 'operationen' (oder None)}]
    → {'zeilen': [...], 'summe': {...}, 'annahmen': str}. Material nur mit pricePerKg und Dichte; Kosten nur mit Stundensatz."""
    k = dict(standard(), **(einstellung or {}))
    zeilen = []
    for t in teile:
        stueck = max(0, int(t.get("stueck") or 1))
        biegungen = len(t.get("operationen") or [])
        umfang_m = 2.0 * (t["breite"] + t["laenge"]) / 1000.0
        min_je = k["ruestMinProTeil"] + biegungen * k["minProBiegung"] + umfang_m * k["minProMeterZuschnitt"]
        min_je *= 1.0 + k["zuschlagProzent"] / 100.0
        m = t.get("material") or {}
        flaeche_m2 = (t["flaeche"] if t.get("flaeche") is not None else t["breite"] * t["laenge"]) / 1e6
        kg = flaeche_m2 * m["thickness"] * m["density"] if m.get("thickness") and m.get("density") else None
        mat = kg * m["pricePerKg"] * stueck if kg is not None and m.get("pricePerKg") is not None else None
        arbeit = min_je / 60.0 * satz * stueck if satz is not None else None
        zeilen.append({"nr": t.get("nr", ""), "name": t["name"], "stueck": stueck, "biegungen": biegungen, "minuten_je": min_je,
                       "minuten": min_je * stueck, "arbeit": arbeit, "material": mat,
                       "summe": (arbeit or 0) + (mat or 0) if (arbeit is not None or mat is not None) else None})
    summe = {"minuten": sum(z["minuten"] for z in zeilen),
             "arbeit": sum(z["arbeit"] for z in zeilen) if satz is not None else None,
             "material": sum(z["material"] or 0 for z in zeilen) if any(z["material"] is not None for z in zeilen) else None}
    summe["gesamt"] = (summe["arbeit"] or 0) + (summe["material"] or 0) if (summe["arbeit"] is not None or summe["material"] is not None) else None
    annahmen = "Annahmen: Rüsten %.1f min je Teil, %.1f min je Biegung, %.1f min je m Zuschnittumfang, Zuschlag %.0f %%." % (
        k["ruestMinProTeil"], k["minProBiegung"], k["minProMeterZuschnitt"], k["zuschlagProzent"])
    return {"zeilen": zeilen, "summe": summe, "annahmen": annahmen, "satz": satz}


def _geld(x):
    return "–" if x is None else "%.2f" % x


def kalkulation_html(erg, quelle, objekt="", auftrag="", datum="", version=""):
    e = html.escape
    z = ['<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Kalkulation %s</title><style>body{font-family:Segoe UI,Arial,sans-serif;margin:14mm}'
         'table{border-collapse:collapse}td,th{border:1px solid #888;padding:3px 8px;text-align:right}td:nth-child(1),td:nth-child(2),th{text-align:left}'
         '.hin{color:#8a5a00}</style></head><body>' % e(auftrag or objekt),
         "<h1>Kalkulation</h1><p>Objekt: <b>%s</b> · Auftrag: <b>%s</b> · %s</p>" % (e(objekt), e(auftrag), e(datum)),
         "<p>Stundensatz: <b>%s</b> (%s)</p>" % (_geld(erg["satz"]) if erg["satz"] is not None else "–", e(quelle)),
         "<table><tr><th>Nr</th><th>Teil</th><th>Stück</th><th>Biegungen</th><th>min je Teil</th><th>Arbeitszeit h</th><th>Arbeit</th><th>Material</th><th>Summe</th></tr>"]
    for r in erg["zeilen"]:
        z.append("<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%.1f</td><td>%.2f</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(str(r["nr"])), e(r["name"]), r["stueck"], r["biegungen"], r["minuten_je"], r["minuten"] / 60.0, _geld(r["arbeit"]), _geld(r["material"]), _geld(r["summe"])))
    s = erg["summe"]
    z.append("<tr><th colspan='5'>Summe</th><th>%.2f</th><th>%s</th><th>%s</th><th>%s</th></tr></table>" % (s["minuten"] / 60.0, _geld(s["arbeit"]), _geld(s["material"]), _geld(s["gesamt"])))
    z.append("<p class='hin'>%s Zeiten sind Schätzwerte. Material nur, wenn im Materialprofil Dichte und Preis je kg stehen. Keine Gewähr – ersetzt keine Offerte.</p>" % e(erg["annahmen"]))
    z.append("<p style='font-size:8pt;color:#666'>Spengler Digital CAD %s</p></body></html>" % e(version))
    return "\n".join(z)

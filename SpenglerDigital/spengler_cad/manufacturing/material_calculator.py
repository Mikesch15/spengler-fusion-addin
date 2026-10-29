"""Material- und Zuschnittberechnung. Schätzwerte werden ausdrücklich als Schätzung gekennzeichnet.

teile: [{'name', 'materialId', 'flaeche' (mm², echte Abwicklungsfläche falls bekannt, sonst None),
         'breite', 'laenge' (mm, umschliessendes Rechteck der Abwicklung), 'stueck'}]
"""
from . import nesting


def berechne(teile, materialien, einstellungen=None):
    """→ {'materialien': [...je Material...], 'hinweise': [...]}"""
    n = (einstellungen or {}).get("nesting", {})
    fuge, rand, drehen = float(n.get("kerf") or 0), float(n.get("margin") or 0), bool(n.get("rotationAllowed"))
    nach = {}
    for t in teile:
        nach.setdefault(t.get("materialId"), []).append(t)
    mats = {m["id"]: m for m in materialien}
    out, hinweise = [], []
    for mid, liste in nach.items():
        m = mats.get(mid)
        e = {"material": m["name"] if m else "(kein Materialprofil)", "materialId": mid, "teile": 0,
             "flaeche_netto_m2": 0.0, "flaeche_rechteck_m2": 0.0, "flaeche_quelle": "Abwicklung",
             "gewicht_kg": None, "gewicht_ist_schaetzung": True, "zuschnitt": None, "hinweise": []}
        for t in liste:
            s = max(0, int(t.get("stueck", 1)))
            e["teile"] += s
            rechteck = t["breite"] * t["laenge"] / 1e6
            e["flaeche_rechteck_m2"] += rechteck * s
            if t.get("flaeche") is not None:
                e["flaeche_netto_m2"] += t["flaeche"] / 1e6 * s
            else:
                e["flaeche_netto_m2"] += rechteck * s
                e["flaeche_quelle"] = "teilweise umschliessendes Rechteck"
        if m and m.get("density"):
            # m² · mm · kg/dm³ : 1 m² · 1 mm = 1 dm³
            e["gewicht_kg"] = e["flaeche_netto_m2"] * m["thickness"] * m["density"]
        elif m:
            e["hinweise"].append("Keine Dichte im Materialprofil – kein Gewicht berechnet.")
        if m and (m.get("sheets") or m.get("coils")):
            formate = nesting.formate_aus_material(m, rand)
            gruppen, h = nesting.teile_gruppieren(liste, drehen, [f["laenge"] for f in formate if f["laenge"]])
            e["hinweise"] += h
            plan = nesting.format_plan(gruppen, formate, fuge)
            e["zuschnitt"] = plan
            if plan["bestes"]:
                b = plan["bestes"]
                brutto = b["format"].get("brutto") or [b["format"]["breite"], b["format"]["laenge"]]
                # Fläche inkl. Randabstand (Brutto-Format)
                if brutto[1]:
                    blaetter = sum(z["abschnitte"] for z in b["zeilen"])
                    e["verbrauch_m2"] = blaetter * brutto[0] * brutto[1] / 1e6
                    e["verbrauch_text"] = "%d × %s" % (blaetter, b["format"]["text"])
                else:
                    e["verbrauch_m2"] = brutto[0] * b["rollenLaenge"] / 1e6
                    e["verbrauch_text"] = "%s, %.2f m ab Rolle" % (b["format"]["text"], b["rollenLaenge"] / 1000)
                e["ausnutzung_prozent"] = e["flaeche_rechteck_m2"] / e["verbrauch_m2"] * 100 if e["verbrauch_m2"] else None
            else:
                e["hinweise"].append("Kein Lagerformat des Materialprofils passt (zu breit oder zu lang).")
        elif m:
            e["hinweise"].append("Keine Tafel-/Rollenformate im Materialprofil – keine Zuschnittoptimierung.")
        out.append(e)
    if any(t.get("flaeche") is None for t in teile):
        hinweise.append("Für einige Teile ist nur das umschliessende Rechteck bekannt – Fläche ist eine obere Schätzung.")
    hinweise.append("Gewicht = Abwicklungsfläche × Dicke × Dichte: Schätzwert ohne Beschichtung/Toleranzen.")
    return {"materialien": out, "hinweise": hinweise}


def bericht_text(erg):
    z = []
    for e in erg["materialien"]:
        z.append("%s: %d Teile, Abwicklung %.3f m² (%s)" % (e["material"], e["teile"], e["flaeche_netto_m2"], e["flaeche_quelle"]))
        if e.get("gewicht_kg") is not None:
            z.append("  Gewicht (Schätzung): %.2f kg" % e["gewicht_kg"])
        if e.get("verbrauch_text"):
            z.append("  Bedarf: %s = %.3f m², Ausnutzung %.1f %%" % (e["verbrauch_text"], e["verbrauch_m2"], e["ausnutzung_prozent"] or 0))
            if not e["zuschnitt"]["bestes"]["optimal"]:
                z.append("  (Suche abgebrochen – Plan gültig, aber evtl. nicht minimal)")
        for h in e["hinweise"]:
            z.append("  Hinweis: " + h)
    z += ["Hinweis: " + h for h in erg["hinweise"]]
    return "\n".join(z)

"""Ampel im Dialog «Kanten bearbeiten»: grün = bereit, gelb = Hinweis/fehlt noch etwas, rot = geht so nicht – jeweils mit einem Satz, was zu tun ist."""
FARBE = {"gruen": "#2d6a2d", "gelb": "#b26a00", "rot": "#b3261e"}
ZEICHEN = {"gruen": "●", "gelb": "●", "rot": "●"}


def ampel(plan, fehler, hat_koerper, anzahl_kanten):
    """→ (farbe, text). plan/fehler wie in edge_apply_command._plan."""
    if not hat_koerper:
        return "gelb", "Schritt 1: Blechkörper wählen."
    if not anzahl_kanten:
        return "gelb", "Schritt 2: Kanten des Körpers wählen."
    if fehler:
        return "rot", fehler
    if not plan:
        return "gelb", "Noch kein Bauplan."
    v = plan.get("validation") or {}
    if v.get("errors"):
        return "rot", v["errors"][0] + (" (+%d weitere)" % (len(v["errors"]) - 1) if len(v["errors"]) > 1 else "")
    ziele = plan.get("targets") or []
    schlecht = [z for z in ziele if not z.get("geeignet")]
    if schlecht:
        z = schlecht[0]
        grund = (z.get("gruende") or ["nicht geeignet"])[0]
        return "rot", "%d von %d Kanten nicht geeignet: %s – %s" % (len(schlecht), len(ziele), z.get("text", "Kante"), grund)
    kopf = "Bereit: %d Kante%s, %s" % (len(ziele), "" if len(ziele) == 1 else "n", plan.get("templateName") or "Vorlage")
    laengen = [z.get("laenge") for z in ziele if isinstance(z.get("laenge"), (int, float))]
    if laengen and len(laengen) <= 4:
        kopf += " (" + ", ".join("%g mm" % round(x, 1) for x in laengen) + ")"
    mat = (plan.get("material") or {}).get("name")
    if mat:
        kopf += ", " + mat
    if v.get("warnings"):
        return "gelb", kopf + " – Hinweis: " + v["warnings"][0]
    return "gruen", kopf


def html(farbe, text):
    return "<font color='%s'><b>%s</b></font> %s" % (FARBE[farbe], ZEICHEN[farbe], text.replace("<", "&lt;"))

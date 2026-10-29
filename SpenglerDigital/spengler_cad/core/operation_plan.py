"""Bauplan (OperationPlan): Validieren → Bauplan → Vorschau → Bestätigung → Operationen → Ergebnisprüfung.

Der Bauplan entsteht ohne Fusion aus Kantenbeschreibungen. Eine Kantenbeschreibung liefert der
Geometrieadapter (geometry/edge_resolver.py) als dict:
  {"ref": beliebig, "text": "Kante 1", "kurve": "linie"|"kreis"|"bogen"|"ellipse"|"spline"|"andere",
   "laenge": mm, "flaechen": Anzahl angrenzender Flächen, "blech": bool (Blechkörper),
   "dicke": mm|None (aus Blechregel), "frei": bool (Aussenkante, nicht Biegezone)}
"""
from . import template_engine
from .bend_geometry import ProfilFehler, zugabe_abwicklung
from .models import neuer_bauplan


def kante_eignung(kante, vorlage, material):
    """→ (geeignet, gruende[]). Ungeeignete Kanten werden NIE stillschweigend bearbeitet."""
    gruende = []
    if not kante.get("blech"):
        gruende.append("gehört nicht zu einem Blechkörper (Fusion-Arbeitsbereich «Blech» verwenden)")
    typ = (vorlage or {}).get("connection", {}).get("edgeType", "gerade")
    kurve = kante.get("kurve")
    # Flansch/Umschlag folgen auch runden Kanten (Kreis, Bogen). Andere Kurven (Ellipse, Spline) sind nicht zuverlässig → abgelehnt.
    if kurve not in ("linie", "kreis", "bogen"):
        gruende.append("hat den Kurventyp «%s» – Flansch/Umschlag sind nur an geraden Kanten, Kreisen und Kreisbögen möglich" % kurve)
    if typ == "gekruemmt" and kurve == "linie":
        gruende.append("ist gerade – die Vorlage ist für gekrümmte Ränder")
    if kante.get("flaechen", 2) != 2:
        gruende.append("grenzt an %s Flächen (erwartet 2) – keine eindeutige Blechkante" % kante.get("flaechen"))
    if kante.get("frei") is False:
        gruende.append("liegt in einer Biegezone oder ist keine Aussenkante")
    c = (vorlage or {}).get("constraints", {}) or {}
    L = kante.get("laenge") or 0
    if c.get("edgeLengthMin") is not None and L < c["edgeLengthMin"]:
        gruende.append("ist mit %.1f mm kürzer als die Mindestlänge %.1f mm der Vorlage" % (L, c["edgeLengthMin"]))
    t_kante = kante.get("dicke")
    t_mat = (material or {}).get("thickness")
    if t_kante is not None and t_mat is not None and abs(t_kante - t_mat) > 0.005:
        gruende.append("Blechdicke des Körpers %.2f mm passt nicht zum Materialprofil %.2f mm" % (t_kante, t_mat))
    t = t_kante if t_kante is not None else t_mat
    if t is not None:
        if c.get("thicknessMin") is not None and t < c["thicknessMin"] - 1e-9:
            gruende.append("Dicke %.2f mm unter dem Vorlagenbereich (min. %.2f mm)" % (t, c["thicknessMin"]))
        if c.get("thicknessMax") is not None and t > c["thicknessMax"] + 1e-9:
            gruende.append("Dicke %.2f mm über dem Vorlagenbereich (max. %.2f mm)" % (t, c["thicknessMax"]))
    mats = c.get("materials") or []
    if mats and material and material.get("id") not in mats:
        gruende.append("Materialprofil «%s» ist für diese Vorlage nicht freigegeben" % material.get("name"))
    return (not gruende), gruende


def erstelle(vorlage, eingaben, material, kanten):
    """Bauplan erstellen. Fehler stehen in plan['validation']['errors'] – ausgeführt wird nur ohne Fehler."""
    ziele = []
    for k in kanten:
        ok, gruende = kante_eignung(k, vorlage, material)
        ziele.append({"ref": k.get("ref"), "text": k.get("text", "Kante"), "geeignet": ok, "gruende": gruende,
                      "laenge": k.get("laenge")})
    plan = neuer_bauplan(vorlage, eingaben or {}, material, ziele)
    err, warn = plan["validation"]["errors"], plan["validation"]["warnings"]
    if not kanten:
        err.append("Keine Kante gewählt.")
    if not material:
        err.append("Kein Materialprofil gewählt. Unter «Einstellungen → Materialien» ein eigenes Profil anlegen.")
    for z in ziele:
        if not z["geeignet"]:
            err.append("%s ist ungeeignet: %s." % (z["text"], "; ".join(z["gruende"])))
    try:
        ops, w = template_engine.aufloesen(vorlage, eingaben, material)
        plan["operations"] = ops
        warn += w
    except template_engine.VorlagenFehler as e:
        err.append(str(e))
        return plan
    if (vorlage.get("manufacturing") or {}).get("cutsAllowed"):
        warn.append("Die Vorlage erlaubt Einschnitte/Freistellungen.")
    if material and material.get("innerRadius") is not None and material.get("kFactor") is not None:
        try:
            zugabe, res = zugabe_abwicklung(ops, material["thickness"], material["innerRadius"], material["kFactor"])
            plan["theory"] = {"zugabe": zugabe, "biegungen": len(res["biegungen"]),
                              "hinweis": "Theoretisch (Blechmitte, K-Faktor des Materialprofils). Verbindlich ist die Fusion-Abwicklung."}
        except ProfilFehler as e:
            err.append("Biegeradien: %s." % e)
    else:
        plan["theory"] = {"zugabe": None, "hinweis": "Keine theoretische Abwicklung: Innenradius/K-Faktor im Materialprofil fehlen."}
    return plan


def ist_ausfuehrbar(plan):
    return not plan["validation"]["errors"] and bool(plan["operations"]) and any(z["geeignet"] for z in plan["targets"])


def beschreibung(plan):
    """Mehrzeiliger Text für Vorschau/Bestätigung."""
    from .short_syntax import als_text
    z = ["Vorlage: %s%s" % (plan["templateName"], " (Version %s)" % plan["templateVersion"] if plan.get("templateVersion") else "")]
    if plan.get("material"):
        z.append("Material: %s, %.2f mm" % (plan["material"]["name"], plan["material"]["thickness"] or 0))
    if plan["operations"]:
        z.append("Folge: " + als_text(plan["operations"]))
        for i, op in enumerate(plan["operations"], 1):
            art = "Umschlag" if op["typ"] == "umschlag" else "Flansch"
            r = "" if op.get("radius") is None else ", Ri %.2f mm" % op["radius"]
            z.append("  %d. %s %g°, %.2f mm%s" % (i, art, op["winkel"], op["laenge"], r))
    z.append("Kanten: %d gewählt, %d geeignet" % (len(plan["targets"]), sum(1 for t in plan["targets"] if t["geeignet"])))
    th = plan.get("theory") or {}
    if th.get("zugabe") is not None:
        z.append("Abwicklungszugabe theoretisch: %.1f mm je Kante" % th["zugabe"])
    if th.get("hinweis"):
        z.append("  (%s)" % th["hinweis"])
    for e in plan["validation"]["errors"]:
        z.append("FEHLER: " + e)
    for w in plan["validation"]["warnings"]:
        z.append("Warnung: " + w)
    return "\n".join(z)

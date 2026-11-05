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


def kante_eignung(kante, vorlage, material, bauweise="nativ", prototyp=False):
    """→ (geeignet, gruende[]). Ungeeignete Kanten werden NIE stillschweigend bearbeitet. bauweise 'eigen' = eigene Profilgeometrie (Kantenwerkzeug);
    prototyp = in den Einstellungen freigegebene Prototypen (nur nach bestandenem Live-Test)."""
    gruende = []
    if not kante.get("blech") and not (bauweise == "eigen" and kante.get("profilteil")):
        gruende.append("gehört nicht zu einem Blechkörper (Fusion-Arbeitsbereich «Blech» verwenden)" +
                       ("" if bauweise == "eigen" else " – oder Bauweise «eigene Geometrie» an einem Profilteil"))
    typ = (vorlage or {}).get("connection", {}).get("edgeType", "gerade")
    kurve = kante.get("kurve")
    arten = {o.get("typ") for o in ((vorlage or {}).get("operations") or [])} or {"flansch"}
    # Eignung nach Operationstyp. Flansch (EdgeFlangeInput) und Saum (HemFeatureInput) sind laut Autodesk-Doku nur für GERADE Kanten
    # beschrieben; Kreis/Bogen werden deshalb VOR dem Modellieren abgelehnt (früher: versucht und gewarnt). Ellipse/Spline ohnehin.
    # Zentral über die Unterstützungsmatrix (core/unterstuetzung): Kantentyp UND angrenzender Flächentyp zählen – eine gerade Kante auf einem Zylinder
    # ist kein ebener Fall. Ohne Flächenangabe (alte Aufrufer) gilt «unbekannt» nur dann als eben, wenn es ein Blechkörper mit ebener Erkennung ist.
    from . import unterstuetzung
    fk = unterstuetzung.flaechenklasse(kante.get("flaeche", "eben"))
    kt = unterstuetzung.kantentyp(kurve)
    beschr = {"kreis": "ein Kreis", "bogen": "ein Bogen"}.get(kurve, "gerade" if kt == "gerade" else "vom Kurventyp «%s»" % kurve)
    for art in sorted(a for a in arten if a in unterstuetzung.OPS):
        grund = unterstuetzung.pruefen_bauweise(art, fk, kt, bauweise, prototyp)
        if grund:
            gruende.append("ist %s auf %s – %s%s" % (beschr, unterstuetzung.FLAECHEN_TEXT.get(fk, fk), grund,
                                                    " Kurz: nur an geraden Kanten ebener Flächen" if kt != "gerade" or fk != "eben" else ""))
    if any(o.get("versatz") for o in ((vorlage or {}).get("operations") or [])):
        grund = unterstuetzung.pruefen_bauweise("versatz", fk, kt, bauweise, prototyp)
        if grund:
            gruende.append(grund)
    if typ == "gekruemmt" and kurve == "linie":
        gruende.append("ist gerade – die Vorlage ist für gekrümmte Ränder")
    ops_ = (vorlage or {}).get("operations") or []
    if ops_ and ops_[0].get("typ") == "umschlag" and kante.get("frei") is None and kante.get("blech"):
        # Eigene Prüfung, wenn der Saum an der GEWÄHLTEN Kante sitzt (erster Schritt): Fusion rechnet ihn nur an freien Aussenkanten (Live-Tests: SM_MODELING_ERROR sonst) – unklare Kanten nicht versuchen.
        gruende.append("ist nicht sicher als freie Aussenkante erkannt – ein Umschlag braucht eine freie Aussenkante des Blechs")
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
    if bauweise == "eigen" and material and material.get("kFactor") is None:
        gruende.append("das Materialprofil hat keinen K-Faktor – ohne ihn ist die eigene Abwicklung nicht rechenbar")
    if bauweise == "eigen" and material and not material.get("innerRadius"):
        gruende.append("das Materialprofil hat keinen Innenradius – die eigene Geometrie braucht einen Biegeradius > 0")
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


def analyse(kante, vorlage, bauweise="nativ"):
    """Geometrieanalyse einer Kante für den Bauplan (Kantenwerkzeug): Kantenart, angrenzende Fläche, Klasse a–e, Stand je Bauweise, Abwicklungsaussicht."""
    from . import unterstuetzung as u
    fk = u.flaechenklasse(kante.get("flaeche", "eben"))
    kt = u.kantentyp(kante.get("kurve"))
    arten = sorted({o.get("typ") for o in ((vorlage or {}).get("operations") or [])} & set(u.OPS)) or ["flansch"]
    teile = []
    for art in arten:
        n = u.stand(art, fk, kt)[0]
        e_ = u.eigen(art, fk, kt)
        teile.append("%s: nativ %s, eigene Geometrie %s (Klasse %s – %s)" % (u.OP_TEXT[art], u.STAND_TEXT[n], u.STAND_TEXT[e_[0]], u.klasse(art, fk, kt),
                                                                         u.KLASSEN_AE[u.klasse(art, fk, kt)]))
    if bauweise == "eigen":
        abw = "Abwicklung: exakt (Profil nur aus Ebenen und Zylindern) – sofern die Prüfungen bestehen" if u.eigen(arten[0], fk, kt)[2] == "b" else \
            "Abwicklung: keine exakte Abwicklung möglich"
    else:
        abw = "Abwicklung: über Fusion-Blech (nach dem Bau geprüft)"
    return "%s: %s auf %s Fläche – %s. %s" % (kante.get("text", "Kante"), u.KANTEN_TEXT.get(kt, kt), u.FLAECHEN_TEXT.get(fk, fk), "; ".join(teile), abw)


def erstelle(vorlage, eingaben, material, kanten, bauweise="nativ", prototyp=False):
    """Bauplan erstellen. Fehler stehen in plan['validation']['errors'] – ausgeführt wird nur ohne Fehler. bauweise/prototyp: siehe kante_eignung."""
    ziele = []
    for k in kanten:
        ok, gruende = kante_eignung(k, vorlage, material, bauweise, prototyp)
        ziele.append({"ref": k.get("ref"), "text": k.get("text", "Kante"), "geeignet": ok, "gruende": gruende,
                      "laenge": k.get("laenge")})
    plan = neuer_bauplan(vorlage, eingaben or {}, material, ziele)
    plan["bauweise"] = bauweise
    plan["analyse"] = [analyse(k, vorlage, bauweise) for k in kanten]
    err, warn = plan["validation"]["errors"], plan["validation"]["warnings"]
    # Einschränkungen der Unterstützungsmatrix im Bauplan anzeigen (eingeschränkt/Prototyp) – gleiche Quelle wie die Sperre
    from . import unterstuetzung
    for k in kanten:
        for art in sorted({o.get("typ") for o in ((vorlage or {}).get("operations") or [])} & set(unterstuetzung.OPS)):
            h = unterstuetzung.hinweis(art, unterstuetzung.flaechenklasse(k.get("flaeche", "eben")), unterstuetzung.kantentyp(k.get("kurve")))
            if h and h not in warn:
                warn.append(h)
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
    # Biegeradius: Standard ist der Innenradius des Materialprofils; nur ein ausdrücklich eingetragener Radius der Vorlage gilt vor ihm.
    if material and material.get("innerRadius") is not None:
        ops = [dict(o, radius=material["innerRadius"]) if o.get("radius") is None else o for o in ops]
        plan["operations"] = ops
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
            extra = "".join(", %s %s" % (n, op[k]) for k, n in (("bezug", "Mass"), ("lage", "Lage")) if op.get(k))
            if op.get("versatz"):
                extra += ", Versatz %+g mm (%s)" % (op["versatz"], "nach innen" if op["versatz"] > 0 else "nach aussen")
            z.append("  %d. %s %g°, %.2f mm%s%s" % (i, art, op["winkel"], op["laenge"], r, extra))
    z.append("Kanten: %d gewählt, %d geeignet" % (len(plan["targets"]), sum(1 for t in plan["targets"] if t["geeignet"])))
    z.append("Bauweise: %s" % ("eigene Geometrie (exaktes Profil entlang gerader Kante)" if plan.get("bauweise") == "eigen" else "Fusion-Blechfunktion (nativ)"))
    for a in plan.get("analyse") or []:
        z.append("Analyse " + a)
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

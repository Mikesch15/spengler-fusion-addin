"""Bauteilvorlagen: ein Blech aus Breite, Verlauf (gerade oder im Grundriss, auch als Ring) und je einer Kantenfolge für Verlaufskante, Gegenkante und die
beiden Stirnseiten. Parameter, Ausdrücke und Kurzschrift sind dieselben wie in den Kantenvorlagen. Reine Logik ohne Fusion."""
from . import grundriss, short_syntax, template_engine
from .expressions import AusdruckFehler, berechne, namen_in
from .models import SEITEN, SEITEN_TEXT, parameter
from .validation import MATERIAL_NAMEN, pruefe_aufgeloest, pruefe_operationen, pruefe_parameter


def namen_der_vorlage(v):
    namen = set()
    texte = [v.get("breite")] if v.get("breite") not in (None, "") else []
    try:
        for t in texte:
            namen |= namen_in(t)
    except AusdruckFehler:
        pass
    for s in SEITEN:
        for op in (v.get("seiten") or {}).get(s, []):
            for f in ("winkel", "laenge", "radius", "versatz"):
                if isinstance(op.get(f), str):
                    try:
                        namen |= namen_in(op[f])
                    except AusdruckFehler:
                        pass
    return namen


def seiten_aus_texten(texte):
    """{'verlauf': 'Kurzschrift', …} → {'verlauf': [Operationen], …}. Wirft KurzschriftFehler mit der betroffenen Seite."""
    out = {}
    for s in SEITEN:
        t = (texte or {}).get(s) or ""
        try:
            out[s] = short_syntax.zerlege(t) if t.strip() else []
        except short_syntax.KurzschriftFehler as e:
            raise short_syntax.KurzschriftFehler("%s: %s" % (SEITEN_TEXT[s], e))
    return out


def parameter_abgleichen(v):
    """Parameter der Vorlage an die tatsächlich verwendeten Namen anpassen: neue Namen werden Parameter (Wert offen), nicht mehr benutzte entfallen,
    vorhandene Einstellungen (Beschriftung, Standardwert, Grenzen) bleiben."""
    benutzt = namen_der_vorlage(v) - MATERIAL_NAMEN
    alt = {p["name"]: p for p in v.get("parameters", [])}
    neu = []
    for n in sorted(benutzt):
        if n in alt:
            neu.append(alt[n])
        else:
            neu.append(parameter(n, n, "mm", None))
    v["parameters"] = neu
    return v


def texte_der_vorlage(v):
    return {s: short_syntax.als_text((v.get("seiten") or {}).get(s, [])) for s in SEITEN}


def pruefe_bauteilvorlage(v):
    fehler, warn = [], []
    if not (v.get("name") or "").strip():
        fehler.append("Die Vorlage braucht einen Namen.")
    f, w = pruefe_parameter(v.get("parameters", []))
    fehler += f
    warn += w
    if str(v.get("breite") or "").strip() == "":
        fehler.append("Die Breite des Grundblechs fehlt (Zahl oder Ausdruck mit Parametern, z. B. Mauerbreite+2*Ueberstand).")
    else:
        try:
            namen_in(v["breite"])
        except AusdruckFehler as e:
            fehler.append("Breite: %s" % e)
    namen = [p.get("name") for p in v.get("parameters", [])]
    hat_ops = False
    for s in SEITEN:
        ops = (v.get("seiten") or {}).get(s, [])
        hat_ops = hat_ops or bool(ops)
        if not ops:
            continue
        f, w = pruefe_operationen(ops, namen)
        fehler += ["%s: %s" % (SEITEN_TEXT[s], x) for x in f]
        warn += ["%s: %s" % (SEITEN_TEXT[s], x) for x in w]
    if not hat_ops:
        warn.append("Keine Kantenfolge – es entsteht nur das ebene Grundblech.")
    vl = v.get("verlauf") or {}
    if vl.get("art") not in ("gerade", "grundriss"):
        fehler.append("Verlauf: «gerade» oder «grundriss» wählen.")
    if vl.get("art") == "grundriss" and (vl.get("beispiel") or "").strip():
        try:
            grundriss.parse(vl["beispiel"])
        except grundriss.VerlaufFehler as e:
            fehler.append("Beispielverlauf: %s" % e)
    benutzt = namen_der_vorlage(v)
    for p in v.get("parameters", []):
        if p.get("name") and p["name"] not in benutzt:
            warn.append("Parameter «%s» wird nirgends verwendet." % p["name"])
    return fehler, warn


def aufloesen(v, eingaben, material):
    """Breite und Kantenfolgen mit Zahlen. → {'breite', 'seiten': {Seite: [Operationen]}, 'warnungen'}. Wirft VorlagenFehler."""
    fehler, warn = pruefe_bauteilvorlage(v)
    if fehler:
        raise template_engine.VorlagenFehler("Bauteilvorlage «%s» ist ungültig:\n%s" % (v.get("name"), "\n".join(fehler)))
    fehlend = (namen_der_vorlage(v) & MATERIAL_NAMEN) - set(template_engine.materialwerte(material))
    if fehlend:
        raise template_engine.VorlagenFehler("Die Vorlage braucht Materialwerte, die im Materialprofil fehlen: %s." % ", ".join(sorted(fehlend)))
    werte = template_engine.werte_zusammenstellen(v, eingaben, material)
    try:
        breite = berechne(v["breite"], werte)
    except AusdruckFehler as e:
        raise template_engine.VorlagenFehler("Breite: %s" % e)
    seiten = {}
    for s in SEITEN:
        ops = (v.get("seiten") or {}).get(s, [])
        try:
            seiten[s] = short_syntax.aufloesen(ops, werte) if ops else []
        except short_syntax.KurzschriftFehler as e:
            raise template_engine.VorlagenFehler("%s: %s" % (SEITEN_TEXT[s], e))
        if seiten[s]:
            f2, w2 = pruefe_aufgeloest(seiten[s], werte.get("t"))
            if f2:
                raise template_engine.VorlagenFehler("%s: %s" % (SEITEN_TEXT[s], "; ".join(f2)))
            warn += w2
    return {"breite": breite, "seiten": seiten, "warnungen": warn}


def plan(v, eingaben, material, verlauf_text="", laenge=None, links=True, geschlossen=False):
    """Alles für den Bau: aufgelöste Werte + Geometrie des Bandes. Wirft VorlagenFehler oder VerlaufFehler."""
    r = aufloesen(v, eingaben, material)
    art = (v.get("verlauf") or {}).get("art")
    if art == "gerade":
        if not laenge or laenge <= 0:
            raise grundriss.VerlaufFehler("Bitte die Länge eingeben.")
        segs, geschlossen = [{"laenge": float(laenge), "drehung": 0.0}], False
    else:
        segs = grundriss.parse(verlauf_text)
    b = grundriss.band(segs, r["breite"], links, geschlossen)
    r["geometrie"] = b
    if geschlossen:                        # Ring: keine Stirnseiten
        r["seiten"]["start"] = r["seiten"]["ende"] = []
    r["text"] = "Breite %g mm, %s" % (round(r["breite"], 2), b["text"])
    return r

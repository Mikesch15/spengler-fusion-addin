"""Live-Test IN Fusion: baut in NEUEN, leeren Dokumenten ein Test-Blech (100 × 60 mm) und probiert die Fusion-Funktionen des Add-ins durch, die ohne
Fusion nicht prüfbar sind (Flansch, Umschlag, Gehrung, Versatz, Abwicklung, DXF …). Jeder Schritt läuft für sich und wird abgefangen – ein Fehler
stoppt den Test nicht. Die Dokumente des Benutzers werden nie verändert; alle Testdokumente werden am Ende ungespeichert geschlossen.
NICHT live geprüft (das IST der Live-Test); Fusion-Wege für das Test-Blech sind Annahmen und im Bericht nachvollziehbar."""
import os
import tempfile
import time
import traceback

import adsk.core
import adsk.fusion

from ..core import livetest_bericht as bericht
from ..core import livetest_messung as messung
from ..manufacturing import dxf_pruefung
from ..geometry import fusion_adapter as fa
from . import fusion_capabilities, logger

LAENGE, BREITE = 100.0, 60.0     # mm
FLANSCH = 20.0                   # mm


class _Ctx(object):
    """Test-Blech des laufenden Schritts."""
    def __init__(self, design, root, body, dicke):
        self.design, self.root, self.body, self.dicke = design, root, body, dicke
        self.seite = "oben"


def _letzte_zeile(e):
    s = str(e).strip()
    return s.splitlines()[-1] if s else type(e).__name__


# ------------------------------------------------------------------ Test-Blech
def _neues_dokument(app):
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    return doc, design, design.rootComponent


def _blech_bauen(design, root, dicke=1.0, name="Live-Test Blech"):
    """Test-Blech wie beim Befehl «Blech aus Massaufnahme»: in einer NEUEN Komponente (fa.neue_komponente + fa.grundblech_bauen)."""
    return fa.grundblech_bauen(fa.neue_komponente(name), LAENGE, BREITE, dicke)


def _zustand(root):
    """Modellzustand für Rückbau-Vergleiche: Zeitleiste (= alle Features), Skizzen, Körper, Konstruktionsebenen/-achsen aller Komponenten, Occurrences,
    Komponenten, Benutzerparameter, Blechregeln, Canvases, Gesamtvolumen (mm³). Nicht messbare Werte sind None (→ Test ungültig, nie «unverändert»)."""
    def alle(comp):
        yield comp
        for occ in comp.allOccurrences:
            yield occ.component
    def zahl(f):
        try:
            return f()
        except Exception:
            return None                                    # nicht messbar – zählt im Vergleich NICHT als unverändert

    def summe(attr):
        try:
            return sum(getattr(c, attr).count for c in alle(root))
        except Exception:
            return None
    try:
        vol = round(sum(sum(b.volume for b in c.bRepBodies) for c in alle(root)) * 1000.0, 1)
    except Exception:
        vol = None
    d = fa.design()

    def regelnamen():
        r = d.designSheetMetalRules
        return tuple(sorted(r.item(i).name for i in range(r.count)))

    def abwicklungen():
        n = 0
        for c in alle(root):
            fp, lesbar = fa._flatpattern_lesen(c)
            if not lesbar:
                return None                                 # beschädigt/unlesbar → nicht messbar, nie «unverändert»
            n += 1 if fp else 0
        return n
    return {"zeitleiste": fa.zeitleiste_stand(), "konstruktionspunkte": summe("constructionPoints"), "abwicklungen": zahl(abwicklungen),
            "blechregel_namen": zahl(regelnamen), "skizzen": summe("sketches"), "koerper": summe("bRepBodies"), "vol": vol,
            "konstruktionsebenen": summe("constructionPlanes"), "konstruktionsachsen": summe("constructionAxes"),
            "occurrences": zahl(lambda: root.allOccurrences.count), "komponenten": zahl(lambda: d.allComponents.count),
            "parameter": zahl(lambda: d.userParameters.count), "blechregeln": zahl(lambda: d.designSheetMetalRules.count),
            "canvases": zahl(lambda: root.canvases.count)}


ZUSTAND_GLEICH = ("zeitleiste", "skizzen", "koerper", "konstruktionsebenen", "konstruktionsachsen", "konstruktionspunkte", "occurrences",
                  "komponenten", "parameter", "blechregeln", "blechregel_namen", "abwicklungen", "canvases")


def _oberflaeche(body, seite="oben"):
    """Grösste ebene Fläche, deren Normale nach +Z (oben) bzw. −Z (unten) zeigt."""
    bester, flaeche = None, 0.0
    for f in body.faces:
        try:
            g = f.geometry
            if not isinstance(g, adsk.core.Plane):
                continue
            nz = fa.flaechennormale(f)[2]
            if (seite == "oben" and nz > 0.99) or (seite == "unten" and nz < -0.99):
                if f.area > flaeche:
                    bester, flaeche = f, f.area
        except Exception:
            continue
    if bester is None:
        raise RuntimeError("Keine ebene %sfläche am Test-Blech gefunden." % seite)
    return bester


def _laenge_mm(edge):
    """Kantenlänge als ZAHL in mm (fa._kantenlaenge_mm liefert nur Text für Meldungen – Live 4.11.: round() auf Text brach 11 Schritte ab)."""
    return edge.length * 10.0


def _rand_kanten(ctx, seite=None):
    """Gerade Randkanten der Ober-/Unterseite, lange (X) zuerst; → Liste."""
    f = _oberflaeche(ctx.root.bRepBodies.item(0), seite or ctx.seite)
    kanten = []
    for e in f.edges:
        if fa._kurventyp(e) == "linie":
            kanten.append(e)
    kanten.sort(key=lambda e: (-round(_laenge_mm(e)), e.boundingBox.minPoint.y, e.boundingBox.minPoint.x))
    return kanten


def _teilen_ecke(a, b):
    ps = [(v.geometry.x, v.geometry.y, v.geometry.z) for v in (a.startVertex, a.endVertex)]
    qs = [(v.geometry.x, v.geometry.y, v.geometry.z) for v in (b.startVertex, b.endVertex)]
    return any(max(abs(p[i] - q[i]) for i in range(3)) < 1e-6 for p in ps for q in qs)


def _eckkanten(ctx):
    """Zwei benachbarte Kanten (eine lange, eine kurze, die sich in einer Ecke treffen)."""
    k = _rand_kanten(ctx)
    for a in k:
        for b in k:
            if a is not b and _teilen_ecke(a, b) and abs(_laenge_mm(a) - _laenge_mm(b)) > 1:
                return [a, b]
    raise RuntimeError("Keine zwei benachbarten Kanten gefunden.")


def _volumen(ctx):
    return ctx.root.bRepBodies.item(0).physicalProperties.volume * 1000.0    # cm³ → mm³


def _messen(ctx):
    """Messwerte des Körpers in mm (Volumen, Ausdehnung, Flächen/Kanten) – Grundlage für core/livetest_messung (nicht live geprüft)."""
    b = ctx.root.bRepBodies.item(0)
    bb = b.boundingBox
    return {"vol": b.physicalProperties.volume * 1000.0,
            "min": (bb.minPoint.x * 10.0, bb.minPoint.y * 10.0, bb.minPoint.z * 10.0),
            "max": (bb.maxPoint.x * 10.0, bb.maxPoint.y * 10.0, bb.maxPoint.z * 10.0),
            "flaechen": b.faces.count, "kanten": b.edges.count}


def _bewerten(ergebnis):
    """('ok'|'warnung'|'fehler', Text) → Text bzw. passende Ausnahme."""
    status, text = ergebnis
    if status == "fehler":
        raise _Falsch(text)
    if status == "warnung":
        raise _Warnung(text)
    return text


def _plausibel(zuwachs, erwartet, unten=0.4, oben=2.0):
    return erwartet <= 0 or unten <= zuwachs / erwartet <= oben


def _op(typ="flansch", winkel=90.0, laenge=FLANSCH, radius=None, versatz=None):
    return {"typ": typ, "winkel": winkel, "laenge": laenge, "radius": radius, "bezug": None, "lage": None, "versatz": versatz}


def _flansch_versuch(ctx, **kw):
    """Flansch an der ersten langen Kante; probiert Ober- und Unterseite, merkt sich, was Fusion annimmt."""
    fehler = []
    for seite in (ctx.seite, "unten" if ctx.seite == "oben" else "oben"):
        try:
            ctx.seite = seite
            kante = _rand_kanten(ctx)[0]
            return fa.flansch(kante, **kw), kante, seite
        except Exception as e:
            fehler.append("%s: %s" % (seite, _letzte_zeile(e)))
    raise RuntimeError(" | ".join(fehler))


# ------------------------------------------------------------------ Schritte
def _blech_bericht(body, soll):
    """Grundblech-Prüfung wie im Adapter (Komponente, Dicke laut Regel und gemessen, Blechkörper) – ausdrücklich im Bericht."""
    bb = body.boundingBox
    gemessen = (bb.maxPoint.z - bb.minPoint.z) * 10.0
    regel = fa.blechdicke_mm(body)
    probleme = fa.grundblech_pruefen(body.parentComponent, body, soll)
    if fa._gleiche(body.parentComponent, fa.design().rootComponent):
        probleme.append("Körper liegt in der Root-Komponente statt in der neuen Zielkomponente")
    txt = "Komponente «%s», Soll %.2f mm, Regel %s mm, gemessen %.3f mm, isSheetMetal=%s" % (
        body.parentComponent.name, soll, ("%.3f" % regel) if regel else "?", gemessen, getattr(body, "isSheetMetal", "?"))
    if probleme:
        raise _Falsch(txt + " – " + " ".join(probleme))
    return txt


def t_blech(ctx):
    return "Test-Blech %.0f × %.0f mm: %s, Volumen %.0f mm³, %d Flächen, %d Kanten" % (
        LAENGE, BREITE, _blech_bericht(ctx.body, 1.0), _volumen(ctx), ctx.body.faces.count, ctx.body.edges.count)


def t_blech_07(ctx):
    """Grundblech 0.7 mm in einer neuen Komponente, während schon eine andere Komponente mit Körper existiert (Akzeptanztest Phase 1)."""
    vorhanden = _blech_bauen(ctx.design, ctx.root, 1.0, "Live-Test vorhanden")
    body = _blech_bauen(ctx.design, ctx.root, 0.7, "Live-Test 0.7 mm")
    if fa._gleiche(body.parentComponent, vorhanden.parentComponent):
        raise _Falsch("Das 0.7-mm-Blech liegt in der Komponente des vorhandenen Blechs.")
    if abs((fa.blechdicke_mm(vorhanden) or 0) - 1.0) > 0.001:
        raise _Falsch("Die Regel des vorhandenen 1.0-mm-Blechs wurde verändert (%s mm)." % fa.blechdicke_mm(vorhanden))
    return _blech_bericht(body, 0.7) + "; vorhandenes Blech unverändert 1.0 mm"


def t_blech_ungueltig(ctx):
    """Ungültiges Profil und ungültige Dicke müssen VOR dem Modellieren abbrechen – das Design bleibt unverändert."""
    vorher = _zustand(ctx.design.rootComponent)
    erg = []
    for profil, dicke, was in (([[(0, 0), (100, 0)]], 1.0, "Profil mit 2 Punkten"), ([[(0, 0), (100, 0), (100, 60), (0, 60)]], 0.0, "Dicke 0 mm")):
        comp = fa.neue_komponente("Live-Test ungültig")
        try:
            fa.blech_aus_profil(comp, profil, dicke)
            erg.append("%s: NICHT abgelehnt" % was)
        except fa.AdapterFehler as e:
            erg.append("%s: abgelehnt (%s)" % (was, str(e)[:90]))
        fa.komponente_entfernen(comp)
    nachher = _zustand(ctx.design.rootComponent)
    if any("NICHT" in x for x in erg) or nachher["skizzen"] != vorher["skizzen"] or nachher["koerper"] != vorher["koerper"]:
        raise _Falsch("; ".join(erg) + "; Zustand vorher %s, nachher %s" % (vorher, nachher))
    return "; ".join(erg) + "; keine Teilgeometrie"


def proben_sammeln(proben):
    """Mehrere Rückbau-Proben NACHEINANDER vollständig ausführen (früher brach der Schritt bei der ersten fehlgeschlagenen Probe ab, die übrigen
    liefen gar nicht). → Text; scheitert mindestens eine, _Falsch mit ALLEN Ergebnissen. proben: [(stelle, aufruf)] mit aufruf() → Text."""
    zeilen, falsch = [], False
    for stelle, aufruf in proben:
        try:
            zeilen.append(aufruf())
        except _Falsch as e:
            falsch = True
            zeilen.append("✗ " + str(e))
    if falsch:
        raise _Falsch("\n".join(zeilen))
    return "\n".join(zeilen)


def _rueckbau_probe(ctx, stelle, bauen):
    """Fehler an einer Stelle absichtlich auslösen und den Modellzustand vor/nach vergleichen (Rückbau-Akzeptanztest)."""
    vorher = _zustand(ctx.design.rootComponent)
    fa.TESTFEHLER.add(stelle)
    try:
        bauen()
        raise _Falsch("Der absichtliche Fehler bei «%s» wurde nicht ausgelöst." % stelle)
    except fa.AdapterFehler as e:
        meldung = str(e)
        ok = getattr(e, "rueckbau_ok", True)
    finally:
        fa.TESTFEHLER.discard(stelle)
    nachher = _zustand(ctx.design.rootComponent)
    # Nur GENAU der eingeschleuste Fehler zählt – ein anderer Adapterfehler vorher wäre kein Beweis für den Rückbau an dieser Stelle.
    # Ein Fusion-Fehler VOR der Teststelle (andere Meldung) ist FAIL – nur der eingeschleuste Fehler beweist den Rückbau an genau dieser Stelle.
    richtig = fa.testfehler_text(stelle) in meldung
    abweichung, offen = messung.zustand_vergleich(vorher, nachher, ZUSTAND_GLEICH)
    txt = "%s: %s; Zustand %s%s%s; Rückbau gemeldet %s" % (
        stelle, "eingeschleuster Fehler ausgelöst" if richtig else "ANDERER Fehler (vor der Teststelle oder Fusion-Ablehnung): " + meldung[:200],
        "unverändert" if not abweichung and not offen else ("VERÄNDERT" if abweichung else "NICHT VOLLSTÄNDIG MESSBAR"),
        (" (%s)" % ", ".join("%s %s→%s" % x for x in abweichung)) if abweichung else "",
        (" (nicht messbar: %s)" % ", ".join(offen)) if offen else "", "ok" if ok else "UNVOLLSTÄNDIG – " + meldung[-300:])
    if not richtig or abweichung or offen or not ok:
        raise _Falsch(txt)
    return txt


def t_rueckbau(ctx):
    """Provozierte Fehler nach Skizze bzw. Extrusion des Versatzes und nach dem Basisflansch: danach darf nichts übrig sein."""
    proben = []
    for stelle in ("versatz_skizze", "versatz_extrusion"):
        proben.append((stelle, lambda s=stelle: _rueckbau_probe(ctx, s, lambda: fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, FLANSCH, versatz=5.0)], ctx.dicke, {"livetest": 1}, []))))
    proben.append(("folge_nach_schritt", lambda: _rueckbau_probe(ctx, "folge_nach_schritt", lambda: fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, FLANSCH)], ctx.dicke, {"livetest": 1}, []))))
    proben.append(("grundblech_feature (Root, 1.0 mm)", lambda: "[Root 1.0 mm] " + _rueckbau_probe(ctx, "grundblech_feature", lambda: fa.grundblech_bauen(ctx.root, LAENGE, BREITE, 1.0))))
    # Neue Komponente mit NEUER Blechregel (0.65 mm): nach dem Fehler darf weder Komponente noch Regel übrig sein (Blechregeln im Zustand)
    def neu_mit_regel():
        comp = fa.neue_komponente("Live-Test Rückbau Regel")
        try:
            fa.grundblech_bauen(comp, LAENGE, BREITE, 0.65)
        except fa.AdapterFehler as e:
            if not fa.komponente_entfernen(comp):
                raise fa.AdapterFehler(str(e) + " – Komponente nicht entfernt", rueckbau_ok=False)
            raise
    proben.append(("grundblech_feature (neue Komponente, neue Regel 0.65 mm)", lambda: "[neue Komponente 0.65 mm] " + _rueckbau_probe(ctx, "grundblech_feature", neu_mit_regel)))
    proben.append(("gruppe_nach_versatz", lambda: _rueckbau_probe(ctx, "gruppe_nach_versatz", lambda: fa.folge_anbringen_gruppe(_eckkanten(ctx), [_op("flansch", 90, FLANSCH, versatz=-5.0)], ctx.dicke, {"livetest": 1}, []))))
    return proben_sammeln(proben)


def _detail_datei(ctx):
    """Kleines Test-Detail (Quader 50 × 10 × 20 mm mit Parameter) als .f3d – im Testdokument erzeugt, danach wieder entfernt."""
    comp = fa.quader_komponente(ctx.design.rootComponent, "Live-Test Detailquelle", 50.0, 10.0, 20.0, "SD_LT_H")
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "detail.f3d")
    fa.komponente_exportieren(comp, pfad)
    fa.komponente_entfernen(comp)
    return pfad


def t_rueckbau_import(ctx):
    """3D-Detail: Fehler in jeder Phase (Import, Ausrichtung, Parameter, Basis-Feature, Kombinieren) – danach darf weder Occurrence, Komponente,
    Parameter noch Zwischenkörper/Feature übrig sein."""
    f3d = _detail_datei(ctx)
    T = [[1, 0, 0, 20.0], [0, 1, 0, 20.0], [0, 0, 1, 1.0], [0, 0, 0, 1]]
    token = ctx.body.entityToken
    erg = []
    for stelle in ("detail_import", "detail_ausrichten", "detail_parameter", "detail_basis", "detail_kombinieren"):
        erg.append(_rueckbau_probe(ctx, stelle, lambda: fa.detail_einsetzen(f3d, ctx.design.rootComponent, T, None, token)))
    return "\n".join(erg)


def _flansch_gemessen(ctx, winkel, hoehe, **kw):
    """Flansch bauen, davor/danach messen und bewerten. Bei einer Kante der Unterseite ist die Richtung nicht vorab bekannt – dann gilt die bessere von +/−. → (Feature, Text)"""
    vor = _messen(ctx)
    feat, kante, seite = _flansch_versuch(ctx, winkel=winkel, laenge_mm=hoehe, **kw)
    nach = _messen(ctx)
    ergebnisse = [messung.pruefe_flansch(vor, nach, w, hoehe, ctx.dicke or 1.0, _laenge_mm(kante), kw.get("radius_mm")) for w in ((winkel, -winkel) if seite != "oben" else (winkel,))]
    ergebnisse.sort(key=lambda e: {"ok": 0, "warnung": 1, "fehler": 2}[e[0]])
    s, t = ergebnisse[0]
    return feat, (s, "Kante der %sseite: %s" % (seite, t))


def _spalt_aus(txt):
    import re
    m_ = re.search(r"Eckspalt ([0-9.]+) mm", txt or "")
    return float(m_.group(1)) if m_ else None


def t_flansch(ctx):
    vor = _messen(ctx)
    feat, erg = _flansch_gemessen(ctx, 90, FLANSCH)
    nach = _messen(ctx)
    # AUSSENMASS (Standard ab 0.4.62): Grundriss bleibt aussen gleich gross (Biegung innen), Gesamthöhe aussen = Flanschhöhe
    dxy = max(abs(nach["min"][i] - vor["min"][i]) for i in (0, 1)) + max(abs(nach["max"][i] - vor["max"][i]) for i in (0, 1))
    dz = nach["max"][2] - nach["min"][2]
    t = "Aussenmass: Grundriss %+.3f mm (Soll 0), Gesamthöhe %.3f mm (Soll %.1f)" % (dxy, dz, FLANSCH)
    if dxy > 0.05 or abs(dz - FLANSCH) > 0.05:
        raise _Falsch(t + " – Aussenmass nicht eingehalten (Lage/Höhenbezug)")
    return _bewerten(erg) + "; " + t


def t_flansch_hinten(ctx):
    vor = _messen(ctx)
    kante = _rand_kanten(ctx)[0]
    fa.flansch(kante, winkel=-90, laenge_mm=FLANSCH)
    return "Flansch nach hinten (−90°): " + _bewerten(messung.pruefe_flansch(vor, _messen(ctx), -90, FLANSCH, ctx.dicke or 1.0, _laenge_mm(kante)))


def t_flansch_winkel(ctx):
    erg, schlecht = [], []
    for w in (45, 135):
        feat, e = _flansch_gemessen(ctx, w, 15)
        erg.append("%d°: %s" % (w, e[1]))
        if e[0] != "ok":
            schlecht.append(e[0])
        fa.entfernen([feat])
    if "fehler" in schlecht:
        raise _Falsch("\n".join(erg))
    if schlecht:
        raise _Warnung("\n".join(erg))
    return "\n".join(erg)


def t_flansch_radius(ctx):
    """Flansch ohne und mit Biegeradius 3 mm: der Radius muss das Ergebnis messbar ändern."""
    vor = _messen(ctx)
    feat, _, _ = _flansch_versuch(ctx, winkel=90, laenge_mm=FLANSCH)
    standard = {"vor": vor, "nach": _messen(ctx)}
    fa.entfernen([feat])
    feat, kante, _ = _flansch_versuch(ctx, winkel=90, laenge_mm=FLANSCH, radius_mm=3.0)
    gross = {"vor": vor, "nach": _messen(ctx)}
    s, t = messung.pruefe_flansch(vor, gross["nach"], 90, FLANSCH, ctx.dicke or 1.0, _laenge_mm(kante), 3.0)
    if s == "ok":
        s, t = messung.pruefe_radius(standard, gross, 3.0)
    return _bewerten((s, "Biegeradius 3 mm: " + t))


def t_winkelfalz(ctx):
    """Winkelfalz 35 mm: Flansch 90° + zweiter Flansch 135° (wie in der Praxis gemeldet) an EINER Kante."""
    hin = []
    erz = fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, 35), _op("flansch", 135, 10)], ctx.dicke, {"livetest": 1}, hin)
    return "%d Schritte gebaut%s" % (len(erz), ("; Hinweise: " + " / ".join(hin)) if hin else "")


def t_umschlag(ctx):
    vor = _messen(ctx)
    kante = _rand_kanten(ctx)[0]
    fa.umschlag(kante, 10.0, False, None, None, ctx.dicke)
    return "Umschlag 10 mm: " + _bewerten(messung.pruefe_umschlag(vor, _messen(ctx), 10.0, ctx.dicke or 1.0, _laenge_mm(kante)))


def t_umschlag_radius(ctx):
    vor = _messen(ctx)
    kante = _rand_kanten(ctx)[0]
    fa.umschlag(kante, 10.0, False, 2.0, None, ctx.dicke)
    return "Umschlag 10 mm mit Radius/Abstand 2 mm: " + _bewerten(messung.pruefe_umschlag(vor, _messen(ctx), 10.0, ctx.dicke or 1.0, _laenge_mm(kante), 2.0))


def t_gehrung_flansch(ctx):
    """Zwei Eckkanten gemeinsam (Gehrung) gegen zwei Einzelflansche: Volumen und Flächenzahl verglichen."""
    kanten = _eckkanten(ctx)
    vor = _messen(ctx)
    feat = fa.flansch(kanten, winkel=90, laenge_mm=FLANSCH)
    gemeinsam = _messen(ctx)
    mit = None
    try:
        mit = getattr(feat, "isMiteredCorners", None)
    except Exception:
        pass
    fa.entfernen([feat])
    einzel = []
    eck_e = fa.ecke_daten(_eckkanten(ctx))
    for k in _eckkanten(ctx):
        einzel.append(fa.flansch(k, winkel=90, laenge_mm=FLANSCH))
    einzeln = _messen(ctx)
    s, t = messung.pruefe_gehrung(einzeln, gemeinsam)
    # Ursache der Volumen-/Flächendifferenz: dieselbe Eckanalyse auch an den EINZELN gebauten Flanschen
    _be, te = fa.gehrung_eckspalt(einzel[-1], eck_e, ctx.dicke or 1.0)
    t += "; Ecke einzeln gebaut: " + te + "; Ecke gemeinsam gebaut ↓"
    # Geometrische Eckprüfung am GEMEINSAMEN Flansch (neu gebaut, Eckdaten vor dem Bau gelesen): Volumen allein beweist keine Gehrung.
    fa.entfernen(einzel)
    eck = fa.ecke_daten(_eckkanten(ctx))
    feat2 = fa.flansch(_eckkanten(ctx), winkel=90, laenge_mm=FLANSCH)
    bew, txt = fa.gehrung_eckspalt(feat2, eck, ctx.dicke or 1.0)
    # Anwender 6. 11. 2026: Ecken mit Spalt sind vorerst zulässig → Stossecke mit gemessenem Spalt ≤ t + 0.5 mm gilt als bestanden
    if bew == "stoss":
        spalt = _spalt_aus(txt)
        if spalt is not None and spalt <= (ctx.dicke or 1.0) + 0.5:
            bew = "ok"
    t += "; " + txt
    if bew != "ok" and s == "ok":
        s = "fehler" if bew == "fehler" else "warnung"
    ratio = messung.pruefe_flansch(vor, gemeinsam, 90, FLANSCH, ctx.dicke or 1.0, _laenge_mm(kanten[0]) + _laenge_mm(kanten[1]))
    if ratio[0] == "fehler":
        s, t = "fehler", "Gemeinsamer Flansch: " + ratio[1]
    eingabe = fa.LETZTE_FLANSCH_EINGABE.get("isMiteredCorners")
    # Volumen-/Flächenvergleich ist nur ein Indiz: ohne GEOMETRISCH nachgewiesene Gehrungsflächen (bew == ok) gilt die Ecke als NICHT verifiziert
    if bew != "ok" and s == "ok":
        s = "warnung"
    return _bewerten((s, "isMiteredCorners: Feature=%s, Eingabe=%s; %s" % (mit, eingabe, t)))


def _gruppe(ctx, ops, name, features_soll=None, erwartete_hinweise=()):
    kanten = _eckkanten(ctx)
    hin = []
    erz = fa.folge_anbringen_gruppe(kanten, ops, ctx.dicke, {"livetest": 1}, hin)
    txt = "%s an 2 Eckkanten: %d Features" % (name, len(erz))
    if features_soll is not None and len(erz) != features_soll:
        raise _Falsch(txt + " (erwartet %d)" % features_soll)
    unerwartet = [h for h in hin if not any(e in h for e in erwartete_hinweise)]
    if unerwartet:
        raise _Warnung(txt + "\n" + "\n".join(unerwartet))
    return txt + ("; " + " / ".join(hin) if hin else "")


def t_gehrung_winkelfalz(ctx):
    return _gruppe(ctx, [_op("flansch", 90, 35), _op("flansch", 135, 10)], "Winkelfalz 35")


def t_gehrung_umschlag(ctx):
    """Umschlag an 2 Eckkanten: je Kante ein ECHTER Saum (kein 179°-Flansch), jeder geometrisch kontrolliert."""
    return _gruppe(ctx, [_op("umschlag", 180, 10)], "Umschlag", 2, ("NICHT auf Gehrung",))


def t_versatz(ctx):
    """Versatz als Unterschied zu einem Bau OHNE Versatz (gleiche Kante, gleicher Flansch) – so kürzen sich Höhenbezug und Blechregeln heraus."""
    def bau(v):
        hin = []
        vor = _messen(ctx)
        erz = fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, FLANSCH, versatz=v)], ctx.dicke, {"livetest": 1}, hin)
        m = {"vor": vor, "nach": _messen(ctx)}
        fa.entfernen(erz)
        return m, hin
    ohne, _ = bau(None)
    erg, schlecht = [], []
    laenge = _laenge_mm(_rand_kanten(ctx)[0])
    for v in (5.0, -5.0):
        try:
            mit, hin = bau(v)
        except Exception as e:
            erg.append("%+g mm: Fehler – %s" % (v, _letzte_zeile(e)))
            schlecht.append("fehler")
            continue
        s, t = messung.pruefe_versatz(ohne, mit, v, ctx.dicke or 1.0, laenge, FLANSCH)
        erg.append("%+g mm: %s%s" % (v, t, ("; " + " / ".join(hin)) if hin else ""))
        if s != "ok":
            schlecht.append(s)
    if "fehler" in schlecht:
        raise _Falsch("\n".join(erg))
    if schlecht:
        raise _Warnung("\n".join(erg))
    return "\n".join(erg)


def _abwickeln(ctx, flansche):
    """Abwicklung OHNE vorgegebene Fläche (feste Auswahlregel des Adapters), DXF-Export und Gegenprobe der DXF (Masse, Einheit, Konturen)."""
    fp, neu = fa.abwicklung(ctx.root)
    m = fa.abwicklung_masse(fp)
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "abwicklung.dxf")
    fa.dxf_abwicklung(fp, pfad)
    gross, klein = max(m["laenge"], m["breite"]), min(m["laenge"], m["breite"])
    ri, k = fa.regel_werte(ctx.body.parentComponent if ctx.body is not None else ctx.root)
    s, t = messung.pruefe_abwicklung(m["breite"], m["laenge"], LAENGE, BREITE, FLANSCH, ctx.dicke or 1.0, ri=ri, k=k if k is not None else 0.44,
                                     flansche=flansche)
    t += "; Regel: Ri %s, K %s (aus Fusion gelesen)" % (ri, k)
    # Gegenprobe der DXF-Datei selbst (Masse, Einheit, Kontur, keine Zusatzprofile) – unabhängig von der Fusion-Abmessung
    dxf = dxf_pruefung.pruefe_datei(pfad, gross, klein, erwartete_konturen=1)
    t += "; DXF: " + dxf_pruefung.zusammenfassung(dxf)
    if not dxf["ok"]:
        s = "fehler"
    elif dxf["hinweise"] and s == "ok":
        s = "warnung"
    return _bewerten((s, t))


def t_abwicklung(ctx):
    """L-Blech: ein Flansch."""
    _flansch_versuch(ctx, winkel=90, laenge_mm=FLANSCH)
    return _abwickeln(ctx, 1)


def t_abwicklung_mehrfach(ctx):
    """U-Blech: Flansche an beiden langen Kanten (zwei Biegungen)."""
    k = _rand_kanten(ctx)
    fa.flansch(k[0], winkel=90, laenge_mm=FLANSCH)
    gegen = [e for e in _rand_kanten(ctx) if abs(_laenge_mm(e) - LAENGE) < 1]
    gegen.sort(key=lambda e: -e.boundingBox.minPoint.y)
    fa.flansch(gegen[0], winkel=90, laenge_mm=FLANSCH)
    return _abwickeln(ctx, 2)


def t_bildschirmfoto(ctx):
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "foto.png")
    ok = adsk.core.Application.get().activeViewport.saveAsImageFile(pfad, 320, 240)
    if not ok or not os.path.exists(pfad) or os.path.getsize(pfad) == 0:
        raise RuntimeError("Bildschirmfoto wurde nicht erzeugt.")
    return "Bildschirmfoto %d Byte" % os.path.getsize(pfad)


def t_ordnerliste(ctx):
    """Nur lesen: Ordner des aktiven Fusion-Projekts auflisten (Auswahl in «Andere Ablage»). Legt nichts an."""
    liste = fa.ordner_liste(2)
    return "%d Ordner bis 2 Ebenen im aktiven Projekt (Namen werden bewusst nicht in den Bericht geschrieben)" % len(liste)


def t_ordnerpfad(ctx):
    pfad = fa.dokument_ordnerpfad()
    n = fa.dokument_name()
    return "Dokument «%s», Ordnerpfad %s" % (n, "/".join(pfad) if pfad else "(ungespeichert, leer)")


def _bauteil(ctx, verlauf, ring, seiten, name, breite="100"):
    """Bauteil im Grundriss wie der Befehl «Bauteil erstellen»: Band aus dem Verlauf, Grundblech, Kantenfolgen an den Ketten."""
    from ..core import bauteil, models
    v = models.neue_bauteilvorlage("Livetest")
    v["breite"] = breite
    v["verlauf"] = {"art": "grundriss", "beispiel": verlauf, "seite": "links"}
    v["seiten"] = bauteil.seiten_aus_texten(seiten)
    p = bauteil.plan(v, {}, {"thickness": 1.0, "innerRadius": 1.0, "kFactor": 0.4}, verlauf, None, True, ring)
    g = p["geometrie"]
    body = fa.blech_aus_profil(ctx.root, g["schleifen"], 1.0)
    ketten = fa.kanten_nach_ketten(body, g["ketten"])
    hin, txt = [], [p["text"]]
    for seite, ops in p["seiten"].items():
        if ops and seite in ketten:
            erz = fa.kanten_folge_bauen(ketten[seite], ops, ctx.dicke, {"livetest": 1}, hin)
            txt.append("%s: %d Feature(s) an %d Kante(n)" % (seite, len(erz), len(ketten[seite])))
    if hin:
        raise _Warnung("%s – %s: %s" % (name, "\n".join(txt), "\n".join(hin)))
    return "%s: %s" % (name, "; ".join(txt))


def t_bauteil_l(ctx):
    return _bauteil(ctx, "300 L90 200", False, {"verlauf": "90 20"}, "L-förmiger Verlauf, Flansch an der Verlaufskante (Gehrung an der Ecke)")


def t_bauteil_ring(ctx):
    return _bauteil(ctx, "300 L90 200 L90 300 L90 200 L90", True, {"verlauf": "90 20", "gegen": "90 15"}, "Ring mit Flansch an beiden Kanten", breite="60")


def t_referenzbild(ctx):
    """Referenzbild (Canvas) einfügen – so wie «In Fusion einfügen» in der Projektkarte (Foto/Skizze der Massaufnahme)."""
    import base64
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "referenz.png")
    with open(pfad, "wb") as f:
        f.write(png)
    fa.referenzbild_einfuegen(pfad, "Live-Test Referenzbild")
    return "Referenzbild eingefügt (%d Canvas im Dokument)" % ctx.root.canvases.count


class _Warnung(Exception):
    """Schritt lief, aber das Ergebnis ist auffällig."""


class _Uebersprungen(Exception):
    """Schritt NICHT getestet (z. B. Testkörper nicht erzeugbar) – mit Grund; zählt nie als bestanden."""


class _Falsch(Exception):
    """Schritt lief ohne Fusion-Fehler, aber das gemessene Ergebnis ist geometrisch falsch."""


SCHRITTE = [
    ("Test-Blech 1.0 mm (Basisflansch in eigener Komponente)", t_blech, False),
    ("Grundblech 0.7 mm neben vorhandener Komponente", t_blech_07, False),
    ("Ungültiges Profil / ungültige Dicke wird abgelehnt", t_blech_ungueltig, False),
    ("Flansch 90° (Kante des Test-Blechs)", t_flansch, True),
    ("Flansch nach hinten (−90°)", t_flansch_hinten, True),
    ("Flansch 45° und 135°", t_flansch_winkel, True),
    ("Flansch mit Biegeradius 3 mm", t_flansch_radius, True),
    ("Winkelfalz 35 mm an einer Kante", t_winkelfalz, True),
    ("Umschlag 10 mm an einer Kante", t_umschlag, True),
    ("Umschlag mit Radius = Abstand 2 mm", t_umschlag_radius, True),
    ("Gehrung: Flansch an 2 Eckkanten", t_gehrung_flansch, True),
    ("Gehrung: Winkelfalz 35 an 2 Eckkanten", t_gehrung_winkelfalz, True),
    ("Gehrung: Umschlag an 2 Eckkanten", t_gehrung_umschlag, True),
    ("Versatz +5 mm und −5 mm", t_versatz, True),
    ("Abwicklung und DXF (L-Blech)", t_abwicklung, True),
    ("Abwicklung und DXF (zwei Biegungen)", t_abwicklung_mehrfach, True),
    ("Rückbau bei provoziertem Fehler (Versatz, Grundblech, Gruppe)", t_rueckbau, True),
    ("Rückbau 3D-Detail-Import in jeder Phase", t_rueckbau_import, True),
    ("Bauteil: L-förmiger Grundrissverlauf", t_bauteil_l, False),
    ("Bauteil: geschlossener Ring", t_bauteil_ring, False),
    ("Referenzbild (Canvas) einfügen", t_referenzbild, False),
    ("Bildschirmfoto der Ansicht", t_bildschirmfoto, False),
    ("Ordnerpfad des Dokuments lesen", t_ordnerpfad, False),
    ("Ordner des aktiven Projekts auflisten (Ablagen)", t_ordnerliste, False),
]
# Gekrümmte Geometrie und Doppelfalz (Nachtauftrag Phase 8) – eigenes Modul, hier angehängt
from . import live_test_gekruemmt as _gekruemmt  # noqa: E402
SCHRITTE.extend(_gekruemmt.SCHRITTE)
from . import live_test_kantenwerkzeug as _kantenwerkzeug  # noqa: E402
SCHRITTE.extend(_kantenwerkzeug.SCHRITTE)


def _alles_schliessen(dokumente):
    for d in reversed(dokumente):
        try:
            d.close(False)
        except Exception:
            logger.warnung("Testdokument nicht geschlossen")


def ausfuehren(fortschritt=None):
    """Alle Schritte nacheinander. → (Ergebnisliste, Kopfzeile). fortschritt(text) wird je Schritt aufgerufen (darf fehlen)."""
    app = adsk.core.Application.get()
    try:
        original = app.activeDocument
    except Exception:
        original = None
    from .. import VERSION
    kopf = ("FUSION-LIVE-TEST (echte Fusion-API, keine Attrappen) – Add-in %s, Fusion %s, %s\n"
            "Teststufe: Fusion-Live-Test in temporären Testdokumenten. Aussagekraft: belegt, dass Fusion die Geometrie erzeugt bzw. ablehnt und die "
            "gemessenen Werte stimmen. NICHT belegt: fachliche Prüfung im CAD durch den Spengler und Freigabe für die produktive Anwendung." % (
                VERSION, app.version, time.strftime("%d.%m.%Y %H:%M")))
    erg, dokumente = [], []
    f = fusion_capabilities.pruefen(app)
    fehlt = [t for ok, t in f.values() if not ok]
    erg.append({"name": "Fähigkeiten der Fusion-Version", "status": "warnung" if fehlt else "ok",
                "detail": ("Fehlt: " + "; ".join(fehlt)) if fehlt else "alle geprüften Funktionen vorhanden", "dauer": None})
    blech_ok = True
    try:
        for nr, (name, funktion, braucht_blech) in enumerate(SCHRITTE, 1):
            if fortschritt:
                try:
                    fortschritt("Schritt %d von %d: %s" % (nr, len(SCHRITTE), name))
                except Exception:
                    pass
            if braucht_blech and not blech_ok:
                erg.append({"name": name, "status": "uebersprungen", "detail": "Test-Blech konnte nicht erzeugt werden", "dauer": None})
                continue
            t0, status, detail = time.time(), "ok", ""
            try:
                doc, design, root = _neues_dokument(app)
                dokumente.append(doc)
                if braucht_blech or funktion is t_blech:
                    body = _blech_bauen(design, root)
                    ctx = _Ctx(design, body.parentComponent, body, fa.blechdicke_mm(body) or 1.0)
                else:
                    ctx = _Ctx(design, root, None, 1.0)
                detail = funktion(ctx) or ""
            except _Uebersprungen as w:
                status, detail = "uebersprungen", str(w)
            except _Warnung as w:
                status, detail = "warnung", str(w)
            except _Falsch as w:
                status, detail = "fehler", str(w)
            except Exception as e:
                status, detail = "fehler", _letzte_zeile(e)
                logger.ausnahme("Live-Test " + name)
                if funktion is t_blech:
                    blech_ok = False
                    detail += "\n" + "\n".join(traceback.format_exc().splitlines()[-3:-1])
            erg.append({"name": name, "status": status, "detail": detail, "dauer": time.time() - t0})
            try:
                adsk.doEvents()
            except Exception:
                pass
        # Rundblech und 3D-Detail (eigener Selbsttest, öffnet selbst ein Dokument)
        t0 = time.time()
        try:
            from . import selftest
            text = selftest.ausfuehren()
            dokumente.append(app.activeDocument)
            schlecht = [z for z in text.splitlines() if z.startswith("✗")]
            erg.append({"name": "Rundblech und 3D-Detail (Export/Import/Ausrichtung)", "status": "fehler" if schlecht else "ok",
                        "detail": "\n".join(schlecht) if schlecht else "ok", "dauer": time.time() - t0})
        except Exception as e:
            erg.append({"name": "Rundblech und 3D-Detail", "status": "fehler", "detail": _letzte_zeile(e), "dauer": time.time() - t0})
            logger.ausnahme("Live-Test Rundblech/Detail")
    finally:
        _alles_schliessen(dokumente)
        try:
            if original is not None:
                original.activate()
        except Exception:
            pass
    return erg, kopf

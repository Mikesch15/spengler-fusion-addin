"""Live-Test IN Fusion für gekrümmte Geometrie (Nachtauftrag Phase 8) – eigene Testkörper in neuen Dokumenten:
Bogenkante auf ebenem Blech, Zylinder (voll und als Teilzylinder mit geraden Mantelkanten), Kegel, gerolltes Blech (Flansch mit grossem
Radius = Übergang Ebene→Zylinder), Kugelband (doppelt gekrümmt) und das Doppelfalz-Testprofil.

Jeder Schritt prüft GEOMETRIE (Normalenwinkel gegen die analytische Normale, gemessene Abstände, Flächentypen, Abwickelbarkeit), nicht nur,
dass ein Objekt existiert. An gekrümmten Kanten wird Fusion ausdrücklich gefragt (fusion_fragen=True): lehnt Fusion ab, bestätigt das die
Unterstützungsmatrix («nicht unterstützt», PASS); baut Fusion, meldet der Test das als Hinweis zur Freigabeprüfung.
NICHT live geprüft – das IST der Live-Test. Fusion-Aufrufe nur über geometry/fusion_adapter."""
from ..core import geometrie_referenz as gr
from ..core import livetest_messung as messung
from ..details import frames
from ..geometry import fusion_adapter as fa


def _lt():
    from . import live_test
    return live_test


def _punkt(x, y, z):
    import adsk.core
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0)


def _flaechen_vom_typ(body, typ):
    return [f for f in body.faces if fa.flaechentyp(f) == typ]


def _normalen_vergleich(ref, soll, was):
    w = gr.winkel_grad(ref["normale"], soll)
    w = min(w, 180.0 - w)                     # Orientierung (innen/aussen) prüfen wir getrennt nicht – die Achse muss stimmen
    if w > 0.5:
        raise _lt()._Falsch("%s: lokale Normale weicht %.2f° von der analytischen ab (%s statt %s)." % (was, w, _v(ref["normale"]), _v(soll)))
    return "%s: Normale %.3f° genau" % (was, w)


def _v(v):
    return "(%.3f, %.3f, %.3f)" % tuple(v)


def _detail_starr(ctx, ref, flaeche, standoff=2.0):
    """Quader 10 × 10 × 5 mm starr tangential am Referenzpunkt mit Abstand entlang der LOKALEN Normale; gemessener Abstand muss = Abstand sein
    (konvexe Fläche: Berührpunkt genau unter dem Ursprung). Stimmt die Normale nicht, schneidet der Quader oder steht schief weg."""
    r = ref["rahmen"]
    ziel = dict(r, origin=[o + standoff * z for o, z in zip(r["origin"], r["z"])])
    comp = fa.quader_komponente(ctx.design.rootComponent, "Live-Test Detail starr", 10.0, 10.0, 5.0)
    occ = fa.occurrence_von(comp)
    occ.transform = fa.matrix_fusion(frames.matrix(ziel))
    a = fa.abstand_mm(occ, flaeche)
    if a is None:
        raise _lt()._Warnung("Abstand Detail↔Fläche nicht messbar.")
    if abs(a - standoff) > 0.05:
        raise _lt()._Falsch("Detail starr: Abstand %.3f mm statt %.2f mm – Ausrichtung an der lokalen Normale stimmt nicht." % (a, standoff))
    return "Detail starr tangential: Abstand %.3f mm (Soll %.2f)" % (a, standoff)


def _fusion_frage(was, bauen):
    """Fusion an einer nicht freigegebenen Geometrie ausdrücklich fragen. → Text. Ablehnung = bestätigt «nicht unterstützt»."""
    try:
        feat = bauen()
    except fa.AdapterFehler as e:
        return "%s: Fusion lehnt ab – bleibt «nicht unterstützt» (%s)" % (was, str(e).splitlines()[0][:160])
    except Exception as e:
        return "%s: Fusion lehnt ab – bleibt «nicht unterstützt» (%s)" % (was, (str(e).strip().splitlines() or ["?"])[-1][:160])
    fa.entfernen([feat] if not isinstance(feat, list) else feat)
    raise _lt()._Warnung("%s: Fusion HAT gebaut – Geometrie prüfen und Freigabe in core/unterstuetzung erwägen (bisher «nicht unterstützt»)." % was)


# ------------------------------------------------------------------ Testkörper und Schritte
def t_bogenkante(ctx):
    """Fixture 2: ebenes Blech mit einer Bogenseite (Grundriss mit Bogen); Referenz an der Bogenkante, Fusion-Anfrage Flansch/Umschlag."""
    body = fa.blech_aus_profil(fa.neue_komponente("Live-Test Bogenblech"), [[(0, 0), (100, 0, 115, 30), (100, 60), (0, 60)]], 1.0)
    boegen = [e for e in body.edges if fa._kurventyp(e) in ("bogen", "kreis")]
    if not boegen:
        raise _lt()._Falsch("Das Bogenblech hat keine Bogenkante – Bögen im Profil wirken nicht.")
    oben = max([e for e in boegen], key=lambda e: e.boundingBox.maxPoint.z)
    ref = fa.referenz_aus_fusion(edge=oben)
    if gr.klasse(ref)[1] not in ("bogen", "kreis"):
        raise _lt()._Falsch("Bogenkante als «%s» eingeordnet." % gr.klasse(ref))
    t = ["Bogenkante erkannt (%s, Fläche %s)" % (ref["kurve"], ref["flaeche"]),
         _fusion_frage("Flansch an Bogenkante", lambda: fa.flansch(oben, 90, 20, fusion_fragen=True))]
    oben = max([e for e in body.edges if fa._kurventyp(e) in ("bogen", "kreis")], key=lambda e: e.boundingBox.maxPoint.z)
    t.append(_fusion_frage("Umschlag an Bogenkante", lambda: fa.umschlag(oben, 10, False, None, None, 1.0, fusion_fragen=True)))
    return "\n".join(t)


def _rohr(ctx, name, winkel=360.0):
    """Fixture 3/4: Zylinderschale R 100 (aussen 101), Höhe 80 mm um Z; winkel < 360 = Teilzylinder mit geraden Mantelkanten."""
    comp = fa.neue_komponente(name)
    feat = fa.drehkoerper(comp, [(100, 0), (101, 0), (101, 80), (100, 80)], name, winkel)
    return feat.bodies.item(0)


def t_zylinder(ctx):
    body = _rohr(ctx, "Live-Test Zylinder")
    zyl = _flaechen_vom_typ(body, "zylinder")
    if len(zyl) != 2:
        raise _lt()._Falsch("Zylinderschale: %d Zylinderflächen statt 2 (Flächentypen: %s)." % (len(zyl), ", ".join(fa.flaechentyp(f) for f in body.faces)))
    aussen = max(zyl, key=lambda f: f.area)
    p = (0.0, 101.0, 40.0)
    ref = fa.referenz_aus_fusion(face=aussen, punkt=_punkt(*p))
    t = [_normalen_vergleich(ref, gr.zylinder_normale((0, 0, 0), (0, 0, 1), p), "Zylinder")]
    k = ref.get("kruemmung")
    if k:
        t.append("Krümmung k1 %.5f, k2 %.5f 1/mm (Soll 1/101 = %.5f und 0)" % (k["k1"], k["k2"], 1 / 101.0))
    try:
        gr.versatz_definition(ref, 5, "tangential")
        raise _lt()._Falsch("Versatz auf Zylinder wurde nicht abgelehnt.")
    except ValueError as e:
        t.append("Versatz tangential abgelehnt: %s" % str(e)[:80])
    art, _g = fa.abwickelbarkeit_koerper(body)
    t.append("Abwickelbarkeit: %s" % art)
    if art != "exakt":
        raise _lt()._Falsch("Zylinderschale als «%s» eingeordnet (erwartet exakt)." % art)
    t.append(_detail_starr(ctx, ref, aussen))
    return "\n".join(t)


def t_teilzylinder(ctx):
    """Fixture 3: Teilzylinder (90°) – gerade Mantelkante auf einer Zylinderfläche: Referenz-Klasse und Fusion-Anfrage Flansch."""
    body = _rohr(ctx, "Live-Test Teilzylinder", 90.0)
    gerade = [e for e in body.edges if fa._kurventyp(e) == "linie" and abs(e.length * 10 - 80) < 0.1]
    if not gerade:
        raise _lt()._Falsch("Teilzylinder ohne gerade Mantelkante.")
    zyl = max(_flaechen_vom_typ(body, "zylinder"), key=lambda f: f.area)
    kante = next((e for e in gerade if any(fa._gleiche(f, zyl) for f in e.faces)), gerade[0])
    ref = fa.referenz_aus_fusion(face=zyl, edge=kante)
    t = ["gerade Kante auf %s, Klasse %s" % (ref["flaeche"], gr.klasse(ref))]
    t.append(_fusion_frage("Flansch an gerader Kante einer Zylinderschale (kein Blechkörper)", lambda: fa.flansch(kante, 90, 20, fusion_fragen=True)))
    return "\n".join(t)


def t_kegel(ctx):
    """Fixture 5: Kegelschale (unten R 100, oben R 60, Höhe 80) – Normale gegen die analytische Kegelnormale, Abwickelbarkeit exakt."""
    comp = fa.neue_komponente("Live-Test Kegel")
    feat = fa.drehkoerper(comp, [(100, 0), (101, 0), (61, 80), (60, 80)], "Live-Test Kegel")
    body = feat.bodies.item(0)
    keg = _flaechen_vom_typ(body, "kegel")
    if not keg:
        raise _lt()._Falsch("Kegelschale ohne Kegelfläche (Typen: %s)." % ", ".join(fa.flaechentyp(f) for f in body.faces))
    aussen = max(keg, key=lambda f: f.area)
    # Aussenmantel: von (101, 0) nach (61, 80): Spitze dort, wo r = 0 → z = 101 / 40 × 80 = 202; Halbwinkel atan(40 / 80)
    import math
    p = (81.0, 0.0, 40.0)
    soll = gr.kegel_normale((0, 0, 202.0), (0, 0, -1), math.degrees(math.atan(40.0 / 80.0)), p)
    ref = fa.referenz_aus_fusion(face=aussen, punkt=_punkt(*p))
    t = [_normalen_vergleich(ref, soll, "Kegel")]
    art, _g = fa.abwickelbarkeit_koerper(body)
    t.append("Abwickelbarkeit: %s" % art)
    if art != "exakt":
        raise _lt()._Falsch("Kegelschale als «%s» eingeordnet (erwartet exakt)." % art)
    t.append(_detail_starr(ctx, ref, aussen))
    return "\n".join(t)


def t_gerollt(ctx):
    """Fixture 6/7: Blech 1 mm mit Flansch 40 mm und Biegeradius 20 mm (Übergang Ebene → Zylinder, gerollter Bereich mit bekannter Dicke):
    Zylinderfläche der Biegung erkannt, Abwicklung exakt und masshaltig, DXF geprüft."""
    lt = _lt()
    body = fa.grundblech_bauen(fa.neue_komponente("Live-Test gerollt"), lt.LAENGE, lt.BREITE, 1.0)
    comp = body.parentComponent
    kante = sorted([e for e in fa._oberseite(body).edges if fa._kurventyp(e) == "linie"], key=lambda e: (-e.length, e.boundingBox.minPoint.y))[0]
    fa.flansch(kante, 90, 40, radius_mm=20.0)
    body = comp.bRepBodies.item(0)
    zyl = _flaechen_vom_typ(body, "zylinder")
    if not zyl:
        raise lt._Falsch("Biegung mit Radius 20 mm ohne Zylinderfläche.")
    ref = fa.referenz_aus_fusion(face=max(zyl, key=lambda f: f.area))
    t = ["Biegezone: %d Zylinderfläche(n), Referenz %s" % (len(zyl), gr.klasse(ref))]
    art, _g = fa.abwickelbarkeit_koerper(body)
    if art != "exakt":
        raise lt._Falsch("Gerolltes Blech als «%s» eingeordnet." % art)
    fp, _neu = fa.abwicklung(comp)
    m = fa.abwicklung_masse(fp)
    s, txt = messung.pruefe_abwicklung(m["breite"], m["laenge"], lt.LAENGE, lt.BREITE, 40.0, 1.0, ri=20.0)
    t.append(txt)
    if s == "fehler":
        raise lt._Falsch("\n".join(t))
    if s == "warnung":
        raise lt._Warnung("\n".join(t))
    return "\n".join(t)


def t_kugel(ctx):
    """Fixture 8: Kugelband (Querschnitt mit Bogen gedreht) – muss als NICHT exakt abwickelbar erkannt werden."""
    comp = fa.neue_komponente("Live-Test Kugelband")
    # Aussenbogen R 101 von 0° bis 40°, Innenbogen R 100 zurück (r, z, Bogenmitte)
    import math
    def P(R, w):
        return (R * math.cos(math.radians(w)), R * math.sin(math.radians(w)))
    a0, a1, ma = P(101, 0), P(101, 40), P(101, 20)
    i1, i0, mi = P(100, 40), P(100, 0), P(100, 20)
    feat = fa.drehkoerper(comp, [(a0[0], a0[1], ma[0], ma[1]), (a1[0], a1[1]), (i1[0], i1[1], mi[0], mi[1]), (i0[0], i0[1])], "Live-Test Kugelband")
    body = feat.bodies.item(0)
    typen = sorted({fa.flaechentyp(f) for f in body.faces})
    art, grund = fa.abwickelbarkeit_koerper(body)
    if "kugel" not in typen:
        raise _lt()._Falsch("Kugelband ohne Kugelfläche (Typen: %s)." % ", ".join(typen))
    if art != "nicht":
        raise _lt()._Falsch("Kugelband als «%s» abwickelbar eingeordnet – eine verzerrte Abwicklung darf nie als exakt gelten." % art)
    return "Flächentypen %s; Abwickelbarkeit «nicht»: %s" % (", ".join(typen), grund)


def t_doppelfalz(ctx):
    """Doppelfalz-Testprofil an der langen Kante des Test-Blechs: Aufkantung 30 mm, Umschlag 10 mm, zweiter Umschlag 8 mm (Folge wie in der Praxis).
    Geprüft: alle Schritte gebaut, Volumen ≈ Kante × (30 + 10 + 8) × Dicke, Körper gültig."""
    lt = _lt()
    vor = lt._messen(ctx)
    kante = lt._rand_kanten(ctx)[0]
    L = lt._laenge_mm(kante)
    hin = []
    erz = fa.folge_anbringen(kante, [lt._op("flansch", 90, 30), lt._op("umschlag", 180, 10), lt._op("umschlag", 180, 8)], ctx.dicke, {"livetest": 1}, hin)
    nach = lt._messen(ctx)
    soll = L * (30 + 10 + 8) * (ctx.dicke or 1.0)
    ratio = (nach["vol"] - vor["vol"]) / soll
    t = "%d Schritte, Volumen %+.0f mm³ = %.0f %% von %.0f; Höhe %.1f mm%s" % (len(erz), nach["vol"] - vor["vol"], 100 * ratio, soll,
                                                                           nach["max"][2] - nach["min"][2], ("; " + " / ".join(hin)) if hin else "")
    if len(erz) != 3 or not (0.6 <= ratio <= 1.5) or fa.koerper_pruefen(ctx.root.bRepBodies.item(0)):
        raise lt._Falsch(t)
    return t


# (Name, Funktion, braucht Test-Blech) – an live_test.SCHRITTE angehängt
SCHRITTE = [
    ("Doppelfalz-Testprofil (Aufkantung + 2 Umschläge)", t_doppelfalz, True),
    ("Gekrümmt: Bogenkante auf ebenem Blech (Fusion-Anfrage)", t_bogenkante, False),
    ("Gekrümmt: Zylinderschale (Normale, Versatz, Abwickelbarkeit, Detail starr)", t_zylinder, False),
    ("Gekrümmt: Teilzylinder mit gerader Mantelkante (Fusion-Anfrage)", t_teilzylinder, False),
    ("Gekrümmt: Kegelschale (Normale, Abwickelbarkeit, Detail starr)", t_kegel, False),
    ("Gekrümmt: gerolltes Blech R20 (Ebene→Zylinder, Abwicklung)", t_gerollt, False),
    ("Gekrümmt: Kugelband – nicht abwickelbar erkannt", t_kugel, False),
]

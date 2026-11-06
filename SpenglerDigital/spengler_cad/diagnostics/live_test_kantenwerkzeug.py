"""Live-Test IN Fusion für das Kantenwerkzeug, Bauweise «eigene Geometrie» (Auftrag Kantenwerkzeug, Phase 2/4/5/6).
Jeder Schritt erzeugt echte Fusion-Objekte in Testdokumenten, führt die Operation aus und prüft Volumen, Flächenarten, Masse, Abwickelbarkeit,
Rückvergleich 2D/3D bzw. den exakten Fehler und den Modellzustand. NICHT live geprüft – das IST der Live-Test."""
import os
import tempfile

from ..core import profil_engine as pe
from ..geometry import fusion_adapter as fa
from ..manufacturing import dxf_pruefung, dxf_writer

T, RI, K = 1.0, 1.0, 0.44


def _lt():
    from . import live_test
    return live_test


def _flansch(L=20.0, w=90.0, r=RI):
    return {"typ": "flansch", "winkel": w, "laenge": L, "radius": r}


def _umschlag(L=10.0, r=0.5):
    return {"typ": "umschlag", "winkel": 180.0, "laenge": L, "radius": r}


def _profil_hoehe(ops):
    """Höchster Punkt des Querschnitts über der Blechmitte (mm, lokale y-Richtung = Flächennormale)."""
    q = pe.querschnitt(pe.ops_zu_profil(ops, T, RI), T, RI, K)
    pts = [p for el in q["umriss"] for p in (el[1:4] if el[0] == "bogen" else el[1:3])]
    return max(p[1] for p in pts), q


def _eigen_an_blech(ctx, ops, name):
    lt = _lt()
    kante = lt._rand_kanten(ctx, "oben")[0]
    vor = lt._messen(ctx)
    hin = []
    erz = fa.eigene_folge(kante, ops, ctx.dicke or T, RI, K, {"livetest": name}, hin)
    nach = lt._messen(ctx)
    hoehe, q = _profil_hoehe(ops)
    body = ctx.root.bRepBodies.item(0)
    art, grund = fa.abwickelbarkeit_koerper(body)
    soll_z = vor["max"][2] - (ctx.dicke or T) / 2.0 + hoehe        # Blech oben bei z = Dicke, Blechmitte = Dicke/2
    soll_v = q["flaeche_mm2"] * lt.LAENGE                           # Kante = lange Seite des Test-Blechs
    t = "%s: %d Objekte, Volumen %+.2f mm³ (Soll %.2f), Höhe z %.3f mm (Soll %.3f), Abwickelbarkeit %s" % (
        name, len(erz), nach["vol"] - vor["vol"], soll_v, nach["max"][2], soll_z, art)
    if art != "exakt" or abs(nach["max"][2] - soll_z) > 0.01 or abs((nach["vol"] - vor["vol"]) - soll_v) > max(0.05, 1e-3 * soll_v) or fa.koerper_pruefen(body):
        raise lt._Falsch(t + " – " + grund)
    return t


def t_eigen_aufkantung(ctx):
    """Regression ebene gerade Kante: Aufkantung 90° 20 mm als eigene Geometrie am regulären Fusion-Blechkörper – Höhe/Volumen, Blechstatus VOR und
    NACH der Operation, native Abwicklung und DXF danach (Korrektur 0.4.49 Phase 2)."""
    import os
    import tempfile
    lt = _lt()
    vorher = getattr(ctx.root.bRepBodies.item(0), "isSheetMetal", None)
    t = _eigen_an_blech(ctx, [_flansch()], "Aufkantung 90° 20 mm")
    body = ctx.root.bRepBodies.item(0)
    nachher = getattr(body, "isSheetMetal", None)
    t += "\nBlechkörper vorher isSheetMetal=%s, nachher isSheetMetal=%s, ist_blech=%s" % (vorher, nachher, fa.ist_blech(body))
    if vorher is not True or nachher is not True:
        raise lt._Falsch(t + " – Blechsemantik nicht erhalten")
    fp, _neu = fa.abwicklung(ctx.root, None, body)
    m = fa.abwicklung_masse(fp)
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "eigen_nativ.dxf")
    fa.dxf_abwicklung(fp, pfad)
    pr = dxf_pruefung.pruefe_datei(pfad, m["breite"], m["laenge"], erwartete_konturen=1)
    t += "\nNative Abwicklung nach eigener Geometrie: %.2f × %.2f mm; DXF: %s" % (m["breite"], m["laenge"], dxf_pruefung.zusammenfassung(pr))
    if not pr["ok"]:
        raise lt._Falsch(t)
    return t


def t_eigen_einfachfalz(ctx):
    return _eigen_an_blech(ctx, [_flansch(25.0), _umschlag(10.0)], "Aufkantung 25 + Einfachfalz 10 (ein Arbeitsgang)")


def t_eigen_doppelfalz(ctx):
    """Doppelfalz als Querschnitt: Materiallagen und Abstände kommen exakt aus dem Profil (Selbstschnitt vorher geprüft)."""
    return _eigen_an_blech(ctx, [_flansch(30.0), _umschlag(10.0), _umschlag(8.0)], "Aufkantung 30 + Doppelfalz 10/8 (ein Arbeitsgang)")


def t_prototyp2(ctx):
    """Prototyp 2: Zylindersegment R 100 / 90° / Breite 80 als Profilteil, Aufkantung 90° 20 mm an der geraden Mantelkante (eigene Geometrie),
    eigene Abwicklung des GANZEN Teils, Rückvergleich 2D/3D (Volumen, Radien), DXF und Gegenprobe; Abweichung quantifiziert."""
    lt = _lt()
    comp = fa.neue_komponente("Live-Test Prototyp 2")
    seg = pe.segment_profil(100.0, 90.0, T)
    body = fa.profil_koerper(comp, seg, T, RI, K, 80.0, "Zylindersegment")
    kanten = [e for e in body.edges if fa._kurventyp(e) == "linie" and abs(e.length * 10 - 80.0) < 0.01 and fa.bezugsflaeche(e) is not None
              and fa.flaechentyp(fa.bezugsflaeche(e)) == "zylinder"]
    attr = fa.profil_attribut(body)
    ende = [e for e in kanten if fa._ende_des_profils(attr, e, T)[0] == "ende"]
    if not ende:
        raise lt._Falsch("Keine gerade Mantelkante am Profilende gefunden (%d Mantelkanten)." % len(kanten))
    hin = []
    fa.eigene_folge(ende[0], [_flansch()], T, RI, K, {"livetest": "prototyp2"}, hin, prototyp=True)
    body = comp.bRepBodies.item(0)
    zuschnitt, vergleich = fa.eigene_abwicklung(body)
    q = pe.querschnitt(fa.profil_attribut(body)["profil"], T, RI, K)
    t = ["Teil: Zylinder R100/90° + Aufkantung 90°/20 mm, Breite 80; Flächen %s" % sorted({fa.flaechentyp(f) for f in body.faces})]
    t += vergleich["texte"]
    t.append("Abwicklung eigen: %.4f × %.4f mm (Biegungen %d)" % (zuschnitt["laenge"], zuschnitt["breite"], len(q["biegungen"])))
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "prototyp2.dxf")
    dxf_writer.elemente_dxf(zuschnitt, "Prototyp 2").speichern(pfad)
    dxf = dxf_pruefung.pruefe_datei(pfad, zuschnitt["breite"], zuschnitt["laenge"], toleranz_mm=0.01, erwartete_konturen=1)
    t.append("DXF: " + dxf_pruefung.zusammenfassung(dxf))
    if not vergleich["ok"] or not dxf["ok"] or len(q["biegungen"]) != 2:
        raise lt._Falsch("\n".join(t))
    return "\n".join(t)


def t_eigen_negativ(ctx):
    """Negativ: Bogenkante (Torus-Biegezone, Klasse d) und Selbstschnitt/zu kleiner Radius werden VOR dem Modellieren mit Grund abgelehnt –
    ohne Reste im Modell."""
    lt = _lt()
    from . import live_test_gekruemmt as gk
    body = fa.blech_aus_profil(fa.neue_komponente("Live-Test Bogenblech eigen"), [[(0, 0), (100, 0, 115, 30), (100, 60), (0, 60)]], T)
    bogen = [e for e in body.edges if fa._kurventyp(e) in ("bogen", "kreis")]
    t = []
    for was, aktion, erwartet in (
            ("Bogenkante", lambda: fa.eigene_folge(bogen[0], [_flansch()], T, RI, K, {}, [], True), ("Torus", "[d –")),
            ("Selbstschnitt", lambda: fa.eigene_folge(lt._rand_kanten(ctx)[0] if ctx.body else bogen[0],
                                                       [_flansch(20), _flansch(40, 170, 0.5), _flansch(40, 170, 0.5)], T, RI, K, {}, []), "sich selbst"),
            ("Radius 0", lambda: fa.eigene_folge(bogen[0], [_flansch(20, 90, 0.0)], T, RI, K, {}, [], True), None)):
        txt = gk._ohne_reste(ctx, was, aktion)
        if "gebaut" in txt.split(":")[1][:8]:
            raise lt._Falsch(txt + " – hätte abgelehnt werden müssen")
        # Bogenkante: je nach gewählter Bogenkante (obere Fläche eben / Mantel) lehnt die Matrix (Klasse d) oder die Torus-Prüfung ab – beides
        # ist die richtige, vorher erfolgte Ablehnung (Live 0.4.59: Matrix-Grund, Test erwartete nur «Torus»)
        if erwartet and not any(x in txt for x in ((erwartet,) if isinstance(erwartet, str) else erwartet)):
            raise lt._Falsch(txt + " – erwarteter Grund «%s» fehlt" % (erwartet if isinstance(erwartet, str) else " oder ".join(erwartet)))
        t.append(txt)
    return "\n".join(t)


def t_eigen_rueckbau(ctx):
    """Rückbau: eingeschleuster Fehler nach der Extrusion (eigene Folge an der Kante und neues Profilteil) – Modellzustand vorher = nachher."""
    lt = _lt()
    t = [lt._rueckbau_probe(ctx, stelle, lambda: fa.eigene_folge(lt._rand_kanten(ctx)[0], [_flansch(25.0), _umschlag()], T, RI, K, {}, []))
         for stelle in ("eigen_nach_extrusion",)]

    def neues_teil():
        comp = fa.neue_komponente("Live-Test Rückbau Profilteil")
        try:
            fa.profil_koerper(comp, pe.segment_profil(100.0, 90.0, T), T, RI, K, 80.0)
        except fa.AdapterFehler as e:
            if not fa.komponente_entfernen(comp):
                raise fa.AdapterFehler(str(e) + " – Komponente nicht entfernt", rueckbau_ok=False)
            raise
    t.append(lt._rueckbau_probe(ctx, "eigen_nach_extrusion", neues_teil))
    return "\n".join(t)


def _quetschfalte_stufe(ctx, stufe):
    """MACHBARKEIT Quetschfalte (Variante a, Anwender 6. 11. 2026) in vier Stufen, jede ein eigener Live-Schritt mit Absturzmarke (Fusion stürzte in
    0.4.67 im gebündelten Schritt ab). Aufkantung bauen, dann je Stufe: 1 Skizze, 2 Platte anfügen, 3 Blechkörper prüfen, 4 Fusion-Abwicklung."""
    lt = _lt()
    fa.flansch(lt._rand_kanten(ctx, "oben")[0], winkel=90, laenge_mm=lt.FLANSCH)
    body = ctx.root.bRepBodies.item(0)
    ok, text, abw = fa.platte_anfuegen_probe(body, stufe=stufe)
    if stufe < 4:
        if not ok:
            raise lt._Warnung(text + "\n→ Das Teil bleibt NICHT als Fusion-Blech erhalten: die Quetschfalte braucht dann einen anderen Weg.")
        return text
    erg = text + "\n" + abw
    if "NICHT möglich" in abw or "Fehler" in abw:
        raise lt._Warnung(erg + "\n→ Fusions Abwicklung scheitert: Zuschnitt und DXF kommen vom Add-in (Variante a), «Abwicklung & DXF» darf auf solchen Teilen Fusions Abwicklung nicht benutzen.")
    return erg


def t_quetschfalte_1(ctx):
    return _quetschfalte_stufe(ctx, 1)


def t_quetschfalte_2(ctx):
    return _quetschfalte_stufe(ctx, 2)


def t_quetschfalte_3(ctx):
    return _quetschfalte_stufe(ctx, 3)


def t_quetschfalte_4(ctx):
    return _quetschfalte_stufe(ctx, 4)


def t_quetschfalte_bauen(ctx):
    """QUETSCHFALTE an einer echten Fusion-Ecke: Blech mit Aufkantung an zwei benachbarten Kanten (gemeinsamer Flansch = Stossecke), dann zwei Aufkantungsflächen
    wählen, die Ecke analysieren, die Quetschfalte bauen (Falte und Eckfüllung als eigene Körper in der eigenen Komponente «Quetschfalte»), das Blech muss
    UNVERÄNDERT bleiben und Fusions Abwicklung samt DXF-Export muss funktionieren."""
    lt = _lt()
    import adsk.core
    fa.flansch(lt._eckkanten(ctx), winkel=90, laenge_mm=lt.FLANSCH)
    body = ctx.root.bRepBodies.item(0)
    nb = fa.flaechennormale(fa.stationaere_flaeche_waehlen(body))
    waende = []
    for f in body.faces:
        try:
            if isinstance(f.geometry, adsk.core.Plane) and abs(sum(a * b for a, b in zip(fa.flaechennormale(f), nb))) < 0.05:
                waende.append((f.area, f, fa.flaechennormale(f)))
        except Exception:
            continue
    waende.sort(key=lambda x: -x[0])
    if len(waende) < 2:
        raise lt._Falsch("Keine zwei Aufkantungsflächen gefunden (%d senkrechte ebene Flächen)." % len(waende))
    erste = waende[0]
    zweite = next((w for w in waende[1:] if abs(sum(a * b for a, b in zip(w[2], erste[2]))) < 0.5), None)
    if zweite is None:
        raise lt._Falsch("Keine zweite, quer stehende Aufkantungsfläche gefunden.")
    vol0 = lt._messen(ctx)["vol"]
    try:
        a = fa.quetschfalte_analysieren(erste[1], zweite[1], "hinten rechts")
    except fa.AdapterFehler as e:
        raise lt._Warnung("Analyse der Ecke abgelehnt (kein Fehler des Test-Aufbaus ausgeschlossen): %s" % e)
    t = [fa.quetschfalte_text(a)]
    objekte = fa.quetschfalte_bauen(a)
    nach = lt._messen(ctx)
    body = ctx.root.bRepBodies.item(0)
    t.append("gebaut: %d Objekte, Volumen %+.2f mm³, Körper %d, isSheetMetal=%s" % (len(objekte), nach["vol"] - vol0, ctx.root.bRepBodies.count,
                                                                                getattr(body, "isSheetMetal", None)))
    # Das Blech ist UNVERÄNDERT in seiner Komponente (Falte und Ecke liegen in der Komponente «Quetschfalte») – Fusions Abwicklung muss funktionieren
    if ctx.root.bRepBodies.count != 1:
        raise lt._Falsch("\n".join(t) + "\nIm Blech blieben %d Körper statt einem zurück." % ctx.root.bRepBodies.count)
    try:
        fp, _neu = fa.abwicklung(ctx.root)
        m = fa.abwicklung_masse(fp)
        pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "quetschfalte_blech.dxf")
        fa.dxf_abwicklung(fp, pfad)
        pr = dxf_pruefung.pruefe_datei(pfad, m["breite"], m["laenge"], erwartete_konturen=1)
    except fa.AdapterFehler as e:
        raise lt._Falsch("\n".join(t) + "\nFusions Abwicklung des Blechs scheitert trotz getrennter Komponente: %s" % e)
    t.append("Fusions Abwicklung des Blechs: %.2f × %.2f mm; DXF: %s" % (m["breite"], m["laenge"], dxf_pruefung.zusammenfassung(pr)))
    if not pr["ok"]:
        raise lt._Falsch("\n".join(t))
    return "\n".join(t)


SCHRITTE = [
    ("KANTENWERKZEUG eigen: Aufkantung (Regression eben)", t_eigen_aufkantung, True),
    ("KANTENWERKZEUG eigen: Aufkantung + Einfachfalz", t_eigen_einfachfalz, True),
    ("KANTENWERKZEUG eigen: Aufkantung + Doppelfalz", t_eigen_doppelfalz, True),
    ("KANTENWERKZEUG eigen: Prototyp 2 Zylindersegment + Aufkantung, eigene Abwicklung, DXF", t_prototyp2, False),
    ("KANTENWERKZEUG eigen: Negativ- und Grenzfälle", t_eigen_negativ, True),
    ("KANTENWERKZEUG eigen: Rückbau", t_eigen_rueckbau, True),
    ("QUETSCHFALTE: Ecke zweier Aufkantungen bauen", t_quetschfalte_bauen, True),
    ("MACHBARKEIT Quetschfalte 1/4: Skizze auf der Aufkantung", t_quetschfalte_1, True),
    ("MACHBARKEIT Quetschfalte 2/4: Platte anfügen (Extrusion, Vereinigung)", t_quetschfalte_2, True),
    ("MACHBARKEIT Quetschfalte 3/4: Blechkörper erhalten und gültig", t_quetschfalte_3, True),
    ("MACHBARKEIT Quetschfalte 4/4: Fusion-Abwicklung nach der Platte", t_quetschfalte_4, True),
]

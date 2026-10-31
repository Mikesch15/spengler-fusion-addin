"""Geometrieadapter – die EINZIGE Stelle mit Fusion-Geometrieaufrufen.

Die Oberfläche (commands/) erzeugt keine Geometrie selbst, sondern ruft diese Funktionen.

Status (ehrlich): Diese Datei konnte in der Entwicklungsumgebung NICHT in Fusion ausgeführt werden.
Die Blech-API von Fusion (FlangeFeatures/HemFeatures) ist bei Autodesk als «Preview» markiert;
Eigenschaftsnamen der Eingabeobjekte werden deshalb vorsichtig gesucht (wie im Prototyp 0.1) und
jeder Versuch wird protokolliert. Fehlt eine nötige Einstellung (z. B. Winkel), wird abgebrochen –
es wird nie stillschweigend ein anderer Wert verwendet.

Längen: Fusion-API in cm, Add-in in mm (Umrechnung über core/units.py).
"""
import json
import math

import adsk.core
import adsk.fusion

from ..core import units
from ..diagnostics import logger

ATTR_GRUPPE = "SpenglerDigitalCAD"


class AdapterFehler(RuntimeError):
    """Verständliche Meldung für den Benutzer; technische Details stehen im Protokoll."""

    def __init__(self, text, rueckbau_ok=True):
        RuntimeError.__init__(self, text)
        self.rueckbau_ok = rueckbau_ok


def app():
    return adsk.core.Application.get()


def design():
    d = adsk.fusion.Design.cast(app().activeProduct)
    if not d:
        raise AdapterFehler("Kein Fusion-Design aktiv. Bitte ein Konstruktionsdokument öffnen.")
    return d


# ------------------------------------------------------------------ Hilfen für Preview-API
_GELOGGT = set()


def _eigenschaften_einmal(name, obj):
    """Die Eigenschaftsliste einer Preview-API-Eingabe nur beim ersten Mal protokollieren (hält das Protokoll lesbar)."""
    if name not in _GELOGGT:
        _GELOGGT.add(name)
        logger.info(name, eigenschaften=_namen(obj))


def _namen(obj):
    try:
        return sorted(n for n in dir(obj) if not n.startswith("_") and n not in ("this", "thisown", "cast", "classType", "objectType", "isValid"))
    except Exception:
        return []


def setze(obj, namen, wert):
    """Erste vorhandene Eigenschaft/Methode setzen → Name oder None. Protokolliert Fehlversuche."""
    for n in namen:
        if not hasattr(obj, n):
            continue
        try:
            a = getattr(obj, n)
            if callable(a):
                a(wert)
            else:
                setattr(obj, n, wert)
            return n
        except Exception as e:
            logger.warnung("setzen fehlgeschlagen", eigenschaft=n, fehler=e)
    return None


def _vi_mm(mm):
    return adsk.core.ValueInput.createByString(units.fusion_ausdruck_mm(mm))


def _vi_grad(g):
    return adsk.core.ValueInput.createByString(units.fusion_ausdruck_grad(g))


# ------------------------------------------------------------------ Kanten analysieren
def _kurventyp(edge):
    t = edge.geometry.curveType
    C = adsk.core.Curve3DTypes
    return {C.Line3DCurveType: "linie", C.Arc3DCurveType: "bogen", C.Circle3DCurveType: "kreis",
            C.Ellipse3DCurveType: "ellipse", C.EllipticalArc3DCurveType: "ellipse",
            C.NurbsCurve3DCurveType: "spline"}.get(t, "andere")


def blechdicke_mm(body):
    """Dicke aus der aktiven Blechregel der Komponente, sonst None (nicht raten)."""
    try:
        regel = body.parentComponent.activeSheetMetalRule
        if regel:
            return units.cm_zu_mm(regel.thickness.value)
    except Exception:
        pass
    return None


def ist_blech(body):
    try:
        v = getattr(body, "isSheetMetal", None)
        if v is not None:
            return bool(v)
    except Exception:
        pass
    return blechdicke_mm(body) is not None


def _punkt_mm(p):
    return [units.cm_zu_mm(p.x), units.cm_zu_mm(p.y), units.cm_zu_mm(p.z)]


def kante_beschreiben(edge, nr=1):
    """BRepEdge → Kantenbeschreibung (dict) für core.operation_plan. Keine Geometrieänderung."""
    edge = adsk.fusion.BRepEdge.cast(edge)
    body = edge.body
    t = blechdicke_mm(body)
    d = {"ref": edge, "text": "Kante %d" % nr, "kurve": _kurventyp(edge), "laenge": units.cm_zu_mm(edge.length),
         "flaechen": edge.faces.count, "blech": ist_blech(body), "dicke": t, "frei": None}
    # Aussenkante: eine angrenzende Fläche ist die schmale Stirnfläche (Breite ≈ Blechdicke)
    if t and edge.faces.count == 2 and d["laenge"] > 0:
        breiten = [units.cm_zu_mm(f.area / edge.length) for f in edge.faces]
        d["frei"] = any(abs(b - t) < max(0.02, 0.05 * t) for b in breiten)
    try:
        d["start"] = _punkt_mm(edge.startVertex.geometry)
        d["ende"] = _punkt_mm(edge.endVertex.geometry)
    except Exception:
        pass
    return d


def flaechennormale(face, punkt=None):
    p = punkt or face.pointOnFace
    ok, n = face.evaluator.getNormalAtPoint(p)
    if not ok:
        raise AdapterFehler("Flächennormale nicht bestimmbar.")
    return [n.x, n.y, n.z]


def kantenrahmen(edge, face=None):
    """Lokales Koordinatensystem an einer Kante (mm): Ursprung Kantenanfang, x entlang Kante, z = Normale der Bezugsfläche."""
    from ..details.frames import rahmen_aus_kante
    edge = adsk.fusion.BRepEdge.cast(edge)
    if _kurventyp(edge) != "linie":
        raise AdapterFehler("Die Anschlusskante muss gerade sein.")
    if face is None:
        # Bezugsfläche: die grössere angrenzende Fläche (Blechfläche, nicht Stirnfläche)
        face = max(list(edge.faces), key=lambda f: f.area)
    return rahmen_aus_kante(_punkt_mm(edge.startVertex.geometry), _punkt_mm(edge.endVertex.geometry), flaechennormale(face))


# ------------------------------------------------------------------ Neue Aussenkante bestimmen
def _linie(edge):
    g = edge.geometry
    p0 = g.startPoint
    d = p0.vectorTo(g.endPoint)
    d.normalize()
    return p0, d


def neue_aussenkante(feature, vorher, erwartet_mm, dicke_mm):
    """Freie Kante am Ende des eben erzeugten Flansches/Saums finden.

    Nicht nur «am weitesten entfernt»: Kandidaten müssen gerade, parallel zur vorigen Kante, etwa gleich
    lang und in plausibler Entfernung liegen (0.3·L … L + 2·t + 5 mm). Am Flanschende liegen zwei Kanten
    (Ober-/Unterseite, Abstand ≈ t). Mehr als dieses eine Paar → mehrdeutig → Abbruch statt Raten.
    """
    flaechen = getattr(feature, "faces", None)
    if flaechen is None:
        raise AdapterFehler("Das erzeugte Feature liefert keine Flächen – neue Kante nicht bestimmbar.")
    if _kurventyp(vorher) in ("kreis", "bogen"):
        return _neue_rundkante(flaechen, vorher, erwartet_mm, dicke_mm)
    p0, d0 = _linie(vorher)
    L0 = vorher.length
    kandidaten = []
    gesehen = set()
    for f in flaechen:
        for k in f.edges:
            try:
                key = k.tempId
            except Exception:
                key = id(k)
            if key in gesehen or _kurventyp(k) != "linie":
                continue
            gesehen.add(key)
            q, d = _linie(k)
            if abs(abs(d.dotProduct(d0)) - 1) > 1e-4:
                continue
            if abs(k.length - L0) > max(0.05, 0.02 * L0, 0.4 * dicke_mm):   # Flansch über ganze Kantenlänge (Gehrung ändert sie um ~Blechdicke)
                continue
            abstand = units.cm_zu_mm(p0.vectorTo(q).crossProduct(d0).length)
            kandidaten.append((abstand, k))
    lo, hi = 0.3 * erwartet_mm, erwartet_mm + 2 * dicke_mm + 5.0
    plausibel = sorted([c for c in kandidaten if lo <= c[0] <= hi], key=lambda c: -c[0])
    logger.info("Aussenkante", erwartet=erwartet_mm, kandidaten=[round(a, 2) for a, _ in kandidaten], plausibel=[round(a, 2) for a, _ in plausibel])
    if not plausibel:
        raise AdapterFehler("Neue Aussenkante nicht gefunden (erwartet ca. %.1f mm von der vorigen Kante)." % erwartet_mm)
    oben = plausibel[0][0]
    paar = [c for c in plausibel if oben - c[0] <= dicke_mm + 0.05]
    rest = [c for c in plausibel if c not in paar and c[0] > 0.6 * erwartet_mm]
    if len(paar) > 2 or rest:
        raise AdapterFehler("Neue Aussenkante ist mehrdeutig (%d Kandidaten). Abbruch statt Raten – bitte die Folge in Einzelschritten anwenden." % len(plausibel))
    return paar[0][1]


def _kreisdaten(edge):
    """Kreis/Bogen → (Mittelpunkt, Achse (normiert), Radius, Öffnungswinkel in rad) – Fusion-Einheiten (cm)."""
    g = edge.geometry
    n = g.normal.copy()
    n.normalize()
    r = g.radius
    return g.center, n, r, (edge.length / r if r > 0 else 0.0)


def _abstand_zur_rundkante(vorher_daten, punkt):
    """Kürzester Abstand eines Punkts zum Vollkreis der vorigen Kante (mm) = √((ρ − r)² + h²)."""
    c, n, r, _ = vorher_daten
    v = c.vectorTo(punkt)
    h = v.dotProduct(n)
    rho = math.sqrt(max(0.0, v.length ** 2 - h * h))
    return units.cm_zu_mm(math.sqrt((rho - r) ** 2 + h * h))


def _neue_rundkante(flaechen, vorher, erwartet_mm, dicke_mm):
    """Wie neue_aussenkante, aber für Kreise/Bögen: Kandidaten sind koaxiale Kreise/Bögen gleichen Typs und gleichen
    Öffnungswinkels (Kreis: gleich vollständig). Das Flanschende besteht aus zwei Kanten (Abstand ≈ t); mehr → Abbruch."""
    vd = _kreisdaten(vorher)
    typ = _kurventyp(vorher)
    kandidaten, gesehen = [], set()
    for f in flaechen:
        for k in f.edges:
            try:
                key = k.tempId
            except Exception:
                key = id(k)
            if key in gesehen or _kurventyp(k) != typ:
                continue
            gesehen.add(key)
            c, n, r, wk = _kreisdaten(k)
            if abs(abs(n.dotProduct(vd[1])) - 1) > 1e-4:
                continue                                    # nicht parallele Achse
            if units.cm_zu_mm(c.vectorTo(vd[0]).crossProduct(vd[1]).length) > 0.05:
                continue                                    # nicht koaxial
            if typ == "bogen" and abs(wk - vd[3]) > 0.02 * max(vd[3], 1e-6):
                continue                                    # anderer Öffnungswinkel
            kandidaten.append((_abstand_zur_rundkante(vd, k.pointOnEdge), k))
    lo, hi = 0.3 * erwartet_mm, erwartet_mm + 2 * dicke_mm + 5.0
    plausibel = sorted([c for c in kandidaten if lo <= c[0] <= hi], key=lambda c: -c[0])
    logger.info("Aussenkante (rund)", erwartet=erwartet_mm, kandidaten=[round(a, 2) for a, _ in kandidaten], plausibel=[round(a, 2) for a, _ in plausibel])
    if not plausibel:
        raise AdapterFehler("Neue runde Aussenkante nicht gefunden (erwartet ca. %.1f mm von der vorigen Kante)." % erwartet_mm)
    oben = plausibel[0][0]
    paar = [c for c in plausibel if oben - c[0] <= dicke_mm + 0.05]
    rest = [c for c in plausibel if c not in paar and c[0] > 0.6 * erwartet_mm]
    if len(paar) > 2 or rest:
        raise AdapterFehler("Neue Aussenkante ist mehrdeutig (%d Kandidaten). Abbruch statt Raten – bitte die Folge in Einzelschritten anwenden." % len(plausibel))
    return paar[0][1]


def schlitze_pruefen(feature, kante, dicke_mm):
    """Hinweise auf ungewollte Einschnitte in einem Flansch an runder Kante (nicht live geprüft).

    Ein durchgehender Flansch an einem Kreis hat KEINE ebenen Stirnflächen quer zur Kante; an einem Bogen genau zwei
    (Anfang/Ende). Mehr ebene, schmale Flächen (Breite ≈ Blechdicke) deuten auf Schlitze/Lappen hin. → Liste von Texten."""
    typ = _kurventyp(kante)
    if typ not in ("kreis", "bogen"):
        return []
    try:
        quer = 0
        for f in feature.faces:
            if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
                continue
            # Stirnfläche eines Schlitzes: ebene Fläche, deren Kanten alle höchstens Blechdicke breit sind
            breite = min(units.cm_zu_mm(e.length) for e in f.edges)
            if abs(breite - dicke_mm) < max(0.02, 0.05 * dicke_mm):
                quer += 1
    except Exception as e:
        logger.warnung("Schlitzprüfung nicht möglich", fehler=e)
        return ["Prüfung auf Einschnitte nicht möglich – Flansch an der runden Kante bitte selbst prüfen."]
    erlaubt = 0 if typ == "kreis" else 2
    if quer > erlaubt:
        return ["Der Flansch an der runden Kante hat %d ebene Stirnflächen (erwartet %d) – möglicherweise Einschnitte/Lappen. Bitte prüfen "
                "(Vorschau, Blechregel: Eckentlastung)." % (quer, erlaubt)]
    return []


# ------------------------------------------------------------------ Flansch / Umschlag
def _flange_features(comp):
    ff = getattr(comp.features, "flangeFeatures", None)
    if ff is None or not hasattr(ff, "createEdgeFlangeInput"):
        raise AdapterFehler("Diese Fusion-Version kann keine Flansche per Add-in erzeugen (FlangeFeatures.createEdgeFlangeInput fehlt; "
                            "die Funktion gibt es laut Autodesk erst seit der API-Version Oktober 2026). Bitte Fusion aktualisieren. Fusion %s" % app().version)
    return ff


def flansch(edge, winkel, laenge_mm, radius_mm=None, gespiegelt=None, bezug=None, lage=None):
    """Kantenflansch über die ganze Kantenlänge. Winkel + zur Sichtseite, − nach hinten.

    edge: eine Kante oder eine Liste zusammenhängender Kanten – in EINEM Feature gebaut, damit Fusion die Ecken auf Gehrung schneidet
    (isMiteredCorners, Standard true).
    Echte API (help.autodesk.com, EdgeFlangeInput, Preview, ab Oktober 2026): createEdgeFlangeInput(edges, distance) nimmt laut Doku NUR
    gerade Aussenkanten; bei Kreis/Bogen wird es trotzdem versucht und Fusions Antwort wörtlich gemeldet. Eigenschaften angle (ValueInput),
    isFlipped, bendRadiusOverride.setOverride(ValueInput). gespiegelt: None → Richtung nach Vorzeichen des Winkels (− = isFlipped);
    True/False setzt isFlipped ausdrücklich."""
    kanten = list(edge) if isinstance(edge, (list, tuple)) else [edge]
    erste = kanten[0]
    comp = erste.body.parentComponent
    ff = _flange_features(comp)
    rund = any(_kurventyp(k) in ("kreis", "bogen") for k in kanten)
    try:
        inp = ff.createEdgeFlangeInput(kanten, _vi_mm(laenge_mm))
    except Exception as e:
        raise AdapterFehler(_flansch_ablehnung(rund, e))
    if inp is None:
        raise AdapterFehler(_flansch_ablehnung(rund, None))
    _eigenschaften_einmal("EdgeFlangeInput", inp)
    w = abs(winkel)
    gesetzt = setze(inp, ["angle", "flangeAngle", "setAngle", "setFlangeAngle"], _vi_grad(w))
    if not gesetzt and abs(w - 90) > 1e-6:
        raise AdapterFehler("Der Flanschwinkel %g° lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % w)
    if gespiegelt is None:
        gespiegelt = winkel < 0
    if gespiegelt:
        if not setze(inp, ["isFlipped", "isDirectionFlipped", "flipDirection", "isFlangeFlipped"], True):
            raise AdapterFehler("Die Flanschrichtung (nach hinten) lässt sich nicht einstellen – abgebrochen.")
    if len(kanten) > 1:
        setze(inp, ["isMiteredCorners"], True)
    if bezug:
        if not setze(inp, ["heightDatumType"], getattr(adsk.fusion.FlangeHeightDatumTypes, BEZUEGE[bezug])):
            raise AdapterFehler("Der Massbezug «%s» lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % bezug)
    if lage:
        if not setze(inp, ["bendPositionType"], _lage_enum(lage)):
            raise AdapterFehler("Die Lage «%s» lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % lage)
    if radius_mm is not None:
        ov = getattr(inp, "bendRadiusOverride", None)
        try:
            ok = bool(ov is not None and ov.setOverride(_vi_mm(radius_mm)))
        except Exception as e:
            logger.warnung("Biegeradius-Override fehlgeschlagen", fehler=e)
            ok = False
        if not ok:
            raise AdapterFehler("Der Biegeradius lässt sich nicht einstellen – abgebrochen (Radius wird nicht stillschweigend ignoriert).")
    try:
        feat = ff.add(inp)
    except Exception as e:
        raise AdapterFehler(_flansch_ablehnung(rund, e))
    if feat is None:
        raise AdapterFehler(_flansch_ablehnung(rund, None))
    return feat


def _flansch_ablehnung(rund, fehler):
    fusion = (str(fehler).strip().splitlines()[-1] if fehler is not None and str(fehler).strip() else "keine Angabe")
    if rund:
        return ("Fusion lehnt den Flansch an dieser runden Kante ab (Fusion: %s). Laut Autodesk-Dokumentation arbeitet die Flansch-Schnittstelle nur an "
                "geraden Kanten." % fusion)
    return "Fusion hat den Flansch nicht erzeugt (Fusion: %s)." % fusion


LAGEN = {"kante": "StartEdgeBendPositionType", "innen": "InsideBendPositionType", "aussen": "OutsideBendPositionType",
         "tangential": "TangentToSideBendPositionType"}
BEZUEGE = {"aussen": "OuterFacesFlangeHeightDatumType", "innen": "InnerFacesFlangeHeightDatumType", "tangential": "TangentToBendFlangeHeightDatumType"}


def _lage_enum(lage):
    return getattr(adsk.fusion.BendPositionTypes, LAGEN[lage])


def _kantenlaenge_mm(edge):
    try:
        return "%.1f" % (edge.length * 10.0)
    except Exception:
        return "?"


def umschlag(edge, laenge_mm, nach_hinten, radius_mm=None, lage=None, dicke_mm=None):
    """Umschlag/Saum 180° mit dem Saum-Werkzeug von Fusion.

    Echte API (help.autodesk.com, HemFeatureInput, ab September 2025): hf.createHemFeatureInput() ohne Argumente, danach
    setFlatHem(edge, length, isFlipped, bendPositionType) bzw. – mit Spalt – setOpenHem(edge, length, gap, isFlipped, bendPositionType);
    beide liefern True bei Erfolg. Ohne Radius: geschlossener Saum (Spalt 0); mit Radius: offener Saum mit Spalt = 2 × Radius (Annahme).
    Live-Test 30.10.: Fusion nahm die Definition an, die Berechnung scheiterte («Failed to create Hem … SM_MODELING_ERROR») – welche
    Kombination aus Biegelage und Richtung passt, hängt vom Körper ab. Ohne ausdrückliche Lage werden deshalb nacheinander Kante/innen/
    aussen/tangential und dann die Gegenrichtung versucht; die erste, die Fusion rechnet, gilt (im Protokoll vermerkt). NICHT live bestätigt."""
    # Live-Test 30.10.: mit Radius (offener Saum, Spalt 2 × Radius) scheiterte Fusion, ohne Radius (geschlossener Saum) klappt es.
    # Der Radius des Umschlags kommt deshalb aus der Blechregel; ein Radius in der Vorlage wird hier bewusst nicht verwendet.
    comp = edge.body.parentComponent
    hf = getattr(comp.features, "hemFeatures", None)
    if hf is None or not hasattr(hf, "createHemFeatureInput"):
        raise AdapterFehler("Diese Fusion-Version hat kein Saum-Werkzeug in der API (hemFeatures).")
    L = _vi_mm(laenge_mm)
    # Live-Test 30.10. (0.4.9): Eine in der Vorlage eingestellte Lage «tangential» scheiterte allein (Modellfehler), Standard (Kante) ging.
    # Die eingestellte Lage wird deshalb zuerst versucht, danach die übrigen; die Richtung der Vorlage bleibt zuerst.
    # Live 0.4.10: «innen»/«aussen» meldet Fusion beim Saum als ungültig, «kante»/«tangential» scheitern mit Modellfehler. Deshalb nur diese
    # beiden (und eine ausdrücklich eingestellte Lage) und zusätzlich verschiedene Biegeradien des Saums (Radius-Überschreibung) und zuletzt
    # ein offener Saum mit kleinem Spalt – die Blechregel kann für diese Blechdicke einen unpassenden Saumradius liefern.
    lagen = ([lage] if lage else []) + [l for l in ("kante", "tangential") if l != lage]
    richtungen = [bool(nach_hinten), not nach_hinten]
    t = dicke_mm if dicke_mm else None
    bauarten = [("Regel", None, None)]
    if t:
        bauarten += [("Radius %.2f" % t, t, None), ("Radius %.2f" % (t / 2.0), t / 2.0, None), ("offen, Spalt %.2f" % t, None, t)]
    if radius_mm:
        bauarten.insert(1, ("Radius %.2f" % radius_mm, radius_mm, None))
    versuche = []
    for art, rad, spalt in bauarten:
        for flip in richtungen:
            for l in lagen:
                inp = hf.createHemFeatureInput()
                if inp is None:
                    raise AdapterFehler("Fusion konnte die Saum-Eingabe nicht anlegen.")
                _eigenschaften_einmal("HemFeatureInput", inp)
                name = "%s, Lage %s%s" % (art, l, ", Gegenrichtung" if flip != bool(nach_hinten) else "")
                try:
                    if rad is not None:
                        ov = getattr(inp, "bendRadiusOverride", None)
                        if ov is None or not ov.setOverride(_vi_mm(rad)):
                            versuche.append("%s: Radius nicht einstellbar" % name)
                            continue
                    if spalt is not None:
                        ok = inp.setOpenHem(edge, L, _vi_mm(spalt), flip, _lage_enum(l))
                    else:
                        ok = inp.setFlatHem(edge, L, flip, _lage_enum(l))
                    if not ok:
                        versuche.append("%s: von Fusion abgelehnt" % name)
                        continue
                    feat = hf.add(inp)
                except Exception as e:
                    versuche.append("%s: %s" % (name, (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)[:160]))
                    continue
                if feat is None:
                    versuche.append("%s: nicht erzeugt" % name)
                    continue
                logger.info("Umschlag erzeugt", variante=name, versuche=len(versuche) + 1)
                if versuche:
                    logger.info("Umschlag: frühere Versuche scheiterten", versuche=" | ".join(versuche))
                return feat
    logger.warnung("Umschlag nicht möglich", versuche=" | ".join(versuche))
    antworten = []
    for v in versuche:
        a = v.split(": ", 1)[-1]
        if a not in antworten:
            antworten.append(a)
    logger.warnung("Umschlag: Eingabe", laenge_mm=laenge_mm, radius_mm=radius_mm, nach_hinten=nach_hinten,
                   kante_laenge_mm=_kantenlaenge_mm(edge))
    raise AdapterFehler("Fusion kann den Umschlag an dieser Kante nicht berechnen (Länge %.1f mm, Kante %s mm; %d Varianten versucht). "
                        "Fusion antwortet: %s. Bitte Länge, Kante (freie Aussenkante?) und Blechregel prüfen."
                        % (laenge_mm, _kantenlaenge_mm(edge), len(versuche), " / ".join(antworten) if antworten else "keine"))


def markieren(obj, daten):
    """Vorlagen-ID/-Version am erzeugten Feature/Occurrence speichern (Bauteil ↔ Vorlage getrennt versioniert)."""
    try:
        obj.attributes.add(ATTR_GRUPPE, "quelle", json.dumps(daten, ensure_ascii=False))
    except Exception:
        logger.warnung("Attribut nicht gesetzt", objekt=type(obj).__name__)


def entfernen(objekte):
    """Kontrollierte Wiederherstellung: erzeugte Features in umgekehrter Reihenfolge löschen."""
    ok = True
    for o in reversed(objekte):
        try:
            if o is not None and o.isValid:
                o.deleteMe()
        except Exception:
            ok = False
            logger.ausnahme("Rückbau fehlgeschlagen")
    return ok


# ------------------------------------------------------------------ Richtung jedes Schritts prüfen
# Die Vorschau (core/bend_geometry) dreht bei jedem Schritt RELATIV zur bisherigen Laufrichtung: Winkel + = nach links, − = nach rechts
# (180° = Umschlag zur linken/rechten Seite). Fusions isFlipped ist dagegen nicht relativ. Deshalb wird nach jedem Schritt gemessen, wohin
# Fusion tatsächlich gebaut hat, und bei Abweichung der Schritt gespiegelt neu angelegt. Rechnung in der Ebene quer zur Kante:
# u = Laufrichtung von der Blechfläche zur Kante, v = «oben» (so, wie Fusion beim ersten Schritt mit Winkel + baut).
def _skal(a, b):
    return sum(x * y for x, y in zip(a, b))


def _plus(a, b, fa_=1.0, fb=1.0):
    return tuple(fa_ * x + fb * y for x, y in zip(a, b))


def _einheit(a):
    n = math.sqrt(_skal(a, a))
    return tuple(x / n for x in a) if n > 1e-9 else None


def _ohne_komponente(a, e):
    return _plus(a, e, 1.0, -_skal(a, e))


def richtung_in_ebene(grad, u, v):
    """Einheitsvektor cos(φ)·u + sin(φ)·v."""
    r = math.radians(grad)
    return _plus(u, v, math.cos(r), math.sin(r))


def richtung_stimmt(laufwinkel_vorher, winkel, tatsaechlich, u, v):
    """Zeigt der gemessene Vektor (von der vorigen zur neuen Kante, quer zur Kante) in die Richtung der Vorlage?
    Flansch: Zielrichtung heading+winkel. Umschlag (≥175°): massgebend ist die SEITE (links für +, rechts für −) der bisherigen Laufrichtung.
    → True/False, None wenn nicht entscheidbar."""
    if abs(winkel) >= 175:
        links = richtung_in_ebene(laufwinkel_vorher + 90, u, v)
        soll = links if winkel > 0 else tuple(-x for x in links)
    else:
        soll = richtung_in_ebene(laufwinkel_vorher + winkel, u, v)
    d = _skal(tatsaechlich, soll)
    return None if abs(d) < 1e-9 else d > 0


def _kantenrahmen_quer(edge):
    """→ (e, u): Kantenrichtung und Laufrichtung von der Blechfläche zur Kante (Einheitsvektoren, cm-Welt) oder None."""
    try:
        p0, d0 = _linie(edge)
        e = _v(d0)
        flaeche = max(list(edge.faces), key=lambda f: f.area)
        w = _plus(_v(p0), _v(flaeche.pointOnFace), 1.0, -1.0)      # von der Flächenmitte zur Kante
        u = _einheit(_ohne_komponente(w, e))
        return (e, u) if u else None
    except Exception as ex:
        logger.warnung("Laufrichtung nicht bestimmbar", fehler=ex)
        return None


def _v(p):
    return (p.x, p.y, p.z)


def _gemessen(vorher, neu, e):
    """Vektor von der vorigen zur neuen Kante, quer zur Kantenrichtung; None bei Nullvektor/Fehler."""
    try:
        p0, _ = _linie(vorher)
        q, _ = _linie(neu)
        w = _ohne_komponente(_plus(_v(q), _v(p0), 1.0, -1.0), e)
        return w if math.sqrt(_skal(w, w)) > 1e-9 else None
    except Exception as ex:
        logger.warnung("Richtung nicht messbar", fehler=ex)
        return None


def _kante_aufloesen(token, alt):
    try:
        t = [x for x in design().findEntityByToken(token) if x and x.isValid]
        return adsk.fusion.BRepEdge.cast(t[0]) if len(t) == 1 else alt
    except Exception:
        return alt


# ------------------------------------------------------------------ Versatz der Biegung von der Startkante – NICHT live geprüft
def _koerper_nach(comp, vorher, feature):
    """Körper nach einem Feature wieder finden: Bericht 31.10. – nach einem Schnitt war feature.bodies.item(0) leer (Volumen 0, keine Kanten).
    Reihenfolge: gleicher entityToken, gleicher Name im Bauteil, Körper des Features; gültig = Volumen > 0."""
    kandidaten = []
    try:
        kandidaten += [adsk.fusion.BRepBody.cast(x) for x in design().findEntityByToken(vorher.entityToken)]
    except Exception:
        pass
    try:
        kandidaten += [b for b in comp.bRepBodies if b.name == vorher.name]
    except Exception:
        pass
    try:
        kandidaten += list(feature.bodies)
    except Exception:
        pass
    for b in kandidaten:
        try:
            if b is not None and getattr(b, "isValid", True) and b.volume > 1e-9:
                return b
        except Exception:
            continue
    return None


def _aufbau_richtung(flaeche, skizze):
    """+1/−1: Vorzeichen der Extrusionsdistanz, das vom Skizzenblatt IN das Blech zeigt (gegen die Aussennormale der Fläche); None wenn unbekannt."""
    try:
        n = _v(flaeche.geometry.normal)
        if getattr(flaeche, "isParamReversed", False):
            n = tuple(-x for x in n)
        xd, yd = _v(skizze.xDirection), _v(skizze.yDirection)
        ns = (xd[1] * yd[2] - xd[2] * yd[1], xd[2] * yd[0] - xd[0] * yd[2], xd[0] * yd[1] - xd[1] * yd[0])
        d = -_skal(ns, n)
        return None if abs(d) < 1e-6 else (1.0 if d > 0 else -1.0)
    except Exception as ex:
        logger.warnung("Richtung des Versatz-Streifens nicht bestimmbar", fehler=ex)
        return None


def _versatz_anwenden(edge, versatz_mm, dicke_mm):
    """Versatz an EINER Kante → (erzeugte Objekte, neue Kante)."""
    erzeugt, kanten = _versatz_gruppe([edge], versatz_mm, dicke_mm)
    return erzeugt, kanten[0]


def _versatz_gruppe(edges, versatz_mm, dicke_mm):
    """Verschiebt die Kanten, an denen die Flansche ansetzen, um versatz_mm quer zur Kante: + nach innen (Streifen wird abgeschnitten), − nach
    aussen (Streifen wird angefügt). Fusions Flansch kennt keine freie Verschiebung der Biegung; das Blech wird deshalb vorher entsprechend
    gekürzt oder verlängert (gerade Kanten, Streifen über die ganze Kantenlänge, alle Streifen in EINER Skizze/Extrusion). Zusammenstossende
    Kanten der Gruppe: beim Anfügen füllen die Streifen die Ecke, damit die versetzten Kanten wieder aufeinandertreffen und Fusion die Gehrung
    rechnen kann. → (erzeugte Objekte, neue Kanten in der Reihenfolge der alten). Rückbau macht der Aufrufer."""
    if not dicke_mm:
        raise AdapterFehler("Für den Versatz fehlt die Blechdicke (Materialprofil).")
    # Auswahlkanten können Proxys im Koordinatensystem der Baugruppe sein; die Körper der neuen Features liegen im Bauteilsystem.
    # Ohne Umrechnung passen die Koordinaten nicht zusammen (Bericht 31.10.: «0 Treffer»), deshalb mit den nativen Kanten rechnen.
    edges = [(getattr(k, "nativeObject", None) or k) for k in edges]
    s = versatz_mm / 10.0                           # cm; > 0 nach innen
    t = dicke_mm / 10.0
    daten = []
    for edge in edges:
        if _kurventyp(edge) != "linie":
            raise AdapterFehler("Ein Versatz ist nur an geraden Kanten möglich.")
        rahmen = _kantenrahmen_quer(edge)
        if rahmen is None:
            raise AdapterFehler("Für den Versatz konnte die Lage der Kante zur Blechfläche nicht bestimmt werden.")
        g = edge.geometry
        p0, p1 = _v(g.startPoint), _v(g.endPoint)
        laenge = math.sqrt(_skal(_plus(p1, p0, 1.0, -1.0), _plus(p1, p0, 1.0, -1.0)))
        daten.append({"p0": p0, "p1": p1, "e": rahmen[0], "u": rahmen[1], "L": laenge, "kante": edge})

    def geteilt(p, ausser):
        return any(math.sqrt(_skal(_plus(p, q, 1.0, -1.0), _plus(p, q, 1.0, -1.0))) < 1e-4
                   for j, d in enumerate(daten) if j != ausser for q in (d["p0"], d["p1"]))
    flaeche = max(list(edges[0].faces), key=lambda f: f.area)
    koerper = edges[0].body
    comp = koerper.parentComponent
    ueber, tief = 0.1, 0.1
    erzeugt = []
    skizze = comp.sketches.add(flaeche)
    skizze.name = "Versatz %+g mm" % versatz_mm
    erzeugt.append(skizze)

    def pt(x):
        return skizze.modelToSketchSpace(adsk.core.Point3D.create(x[0], x[1], x[2]))

    def ecke(d, laengs, quer):
        return _plus(_plus(d["p0"], d["e"], 1.0, laengs), d["u"], 1.0, quer)
    linien = skizze.sketchCurves.sketchLines
    for i, d in enumerate(daten):
        if s > 0:       # Rückversatz: von etwas ausserhalb der Kante bis s nach innen wegschneiden, an den Enden etwas länger
            x0, x1, q0, q1 = -0.05, d["L"] + 0.05, ueber, -s
        else:           # Vorversatz: Streifen der Breite |s| aussen anfügen; an Ecken zu Nachbarkanten bis in die Ecke verlängert
            x0 = -abs(s) if geteilt(d["p0"], i) else 0.0
            x1 = d["L"] + (abs(s) if geteilt(d["p1"], i) else 0.0)
            q0, q1 = -tief, -s
        a, b, c, e_ = ecke(d, x0, q0), ecke(d, x1, q0), ecke(d, x1, q1), ecke(d, x0, q1)
        l1 = linien.addByTwoPoints(pt(a), pt(b))
        l2 = linien.addByTwoPoints(l1.endSketchPoint, pt(c))
        l3 = linien.addByTwoPoints(l2.endSketchPoint, pt(e_))
        linien.addByTwoPoints(l3.endSketchPoint, l1.startSketchPoint)
    if skizze.profiles.count < 1:
        raise AdapterFehler("Der Versatz-Streifen ergab keine Fläche in der Skizze.")
    profile = adsk.core.ObjectCollection.create()
    for k in range(skizze.profiles.count):
        profile.add(skizze.profiles.item(k))
    ef = comp.features.extrudeFeatures
    vol0 = koerper.volume
    soll = abs(s) * sum(d["L"] for d in daten) * t
    feat = None
    versuche = []
    sign = _aufbau_richtung(flaeche, skizze)
    for richtung in ((None,) if s > 0 else ((sign, -sign) if sign else (1.0, -1.0))):
        try:
            if s > 0:
                ei = ef.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
                ei.setSymmetricExtent(adsk.core.ValueInput.createByReal(4 * t + 0.2), True)
            else:
                ei = ef.createInput(profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(richtung * t))
            ei.participantBodies = [koerper]
            f = ef.add(ei)
        except Exception as ex:
            versuche.append(str(ex).strip().splitlines()[-1][:120] if str(ex).strip() else type(ex).__name__)
            continue
        koerper_neu = _koerper_nach(comp, koerper, f)
        delta = (koerper_neu.volume - vol0) if koerper_neu is not None else None
        # Schnitt: Volumen sinkt um etwa den Streifen (nicht auf 0!); Anfügen: Volumen steigt um etwa den Streifen
        if delta is not None and ((s > 0 and -1.5 * soll < delta < -0.5 * soll) or (s < 0 and 0.5 * soll < delta < 1.5 * soll)):
            feat, koerper = f, koerper_neu
            break
        versuche.append("Körper nach dem Feature %s, Volumenänderung %s cm³ (erwartet %+.3f)" % (
            "nicht gefunden" if koerper_neu is None else "gefunden", "–" if delta is None else "%.3f" % delta, -soll if s > 0 else soll))
        f.deleteMe()
    if feat is None:
        raise AdapterFehler("Der Versatz konnte nicht an das Blech angefügt/abgeschnitten werden (%s)." % "; ".join(versuche))
    erzeugt.append(feat)
    # Kandidaten: Kanten der vom Feature erzeugten Flächen (so wie bei Flanschen, live bewährt), dazu alle Kanten des Körpers.
    # Bericht 31.10.: beim Zurückschneiden (+) fand sich unter den Körperkanten keine einzige parallele Kante.
    pool, gesehen = [], set()
    try:
        quellen = [k for f in feat.faces for k in f.edges] + list(koerper.edges)
    except Exception:
        quellen = list(koerper.edges)
    for k in quellen:
        try:
            schluessel = k.tempId
        except Exception:
            schluessel = id(k)
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            pool.append(k)
    try:
        logger.info("Versatz: Körper nach der Extrusion", richtung=sign, kanten=len(list(koerper.edges)), flaechen_des_features=len(list(feat.faces)),
                    volumen_cm3=koerper.volume)
    except Exception:
        logger.warnung("Versatz: Körper nach der Extrusion nicht lesbar")
    neue = []
    for nr, d in enumerate(daten, 1):
        mitte = _plus(_plus(d["p0"], d["p1"], 0.5, 0.5), d["u"], 1.0, -s)
        kandidaten = []
        for k in pool:
            try:
                q0, dk = _linie(k)
            except Exception:
                continue
            dk = _v(dk)
            if abs(abs(_skal(dk, d["e"])) - 1.0) > 1e-6 or k.length < 0.3 * d["L"]:
                continue
            w = _plus(mitte, _v(q0), 1.0, -1.0)
            if math.sqrt(_skal(_ohne_komponente(w, dk), _ohne_komponente(w, dk))) > 0.005:
                continue
            if -0.005 <= _skal(w, dk) <= k.length + 0.005:
                kandidaten.append(k)
        if len(kandidaten) != 1:
            nah = []       # Diagnose: die nächsten parallelen Kanten (Abstand von der Zielkante in mm, Länge in mm)
            for k in pool:
                try:
                    q0, dk = _linie(k)
                    dk = _v(dk)
                    if abs(abs(_skal(dk, d["e"])) - 1.0) > 1e-6:
                        continue
                    w = _plus(mitte, _v(q0), 1.0, -1.0)
                    lot = _ohne_komponente(w, dk)
                    nah.append((math.sqrt(_skal(lot, lot)) * 10, k.length * 10))
                except Exception:
                    continue
            nah.sort()
            logger.warnung("Versatz: versetzte Kante nicht gefunden", kante=nr, treffer=len(kandidaten), laenge_mm=d["L"] * 10, versatz_mm=versatz_mm,
                           naechste=" | ".join("%.2f mm weg, %.1f lang" % x for x in nah[:5]) or "keine parallele Kante", pool=len(pool))
            raise AdapterFehler("Die versetzte Kante %d wurde nicht eindeutig gefunden (%d Treffer). Nächste parallele Kante: %s." % (
                nr, len(kandidaten), "%.2f mm vom Soll entfernt" % nah[0][0] if nah else "keine"))
        neue.append(kandidaten[0])
    logger.info("Versatz angewendet", versatz_mm=versatz_mm, art="Rückversatz" if s > 0 else "Vorversatz", kanten=len(neue))
    return erzeugt, neue


def _schritt_bauen(edge, op, gespiegelt, dicke_mm=None):
    if op["typ"] == "umschlag":
        return umschlag(edge, op["laenge"], gespiegelt, op.get("radius"), op.get("lage"), dicke_mm)
    return flansch(edge, op["winkel"], op["laenge"], op.get("radius"), gespiegelt, op.get("bezug"), op.get("lage"))


def folge_anbringen(edge, ops, dicke_mm, markierung, hinweise=None, start=None):
    """Operationsfolge an EINER Kante. → Liste erzeugter Features. Bei Fehler: alles wieder entfernen und AdapterFehler.
    Hinweise (z. B. mögliche Einschnitte an runden Kanten, automatisch umgekehrte Richtungen) werden in die übergebene Liste geschrieben.
    Richtungsprüfung ab Schritt 2 (nach Fusion-Standard bei Schritt 1) – NICHT live geprüft."""
    hinweise = hinweise if hinweise is not None else []
    erzeugt = []
    aktuell = edge
    phase = "Schritt 1"
    rahmen = _kantenrahmen_quer(edge)      # (e, u) – ohne: keine Richtungsprüfung
    v = None                               # «oben»; entsteht aus dem Bau von Schritt 1 (Fusion-Standard bei Winkel +)
    lauf = 0.0                             # Laufwinkel in Grad (0 = u)
    erster = 1                             # bei start: ab diesem Schritt weiterbauen (Schritt 1 war ein gemeinsamer Flansch, siehe Gruppe)
    if start:
        erster, lauf, v, rahmen = start["i"], start["lauf"], start["v"], start["rahmen"]
    geprueft = rahmen is not None
    try:
        for i, op in enumerate(ops, 1):
            if i < erster:
                continue
            phase = "Schritt %d" % i
            token = None
            try:
                token = aktuell.entityToken
            except Exception:
                pass
            gespiegelt = op["winkel"] < 0 if i == 1 else False
            if op.get("versatz"):
                phase = "Schritt %d (Versatz)" % i
                vorbereitung, aktuell = _versatz_anwenden(aktuell, op["versatz"], dicke_mm)
                erzeugt.extend(vorbereitung)
                try:
                    token = aktuell.entityToken
                except Exception:
                    token = None
                phase = "Schritt %d" % i
            feat = _schritt_bauen(aktuell, op, gespiegelt, dicke_mm)
            erzeugt.append(feat)
            neu = None
            if i < len(ops):
                phase = "Nach Schritt %d (Kante für Schritt %d suchen)" % (i, i + 1)
                neu = neue_aussenkante(feat, aktuell, op["laenge"], dicke_mm or 1.0)
                phase = "Schritt %d" % i
            elif geprueft and i > 1:
                try:
                    neu = neue_aussenkante(feat, aktuell, op["laenge"], dicke_mm or 1.0)
                except AdapterFehler:
                    hinweise.append("Schritt %d: Richtung konnte nicht geprüft werden (neue Kante nicht eindeutig)." % i)
            gemessen = _gemessen(aktuell, neu, rahmen[0]) if (geprueft and neu is not None) else None
            if geprueft and i == 1 and gemessen is not None and abs(op["winkel"]) < 175:
                # Schritt 1 definiert «oben»: der Anteil quer zu u, mit dem Vorzeichen des Winkels
                quer = _einheit(_ohne_komponente(gemessen, rahmen[1]))
                v = tuple(x * (1 if op["winkel"] > 0 else -1) for x in quer) if quer else None
            elif geprueft and i > 1 and v is not None and gemessen is not None:
                stimmt = richtung_stimmt(lauf, op["winkel"], gemessen, rahmen[1], v)
                if stimmt is False:
                    logger.info("Richtung weicht ab – Schritt wird gespiegelt neu angelegt", schritt=i, typ=op["typ"])
                    phase = "Schritt %d (gespiegelt neu anlegen)" % i
                    erzeugt.pop()
                    feat.deleteMe()
                    aktuell = _kante_aufloesen(token, aktuell) if token else aktuell
                    feat = _schritt_bauen(aktuell, op, True, dicke_mm)
                    erzeugt.append(feat)
                    neu = neue_aussenkante(feat, aktuell, op["laenge"], dicke_mm or 1.0)
                    nochmal = richtung_stimmt(lauf, op["winkel"], _gemessen(aktuell, neu, rahmen[0]) or gemessen, rahmen[1], v)
                    if nochmal is False:
                        raise AdapterFehler("Die Richtung von Schritt %d weicht von der Vorlage ab und liess sich auch gespiegelt nicht herstellen." % i)
                    hinweise.append("Schritt %d: Richtung automatisch umgekehrt (Fusion-Standard wich von der Vorlage ab)." % i)
                elif stimmt is None:
                    hinweise.append("Schritt %d: Richtung nicht eindeutig messbar – bitte Ergebnis prüfen." % i)
            elif geprueft and i > 1 and (v is None or gemessen is None):
                hinweise.append("Schritt %d: Richtung nicht geprüft (Messung nicht möglich) – bitte Ergebnis prüfen." % i)
            lauf += op["winkel"]
            hinweise.extend(schlitze_pruefen(feat, aktuell, dicke_mm or 1.0))
            markieren(feat, dict(markierung, schritt=i))
            logger.info("Schritt erzeugt", nr=i, typ=op["typ"], winkel=op["winkel"], laenge=op["laenge"])
            if neu is not None:
                aktuell = neu
        return erzeugt
    except Exception as e:
        logger.ausnahme("Folge abgebrochen", phase=phase)
        zurueck = entfernen(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)
        if erzeugt:
            text += (" – die %d bereits erzeugten Schritte wurden wieder entfernt." % len(erzeugt) if zurueck else
                     " – ACHTUNG: die bereits erzeugten Schritte liessen sich nicht vollständig entfernen. Bitte mit Strg+Z zurücknehmen.")
        raise AdapterFehler("%s: %s" % (phase, text), rueckbau_ok=zurueck)


def gruppen_bilden(kanten, tol_cm=1e-4):
    """Zusammenhängende Kanten (gemeinsamer Eckpunkt, gleicher Körper) → Liste von Indexlisten, in Auswahlreihenfolge."""
    n = len(kanten)
    punkte = []
    for k in kanten:
        try:
            punkte.append((_v(k.startVertex.geometry), _v(k.endVertex.geometry)))
        except Exception:
            punkte.append(None)
    eltern = list(range(n))

    def wurzel(i):
        while eltern[i] != i:
            eltern[i] = eltern[eltern[i]]
            i = eltern[i]
        return i

    def koerper(k):
        try:
            return k.body.entityToken
        except Exception:
            return id(getattr(k, "body", None))
    for i in range(n):
        for j in range(i + 1, n):
            if punkte[i] and punkte[j] and koerper(kanten[i]) == koerper(kanten[j]) and any(
                    math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) < tol_cm for a in punkte[i] for b in punkte[j]):
                eltern[wurzel(i)] = wurzel(j)
    gruppen = {}
    for i in range(n):
        gruppen.setdefault(wurzel(i), []).append(i)
    return sorted(gruppen.values(), key=lambda g: g[0])


def folge_anbringen_gruppe(edges, ops, dicke_mm, markierung, hinweise=None):
    """Wie folge_anbringen für MEHRERE zusammenhängende Kanten: Schritt 1 (Flansch) als ein Feature – Fusion schneidet die Ecken auf
    Gehrung –, die weiteren Schritte je Kante. → Liste erzeugter Features. Jeder Fehler baut ALLES wieder zurück und meldet AdapterFehler
    (der Aufrufer baut dann einzeln). NICHT live geprüft."""
    hinweise = hinweise if hinweise is not None else []
    if len(edges) < 2 or ops[0]["typ"] == "umschlag":
        raise AdapterFehler("Gemeinsamer Flansch nur für mehrere Kanten und einen Flansch als ersten Schritt.")
    erzeugt = []
    phase = "Gemeinsamer Flansch (Gehrung)"
    try:
        op = ops[0]
        rahmen = [_kantenrahmen_quer(e) for e in edges]
        if op.get("versatz"):
            phase = "Versatz der gemeinsamen Kanten"
            vorbereitung, edges = _versatz_gruppe(list(edges), op["versatz"], dicke_mm)
            erzeugt.extend(vorbereitung)
            phase = "Gemeinsamer Flansch (Gehrung)"
        feat = flansch(list(edges), op["winkel"], op["laenge"], op.get("radius"), op["winkel"] < 0, op.get("bezug"), op.get("lage"))
        erzeugt.append(feat)
        markieren(feat, dict(markierung, schritt=1, kanten=len(edges)))
        logger.info("Gemeinsamer Flansch erzeugt", kanten=len(edges), winkel=op["winkel"], laenge=op["laenge"])
        if len(ops) == 1:
            return erzeugt
        phase = "Nach dem gemeinsamen Flansch (Kanten für Schritt 2 suchen)"
        neue = [neue_aussenkante(feat, e, op["laenge"], dicke_mm or 1.0) for e in edges]
        v = None
        if rahmen[0] is not None and abs(op["winkel"]) < 175:
            gemessen = _gemessen(edges[0], neue[0], rahmen[0][0])
            quer = _einheit(_ohne_komponente(gemessen, rahmen[0][1])) if gemessen is not None else None
            v = tuple(x * (1 if op["winkel"] > 0 else -1) for x in quer) if quer else None
        for nr, (e, n) in enumerate(zip(edges, neue), 1):
            phase = "Kante %d, weitere Schritte" % nr
            erzeugt.extend(folge_anbringen(n, ops, dicke_mm, markierung, hinweise,
                                           start={"i": 2, "lauf": op["winkel"], "v": v, "rahmen": rahmen[nr - 1]}))
        return erzeugt
    except Exception as e:
        logger.ausnahme("Gemeinsamer Flansch abgebrochen", phase=phase)
        zurueck = entfernen(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)
        raise AdapterFehler("%s: %s%s" % (phase, text, "" if zurueck else " – ACHTUNG: Rückbau unvollständig, bitte mit Strg+Z zurücknehmen."),
                            rueckbau_ok=zurueck)


def koerper_neu(token):
    """Körper nach dem Bauen über seinen entityToken neu holen (alte Referenzen werden in Fusion oft ungültig)."""
    try:
        t = [x for x in design().findEntityByToken(token) if x and x.isValid]
        return t[0] if len(t) == 1 else None
    except Exception:
        return None


def koerper_pruefen(body):
    """Ergebnisprüfung nach dem Bauen: gültiger, geschlossener Körper."""
    probleme = []
    try:
        if not body.isValid:
            probleme.append("Körper ist ungültig.")
        if hasattr(body, "isSolid") and not body.isSolid:
            probleme.append("Körper ist nicht geschlossen.")
    except Exception as e:
        probleme.append("Prüfung nicht möglich: %s" % e)
    return probleme


# ------------------------------------------------------------------ Abwicklung / DXF
def abwicklung(comp, stationaere_flaeche=None):
    """Bestehende Abwicklung verwenden oder neu erzeugen (Fusion-Blechfunktion). → FlatPattern"""
    fp = getattr(comp, "flatPattern", None)
    if fp:
        return fp, False
    if not hasattr(comp, "createFlatPattern"):
        raise AdapterFehler("Diese Fusion-Version kann per API keine Abwicklung erzeugen.")
    if stationaere_flaeche is None:
        raise AdapterFehler("Für die Abwicklung bitte die feststehende Fläche (Blechoberseite) wählen.")
    fp = comp.createFlatPattern(stationaere_flaeche)
    if not fp:
        raise AdapterFehler("Fusion konnte keine Abwicklung erzeugen (Körper evtl. nicht abwickelbar).")
    return fp, True


def abwicklung_masse(fp):
    """Umschliessendes Rechteck und Fläche der Abwicklung (mm, mm²). Fläche nur wenn Fusion sie liefert."""
    body = None
    for n in ("flatBody", "body"):
        body = getattr(fp, n, None)
        if body:
            break
    if body is None:
        try:
            body = fp.bodies.item(0)
        except Exception:
            body = None
    if body is None:
        raise AdapterFehler("Abwicklungskörper nicht lesbar.")
    bb = body.boundingBox
    # Die Lage der Abwicklung im Raum ist nicht garantiert (nicht zwingend XY): alle drei Ausdehnungen nehmen,
    # die kleinste ist die Blechdicke, die beiden grösseren sind Breite und Länge.
    ausdehnung = sorted(units.cm_zu_mm(abs(getattr(bb.maxPoint, a) - getattr(bb.minPoint, a))) for a in ("x", "y", "z"))
    dx, dy = ausdehnung[1], ausdehnung[2]
    flaeche = None
    try:
        # grösste ebene Fläche des flachen Körpers = Blechfläche (inkl. Ausschnitte)
        flaeche = max(f.area for f in body.faces) * 100.0
    except Exception:
        pass
    return {"breite": min(dx, dy), "laenge": max(dx, dy), "flaeche": flaeche, "quelle": "Fusion-Abwicklung (Begrenzungsrahmen)"}


def dxf_abwicklung(fp, dateipfad):
    em = design().exportManager
    if not hasattr(em, "createDXFFlatPatternExportOptions"):
        raise AdapterFehler("Diese Fusion-Version kann die Abwicklung nicht als DXF exportieren.")
    opt = em.createDXFFlatPatternExportOptions(dateipfad, fp)
    ok = em.execute(opt)
    import os
    if not ok or not os.path.exists(dateipfad) or os.path.getsize(dateipfad) == 0:
        raise AdapterFehler("Fusion hat die DXF-Datei nicht erzeugt: %s" % dateipfad)
    return dateipfad


# ------------------------------------------------------------------ Rundblech als Drehkörper
def drehkoerper(comp, kontur_mm, name):
    """Geschlossene Querschnittskontur (r, z in mm) um die Z-Achse drehen → neuer Körper (KEIN Blechkörper).
    Ohne Einschnitte; Abwicklung/Umformung beurteilt forming/forming.py."""
    sk = comp.sketches.add(comp.xZConstructionPlane)
    sk.name = name
    linien = sk.sketchCurves.sketchLines
    # Skizze auf XZ: Skizzen-x = Welt-x, Skizzen-y = −Welt-z (Fusion-Konvention); Profil liegt bei x ≥ 0
    pts = [adsk.core.Point3D.create(units.mm_zu_cm(r), -units.mm_zu_cm(z), 0) for r, z in kontur_mm]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        if a.distanceTo(b) > 1e-7:
            linien.addByTwoPoints(a, b)
    if sk.profiles.count < 1:
        raise AdapterFehler("Querschnitt des Rundblechs ist nicht geschlossen.")
    prof = max(list(sk.profiles), key=lambda p: p.areaProperties().area)
    rv = comp.features.revolveFeatures
    inp = rv.createInput(prof, comp.zConstructionAxis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.setAngleExtent(False, adsk.core.ValueInput.createByString("360 deg"))
    feat = rv.add(inp)
    if not feat or feat.bodies.count < 1:
        raise AdapterFehler("Fusion hat den Drehkörper nicht erzeugt.")
    feat.bodies.item(0).name = name
    return feat


def abwicklung_koerper(comp, zuschnitt, dicke_mm, name):
    """Flachen Körper aus einem Zuschnitt (forming.zuschnitt) erzeugen – NICHT live geprüft.

    Kontur (Skizze auf XY) um die Blechdicke NACH UNTEN extrudiert (die Oberseite liegt in der Skizzenebene); die Biegelinien kommen als zweite
    Skizze auf dieselbe Ebene und teilen die Oberseite per «Fläche teilen» – so sind sie als Kanten sichtbar und in einer Fusion-Zeichnung
    darstellbar. Klappt das Teilen nicht, bleibt die Skizze «… Biegelinien» sichtbar. → (Körper, Hinweise)."""
    P = adsk.core.Point3D.create

    def zeichnen(sk, elemente):
        kurven = []
        for e in elemente:
            if e[0] == "kreis":
                kurven.append(sk.sketchCurves.sketchCircles.addByCenterRadius(P(units.mm_zu_cm(e[1]), units.mm_zu_cm(e[2]), 0), units.mm_zu_cm(e[3])))
            elif e[0] == "bogen":
                a0 = math.radians(e[4])
                start = P(units.mm_zu_cm(e[1] + e[3] * math.cos(a0)), units.mm_zu_cm(e[2] + e[3] * math.sin(a0)), 0)
                kurven.append(sk.sketchCurves.sketchArcs.addByCenterStartSweep(P(units.mm_zu_cm(e[1]), units.mm_zu_cm(e[2]), 0), start, math.radians(e[5] - e[4])))
            else:
                kurven.append(sk.sketchCurves.sketchLines.addByTwoPoints(P(units.mm_zu_cm(e[1]), units.mm_zu_cm(e[2]), 0), P(units.mm_zu_cm(e[3]), units.mm_zu_cm(e[4]), 0)))
        return kurven
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = name + " Kontur"
    zeichnen(sk, zuschnitt["kontur"])
    if sk.profiles.count < 1:
        raise AdapterFehler("Der Zuschnitt bildet keine geschlossene Fläche – Körper nicht erzeugt.")
    prof = max(list(sk.profiles), key=lambda p: p.areaProperties().area)
    ext = comp.features.extrudeFeatures
    ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-units.mm_zu_cm(dicke_mm)))
    feat = ext.add(ei)
    if not feat or feat.bodies.count < 1:
        raise AdapterFehler("Fusion hat den Körper des Zuschnitts nicht erzeugt.")
    body = feat.bodies.item(0)
    body.name = name
    hinweise = []
    if zuschnitt["biegelinien"]:
        sk2 = comp.sketches.add(comp.xYConstructionPlane)
        sk2.name = name + " Biegelinien"
        kurven = zeichnen(sk2, zuschnitt["biegelinien"])
        try:
            oben = [f for f in body.faces if f.boundingBox.minPoint.z > -1e-6]
            if len(oben) != 1:
                raise AdapterFehler("Oberseite nicht eindeutig (%d Flächen)" % len(oben))
            flaechen = adsk.core.ObjectCollection.create()
            flaechen.add(oben[0])
            werkzeug = adsk.core.ObjectCollection.create()
            for k in kurven:
                werkzeug.add(k)
            sf = comp.features.splitFaceFeatures
            sf.add(sf.createInput(flaechen, werkzeug, False))
        except Exception as e:
            logger.ausnahme("Biegelinien teilen", fehler=e)
            hinweise.append("Die Biegelinien konnten die Oberseite nicht teilen (%s) – sie liegen als Skizze «%s» vor." % (
                str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__, sk2.name))
    return body, hinweise


# ------------------------------------------------------------------ 3D-Detailvorlagen
def komponente_exportieren(comp, dateipfad):
    em = design().exportManager
    opt = em.createFusionArchiveExportOptions(dateipfad, comp)
    import os
    if not em.execute(opt) or not os.path.exists(dateipfad):
        raise AdapterFehler("Fusion hat die Komponente nicht als .f3d exportiert.")
    return dateipfad


def benutzerparameter():
    out = []
    for p in design().userParameters:
        out.append({"name": p.name, "expression": p.expression, "unit": p.unit, "value": p.value, "comment": p.comment})
    return out


def detail_importieren(f3d, ziel_comp):
    """Fusion-Archiv in die Zielkomponente importieren → (neue Occurrence, Namen der beim Import neu entstandenen Benutzerparameter).

    Live-Test 29.10.2026 (Fusion 2706.1.17): Gibt es den Parameternamen im Dokument schon, legt Fusion beim Import eine Kopie
    mit Zusatz an (SD_H → SD_H_1). Deshalb werden nur die NEU entstandenen Parameter verändert, nie die vorhandenen."""
    im = app().importManager
    vorher = {o.entityToken for o in ziel_comp.occurrences}
    param_vorher = {p.name for p in design().userParameters}
    opt = im.createFusionArchiveImportOptions(f3d)
    if hasattr(im, "importToTarget2"):
        im.importToTarget2(opt, ziel_comp)
    elif not im.importToTarget(opt, ziel_comp):
        raise AdapterFehler("Fusion hat das Detail nicht importiert.")
    neu = [o for o in ziel_comp.occurrences if o.entityToken not in vorher]
    if len(neu) != 1:
        raise AdapterFehler("Import lieferte %d neue Komponenten (erwartet 1)." % len(neu))
    return neu[0], [p.name for p in design().userParameters if p.name not in param_vorher]


def detail_integrieren(occ, ziel_body, neue_param=()):
    """Eingesetztes Detail (Occurrence) direkt in den Zielkörper übernehmen – NICHT live geprüft.

    Ablauf: Körper der Occurrence als temporäre Kopie (Weltlage inkl. Ausrichtung) → Basis-Feature in der Komponente des
    Zielkörpers → Feature «Kombinieren» (Vereinigen) mit dem Zielkörper → leere Import-Komponente und beim Import neu
    entstandene, nicht mehr benutzte Parameter entfernen. Ergebnis: eine bearbeitbare Basis- und Kombinieren-Feature-Folge
    im Zeitverlauf, keine separate Komponente. Die Detailgeometrie selbst ist eingefroren (Masse = beim Anwenden gesetzte Werte).
    → (Kombinieren-Feature, Warnungen). Bei Fehler: alles wieder entfernen und AdapterFehler."""
    if getattr(ziel_body, "assemblyContext", None) is not None:
        raise AdapterFehler("Der Zielkörper liegt in einer Unterkomponente. Bitte die Komponente des Zielkörpers aktivieren oder "
                            "das Detail ohne Integration (eigene Komponente) einsetzen.")
    comp = ziel_body.parentComponent
    token = ziel_body.entityToken
    werkzeuge = [b for b in occ.bRepBodies]
    if not werkzeuge:
        raise AdapterFehler("Das Detail enthält keinen Körper, der sich ins Modell übernehmen liesse.")
    warnungen, erzeugt = [], []
    vol_vorher = ziel_body.volume
    try:
        tbm = adsk.fusion.TemporaryBRepManager.get()
        kopien = [tbm.copy(b) for b in werkzeuge]
        bf = comp.features.baseFeatures.add()
        erzeugt.append(bf)
        bf.startEdit()
        try:
            for k in kopien:
                comp.bRepBodies.add(k, bf)
        finally:
            bf.finishEdit()
        tools = adsk.core.ObjectCollection.create()
        for b in bf.bodies:
            tools.add(b)
        if tools.count != len(werkzeuge):
            raise AdapterFehler("Beim Übernehmen der Detailgeometrie entstanden %d statt %d Körper." % (tools.count, len(werkzeuge)))
        ci = comp.features.combineFeatures.createInput(ziel_body, tools)
        ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        ci.isKeepToolBodies = False
        try:
            cf = comp.features.combineFeatures.add(ci)
        except RuntimeError as e:
            raise AdapterFehler("Fusion konnte das Detail nicht mit dem Körper vereinigen – es berührt den Körper vermutlich nicht oder "
                                "die Geometrie überschneidet sich unzulässig (Fusion: %s)." % (str(e).strip().splitlines()[-1] if str(e).strip() else "keine Angabe"))
        erzeugt.append(cf)
        body = koerper_neu(token)
        if body is None:
            raise AdapterFehler("Zielkörper nach dem Vereinigen nicht auffindbar.")
        for p in koerper_pruefen(body):
            raise AdapterFehler("Nach dem Vereinigen: " + p)
        if abs(body.volume - vol_vorher) < 1e-9:
            raise AdapterFehler("Das Detail hat den Körper nicht verändert (kein Volumenzuwachs) – Position/Ausrichtung prüfen.")
        if ist_blech(ziel_body) and not ist_blech(body):
            warnungen.append("Der Körper ist nach dem Vereinigen kein Blechkörper mehr – Abwicklung und Blechregeln sind für ihn "
                             "womöglich nicht mehr verfügbar. Mit Strg+Z lässt sich der ganze Schritt zurücknehmen.")
        elif ist_blech(body):
            warnungen.append("Zielkörper ist ein Blechkörper: bitte Abwicklung/Biegezonen nach dem Vereinigen prüfen (nicht live geprüft).")
    except Exception as e:
        logger.ausnahme("Detail-Integration")
        zurueck = entfernen(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)
        raise AdapterFehler(text + (" – die Änderungen wurden zurückgenommen." if zurueck else
                                    " – ACHTUNG: Rückbau unvollständig, bitte mit Strg+Z zurücknehmen."), rueckbau_ok=zurueck)
    # Aufräumen erst nach Erfolg: die Kopie im Basis-Feature hängt nicht an der Import-Komponente.
    try:
        occ.deleteMe()
    except Exception:
        logger.ausnahme("Import-Komponente nicht entfernt")
        warnungen.append("Die leere Import-Komponente «%s» liess sich nicht entfernen – bitte von Hand löschen." % getattr(occ, "name", "?"))
    up = design().userParameters
    for n in neue_param:
        try:
            p = up.itemByName(n)
            if p is not None:
                p.deleteMe()   # False, solange der Parameter noch benutzt wird – dann bleibt er stehen
        except Exception:
            pass
    return cf, warnungen


def matrix_fusion(m_mm):
    """4×4 (mm) → adsk.core.Matrix3D (cm)."""
    m = adsk.core.Matrix3D.create()
    werte = []
    for i in range(4):
        for j in range(4):
            v = m_mm[i][j]
            werte.append(units.mm_zu_cm(v) if j == 3 and i < 3 else v)
    m.setWithArray(werte)
    return m


def parameter_setzen(werte_nach_fusionname):
    """Benutzerparameter setzen: {tatsächlicher Name: Ausdruck} → (gesetzt, nicht_gefunden).
    Für importierte Details vorher details.detail_validation.parameter_zuordnen() verwenden."""
    up = design().userParameters
    gesetzt, fehlend = [], []
    for name, ausdruck in werte_nach_fusionname.items():
        p = up.itemByName(name)
        if p is None:
            fehlend.append(name)
            continue
        p.expression = ausdruck
        gesetzt.append(name)
    return gesetzt, fehlend


def kollision(occ, andere_koerper):
    """Grobe Kollisionsprüfung über Begrenzungsrahmen-Überlappung (Volumenprüfung ist per API nicht zuverlässig verfügbar)."""
    try:
        a = occ.boundingBox
        out = []
        for b in andere_koerper:
            bb = b.boundingBox
            if a.intersects(bb):
                out.append(b.name)
        return out
    except Exception:
        return []


# ------------------------------------------------------------------ Teilenummern
# ------------------------------------------------------------------ Auftragsordner (Fusion-Daten) – NICHT live geprüft
def dokument_ordnerpfad():
    """Namen der Ordner vom Stamm des Projekts bis zum Ordner des aktiven Dokuments; leer, wenn es noch nicht gespeichert ist."""
    try:
        datei = adsk.core.Application.get().activeDocument.dataFile
        ordner, namen = datei.parentFolder if datei is not None else None, []
        while ordner is not None and len(namen) < 30:
            namen.insert(0, ordner.name)
            ordner = ordner.parentFolder
        return namen
    except Exception:
        logger.warnung("Ordnerpfad des Dokuments nicht lesbar")
        return []


def _unterordner(ordner, name):
    for f in ordner.dataFolders:
        if f.name == name:
            return f
    return None


def auftrag_ordner_anlegen(plan):
    """Legt Jahresordner/Auftragsordner/Unterordner im aktiven Projekt an (aus core.auftrag.plan). Vorhandene Ordner werden wiederverwendet,
    nichts wird gelöscht oder umbenannt. → (Pfadtext, Hinweise). Der Stammordner «wurzel» ist das aktive Projekt selbst oder ein Ordner darin."""
    app = adsk.core.Application.get()
    projekt = app.data.activeProject
    if projekt is None:
        raise AdapterFehler("Kein aktives Projekt in Fusion. Bitte zuerst im Datenfenster das Projekt öffnen.")
    wurzel = projekt.rootFolder
    hinweise = []
    if plan["wurzel"] and projekt.name != plan["wurzel"]:
        w = _unterordner(wurzel, plan["wurzel"])
        if w is None:
            raise AdapterFehler("Der Stammordner «%s» wurde im aktiven Projekt «%s» nicht gefunden. Bitte das richtige Projekt öffnen oder "
                                "den Stammordner in den Einstellungen anpassen." % (plan["wurzel"], projekt.name))
        wurzel = w
    ordner = wurzel
    pfad = [plan["wurzel"] or projekt.name]
    for name in plan["pfad"]:
        n = _unterordner(ordner, name)
        if n is None:
            n = ordner.dataFolders.add(name)
        elif name == plan["pfad"][-1]:
            hinweise.append("Der Auftragsordner «%s» gab es schon – vorhandene Ordner wurden weiterverwendet." % name)
        if n is None:
            raise AdapterFehler("Fusion hat den Ordner «%s» nicht angelegt." % name)
        ordner = n
        pfad.append(name)
    for u in plan["unterordner"]:
        if _unterordner(ordner, u) is None and ordner.dataFolders.add(u) is None:
            raise AdapterFehler("Fusion hat den Unterordner «%s» nicht angelegt." % u)
    logger.info("Auftragsordner angelegt", pfad="/".join(pfad), unterordner=",".join(plan["unterordner"]))
    return "/".join(pfad), hinweise


def dokument_name():
    try:
        return adsk.core.Application.get().activeDocument.name
    except Exception:
        return ""


def _ordner_rekursiv(ordner, tiefe, pfad, ausgabe):
    if tiefe < 0:
        return
    for f in ordner.dataFolders:
        ausgabe.append((f, pfad + [f.name]))
        _ordner_rekursiv(f, tiefe - 1, pfad + [f.name], ausgabe)


def _stamm_ordner(wurzel_name):
    projekt = adsk.core.Application.get().data.activeProject
    if projekt is None:
        raise AdapterFehler("Kein aktives Projekt in Fusion. Bitte zuerst im Datenfenster das Projekt öffnen.")
    wurzel = projekt.rootFolder
    if wurzel_name and projekt.name != wurzel_name:
        w = _unterordner(wurzel, wurzel_name)
        if w is None:
            raise AdapterFehler("Der Stammordner «%s» wurde im aktiven Projekt «%s» nicht gefunden." % (wurzel_name, projekt.name))
        wurzel = w
    return wurzel


def auftraege_lesen(wurzel_name, tiefe=2):
    """Vorhandene Auftragsordner («Nummer Objekt») unterhalb des Stammordners, neueste Nummer zuerst → [{'name','nummer','objekt','jahr'}].
    NICHT live geprüft."""
    from ..core import auftrag
    alle = []
    _ordner_rekursiv(_stamm_ordner(wurzel_name), tiefe, [], alle)
    out = []
    for f, pfad in alle:
        z = auftrag.aus_pfad_voll(pfad[-2:]) if auftrag.zerlegen(f.name) else None
        if z and auftrag.zerlegen(pfad[-1]):
            out.append({"name": f.name, "nummer": z[0], "objekt": z[1], "jahr": z[2]})
    out.sort(key=lambda a: (int(a["nummer"]), a["name"]), reverse=True)
    return out


def dokument_im_auftrag_speichern(wurzel_name, auftragsname, unterordner_name, tiefe=2):
    """Aktives Dokument im Unterordner (z. B. «Modelle») des Auftrags speichern. Ungespeichert: saveAs. Schon dort: nichts. Sonst eine KOPIE
    (die offene Datei lässt sich nicht verschieben). → Text. NICHT live geprüft."""
    alle = []
    _ordner_rekursiv(_stamm_ordner(wurzel_name), tiefe, [], alle)
    ziel = next((f for f, pfad in alle if f.name == auftragsname), None)
    if ziel is None:
        raise AdapterFehler("Der Auftragsordner «%s» wurde nicht gefunden." % auftragsname)
    sub = _unterordner(ziel, unterordner_name) or ziel.dataFolders.add(unterordner_name)
    doc = adsk.core.Application.get().activeDocument
    datei = doc.dataFile
    if datei is not None and datei.parentFolder is not None and datei.parentFolder.id == sub.id:
        return "Das Dokument liegt schon im Ordner «%s»." % unterordner_name
    if not doc.saveAs(doc.name, sub, "", ""):
        raise AdapterFehler("Fusion hat das Dokument nicht gespeichert.")
    return ("Das Dokument wurde im Ordner «%s» gespeichert." % unterordner_name) if datei is None else (
        "Eine Kopie wurde im Ordner «%s» gespeichert (die bisherige Datei bleibt, wo sie war)." % unterordner_name)


def teilnummer(body, vergeben=True):
    """Teilenummer eines Körpers (Attribut am nativen Körper). Fehlt sie und vergeben=True: nächste freie Nummer im Dokument."""
    body = body.nativeObject or body
    a = body.attributes.itemByName(ATTR_GRUPPE, "teilnummer")
    if a:
        return int(a.value)
    if not vergeben:
        return None
    vorhanden = []
    for x in design().findAttributes(ATTR_GRUPPE, "teilnummer"):
        try:
            vorhanden.append(int(x.value))
        except (TypeError, ValueError):
            pass
    nr = max(vorhanden or [0]) + 1
    body.attributes.add(ATTR_GRUPPE, "teilnummer", str(nr))
    return nr

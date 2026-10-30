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
            if abs(k.length - L0) > max(0.05, 0.02 * L0):   # Flansch über ganze Kantenlänge
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


def flansch(edge, winkel, laenge_mm, radius_mm=None, gespiegelt=None):
    """Kantenflansch über die ganze Kantenlänge. Winkel + zur Sichtseite, − nach hinten.

    Echte API (help.autodesk.com, EdgeFlangeInput, Preview, ab Oktober 2026): createEdgeFlangeInput(edges, distance) nimmt NUR gerade
    Aussenkanten; Eigenschaften angle (ValueInput), isFlipped, bendRadiusOverride.setOverride(ValueInput). NICHT live geprüft."""
    if _kurventyp(edge) != "linie":
        raise AdapterFehler("Der Fusion-Flansch (EdgeFlange-API) arbeitet nur an geraden Kanten, nicht an Kreisen/Bögen – "
                            "laut Autodesk-Dokumentation «linear edges on the outside of a sheet metal body». Für runde Ränder bleibt der Umschlag (Saum) "
                            "oder das Rundblech-Werkzeug.")
    comp = edge.body.parentComponent
    ff = _flange_features(comp)
    inp = ff.createEdgeFlangeInput([edge], _vi_mm(laenge_mm))
    if inp is None:
        raise AdapterFehler("Fusion konnte die Flansch-Eingabe nicht anlegen (Kante ungeeignet?).")
    logger.info("EdgeFlangeInput", eigenschaften=_namen(inp))
    w = abs(winkel)
    gesetzt = setze(inp, ["angle", "flangeAngle", "setAngle", "setFlangeAngle"], _vi_grad(w))
    if not gesetzt and abs(w - 90) > 1e-6:
        raise AdapterFehler("Der Flanschwinkel %g° lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % w)
    if gespiegelt is None:
        gespiegelt = winkel < 0
    if gespiegelt:
        if not setze(inp, ["isFlipped", "isDirectionFlipped", "flipDirection", "isFlangeFlipped"], True):
            raise AdapterFehler("Die Flanschrichtung (nach hinten) lässt sich nicht einstellen – abgebrochen.")
    if radius_mm is not None:
        ov = getattr(inp, "bendRadiusOverride", None)
        try:
            ok = bool(ov is not None and ov.setOverride(_vi_mm(radius_mm)))
        except Exception as e:
            logger.warnung("Biegeradius-Override fehlgeschlagen", fehler=e)
            ok = False
        if not ok:
            raise AdapterFehler("Der Biegeradius lässt sich nicht einstellen – abgebrochen (Radius wird nicht stillschweigend ignoriert).")
    feat = ff.add(inp)
    if feat is None:
        raise AdapterFehler("Fusion hat den Flansch nicht erzeugt.")
    return feat


def umschlag(edge, laenge_mm, nach_hinten, radius_mm=None):
    """Umschlag/Saum 180° mit dem Saum-Werkzeug von Fusion.

    Echte API (help.autodesk.com, HemFeatureInput, ab September 2025): hf.createHemFeatureInput() ohne Argumente, danach
    setFlatHem(edge, length, isFlipped, bendPositionType) bzw. – mit Spalt – setOpenHem(edge, length, gap, isFlipped, bendPositionType);
    beide liefern True bei Erfolg. Ohne Radius: geschlossener Saum (Spalt 0); mit Radius: offener Saum mit Spalt = 2 × Radius (Annahme).
    NICHT live geprüft."""
    comp = edge.body.parentComponent
    hf = getattr(comp.features, "hemFeatures", None)
    if hf is None or not hasattr(hf, "createHemFeatureInput"):
        raise AdapterFehler("Diese Fusion-Version hat kein Saum-Werkzeug in der API (hemFeatures).")
    inp = hf.createHemFeatureInput()
    if inp is None:
        raise AdapterFehler("Fusion konnte die Saum-Eingabe nicht anlegen.")
    logger.info("HemFeatureInput", eigenschaften=_namen(inp))
    bp = adsk.fusion.BendPositionTypes.StartEdgeBendPositionType
    L = _vi_mm(laenge_mm)
    try:
        if radius_mm is None:
            ok = inp.setFlatHem(edge, L, bool(nach_hinten), bp)
        else:
            ok = inp.setOpenHem(edge, L, _vi_mm(2 * radius_mm), bool(nach_hinten), bp)
    except Exception as e:
        raise AdapterFehler("Der Umschlag lässt sich so nicht definieren: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__))
    if not ok:
        raise AdapterFehler("Fusion hat die Umschlag-Definition abgelehnt (Kante/Länge ungeeignet).")
    feat = hf.add(inp)
    if feat is None:
        raise AdapterFehler("Fusion hat den Umschlag nicht erzeugt.")
    return feat


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


def _schritt_bauen(edge, op, gespiegelt):
    if op["typ"] == "umschlag":
        return umschlag(edge, op["laenge"], gespiegelt, op.get("radius"))
    return flansch(edge, op["winkel"], op["laenge"], op.get("radius"), gespiegelt)


def folge_anbringen(edge, ops, dicke_mm, markierung, hinweise=None):
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
    geprueft = rahmen is not None
    try:
        for i, op in enumerate(ops, 1):
            phase = "Schritt %d" % i
            token = None
            try:
                token = aktuell.entityToken
            except Exception:
                pass
            gespiegelt = op["winkel"] < 0 if i == 1 else False
            feat = _schritt_bauen(aktuell, op, gespiegelt)
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
                    feat = _schritt_bauen(aktuell, op, True)
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

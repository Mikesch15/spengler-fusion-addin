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


LETZTE_FLANSCH_EINGABE = {}      # Diagnose für den Live-Test: zuletzt an der EdgeFlangeInput zurückgelesene Werte


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
    try:
        n_flaechen = edge.faces.count
    except Exception:
        n_flaechen = None                      # nicht lesbar → kante_eignung lehnt ab («grenzt an None Flächen»)
    d = {"ref": edge, "text": "Kante %d" % nr, "kurve": _kurventyp(edge), "laenge": units.cm_zu_mm(edge.length),
         "flaechen": n_flaechen, "blech": ist_blech(body), "dicke": t, "frei": None}
    # Aussenkante: eine angrenzende Fläche ist die schmale Stirnfläche (Breite ≈ Blechdicke)
    try:
        if t and n_flaechen == 2 and d["laenge"] > 0:
            breiten = [units.cm_zu_mm(f.area / edge.length) for f in edge.faces]
            d["frei"] = any(abs(b - t) < max(0.02, 0.05 * t) for b in breiten)
    except Exception:
        d["frei"] = None
    try:
        d["start"] = _punkt_mm(edge.startVertex.geometry)
        d["ende"] = _punkt_mm(edge.endVertex.geometry)
    except Exception:
        pass
    d["profilteil"] = profil_attribut(body) is not None
    # Flächentyp der Bezugsfläche (grösste angrenzende) für die Unterstützungsmatrix. Nicht lesbar → «unbekannt» (NIE «eben»), mit Diagnose.
    d["flaeche"], d["flaeche_diagnose"] = flaechentyp_kante(edge)
    return d


def flaechentyp_kante(edge):
    """→ (Flächentyp der Bezugsfläche, Diagnose oder None). Jeder Lesefehler ergibt «unbekannt» mit Grund – nie einen stillen Standardwert."""
    try:
        faces = list(edge.faces)
    except Exception as e:
        logger.warnung("Flächen der Kante nicht lesbar", fehler=e)
        return "unbekannt", "angrenzende Flächen nicht lesbar (%s)" % ((str(e).strip().splitlines() or [type(e).__name__])[-1][:80])
    if not faces:
        return "unbekannt", "keine angrenzende Fläche"
    try:
        f = max(faces, key=lambda x: x.area)
    except Exception as e:
        logger.warnung("Flächengrösse nicht lesbar", fehler=e)
        return "unbekannt", "Flächengrösse nicht lesbar (%s)" % ((str(e).strip().splitlines() or [type(e).__name__])[-1][:80])
    typ = flaechentyp(f)
    return typ, (None if typ != "unbekannt" else "Flächentyp von Fusion nicht erkannt/nicht lesbar")


def flaechennormale(face, punkt=None):
    p = punkt or face.pointOnFace
    ok, n = face.evaluator.getNormalAtPoint(p)
    if not ok:
        raise AdapterFehler("Flächennormale nicht bestimmbar.")
    return [n.x, n.y, n.z]


def kantenrahmen(edge, face=None):
    """Lokales Koordinatensystem an einer Kante (mm): Ursprung Kantenanfang, x entlang Kante, z = Normale der Bezugsfläche AM KANTENANFANG
    (früher an einem beliebigen Flächenpunkt – auf Zylinder/Kegel falsch). Gekrümmte Kante: x = Tangente am Kantenanfang (Detail starr tangential).
    Nicht live geprüft für gekrümmte Kanten/Flächen."""
    from ..details.frames import rahmen_aus_kante, rahmen_aus_normale
    edge = adsk.fusion.BRepEdge.cast(edge)
    if face is None:
        # Bezugsfläche: die grössere angrenzende Fläche (Blechfläche, nicht Stirnfläche)
        face = max(list(edge.faces), key=lambda f: f.area)
    start = edge.startVertex.geometry
    n = flaechennormale(face, start)
    if _kurventyp(edge) == "linie":
        return rahmen_aus_kante(_punkt_mm(start), _punkt_mm(edge.endVertex.geometry), n)
    return rahmen_aus_normale(_punkt_mm(start), n, _kantentangente(edge, start))


FLAECHENTYP_FUSION = {"PlaneSurfaceType": "eben", "CylinderSurfaceType": "zylinder", "ConeSurfaceType": "kegel", "SphereSurfaceType": "kugel",
                      "TorusSurfaceType": "torus", "NurbsSurfaceType": "freiform", "EllipticalCylinderSurfaceType": "einfach_gekruemmt",
                      "EllipticalConeSurfaceType": "einfach_gekruemmt"}


def bezugsflaeche(edge):
    """Angrenzende Blechfläche einer Kante (die grösste) oder None (nicht lesbar – Aufrufer behandeln das als «unbekannt»)."""
    try:
        faces = list(edge.faces)
        return max(faces, key=lambda f: f.area) if faces else None
    except Exception as e:
        logger.warnung("Bezugsfläche nicht lesbar", fehler=e)
        return None


def matrix_sperre(op, edges, prototyp_erlaubt=False):
    """VOR dem Erzeugen eines Features: Kantentyp und angrenzender Flächentyp jeder Kante gegen core/unterstuetzung prüfen. Wirft AdapterFehler
    (nichts wurde gebaut). Unbekannte Flächen gelten nie als eben. → Liste der Hinweise (Einschränkungen)."""
    from ..core import unterstuetzung as u
    hinweise = []
    for nr, e in enumerate(edges if isinstance(edges, (list, tuple)) else [edges], 1):
        f = bezugsflaeche(e)
        fk = u.flaechenklasse(flaechentyp(f) if f is not None else "unbekannt")
        kt = u.kantentyp(_kurventyp(e))
        grund = u.pruefen(op, fk, kt, prototyp_erlaubt)
        if grund:
            raise AdapterFehler(("Kante %d: " % nr if len(edges if isinstance(edges, (list, tuple)) else [edges]) > 1 else "") + grund)
        h = u.hinweis(op, fk, kt)
        if h and h not in hinweise:
            hinweise.append(h)
    return hinweise


def flaechentyp(face):
    """Fusion-Flächentyp → Typ der Geometrie-Referenz (eben, zylinder, kegel, einfach_gekruemmt, kugel, torus, freiform, unbekannt).
    Elliptische Zylinder/Kegel sind abwickelbar (einfach gekrümmt). Nicht lesbar → «unbekannt» (wird nie wie eben behandelt)."""
    if face is None:
        return "unbekannt"
    try:
        t = face.geometry.surfaceType
        for name, typ in FLAECHENTYP_FUSION.items():
            if t == getattr(adsk.core.SurfaceTypes, name):
                return typ
        logger.warnung("Unbekannter Fusion-Flächentyp", typ=t)
    except Exception as e:
        logger.warnung("Flächentyp nicht lesbar", fehler=e)
    return "unbekannt"


def _kantentangente(edge, punkt):
    ev = edge.evaluator
    ok, par = ev.getParameterAtPoint(punkt)
    if not ok:
        raise AdapterFehler("Kantentangente nicht bestimmbar.")
    ok, t = ev.getTangent(par)
    if not ok:
        raise AdapterFehler("Kantentangente nicht bestimmbar.")
    return [t.x, t.y, t.z]


def _kruemmung(face, punkt):
    """Hauptkrümmungen (1/mm) am Punkt über SurfaceEvaluator.getCurvature → {'k1','k2'} oder None. Nicht live geprüft."""
    try:
        ev = face.evaluator
        ok, par = ev.getParameterAtPoint(punkt)
        if not ok:
            return None
        ok, _richtung, k_max, k_min = ev.getCurvature(par)
        if not ok:
            return None
        return {"k1": k_max / 10.0, "k2": k_min / 10.0}       # 1/cm → 1/mm
    except Exception:
        return None


def rahmen_entlang(edge, face=None, n=5):
    """Lokale Rahmen (mm) an n Punkten von Kantenanfang bis -ende: Normale der Fläche AM JEWEILIGEN Punkt, Tangente der Kante dort. Grundlage, um eine
    Bearbeitung entlang der GANZEN Kante zu prüfen (nicht nur am Anfang). Nicht live geprüft (CurveEvaluator.getParameterExtents/getPointAtParameter)."""
    from ..details.frames import rahmen_aus_normale
    face = face or bezugsflaeche(edge)
    if face is None:
        raise AdapterFehler("Für die Kante gibt es keine Bezugsfläche.")
    ev = edge.evaluator
    ok, t0, t1 = ev.getParameterExtents()
    if not ok:
        raise AdapterFehler("Parameterbereich der Kante nicht lesbar.")
    rahmen = []
    for i in range(n):
        par = t0 + (t1 - t0) * i / (n - 1.0)
        ok, p = ev.getPointAtParameter(par)
        ok2, t = ev.getTangent(par)
        if not (ok and ok2):
            raise AdapterFehler("Kantenpunkt %d nicht auswertbar." % (i + 1))
        rahmen.append(rahmen_aus_normale(_punkt_mm(p), flaechennormale(face, p), [t.x, t.y, t.z]))
    return rahmen


def referenz_aus_fusion(face=None, edge=None, punkt=None, seite=1):
    """Zentrale Geometrie-Referenz (core/geometrie_referenz) aus einer Fusion-Auswahl: Fläche und/oder Kante, Ankerpunkt (Point3D in cm; Standard
    Kantenanfang bzw. Flächenpunkt). Normale und Tangente werden AM ANKERPUNKT gelesen, Krümmung über den Flächen-Evaluator.
    → dict. Nicht live geprüft (BRepFace.evaluator, getCurvature, getFirstDerivative)."""
    from ..core import geometrie_referenz as gr
    if face is None and edge is None:
        raise AdapterFehler("Für die Referenz bitte eine Fläche oder Kante wählen.")
    if face is None:
        face = max(list(edge.faces), key=lambda f: f.area)
    if punkt is None:
        punkt = edge.startVertex.geometry if edge is not None else face.pointOnFace
    n = flaechennormale(face, punkt)
    if edge is not None:
        tangente = _kantentangente(edge, punkt)
    else:
        try:
            ev = face.evaluator
            ok, par = ev.getParameterAtPoint(punkt)
            ok2, du, _dv = ev.getFirstDerivative(par)
            tangente = [du.x, du.y, du.z] if ok and ok2 else None
        except Exception:
            tangente = None
    body = face.body
    kennung = {"flaeche": getattr(face, "entityToken", None), "flaeche_mm2": face.area * 100.0}
    if edge is not None:
        kennung.update(kante=getattr(edge, "entityToken", None), kante_mm=edge.length * 10.0)
    regel = None
    try:
        r = body.parentComponent.activeSheetMetalRule
        regel = r.name if r else None
    except Exception:
        pass
    return gr.referenz(flaechentyp(face), _punkt_mm(punkt), n, tangente, _kurventyp(edge) if edge is not None else None, _kruemmung(face, punkt),
                       seite, blechdicke_mm(body) if ist_blech(body) else None, regel, kennung)


# ------------------------------------------------------------------ Neue Aussenkante bestimmen
class _Abbild(object):
    """Unveränderliches Abbild einer Kante VOR dem Bau: Geometrie (transiente Kopie, bleibt gültig) und Länge. Live 0.4.62: mit Biegung «innen»
    schneidet Fusion das Grundblech zurück, die Kante selbst wird ungültig – alle Zugriffe NACH dem Bau laufen über dieses Abbild. Nicht live geprüft."""
    def __init__(self, edge):
        self.geometry = edge.geometry
        self.length = edge.length


def _abbild(edge):
    return edge if isinstance(edge, _Abbild) else _Abbild(edge)


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


def flansch(edge, winkel, laenge_mm, radius_mm=None, gespiegelt=None, bezug=None, lage=None, fusion_fragen=False):
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
    rund = any(_kurventyp(k) != "linie" for k in kanten)
    if not fusion_fragen:           # fusion_fragen=True nur im Live-Test: Fusions echte Antwort erheben bzw. Prototypen ausführen
        matrix_sperre("flansch" if len(kanten) == 1 else "mehrkant_gehrung", kanten)
    try:
        inp = ff.createEdgeFlangeInput(kanten, _vi_mm(laenge_mm))
    except Exception as e:
        raise AdapterFehler(_flansch_ablehnung(rund, e))
    if inp is None:
        raise AdapterFehler(_flansch_ablehnung(rund, None))
    _eigenschaften_einmal("EdgeFlangeInput", inp)
    for ecke in ("twoBendCornerOverride", "threeBendCornerOverride"):       # Eckenbehandlung (Gehrung) – nur die Möglichkeiten protokollieren
        try:
            _eigenschaften_einmal("EdgeFlange." + ecke, getattr(inp, ecke))
        except Exception:
            pass
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
        try:
            LETZTE_FLANSCH_EINGABE["isMiteredCorners"] = getattr(inp, "isMiteredCorners", None)   # an der EINGABE zurückgelesen (Feature gibt es nicht her)
        except Exception:
            LETZTE_FLANSCH_EINGABE["isMiteredCorners"] = None
    # Aussenmass (Anwender 6. 11. 2026): ohne Angabe Höhe AUSSEN gemessen. Biegung «innen» (Teil aussen so gross wie das Grundblech) ist noch
    # zurückgestellt – siehe STANDARD_LAGE. Vorlagen mit eigener Lage/Bezug behalten diese.
    bezug = bezug or STANDARD_BEZUG
    lage = lage or STANDARD_LAGE
    if bezug:
        if not setze(inp, ["heightDatumType"], getattr(adsk.fusion.FlangeHeightDatumTypes, BEZUEGE[bezug])):
            raise AdapterFehler("Der Massbezug «%s» lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % bezug)
    if lage:
        if not setze(inp, ["bendPositionType"], _lage_enum(lage)):
            raise AdapterFehler("Die Lage «%s» lässt sich in dieser Fusion-Version nicht einstellen – abgebrochen." % lage)
    if radius_mm is not None and radius_mm < 0:
        raise AdapterFehler("Der Biegeradius %g mm ist ungültig (negativ) – abgebrochen." % radius_mm)
    if radius_mm is not None:
        ov = getattr(inp, "bendRadiusOverride", None)
        try:
            ok = bool(ov is not None and ov.setOverride(_vi_mm(radius_mm)))
            logger.info("Biegeradius der Vorlage gesetzt", radius_mm=radius_mm, angenommen=ok, aktiv=getattr(ov, "isOverridden", None))
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


# AUSSENMASS (Anwender 6. 11. 2026): Höhe aussen + Biegung INNEN. Live 0.4.62: mit Biegung innen schneidet Fusion das Grundblech zurück, die gewählte
# Kante wird ungültig («InternalValidationError : thisASMEdge») – deshalb in 0.4.63 zurückgenommen. Seit 0.4.66 laufen alle Zugriffe NACH dem Bau
# über ein Abbild der Kante, das VOR dem Bau gemacht wurde (_Abbild; Einzelkante, Gruppe, Live-Test). NICHT live geprüft.
STANDARD_BEZUG, STANDARD_LAGE = "aussen", "innen"


def _lage_enum(lage):
    return getattr(adsk.fusion.BendPositionTypes, LAGEN[lage])


def _kantenlaenge_mm(edge):
    try:
        return "%.1f" % (edge.length * 10.0)
    except Exception:
        return "?"


def umschlag(edge, laenge_mm, nach_hinten, radius_mm=None, lage=None, dicke_mm=None, nur_erste_bauart=False, fusion_fragen=False):
    """Umschlag/Saum 180° mit dem Saum-Werkzeug von Fusion.

    Echte API (help.autodesk.com, HemFeatureInput, ab September 2025): hf.createHemFeatureInput() ohne Argumente, danach
    setFlatHem(edge, length, isFlipped, bendPositionType) bzw. – mit Spalt – setOpenHem(edge, length, gap, isFlipped, bendPositionType);
    beide liefern True bei Erfolg. Ohne Radius: geschlossener Saum (Spalt 0); mit Radius: offener Saum mit Spalt = 2 × Radius (Annahme).
    Live-Test 30.10.: Fusion nahm die Definition an, die Berechnung scheiterte («Failed to create Hem … SM_MODELING_ERROR») – welche
    Kombination aus Biegelage und Richtung passt, hängt vom Körper ab. Ohne ausdrückliche Lage werden deshalb nacheinander Kante/innen/
    aussen/tangential und dann die Gegenrichtung versucht; die erste, die Fusion rechnet, gilt (im Protokoll vermerkt). NICHT live bestätigt."""
    # Live-Test 30.10.: mit Radius (offener Saum, Spalt 2 × Radius) scheiterte Fusion, ohne Radius (geschlossener Saum) klappt es.
    # Der Radius des Umschlags kommt deshalb aus der Blechregel; ein Radius in der Vorlage wird hier bewusst nicht verwendet.
    if isinstance(edge, (list, tuple)):
        if len(edge) != 1:
            raise AdapterFehler("Ein Saum-Feature nimmt genau EINE Kante (setFlatHem/setOpenHem(edge, …) laut Autodesk-Doku) – mehrere Kanten baut "
                                "_umschlag_gruppe je Kante.")
        edge = edge[0]
    # Live 31.10.: setFlatHem/setOpenHem nehmen nur EINE Kante. Mehrfaches Aufrufen derselben Eingabe mit weiteren Kanten ist nicht dokumentiert
    # und wird deshalb nicht mehr gemacht.
    if not fusion_fragen:
        matrix_sperre("umschlag", [edge])
    t_min = dicke_mm or blechdicke_mm(edge.body)
    if t_min and laenge_mm < 2.0 * t_min:
        raise AdapterFehler("Umschlag %.1f mm ist zu kurz: mindestens 2 × Blechdicke (%.1f mm), sonst entsteht keine zweite Materiallage." % (laenge_mm, 2.0 * t_min))
    if radius_mm is not None and radius_mm < 0:
        raise AdapterFehler("Der Abstand/Radius des Umschlags darf nicht negativ sein.")
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
    # Live 31.10. (0.4.21): Gerechnet wurde immer nur «offen, Spalt = Blechdicke», alle 16 Versuche davor (geschlossen, Radien) scheiterten –
    # wie im Fusion-Dialog («Typ Offen, Abstand 1 mm»). Deshalb zuerst der offene Saum, die anderen nur als Rückfall.
    bauarten = [("Regel", None, None)]
    if t:
        bauarten = [("offen, Spalt %.2f" % t, None, t), ("Regel", None, None), ("Radius %.2f" % t, t, None), ("Radius %.2f" % (t / 2.0), t / 2.0, None)]
    if radius_mm:       # «Radius» der Vorlage = «Abstand» im Fusion-Dialog «Falz» (Typ Offen): offener Saum mit diesem Abstand zuerst, dann die übrigen
        bauarten.insert(0, ("offen, Abstand %.2f" % radius_mm, None, radius_mm))
    if nur_erste_bauart:
        bauarten = bauarten[:1]
    versuche = []
    try:
        token = edge.entityToken
    except Exception:
        token = None
    kante_cm = edge.length
    t_kontrolle = t or blechdicke_mm(edge.body) or 1.0
    for art, rad, spalt in bauarten:
        for flip in richtungen:
            for l in lagen:
                if token:
                    edge = _kante_aufloesen(token, edge)     # nach einem verworfenen Versuch kann die alte Referenz ungültig sein
                vol0, n0 = _comp_volumen(comp), _koerperzahl(comp)
                inp = hf.createHemFeatureInput()
                if inp is None:
                    raise AdapterFehler("Fusion konnte die Saum-Eingabe nicht anlegen.")
                _eigenschaften_einmal("HemFeatureInput", inp)
                for ecke in ("twoBendCornerOverride", "threeBendCornerOverride", "bendReliefOverride"):
                    try:
                        _eigenschaften_einmal("Hem." + ecke, getattr(inp, ecke))
                    except Exception:
                        pass
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
                # Ergebnis kontrollieren statt «erste angenommene Variante gilt»: zweite Materiallage (Volumenzuwachs ≈ Kante × Saumlänge × Dicke),
                # gültiger geschlossener Körper, kein zusätzlicher Körper. Sonst Variante verwerfen und die nächste versuchen.
                schlecht = umschlag_kontrolle(comp, vol0, n0, kante_cm, laenge_mm, t_kontrolle)
                if schlecht:
                    versuche.append("%s: Geometrie verworfen (%s)" % (name, "; ".join(schlecht)))
                    p_ = _loeschen(feat)
                    if p_:
                        raise AdapterFehler("Ein verworfener Umschlag liess sich nicht entfernen: " + p_)
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


def _objektname(o):
    t = type(o).__name__
    try:
        n = o.name
        return "%s «%s»" % (t, n) if n else t
    except Exception:
        return t


ABWICKLUNG_BESCHAEDIGT = ("Die Abwicklung der Komponente «%s» ist in Fusion nicht mehr zugänglich (Fusion: «InternalValidationError : res») – "
                         "vermutlich durch das Löschen einer Prüf-Abwicklung in Spengler 0.4.50–0.4.56. Abhilfe: im Browser unter der Komponente "
                         "die «Abwicklung» löschen (Rechtsklick → Löschen) oder das Dokument ohne Speichern schliessen und eine frühere Version öffnen.")


def _flatpattern_lesen(comp):
    """→ (Abwicklung oder None, lesbar). Live 0.4.54: Nach dem Löschen der Abwicklung wirft Component.flatPattern «InternalValidationError : res»
    statt None zu liefern – das gilt als «keine Abwicklung»; ob das gelöschte Objekt wirklich ungültig ist, prüft _loeschen separat."""
    try:
        return comp.flatPattern, True
    except Exception as e:
        logger.info("Component.flatPattern nicht lesbar", fusion=(str(e).strip().splitlines() or ["?"])[-1])
        return None, False


def _ist_regel(o):
    return type(o).__name__ == "SheetMetalRule" or (hasattr(o, "thickness") and hasattr(o, "kFactor"))


def _regel_in_design(name):
    """True/False: Regel dieses Namens steht in den Design-Blechregeln; None: nicht lesbar. Nicht live geprüft."""
    try:
        r = design().designSheetMetalRules
        return any(r.item(i).name == name for i in range(r.count))
    except Exception:
        return None


def _regel_verwendet(o):
    try:
        return " (Regel wird noch verwendet)" if getattr(o, "isUsed", False) else ""
    except Exception:
        return ""


def _loeschen(o):
    """Ein Fusion-Objekt löschen und das Ergebnis PRÜFEN. → None = weg (oder war schon weg), sonst Problemtext mit Objektname/-typ.
    deleteMe() → False gilt als Fehlschlag (nicht als Erfolg); ein Objekt, das danach noch gültig ist, ebenso. Nicht live geprüft."""
    if o is None:
        return None
    try:
        if not o.isValid:
            return None                       # schon weg (z. B. als abhängiges Objekt mitgelöscht)
    except Exception:
        pass
    name = _objektname(o)
    regel = _ist_regel(o)
    try:
        regel_name = o.name if regel else None
    except Exception:
        regel_name = None
    try:
        r = o.deleteMe()
    except Exception as e:
        return "%s: Löschen fehlgeschlagen (%s)%s" % (name, (str(e).strip().splitlines() or [type(e).__name__])[-1][:120], _regel_verwendet(o) if regel else "")
    if regel and regel_name:
        # Blechregeln: Nachweis über die Liste der Design-Regeln (isValid allein ist bei Regeln nicht belastbar) – siehe Rückbau-Analyse 0.4.59
        da = _regel_in_design(regel_name)
        if da is False:
            if r is False:
                logger.info("Blechregel: deleteMe() meldete False, die Regel fehlt aber in den Design-Regeln – gilt als entfernt", regel=regel_name)
            return None
        if da is True:
            return "%s: nach dem Löschen noch in den Design-Regeln%s%s" % (name, " (deleteMe() meldet False)" if r is False else "", _regel_verwendet(o))
    if r is False:
        return "%s: deleteMe() meldet False (nicht gelöscht)" % name
    try:
        if o.isValid:
            return "%s: nach dem Löschen noch vorhanden" % name
    except Exception:
        pass
    return None


def entfernen_bericht(objekte):
    """Erzeugte Objekte in UMGEKEHRTER Erstellungsreihenfolge löschen (abhängige zuerst). → Liste der Probleme (leer = alles entfernt)."""
    probleme = [p for p in (_loeschen(o) for o in reversed(list(objekte or []))) if p]
    if probleme:
        logger.warnung("Rückbau unvollständig", objekte=" | ".join(probleme))
    return probleme


def entfernen(objekte):
    """Kontrollierte Wiederherstellung: erzeugte Objekte in umgekehrter Reihenfolge löschen. → True nur, wenn ALLE nachweislich entfernt sind."""
    return not entfernen_bericht(objekte)


class Rueckbau(object):
    """Transaktion für mehrstufige Geometrieoperationen: jedes neu erzeugte Fusion-Objekt sofort mit merke() registrieren; bei einem Fehler
    löscht zurueck() GENAU diese Objekte (umgekehrte Reihenfolge, deleteMe-Ergebnis geprüft) – bestehende Modellobjekte werden nie angefasst."""

    def __init__(self, was):
        self.was, self.objekte, self.probleme = was, [], []

    def merke(self, obj):
        if obj is not None:
            self.objekte.append(obj)
        return obj

    def zurueck(self):
        self.probleme = entfernen_bericht(self.objekte)
        self.objekte = []
        return not self.probleme

    def abbrechen(self, fehler):
        """Zurückbauen und AdapterFehler mit klarer Aussage zum Rückbau werfen."""
        anzahl = len(self.objekte)
        ok = self.zurueck()
        text = str(fehler) if isinstance(fehler, AdapterFehler) else "Fusion meldet: %s" % ((str(fehler).strip().splitlines() or [type(fehler).__name__])[-1])
        if anzahl:
            text += (" – die %d dabei erzeugten Objekte wurden wieder entfernt." % anzahl if ok else
                     " – ACHTUNG: Rückbau unvollständig (%s). Bitte mit Strg+Z zurücknehmen." % "; ".join(self.probleme))
        raise AdapterFehler("%s: %s" % (self.was, text), rueckbau_ok=ok)


# Nur für den Live-Test: an diesen Stellen absichtlich einen Fehler auslösen, um den Rückbau in Fusion zu prüfen (sonst leer).
TESTFEHLER = set()


def testfehler_text(stelle):
    return "Absichtlich ausgelöster Testfehler (%s)" % stelle


def _testfehler(stelle):
    if stelle in TESTFEHLER:
        raise AdapterFehler(testfehler_text(stelle))


testfehler = _testfehler


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
def _koerper_nach(comp, vorher, feature, erwartet=None, tol=0.0):
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
    # Bericht 31.10.: nach dem Schnitt waren Token, Name und Feature-Körper unbrauchbar – dann der Körper des Bauteils, dessen Volumen am
    # besten zum erwarteten passt.
    if erwartet is not None:
        besten, abstand = None, None
        try:
            for b in comp.bRepBodies:
                try:
                    a = abs(b.volume - erwartet)
                except Exception:
                    continue
                if b.volume > 1e-9 and (abstand is None or a < abstand):
                    besten, abstand = b, a
        except Exception:
            pass
        if besten is not None and abstand is not None and abstand < tol:
            logger.info("Körper nach dem Feature über das Volumen gefunden", name=getattr(besten, "name", "?"))
            return besten
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


_VERSATZ_ALT = {}      # entityToken der versetzten Kante → [entityToken der Kanten auf der Stirnfläche (anderes Niveau)] – Ersatz, falls Fusion die Kante ablehnt


def _kante_sonde(edge, text=""):
    """Diagnose für das Protokoll: Flächen der Kante, Blech-Eigenschaft, und ob Fusion für diese Kante überhaupt eine Flansch-Eingabe anlegt
    (createEdgeFlangeInput). Verändert nichts. Nicht live geprüft."""
    info = {}
    try:
        info["flaechen"] = " | ".join("%s %.3f cm²" % (type(f.geometry).__name__, f.area) for f in edge.faces)
    except Exception as ex:
        info["flaechen"] = "nicht lesbar (%s)" % ex
    try:
        info["blech"] = getattr(edge.body, "isSheetMetal", None)
    except Exception:
        info["blech"] = "?"
    try:
        inp = _flange_features(edge.body.parentComponent).createEdgeFlangeInput([edge], _vi_mm(5))
        info["eingabe"] = "ok" if inp is not None else "keine Eingabe"
    except Exception as ex:
        info["eingabe"] = (str(ex).strip().splitlines() or [type(ex).__name__])[-1][:160]
    try:
        info["laenge_mm"] = round(edge.length * 10, 2)
    except Exception:
        pass
    logger.info("Kanten-Sonde " + text, **info)
    return info


def _versatz_alternativen(edge):
    """Die andere lange Kante derselben Stirnfläche (Blech-Dickenfläche) – oben/unten. → Liste entityToken."""
    try:
        stirn = min(list(edge.faces), key=lambda f: f.area)
        _, d0 = _linie(edge)
        out = []
        for k in stirn.edges:
            if k.entityToken == edge.entityToken or _kurventyp(k) != "linie":
                continue
            _, dk = _linie(k)
            if abs(abs(_skal(_v(dk), _v(d0))) - 1.0) < 1e-6 and k.length > 0.5 * edge.length:
                out.append(k.entityToken)
        return out
    except Exception:
        logger.warnung("Versatz: Alternativkanten nicht bestimmbar")
        return []


def versatz_text(versatz_mm):
    """Für den Bericht: was der Versatz bedeutet (lokale Richtung, nicht global)."""
    from ..core import geometrie_referenz as gr
    return gr.versatz_definition(gr.referenz("eben", (0, 0, 0), (0, 0, 1), (1, 0, 0), "linie"), versatz_mm, "tangential")[1]


def versatz_zylinder(edge, versatz_mm, dicke_mm):
    """PROTOTYP (Korrekturauftrag Phase 5): Versatz einer GERADEN Kante parallel zur Achse eines gerollten Blechs als BOGENLÄNGE entlang des Mantels
    (tangential in der Fläche, nicht global): + = Streifen abschneiden, − = anfügen. Exakt per Drehung eines Rechtecks (Ebene durch Achse und Kante)
    um die Zylinderachse um Δφ = Versatz / Radius der Bezugsfläche. Prüfung: Volumenänderung = Versatz × Kantenlänge × Dicke, neue Kante parallel zur
    Achse am gedrehten Ort. Eigene Konstruktionsachse/-ebene/Skizze/Feature werden bei jedem Fehler zurückgebaut. → (erzeugte Objekte, neue Kante).
    NICHT live geprüft."""
    import math
    f = bezugsflaeche(edge)
    if f is None or flaechentyp(f) != "zylinder":
        raise AdapterFehler("Zylinder-Versatz: Die Bezugsfläche der Kante ist kein Zylinder.")
    if _kurventyp(edge) != "linie":
        raise AdapterFehler("Zylinder-Versatz nur an einer GERADEN Kante (Mantellinie).")
    cyl = f.geometry
    o, a = _v(cyl.origin), _einheit(_v(cyl.axis))
    p0, p1 = _v(edge.startVertex.geometry), _v(edge.endVertex.geometry)
    richt = _einheit(_plus(p1, p0, 1.0, -1.0))
    if abs(abs(_skal(richt, a)) - 1.0) > 1e-4:
        raise AdapterFehler("Zylinder-Versatz: Die Kante liegt nicht parallel zur Zylinderachse – Versatz nicht eindeutig.")
    R = cyl.radius
    t = dicke_mm / 10.0
    dphi = (versatz_mm / 10.0) / R
    comp = edge.body.parentComponent
    koerper = edge.body
    rb = Rueckbau("Zylinder-Versatz")
    try:
        ai = comp.constructionAxes.createInput()
        # Live 0.4.60: «setByCylinderOrConeOrTorus» gibt es nicht – die API-Methode heisst setByRevolvedFace (Zylinder/Kegel/Torus). Nicht live geprüft.
        # Live 0.4.61: auch setByRevolvedFace fehlt. Fusion-API: setByCircularFace (Zylinder/Kegel/Torus) – sonst die vorhandenen setBy-Methoden nennen
        for name in ("setByCircularFace", "setByRevolvedFace"):
            if hasattr(ai, name):
                getattr(ai, name)(f)
                break
        else:
            raise AdapterFehler("Achse des Zylinders lässt sich per API nicht anlegen – vorhandene Methoden: %s" % ", ".join(
                n for n in dir(ai) if n.startswith("setBy")))
        achse = rb.merke(comp.constructionAxes.add(ai))
        pi = comp.constructionPlanes.createInput()
        pi.setByTwoEdges(achse, edge)
        ebene = rb.merke(comp.constructionPlanes.add(pi))
        sk = rb.merke(comp.sketches.add(ebene))
        _testfehler("versatz_zyl_skizze")
        w = _plus(p0, o, 1.0, -1.0)
        radial = _einheit(_plus(w, a, 1.0, -_skal(w, a)))
        aussen = _skal(flaechennormale(f, edge.startVertex.geometry), radial) > 0
        r_lo, r_hi = (R - t - 0.002, R + 0.002) if aussen else (R - 0.002, R + t + 0.002)
        s0, s1 = _skal(_plus(p0, o, 1.0, -1.0), a), _skal(_plus(p1, o, 1.0, -1.0), a)
        lo, hi = min(s0, s1) - 0.01, max(s0, s1) + 0.01

        def P(axial, rad):
            q = _plus(_plus(o, a, 1.0, axial), radial, 1.0, rad)
            return sk.modelToSketchSpace(adsk.core.Point3D.create(*q))
        sk.sketchCurves.sketchLines.addTwoPointRectangle(P(lo, r_lo), P(hi, r_hi))
        prof = sk.profiles.item(0)
        rv = comp.features.revolveFeatures
        vol0 = koerper.volume
        soll = abs(versatz_mm / 10.0) * abs(s1 - s0) * t
        feat, versuche = None, []
        for vz in (1.0, -1.0):
            op_ = adsk.fusion.FeatureOperations.CutFeatureOperation if versatz_mm > 0 else adsk.fusion.FeatureOperations.JoinFeatureOperation
            ri = rv.createInput(prof, achse, op_)
            ri.setAngleExtent(False, adsk.core.ValueInput.createByReal(vz * abs(dphi)))
            try:
                ri.participantBodies = [koerper]
            except Exception:
                pass
            try:
                f_ = rv.add(ri)
            except Exception as e:
                versuche.append("Richtung %+g: %s" % (vz, (str(e).strip().splitlines() or ["?"])[-1][:100]))
                continue
            k_neu = _koerper_nach(comp, koerper, f_, vol0 + (soll if versatz_mm < 0 else -soll), 0.5 * soll)
            delta = (k_neu.volume - vol0) if k_neu is not None else None
            if delta is not None and ((versatz_mm > 0 and -1.5 * soll < delta < -0.5 * soll) or (versatz_mm < 0 and 0.5 * soll < delta < 1.5 * soll)):
                feat, koerper = rb.merke(f_), k_neu
                gedreht = vz * abs(dphi)
                break
            versuche.append("Richtung %+g: Volumenänderung %s (Soll %+.4f cm³)" % (vz, "–" if delta is None else "%.4f" % delta, soll if versatz_mm < 0 else -soll))
            p_ = _loeschen(f_)
            if p_:
                raise AdapterFehler("Verworfener Versatz-Versuch nicht entfernbar: " + p_)
        if feat is None:
            raise AdapterFehler("Zylinder-Versatz nicht möglich (%s)." % "; ".join(versuche))
        _testfehler("versatz_zyl_feature")
        # neue Kante: Mantellinie, um ±Δφ um die Achse gedreht (die Seite, auf der das Material jetzt endet)
        mitte = _plus(p0, p1, 0.5, 0.5)
        kandidaten = []
        for sgn in (1.0, -1.0):
            winkel = sgn * gedreht
            wm = _plus(mitte, o, 1.0, -1.0)
            ax_ = _plus(o, a, 1.0, _skal(wm, a))
            rv_ = _plus(mitte, ax_, 1.0, -1.0)
            quer = (a[1] * rv_[2] - a[2] * rv_[1], a[2] * rv_[0] - a[0] * rv_[2], a[0] * rv_[1] - a[1] * rv_[0])
            ziel = _plus(ax_, _plus(tuple(math.cos(winkel) * x for x in rv_), quer, 1.0, math.sin(winkel)), 1.0, 1.0)
            for k in koerper.edges:
                try:
                    if _kurventyp(k) != "linie":
                        continue
                    q0, dk = _linie(k)
                    if abs(abs(_skal(_v(dk), a)) - 1.0) > 1e-4:
                        continue
                    wq = _plus(ziel, _v(q0), 1.0, -1.0)
                    if math.sqrt(_skal(_ohne_komponente(wq, _v(dk)), _ohne_komponente(wq, _v(dk)))) < 0.005:
                        kandidaten.append(k)
                except Exception:
                    continue
            if kandidaten:
                break
        if len(kandidaten) < 1:
            raise AdapterFehler("Zylinder-Versatz: neue Mantelkante nicht gefunden.")
        logger.info("Zylinder-Versatz (Prototyp)", versatz_mm=versatz_mm, dphi_grad=math.degrees(dphi), radius_mm=R * 10)
        return list(rb.objekte), kandidaten[0]
    except Exception as e:
        rb.abbrechen(e)


def _versatz_anwenden(edge, versatz_mm, dicke_mm):
    """Versatz an EINER Kante → (erzeugte Objekte, neue Kante)."""
    erzeugt, kanten = _versatz_gruppe([edge], versatz_mm, dicke_mm)
    return erzeugt, kanten[0]


def _versatz_gruppe(edges, versatz_mm, dicke_mm):
    """Verschiebt die Kanten, an denen die Flansche ansetzen, um versatz_mm quer zur Kante: + nach innen (Streifen wird abgeschnitten), − nach
    aussen (Streifen wird angefügt). Fusions Flansch kennt keine freie Verschiebung der Biegung; das Blech wird deshalb vorher entsprechend
    gekürzt oder verlängert (gerade Kanten, Streifen über die ganze Kantenlänge, alle Streifen in EINER Skizze/Extrusion). Zusammenstossende
    Kanten der Gruppe: beim Anfügen füllen die Streifen die Ecke, damit die versetzten Kanten wieder aufeinandertreffen und Fusion die Gehrung
    rechnen kann. → (erzeugte Objekte, neue Kanten in der Reihenfolge der alten). Scheitert etwas nach dem Anlegen der Skizze, baut die Funktion
    ihre Skizze/Extrusion SELBST zurück, bevor der Fehler weitergeht; nach Erfolg übernimmt der Aufrufer den Rückbau. Nicht live geprüft."""
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
    typ = flaechentyp(flaeche)
    if typ != "eben":
        from ..core import geometrie_referenz as gr
        if typ == "unbekannt":
            raise AdapterFehler("Versatz: Der Flächentyp der Blechfläche ist nicht lesbar – ohne sichere Erkennung wird nichts gebaut (nie stillschweigend «eben»).")
        try:
            gr.versatz_definition(gr.referenz(typ, (0, 0, 0), (0, 0, 1)), versatz_mm, "tangential")
        except ValueError as e:
            raise AdapterFehler(str(e))
    koerper = edges[0].body
    comp = koerper.parentComponent
    ueber, tief = 0.1, 0.1
    erzeugt = []
    skizze = comp.sketches.add(flaeche)
    erzeugt.append(skizze)
    try:
        skizze.name = "Versatz %+g mm" % versatz_mm
        _testfehler("versatz_skizze")

        def pt(x):
            return skizze.modelToSketchSpace(adsk.core.Point3D.create(x[0], x[1], x[2]))

        def ecke(d, laengs, quer):
            return _plus(_plus(d["p0"], d["e"], 1.0, laengs), d["u"], 1.0, quer)
        linien = skizze.sketchCurves.sketchLines
        rechtecke = []
        for i, d in enumerate(daten):
            if s > 0:       # Rückversatz: von etwas ausserhalb der Kante bis s nach innen wegschneiden, an den Enden etwas länger
                x0, x1, q0, q1 = -0.05, d["L"] + 0.05, ueber, -s
            else:           # Vorversatz: Streifen der Breite |s| aussen anfügen; an Ecken zu Nachbarkanten bis in die Ecke verlängert
                x0 = -abs(s) if geteilt(d["p0"], i) else 0.0
                x1 = d["L"] + (abs(s) if geteilt(d["p1"], i) else 0.0)
                q0, q1 = -tief, -s
            rechtecke.append(((x1 - x0) * abs(q0 - q1),))
            a, b, c, e_ = ecke(d, x0, q0), ecke(d, x1, q0), ecke(d, x1, q1), ecke(d, x0, q1)
            l1 = linien.addByTwoPoints(pt(a), pt(b))
            l2 = linien.addByTwoPoints(l1.endSketchPoint, pt(c))
            l3 = linien.addByTwoPoints(l2.endSketchPoint, pt(e_))
            linien.addByTwoPoints(l3.endSketchPoint, l1.startSketchPoint)
        if skizze.profiles.count < 1:
            raise AdapterFehler("Der Versatz-Streifen ergab keine Fläche in der Skizze.")
        # Nur die Streifen-Profile verwenden. Live 31.10.: In der Skizze waren auch Profile der Blechfläche selbst (automatisch projizierte Kanten) –
        # damit wurde beim Anfügen die Dicke verdoppelt und beim Schneiden der ganze Körper entfernt. Profile, die viel grösser sind als die
        # gezeichneten Rechtecke, gehören nicht zum Streifen.
        grenze = 1.05 * sum(abs(r[0]) for r in rechtecke) if rechtecke else None
        profile = adsk.core.ObjectCollection.create()
        uebersprungen = 0
        for k in range(skizze.profiles.count):
            pr = skizze.profiles.item(k)
            try:
                flaeche_pr = pr.areaProperties().area
            except Exception:
                flaeche_pr = None
            if flaeche_pr is not None and grenze is not None and flaeche_pr > grenze:
                uebersprungen += 1
                continue
            profile.add(pr)
        if uebersprungen:
            logger.info("Versatz: Profile der Blechfläche in der Skizze übersprungen", anzahl=uebersprungen)
        if profile.count < 1:
            raise AdapterFehler("Der Versatz-Streifen ergab keine passende Fläche in der Skizze.")
        ef = comp.features.extrudeFeatures
        vol0 = koerper.volume
        soll = abs(s) * sum(d["L"] for d in daten) * t
        feat = None
        versuche = []
        sign = _aufbau_richtung(flaeche, skizze)
        # Live 31.10.: Der symmetrische Schnitt liess keinen Körper übrig (Volumen 0). Das Anfügen (einseitig, Richtung Blech) klappt – deshalb
        # schneidet das Add-in zuerst genauso einseitig 1.5 × Dicke ins Blech, dann die Gegenrichtung, zuletzt symmetrisch.
        if s > 0:
            reihe = ((sign, "einseitig"), (-sign, "einseitig")) if sign else ((1.0, "einseitig"), (-1.0, "einseitig"))
            reihe = reihe + ((None, "symmetrisch"),)
        else:
            reihe = tuple((r, "anfuegen") for r in ((sign, -sign) if sign else (1.0, -1.0)))
        for richtung, art_ in reihe:
            try:
                if s > 0:
                    ei = ef.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
                    if art_ == "einseitig":
                        ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(richtung * 1.5 * t))
                    else:
                        ei.setSymmetricExtent(adsk.core.ValueInput.createByReal(4 * t + 0.2), True)
                else:
                    ei = ef.createInput(profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
                    ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(richtung * t))
                ei.participantBodies = [koerper]
                f = ef.add(ei)
            except Exception as ex:
                versuche.append(str(ex).strip().splitlines()[-1][:120] if str(ex).strip() else type(ex).__name__)
                continue
            koerper_neu = _koerper_nach(comp, koerper, f, vol0 + (soll if s < 0 else -soll), 0.5 * soll)
            delta = (koerper_neu.volume - vol0) if koerper_neu is not None else None
            # Schnitt: Volumen sinkt um etwa den Streifen (nicht auf 0!); Anfügen: Volumen steigt um etwa den Streifen
            if delta is not None and ((s > 0 and -1.5 * soll < delta < -0.5 * soll) or (s < 0 and 0.5 * soll < delta < 1.5 * soll)):
                feat, koerper = f, koerper_neu
                break
            versuche.append("%s: Körper nach dem Feature %s, Volumenänderung %s cm³ (erwartet %+.3f)" % (
                art_ if richtung is None else "%s %+g" % (art_, richtung), "nicht gefunden" if koerper_neu is None else "gefunden",
                "–" if delta is None else "%.3f" % delta, -soll if s > 0 else soll))
            try:
                versuche[-1] += " [Körper im Bauteil: %s]" % ", ".join("%s %.2f cm³" % (b.name, b.volume) for b in comp.bRepBodies)
            except Exception:
                pass
            p_ = _loeschen(f)
            if p_:
                raise AdapterFehler("Ein verworfener Versatz-Versuch liess sich nicht entfernen: " + p_)
        if feat is None:
            raise AdapterFehler("Der Versatz konnte nicht an das Blech angefügt/abgeschnitten werden (%s)." % "; ".join(versuche))
        erzeugt.append(feat)
        _testfehler("versatz_extrusion")
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
        for k in neue:           # Ersatzkanten merken und die Kante für das Protokoll untersuchen (Live 4.11.: Fusion lehnte die Kante nach dem Rückversatz ab)
            try:
                _VERSATZ_ALT[k.entityToken] = _versatz_alternativen(k)
                _kante_sonde(k, "nach dem Versatz")
            except Exception:
                logger.warnung("Versatz: Kante nicht untersucht")
        return erzeugt, neue
    except Exception as e:
        # Selbst zurückbauen, bevor der Fehler weitergeht – der Aufrufer bekommt die Liste sonst nie zu sehen (Skizze/Extrusion blieben zurück).
        probleme = entfernen_bericht(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % ((str(e).strip().splitlines() or [type(e).__name__])[-1])
        raise AdapterFehler(text + (" (Versatz-Skizze/-Extrusion wieder entfernt)" if not probleme else
                                    " – ACHTUNG: Versatz-Teile nicht vollständig entfernt: %s" % "; ".join(probleme)), rueckbau_ok=not probleme)


def _schritt_bauen(edge, op, gespiegelt, dicke_mm=None, prototyp=False):
    """prototyp=True NUR im Live-Test: gesperrte Prototyp-Fälle der Matrix (z. B. gerade Kante auf Zylinder) werden an Fusion gegeben."""
    extra = {"fusion_fragen": True} if prototyp else {}
    if op["typ"] == "umschlag":
        return umschlag(edge, op["laenge"], gespiegelt, op.get("radius"), op.get("lage"), dicke_mm, **extra)
    return flansch(edge, op["winkel"], op["laenge"], op.get("radius"), gespiegelt, op.get("bezug"), op.get("lage"), **extra)


def _kein_doppelfalz_nativ(ops):
    from ..core import profil_engine as pe
    if pe.doppelfalz_stellen(ops):
        raise AdapterFehler("Doppelfalz (Umschlag samt Umschlag nochmals umgelegt, wie beim Stehfalz) kann die Fusion-Blechfunktion nicht bauen – "
                            "Bauweise «eigene Geometrie» wählen. Es wurde nichts verändert.")


def folge_anbringen(edge, ops, dicke_mm, markierung, hinweise=None, start=None, prototyp=False):
    """Operationsfolge an EINER Kante. → Liste erzeugter Features. Bei Fehler: alles wieder entfernen und AdapterFehler.
    Hinweise (z. B. mögliche Einschnitte an runden Kanten, automatisch umgekehrte Richtungen) werden in die übergebene Liste geschrieben.
    Richtungsprüfung ab Schritt 2 (nach Fusion-Standard bei Schritt 1) – NICHT live geprüft."""
    _kein_doppelfalz_nativ(ops)
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
                hinweise.append("Schritt %d: %s" % (i, versatz_text(op["versatz"])))
                try:
                    token = aktuell.entityToken
                except Exception:
                    token = None
                phase = "Schritt %d" % i
            vorher = _abbild(aktuell)          # VOR dem Bau – die Kante kann danach ungültig sein (Biegung innen)
            try:
                feat = _schritt_bauen(aktuell, op, gespiegelt, dicke_mm, prototyp)
            except AdapterFehler as ex_versatz:
                # Versetzte Kante von Fusion abgelehnt: dieselbe Stirnfläche hat noch eine Kante auf dem anderen Niveau (Blech oben/unten) – damit versuchen.
                feat = None
                alt = _VERSATZ_ALT.get(token, []) if (op.get("versatz") and token) else []
                for nr_alt, tok in enumerate(alt, 1):
                    k_alt = _kante_aufloesen(tok, None)
                    if k_alt is None:
                        continue
                    _kante_sonde(k_alt, "Ersatzkante %d" % nr_alt)
                    try:
                        vorher = _abbild(k_alt)
                        feat = _schritt_bauen(k_alt, op, gespiegelt, dicke_mm, prototyp)
                        aktuell = k_alt
                        logger.info("Flansch an der Ersatzkante der Stirnfläche gebaut", ersatz=nr_alt)
                        hinweise.append("Schritt %d: Fusion lehnte die versetzte Kante ab – die Kante auf dem anderen Niveau der Stirnfläche wurde verwendet." % i)
                        break
                    except AdapterFehler as ex2:
                        logger.warnung("Ersatzkante abgelehnt", ersatz=nr_alt, grund=str(ex2).splitlines()[0][:160])
                if feat is None:
                    raise ex_versatz
            erzeugt.append(feat)
            _testfehler("folge_nach_schritt")
            neu = None
            if i < len(ops):
                phase = "Nach Schritt %d (Kante für Schritt %d suchen)" % (i, i + 1)
                neu = neue_aussenkante(feat, vorher, op["laenge"], dicke_mm or 1.0)
                phase = "Schritt %d" % i
            elif geprueft and i > 1:
                try:
                    neu = neue_aussenkante(feat, vorher, op["laenge"], dicke_mm or 1.0)
                except AdapterFehler:
                    hinweise.append("Schritt %d: Richtung konnte nicht geprüft werden (neue Kante nicht eindeutig)." % i)
            gemessen = _gemessen(vorher, neu, rahmen[0]) if (geprueft and neu is not None) else None
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
                    p_ = _loeschen(feat)
                    if p_:
                        raise AdapterFehler("Der falsch gerichtete Schritt liess sich nicht entfernen: " + p_)
                    aktuell = _kante_aufloesen(token, aktuell) if token else aktuell
                    feat = _schritt_bauen(aktuell, op, True, dicke_mm, prototyp)
                    erzeugt.append(feat)
                    neu = neue_aussenkante(feat, vorher, op["laenge"], dicke_mm or 1.0)
                    nochmal = richtung_stimmt(lauf, op["winkel"], _gemessen(vorher, neu, rahmen[0]) or gemessen, rahmen[1], v)
                    if nochmal is False:
                        raise AdapterFehler("Die Richtung von Schritt %d weicht von der Vorlage ab und liess sich auch gespiegelt nicht herstellen." % i)
                    hinweise.append("Schritt %d: Richtung automatisch umgekehrt (Fusion-Standard wich von der Vorlage ab)." % i)
                elif stimmt is None:
                    hinweise.append("Schritt %d: Richtung nicht eindeutig messbar – bitte Ergebnis prüfen." % i)
            elif geprueft and i > 1 and (v is None or gemessen is None):
                hinweise.append("Schritt %d: Richtung nicht geprüft (Messung nicht möglich) – bitte Ergebnis prüfen." % i)
            lauf += op["winkel"]
            hinweise.extend(schlitze_pruefen(feat, vorher, dicke_mm or 1.0))
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


def _comp_volumen(comp):
    """Summe der Körpervolumen (cm³) oder None, wenn nicht lesbar – dann entfällt die Volumenkontrolle (im Protokoll vermerkt)."""
    try:
        return sum(b.volume for b in comp.bRepBodies)
    except Exception:
        return None


def _koerperzahl(comp):
    try:
        return comp.bRepBodies.count
    except Exception:
        return None


def _koerper_kontrolle(comp, koerper_vorher):
    probleme = []
    n = _koerperzahl(comp)
    if n is None:
        logger.warnung("Körperkontrolle nicht möglich (Körper nicht lesbar)")
        return probleme
    if koerper_vorher is not None and n != koerper_vorher:
        probleme.append("%d statt %d Körper" % (n, koerper_vorher))
    for b in comp.bRepBodies:
        probleme += koerper_pruefen(b)
    return probleme


def _volumen_kontrolle(comp, vol0, soll, unten, oben, text):
    v1 = _comp_volumen(comp)
    if vol0 is None or v1 is None or soll <= 0:
        logger.warnung("Volumenkontrolle nicht möglich", was=text)
        return []
    delta = v1 - vol0
    if not (unten <= delta / soll <= oben):
        return ["Volumenzuwachs %.0f mm³ statt ca. %.0f mm³ (%s)" % (delta * 1000, soll * 1000, text)]
    return []


def umschlag_kontrolle(comp, vol0, koerper_vorher, kante_cm, laenge_mm, dicke_mm):
    """Saum nach dem Bauen prüfen. → Liste der Probleme (leer = plausibel). Volumen in cm³, Kante in cm. Nicht live geprüft."""
    probleme = _koerper_kontrolle(comp, koerper_vorher)
    return probleme + _volumen_kontrolle(comp, vol0, kante_cm * (laenge_mm / 10.0) * (dicke_mm / 10.0), 0.5, 2.5,
                                         "keine zweite Materiallage in der erwarteten Länge?")


def gruppe_pruefen(kanten):
    """VOR einer Gruppenoperation: alle Kanten gerade, am selben Körper, zusammenhängend als Kette (jede Kante hat höchstens zwei Nachbarn, über
    gemeinsame Eckpunkte verbunden; geschlossener Umlauf erlaubt). → Problemtext oder None."""
    if len(kanten) < 2:
        return "Eine Gruppe braucht mindestens zwei Kanten."
    for nr, k in enumerate(kanten, 1):
        if _kurventyp(k) != "linie":
            return "Kante %d ist nicht gerade." % nr
    try:
        koerper = {k.body.entityToken for k in kanten}
    except Exception:
        return "Der Körper der Kanten ist nicht lesbar."
    if len(koerper) != 1:
        return "Die Kanten gehören zu %d verschiedenen Körpern." % len(koerper)
    try:
        enden = [(_v(k.startVertex.geometry), _v(k.endVertex.geometry)) for k in kanten]
    except Exception:
        return "Die Eckpunkte der Kanten sind nicht lesbar."

    def gleich(p, q):
        return max(abs(a - b) for a, b in zip(p, q)) < 1e-4
    nachbarn = [set() for _ in kanten]
    for i in range(len(kanten)):
        for j in range(i + 1, len(kanten)):
            if any(gleich(p, q) for p in enden[i] for q in enden[j]):
                nachbarn[i].add(j)
                nachbarn[j].add(i)
    for i, n in enumerate(nachbarn):
        if len(n) > 2:
            return "An Kante %d stossen %d andere Kanten – keine einfache Kantenkette." % (i + 1, len(n))
    gesehen, offen = {0}, [0]
    while offen:
        for j in nachbarn[offen.pop()]:
            if j not in gesehen:
                gesehen.add(j)
                offen.append(j)
    if len(gesehen) != len(kanten):
        return "Die Kanten hängen nicht über gemeinsame Ecken zusammen."
    return None


def gehrung_kontrolle(feat, comp, vol0, koerper_vorher, laengen_cm, hoehe_mm, dicke_mm):
    """Gemeinsamer Flansch nach dem Bauen: Fusion meldet Gehrung (isMiteredCorners, falls lesbar), gültige Körper, kein zusätzlicher Körper,
    Volumenzuwachs passt zu Σ Kantenlänge × Höhe × Dicke (fehlender Flansch, Spalt/Überlappung grösseren Umfangs). Feine Spalte an der Ecke kann
    diese Prüfung NICHT erkennen. → Liste der Probleme. Nicht live geprüft."""
    probleme = []
    try:
        if getattr(feat, "isMiteredCorners", None) is False:
            probleme.append("Fusion meldet keine Gehrung (isMiteredCorners = False)")
    except Exception:
        pass
    probleme += _koerper_kontrolle(comp, koerper_vorher)
    return probleme + _volumen_kontrolle(comp, vol0, sum(laengen_cm) * (hoehe_mm / 10.0) * (dicke_mm / 10.0), 0.6, 1.5,
                                         "Flansch fehlt, Spalt oder Überlappung?")


def kante_entlang_pruefen(alt_rahmen, neue_kante, hoehe_mm, dicke_mm, ri_mm=None, n=5):
    """Nach einem Flansch an einer (geraden) Kante einer gekrümmten Fläche: entlang der GANZEN Kante prüfen, dass der Flansch der LOKALEN Normale folgt
    und überall gleich hoch ist. alt_rahmen = rahmen_entlang(kante) VOR dem Bau; neue_kante = Flanschende (neue_aussenkante). → (ok, Text).
    Nicht live geprüft."""
    from ..core import geometrie_referenz as gr
    ev = neue_kante.evaluator
    ok, t0, t1 = ev.getParameterExtents()
    punkte = []
    for i in range(n):
        ok, p = ev.getPointAtParameter(t0 + (t1 - t0) * i / (n - 1.0))
        punkte.append(_punkt_mm(p))
    # zu jedem alten Stützpunkt den nächsten Punkt der neuen Kante: Richtung und Abstand
    hoehen, winkel = [], []
    for r in alt_rahmen:
        o = r["origin"]
        q = min(punkte, key=lambda x: sum((a - b) ** 2 for a, b in zip(x, o)) - sum((a - b) * c for a, b, c in zip(x, o, r["x"])) ** 2)
        d = [a - b for a, b in zip(q, o)]
        laengs = sum(a * c for a, c in zip(d, r["x"]))
        quer = [a - laengs * c for a, c in zip(d, r["x"])]
        h = sum(a * a for a in quer) ** 0.5
        hoehen.append(h)
        if h > 1e-6:
            w = gr.winkel_grad(quer, r["z"])
            winkel.append(min(w, 180.0 - w))
    tol = 2 * dicke_mm + (ri_mm if ri_mm is not None else dicke_mm) + 1.0
    streuung = max(hoehen) - min(hoehen)
    text = "Flanschhöhe entlang der Kante %.2f … %.2f mm (Soll %.1f ± %.1f), Richtung zur lokalen Normale max. %.2f°" % (
        min(hoehen), max(hoehen), hoehe_mm, tol, max(winkel) if winkel else -1)
    gut = streuung <= 0.2 and all(abs(h - hoehe_mm) <= tol for h in hoehen) and winkel and max(winkel) <= 2.0
    return bool(gut), text


def ecke_daten(kanten):
    """VOR dem Bau lesen (danach sind die Kanten oft ungültig): gemeinsame Ecke, Kantenrichtungen von der Ecke weg, Blechnormale an der Ecke.
    → dict oder None. Nicht live geprüft."""
    try:
        ecke = None
        for a in (kanten[0].startVertex, kanten[0].endVertex):
            for b in (kanten[1].startVertex, kanten[1].endVertex):
                if max(abs(x - y) for x, y in zip(_v(a.geometry), _v(b.geometry))) < 1e-4:
                    ecke = _v(a.geometry)
        if ecke is None:
            return None

        def weg(k):
            p0, p1 = _v(k.startVertex.geometry), _v(k.endVertex.geometry)
            q = p1 if max(abs(x - y) for x, y in zip(p0, ecke)) < 1e-4 else p0
            return _einheit(_plus(q, ecke, 1.0, -1.0))
        blech = max(list(kanten[0].faces), key=lambda f: f.area)
        return {"ecke": ecke, "e1": weg(kanten[0]), "e2": weg(kanten[1]), "nb": tuple(flaechennormale(blech, adsk.core.Point3D.create(*ecke)))}
    except Exception:
        logger.warnung("Eckdaten nicht lesbar")
        return None


def gehrung_eckspalt(feat, daten, dicke_mm):
    """Gemeinsamen Flansch an einer Ecke GEOMETRISCH prüfen (nicht nur Volumen): Gehrungsflächen suchen (core/gehrung) und ihren kleinsten
    Abstand mit Fusions MeasureManager messen. daten = ecke_daten(kanten) VOR dem Bau. → ('ok'|'fehler'|'stoss'|'unbekannt', Text).
    'stoss' = Stossecke ohne 45°-Gehrung mit gemessenem Spalt (so baut Fusion live 0.4.59). Gesucht wird zuerst unter den Flächen des Features, sonst unter den ebenen Flächen des ganzen Körpers in Eckennähe (Live 0.4.57: 0 Treffer
    unter den Feature-Flächen). Findet sich nichts, nennt der Text die eckennahen ebenen Flächen mit ihren Winkeln – für die Ursachenanalyse.
    Nicht live geprüft (Annahme: Gehrungsflächen sind ebene Stirnflächen, Normale in der Blechebene, gleicher Winkel zu beiden Kanten)."""
    from ..core import gehrung
    if not daten:
        return "unbekannt", "Die Ecke der Kanten war nicht lesbar."

    def ebene(flaechen):
        out = []
        for f in flaechen:
            try:
                if not isinstance(f.geometry, adsk.core.Plane):
                    continue
                c = f.centroid
                out.append((f, tuple(flaechennormale(f)), (c.x * 10.0, c.y * 10.0, c.z * 10.0)))
            except Exception:
                continue
        return out
    try:
        ecke_mm = tuple(x * 10.0 for x in daten["ecke"])
        quelle, kandidaten = "Feature", ebene(feat.faces)
        gw = gehrung.gehrungsflaechen([(i, n, c) for i, (_f, n, c) in enumerate(kandidaten)], daten["e1"], daten["e2"], daten["nb"], ecke_mm)
        if len(gw) < 2:
            koerper = []
            try:
                koerper = list(feat.bodies)
            except Exception:
                pass
            quelle = "Körper"
            kandidaten = ebene(f for b in koerper for f in b.faces)
            gw = gehrung.gehrungsflaechen([(i, n, c) for i, (_f, n, c) in enumerate(kandidaten)], daten["e1"], daten["e2"], daten["nb"], ecke_mm,
                                          reichweite_mm=60.0)
        if len(gw) < 2:
            k3 = [(i, n, c) for i, (_f, n, c) in enumerate(kandidaten)]
            s1, s2 = gehrung.stossflaechen(k3, daten["e1"], daten["e2"], daten["nb"], ecke_mm, 2.0 * (dicke_mm or 1.0), 25.0)
            if s1 and s2:
                gr_ = []
                werte = [abstand_mm(kandidaten[i][0], kandidaten[j][0], gr_) for i in s1 for j in s2]
                werte = [w for w in werte if w is not None]
                if not werte:
                    return "unbekannt", "Stossecke erkannt, Eckspalt aber nicht messbar (%s)." % ("; ".join(gr_)[:200] or "?")
                spalt = min(werte)
                return "stoss", ("Stossecke – KEINE 45°-Gehrung: die Flansch-Stirnflächen stehen senkrecht zu ihrer Kante (%d/%d Flächen), "
                                 "Eckspalt %.2f mm. Fachlich zu bewerten." % (len(s1), len(s2), spalt))
            return "unbekannt", "Gehrungsflächen nicht eindeutig gefunden (%d) – Ecke bitte ansehen. Eckennahe ebene Flächen: %s" % (
                len(gw), gehrung.diagnose([(i, n, c) for i, (_f, n, c) in enumerate(kandidaten)], daten["e1"], daten["e2"], daten["nb"], ecke_mm))
        bester, gr_ = None, []
        for i in range(len(gw)):
            for j in range(i + 1, len(gw)):
                d = abstand_mm(kandidaten[gw[i]][0], kandidaten[gw[j]][0], gr_)     # mit Proxy-Rückfall (Live 0.4.60: «invalid argument geometryOne»)
                if d is not None:
                    bester = d if bester is None else min(bester, d)
        s_, t_ = gehrung.bewerte_eckspalt(bester, dicke_mm)
        return s_, "%s (%d Gehrungsflächen aus %s)" % (t_, len(gw), quelle)
    except Exception as e:
        return "unbekannt", "Eckspalt nicht messbar (%s)." % ((str(e).strip().splitlines() or [type(e).__name__])[-1][:100])


def _umschlag_gruppe(kanten, op, dicke_mm, gespiegelt):
    """Umschlag an mehreren zusammenhängenden Kanten: je Kante ein EIGENES Saum-Feature (Fusions Saum-Eingabe nimmt laut Doku genau eine Kante),
    jedes mit Geometriekontrolle. Die Ecken sind dabei NICHT auf Gehrung geschnitten. Scheitert eine Kante, werden ALLE Säume dieser Gruppe
    zurückgebaut. Kein Ersatz durch einen 179°-Flansch (der wäre kein echter Umschlag). → Liste der Features. Nicht live geprüft."""
    tokens = []
    for k in kanten:
        try:
            tokens.append(k.entityToken)
        except Exception:
            tokens.append(None)
    rb = Rueckbau("Umschlag an %d Kanten" % len(kanten))
    try:
        for nr, (k, tok) in enumerate(zip(kanten, tokens), 1):
            kante = _kante_aufloesen(tok, k) if tok else k
            rb.merke(umschlag(kante, op["laenge"], gespiegelt, op.get("radius"), op.get("lage"), dicke_mm))
        feats = list(rb.objekte)
        logger.info("Umschlag je Kante gebaut (eigene Saum-Features, keine Gehrung)", kanten=len(kanten))
        return feats
    except Exception as e:
        rb.abbrechen(e)


def _schritt_gruppe(kanten, op, dicke_mm, gespiegelt):
    """Ein Schritt an mehreren zusammenhängenden Kanten. Flansch: EIN Feature (Gehrung). Umschlag: je Kante ein Saum-Feature. → Liste der Features."""
    if op["typ"] == "umschlag":
        return _umschlag_gruppe(kanten, op, dicke_mm, gespiegelt)
    return [flansch(list(kanten), -abs(op["winkel"]) if gespiegelt else abs(op["winkel"]), op["laenge"], op.get("radius"), gespiegelt,
                    op.get("bezug"), op.get("lage"))]


def _neue_kanten(feats, kanten, laenge_mm, dicke_mm):
    if len(feats) == 1:
        return [neue_aussenkante(feats[0], e, laenge_mm, dicke_mm or 1.0) for e in kanten]
    return [neue_aussenkante(f, e, laenge_mm, dicke_mm or 1.0) for f, e in zip(feats, kanten)]


def folge_anbringen_gruppe(edges, ops, dicke_mm, markierung, hinweise=None):
    """Wie folge_anbringen für MEHRERE zusammenhängende Kanten: Flansch-Schritte als EIN Feature – Fusion schneidet die Ecken auf Gehrung, das
    Ergebnis wird kontrolliert –, Umschläge je Kante als eigenes Saum-Feature. Vor dem Modellieren wird die Gruppe geprüft (gerade, ein Körper,
    Kette). Scheitert ein Schritt oder fällt die Kontrolle durch, wird ALLES zurückgebaut und AdapterFehler gemeldet – es gibt KEINEN stillen
    Rückfall auf Einzelkanten (den entscheidet der Aufrufer nach Rückfrage). Nur ein Versatz in einem späteren Schritt wird je Kante gebaut
    (Hinweis «ohne Gehrung»). NICHT live geprüft."""
    _kein_doppelfalz_nativ(ops)
    hinweise = hinweise if hinweise is not None else []
    if len(edges) < 2 or (ops[0]["typ"] == "umschlag" and len(ops) > 1):
        raise AdapterFehler("Gemeinsamer Flansch nur für mehrere Kanten und einen Flansch als ersten Schritt (ein Umschlag nur allein).")
    problem = gruppe_pruefen(list(edges))
    if problem:
        raise AdapterFehler("Gemeinsam mit Gehrung nicht möglich, vor dem Modellieren abgelehnt: " + problem)
    erzeugt = []
    phase = "Gemeinsamer Flansch (Gehrung)"
    t = dicke_mm or blechdicke_mm(edges[0].body) or 1.0
    try:
        comp = getattr(edges[0].body, "parentComponent", None)
        op = ops[0]
        rahmen = [_kantenrahmen_quer(e) for e in edges]
        if op.get("versatz"):
            phase = "Versatz der gemeinsamen Kanten"
            vorbereitung, edges = _versatz_gruppe(list(edges), op["versatz"], dicke_mm)
            erzeugt.extend(vorbereitung)
            _testfehler("gruppe_nach_versatz")
            phase = "Gemeinsamer Flansch (Gehrung)"
        if op["typ"] == "umschlag":
            phase = "Umschlag je Kante"
            feats = _umschlag_gruppe(list(edges), op, dicke_mm, op["winkel"] < 0)
            erzeugt.extend(feats)
            for f in feats:
                markieren(f, dict(markierung, schritt=1, kanten=len(edges)))
            hinweise.append("Umschlag an %d Kanten: je Kante ein eigenes Saum-Feature (Fusions Saum nimmt eine Kante je Feature) – die Ecken sind NICHT "
                            "auf Gehrung geschnitten." % len(edges))
            return erzeugt
        laengen = [e.length for e in edges]
        eck = ecke_daten(list(edges)) if len(edges) == 2 else None
        vol0, n0 = _comp_volumen(comp), _koerperzahl(comp)
        abb = [_abbild(e) for e in edges]       # VOR dem Bau (Biegung innen macht die Kanten ungültig)
        feat = flansch(list(edges), op["winkel"], op["laenge"], op.get("radius"), op["winkel"] < 0, op.get("bezug"), op.get("lage"))
        erzeugt.append(feat)
        phase = "Kontrolle des gemeinsamen Flansches"
        schlecht = gehrung_kontrolle(feat, comp, vol0, n0, laengen, op["laenge"], t)
        if schlecht:
            raise AdapterFehler("Fusion hat den gemeinsamen Flansch gebaut, die Kontrolle schlägt aber fehl: " + "; ".join(schlecht))
        if len(edges) == 2:
            # Geometrische Eckprüfung: gemessener Spalt zwischen den Gehrungsflächen. Im Bau nur als Hinweis (die Flächensuche ist live noch nicht
            # bestätigt und soll ein gutes Ergebnis nicht verwerfen); der Live-Test wertet sie als PASS/FAIL.
            bew, txt = gehrung_eckspalt(feat, eck, t)
            hinweise.append("Gehrungsecke: " + txt if bew != "fehler" else "Gehrungsecke AUFFÄLLIG: " + txt)
        markieren(feat, dict(markierung, schritt=1, kanten=len(edges)))
        logger.info("Gemeinsamer Flansch mit Gehrung erzeugt und kontrolliert", kanten=len(edges), winkel=op["winkel"], laenge=op["laenge"])
        if len(ops) == 1:
            return erzeugt
        phase = "Nach dem gemeinsamen Flansch (Kanten für Schritt 2 suchen)"
        neue = [neue_aussenkante(feat, e, op["laenge"], dicke_mm or 1.0) for e in abb]
        v = None
        if rahmen[0] is not None and abs(op["winkel"]) < 175:
            gemessen = _gemessen(abb[0], neue[0], rahmen[0][0])
            quer = _einheit(_ohne_komponente(gemessen, rahmen[0][1])) if gemessen is not None else None
            v = tuple(x * (1 if op["winkel"] > 0 else -1) for x in quer) if quer else None
        aktuell, lauf, i = list(neue), op["winkel"], 2
        while i <= len(ops):
            o = ops[i - 1]
            if o.get("versatz"):
                break
            phase = "Gemeinsamer Schritt %d" % i
            laengen = [e.length for e in aktuell]
            abb_i = [_abbild(e) for e in aktuell]
            vol0, n0 = _comp_volumen(comp), _koerperzahl(comp)
            feats = _schritt_gruppe(aktuell, o, dicke_mm, False)
            erzeugt.extend(feats)
            nxt = None
            if i < len(ops) or (rahmen[0] is not None and v is not None):
                try:
                    nxt = _neue_kanten(feats, abb_i, o["laenge"], dicke_mm)
                except AdapterFehler:
                    if i < len(ops):
                        raise
                    hinweise.append("Schritt %d: Richtung konnte nicht geprüft werden (neue Kante nicht eindeutig)." % i)
            if nxt is not None and rahmen[0] is not None and v is not None:
                gem = _gemessen(abb_i[0], nxt[0], rahmen[0][0])
                if gem is not None and richtung_stimmt(lauf, o["winkel"], gem, rahmen[0][1], v) is False:
                    phase = "Gemeinsamer Schritt %d (gespiegelt neu anlegen)" % i
                    for f in feats:
                        erzeugt.remove(f)
                    probleme = entfernen_bericht(feats)
                    if probleme:
                        raise AdapterFehler("Der falsch gerichtete Schritt liess sich nicht entfernen: " + "; ".join(probleme))
                    feats = _schritt_gruppe(aktuell, o, dicke_mm, True)
                    erzeugt.extend(feats)
                    nxt = _neue_kanten(feats, abb_i, o["laenge"], dicke_mm)
                    gem2 = _gemessen(abb_i[0], nxt[0], rahmen[0][0])
                    if gem2 is not None and richtung_stimmt(lauf, o["winkel"], gem2, rahmen[0][1], v) is False:
                        raise AdapterFehler("Die Richtung von Schritt %d weicht von der Vorlage ab." % i)
                    hinweise.append("Schritt %d: Richtung automatisch umgekehrt (Fusion-Standard wich von der Vorlage ab)." % i)
            if o["typ"] == "flansch" and len(feats) == 1:
                schlecht = gehrung_kontrolle(feats[0], comp, vol0, n0, laengen, o["laenge"], t)
                if schlecht:
                    raise AdapterFehler("Schritt %d: Kontrolle des gemeinsamen Flansches schlägt fehl: %s" % (i, "; ".join(schlecht)))
            else:
                hinweise.append("Schritt %d (Umschlag): je Kante ein eigenes Saum-Feature – die Ecken sind NICHT auf Gehrung geschnitten." % i)
            for f in feats:
                markieren(f, dict(markierung, schritt=i, kanten=len(aktuell)))
            logger.info("Gemeinsamer Schritt erzeugt", schritt=i, typ=o["typ"], kanten=len(aktuell), features=len(feats))
            lauf += o["winkel"]
            if i == len(ops):
                return erzeugt
            aktuell = nxt
            i += 1
        if i <= len(ops):
            hinweise.append("Ab Schritt %d (Versatz) wird je Kante gebaut – die Ecken dieser Schritte sind NICHT auf Gehrung geschnitten." % i)
            for nr, n in enumerate(aktuell, 1):
                phase = "Kante %d, weitere Schritte" % nr
                erzeugt.extend(folge_anbringen(n, ops, dicke_mm, markierung, hinweise,
                                               start={"i": i, "lauf": lauf, "v": v, "rahmen": rahmen[nr - 1]}))
        return erzeugt
    except Exception as e:
        logger.ausnahme("Gemeinsamer Flansch abgebrochen", phase=phase)
        probleme = entfernen_bericht(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)
        raise AdapterFehler("%s: %s%s" % (phase, text, (" – alle %d erzeugten Teile wurden wieder entfernt." % len(erzeugt) if erzeugt else "") if not probleme else
                                          " – ACHTUNG: Rückbau unvollständig (%s), bitte mit Strg+Z zurücknehmen." % "; ".join(probleme)),
                            rueckbau_ok=not probleme)


def komponente_entfernen(comp):
    """Eine vom Add-in neu angelegte Komponente samt Inhalt wieder löschen (Rückbau nach einem Fehler). → True, wenn sie weg ist. Nicht live geprüft (Occurrence.deleteMe)."""
    try:
        try:
            token = comp.entityToken
        except Exception:
            token = None
        for occ in list(design().rootComponent.occurrences):
            try:
                gleich = (occ.component.entityToken == token) if token else (occ.component == comp)
            except Exception:
                gleich = False
            if gleich:
                ok = bool(occ.deleteMe())
                if ok:
                    for eintrag in [x for x in _NACH_KOMPONENTE if x[0] == token]:
                        _NACH_KOMPONENTE.remove(eintrag)
                        p_ = _loeschen(eintrag[1])
                        if p_:
                            logger.warnung("Blechregel des Rückbaus nicht gelöscht", problem=p_)
                            ok = False
                return ok
        return False
    except Exception:
        logger.ausnahme("Rückbau der Komponente fehlgeschlagen")
        return False


def abbruch_mit_rueckbau(comp, fehler, was):
    """Nach einem Fehler beim Bau einer NEUEN Komponente: halbfertige Komponente entfernen und mit klarer Aussage abbrechen (das Modell bleibt nicht halb verändert zurück).
    Gelingt der Rückbau nicht, steht das ausdrücklich in der Meldung."""
    ok = komponente_entfernen(comp)
    text = str(fehler) if isinstance(fehler, AdapterFehler) else "Fusion meldet: %s" % ((str(fehler).strip().splitlines() or [type(fehler).__name__])[-1])
    try:
        name = comp.name
    except Exception:
        name = "?"
    raise AdapterFehler("%s: %s %s" % (was, text, "Das halbfertige Bauteil wurde wieder entfernt." if ok else
                                       "ACHTUNG: Das halbfertige Bauteil «%s» liess sich nicht entfernen – bitte mit Strg+Z zurücknehmen oder die Komponente löschen." % name), rueckbau_ok=ok)


def referenzbild_einfuegen(dateipfad, name="Referenzbild"):
    """Bild (Foto/Skizze aus der App) als Referenzbild (Canvas) auf die XY-Ebene des aktiven Dokuments legen; Grösse und Lage stellt der Benutzer in Fusion ein.
    NICHT live geprüft (Canvases.createInput/add)."""
    comp = design().rootComponent
    cv = getattr(comp, "canvases", None)
    if cv is None or not hasattr(cv, "createInput"):
        raise AdapterFehler("Diese Fusion-Version kann keine Referenzbilder (Canvas) per Add-in einfügen. Das Bild wurde gespeichert: %s" % dateipfad)
    eingabe = cv.createInput(dateipfad, comp.xYConstructionPlane)
    bild = cv.add(eingabe)
    try:
        bild.name = name
    except Exception:
        pass
    return bild


def neue_komponente(name):
    """Leere neue Komponente im aktiven Design (unter der Root-Komponente). → Komponente; die Occurrence findet _occurrence_von().
    Aktiviert wird sie erst beim Bauen (blech_aus_profil) und danach wieder zurückgestellt. Nicht live geprüft."""
    occ = design().rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def _gleiche(a, b):
    if a is None or b is None:
        return False
    try:
        return a.entityToken == b.entityToken
    except Exception:
        return a == b


def _occurrence_von(comp):
    """Occurrence der Komponente (None = Root-Komponente). Bei mehreren Vorkommen die erste."""
    root = design().rootComponent
    if _gleiche(comp, root):
        return None
    try:
        vorkommen = list(root.allOccurrencesByComponent(comp))
        if vorkommen:
            return vorkommen[0]
    except Exception:
        pass
    for occ in list(root.allOccurrences):
        if _gleiche(occ.component, comp):
            return occ
    raise AdapterFehler("Die Zielkomponente «%s» ist im Design nicht zu finden." % getattr(comp, "name", "?"))


class _Aktiviert(object):
    """Zielkomponente für die Blech-Erstellung aktivieren (Fusion legt Blechkörper sonst u. U. in der aktiven/Root-Komponente an) und danach
    – nach Erfolg UND nach Fehler – den vorherigen Aktivierungszustand wiederherstellen. Nicht live geprüft (Occurrence.activate,
    Design.activeOccurrence, Design.activateRootComponent)."""

    def __init__(self, occ):
        self.occ, self.vorher, self.bekannt = occ, None, False

    def __enter__(self):
        d = design()
        try:
            self.vorher, self.bekannt = d.activeOccurrence, True
        except Exception:
            self.bekannt = False
        ok = self.occ.activate() if self.occ is not None else d.activateRootComponent()
        if ok is False:
            raise AdapterFehler("Die Zielkomponente liess sich nicht aktivieren – das Blech wird nicht gebaut (es entstünde sonst womöglich in der falschen Komponente).")
        return self

    def __exit__(self, *_):
        if not self.bekannt:
            return False
        try:
            if self.vorher is None:
                design().activateRootComponent()
            elif self.vorher.isValid:
                self.vorher.activate()
        except Exception:
            logger.warnung("Vorherige Aktivierung nicht wiederhergestellt")
        return False


def regel_werte(comp):
    """Biegeradius (mm) und K-Faktor der aktiven Blechregel der Komponente → (ri_mm|None, k|None). Für Soll-Ist-Vergleiche, damit nicht mit
    angenommenen Werten verglichen wird. API: SheetMetalRule.bendRadius / kFactor (Parameter mit .value oder Zahl). Nicht live geprüft."""
    def wert(o):
        v = getattr(o, "value", o)
        return float(v) if isinstance(v, (int, float)) else None
    try:
        r = comp.activeSheetMetalRule
    except Exception:
        return None, None
    ri = k = None
    try:
        v = wert(getattr(r, "bendRadius", None))
        ri = None if v is None else v * 10.0
    except Exception:
        pass
    try:
        k = wert(getattr(r, "kFactor", None))
    except Exception:
        pass
    return ri, k


def _regel_dicke_mm(regel):
    try:
        return units.cm_zu_mm(regel.thickness.value)
    except Exception:
        return None


def _design_regeln(regeln):
    """Liste der Design-Blechregeln oder None, wenn Fusion sie (noch) nicht herausgibt. Live 0.4.53: in einem frischen Dokument ohne Blechdaten
    wirft SheetMetalRules.count «InternalValidationError : smDataRoot»."""
    try:
        return [regeln.item(i) for i in range(regeln.count)]
    except Exception as e:
        logger.info("Design-Blechregeln nicht lesbar", fusion=(str(e).strip().splitlines() or ["?"])[-1])
        return None


def _blechdaten_anlegen(comp, d, dicke_mm):
    """Blechdaten des Dokuments anlegen, indem der Komponente eine Bibliotheksregel zugewiesen wird (bevorzugt mit passender Dicke) – wie die Auswahl
    einer Regel im Register «Blech». Annahme: Fusion übernimmt sie dabei als Design-Regel. Die Bibliotheksregel selbst wird nicht verändert.
    Nicht live geprüft."""
    bib = getattr(d, "librarySheetMetalRules", None)
    try:
        kandidaten = [bib.item(i) for i in range(bib.count)] if bib is not None else []
    except Exception:
        kandidaten = []
    kandidaten.sort(key=lambda r: abs((_regel_dicke_mm(r) or 1e9) - dicke_mm))
    for r in kandidaten:
        try:
            comp.activeSheetMetalRule = r
            logger.info("Blechdaten über Bibliotheksregel angelegt", regel=getattr(r, "name", "?"))
            return True
        except Exception as e:
            logger.info("Bibliotheksregel nicht zuweisbar", regel=getattr(r, "name", "?"), fusion=(str(e).strip().splitlines() or ["?"])[-1])
    return False


def regel_fuer_dicke(comp, dicke_mm):
    """Blechregel mit genau dieser Dicke: vorhandene Design-Regel wiederverwenden, sonst eine KOPIE anlegen («Spengler 0.70 mm») und deren Dicke
    setzen. Bibliotheks- und Standardregeln werden nie verändert. → (Regel, neu angelegt). Bricht ab, wenn die Dicke nicht stimmt.
    API: Design.designSheetMetalRules / librarySheetMetalRules, SheetMetalRules.addByCopy(regel, name), SheetMetalRule.thickness.expression
    (Autodesk: «Sheet Metal Rules», ab November 2022). Nicht live geprüft."""
    d = design()
    regeln = getattr(d, "designSheetMetalRules", None)
    if regeln is None or not hasattr(regeln, "addByCopy"):
        raise AdapterFehler("Diese Fusion-Version kann per API keine Blechregel anlegen (designSheetMetalRules.addByCopy fehlt) – das Grundblech wird nicht gebaut.")
    alle = _design_regeln(regeln)
    if alle is None:
        _blechdaten_anlegen(comp, d, dicke_mm)
        alle = _design_regeln(regeln)
        if alle is None:
            raise AdapterFehler("Fusion gibt die Blechregeln dieses Dokuments nicht heraus (Blechdaten nicht angelegt, «smDataRoot») – das Grundblech "
                                "wird nicht gebaut. Abhilfe: im Register «Blech» einmal eine Blechregel wählen, dann erneut versuchen.")
    for r in alle:
        t = _regel_dicke_mm(r)
        if t is not None and abs(t - dicke_mm) < 0.001:
            return r, False
    quelle = None
    try:
        quelle = comp.activeSheetMetalRule
    except Exception:
        pass
    if quelle is None and alle:
        quelle = alle[0]
    if quelle is None:
        bib = getattr(d, "librarySheetMetalRules", None)
        if bib is not None and bib.count:
            quelle = bib.item(0)
    if quelle is None:
        raise AdapterFehler("Keine Blechregel als Vorlage gefunden (Design und Bibliothek leer) – das Grundblech wird nicht gebaut.")
    namen = set()
    for r in alle:
        try:
            namen.add(r.name)
        except Exception:
            pass
    name, nr = "Spengler %.2f mm" % dicke_mm, 2
    while name in namen:
        name, nr = "Spengler %.2f mm (%d)" % (dicke_mm, nr), nr + 1
    neu = regeln.addByCopy(quelle, name)
    if neu is None:
        raise AdapterFehler("Fusion hat die Blechregel «%s» nicht angelegt." % name)
    try:
        neu.thickness.expression = "%g mm" % dicke_mm
    except Exception as e:
        raise AdapterFehler("Die Dicke der Blechregel «%s» liess sich nicht auf %g mm setzen (Fusion: %s)." % (name, dicke_mm, (str(e).strip().splitlines() or ["?"])[-1]))
    t = _regel_dicke_mm(neu)
    if t is None or abs(t - dicke_mm) > 0.001:
        raise AdapterFehler("Die Blechregel «%s» hat %s mm statt %g mm – das Grundblech wird nicht gebaut." % (name, "?" if t is None else "%.3f" % t, dicke_mm))
    logger.info("Blechregel angelegt", name=name, dicke_mm=dicke_mm, vorlage=getattr(quelle, "name", "?"))
    return neu, True


def schleifen_pruefen(schleifen_mm):
    """Profil VOR dem Modellieren prüfen: 1–2 geschlossene Polygonzüge mit je ≥ 3 Punkten und Fläche > 1 mm². → Problemtext oder None."""
    if not schleifen_mm or len(schleifen_mm) > 2:
        return "Das Profil braucht einen Umriss (und höchstens ein Loch), erhalten: %d Polygonzüge." % len(schleifen_mm or [])
    for nr, poly in enumerate(schleifen_mm, 1):
        try:
            pts = [(float(p[0]), float(p[1])) for p in poly]
        except Exception:
            return "Polygonzug %d enthält ungültige Koordinaten." % nr
        if len(pts) < 3 and not any(len(p) >= 4 for p in poly):
            return "Polygonzug %d hat nur %d Punkte (mindestens 3)." % (nr, len(pts))
        # Bögen (x, y, mx, my): für die Flächenprüfung den Bogenmittelpunkt als Stützpunkt mitnehmen
        mit_boegen = []
        for p in poly:
            mit_boegen.append((float(p[0]), float(p[1])))
            if len(p) >= 4:
                mit_boegen.append((float(p[2]), float(p[3])))
        pts = mit_boegen
        flaeche = 0.5 * abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))))
        if flaeche < 1.0:
            return "Polygonzug %d umschliesst keine Fläche (%.2f mm²)." % (nr, flaeche)
    return None


def grundblech_pruefen(comp, body, dicke_mm, root_koerper_vorher=None):
    """Nach dem Bauen: Körper in der Zielkomponente, nichts in Root, gültiger Blechkörper, Dicke laut Regel UND gemessen (Ausdehnung in Z beim
    ebenen Blech auf XY) = Soll, Oberseite für die Abwicklung vorhanden. → Liste der Probleme. Nicht live geprüft."""
    probleme = []
    try:
        if not _gleiche(body.parentComponent, comp):
            probleme.append("Der Körper liegt nicht in der Zielkomponente «%s», sondern in «%s»." % (getattr(comp, "name", "?"), getattr(body.parentComponent, "name", "?")))
    except Exception:
        probleme.append("Die Komponente des Körpers ist nicht lesbar.")
    if root_koerper_vorher is not None:
        try:
            n = design().rootComponent.bRepBodies.count
            if n != root_koerper_vorher:
                probleme.append("In der Root-Komponente ist ein Körper entstanden (%d statt %d)." % (n, root_koerper_vorher))
        except Exception:
            pass
    probleme += koerper_pruefen(body)
    v = getattr(body, "isSheetMetal", None)
    if v is False:
        probleme.append("Der Körper ist kein Blechkörper (isSheetMetal = False).")
    t_regel = blechdicke_mm(body)
    if t_regel is None or abs(t_regel - dicke_mm) > 0.001:
        probleme.append("Blechregel der Komponente: %s mm statt %g mm." % ("?" if t_regel is None else "%.3f" % t_regel, dicke_mm))
    try:
        bb = body.boundingBox
        t_mess = units.cm_zu_mm(bb.maxPoint.z - bb.minPoint.z)
        if abs(t_mess - dicke_mm) > 0.005:
            probleme.append("Gemessene Blechdicke %.3f mm statt %g mm." % (t_mess, dicke_mm))
    except Exception:
        probleme.append("Die Blechdicke liess sich nicht messen.")
    try:
        _oberseite(body)
    except AdapterFehler:
        probleme.append("Keine ebene Oberseite – für die Abwicklung ungeeignet.")
    return probleme


_NACH_KOMPONENTE = []          # (Token der Komponente, Blechregel): erst nach dem Entfernen der Komponente löschbar


def blech_aus_profil(comp, schleifen_mm, dicke_mm=1.0):
    """Ebenes Blech (Basisflansch) aus einem oder zwei geschlossenen Polygonzügen auf der XY-Ebene (mm; ein Polygon = Fläche, zwei = Ring mit Loch)
    in der Komponente comp, mit GENAU der Soll-Dicke dicke_mm. Ablauf: Profil und Dicke prüfen → Zielkomponente aktivieren → Blechregel mit
    dieser Dicke setzen (comp.activeSheetMetalRule, VOR dem Feature) → Skizze → createBaseFlangeInput(profil) → Ergebnis prüfen (Komponente,
    Dicke, Blechkörper). Jeder Fehler baut Skizze/Feature wieder ab und stellt Regel und Aktivierung zurück; mit falscher Dicke wird nie
    weitergearbeitet. → Blechkörper. createBaseFlangeInput ist laut Autodesk «Preview». NICHT live geprüft."""
    if dicke_mm is None or not (0.1 <= float(dicke_mm) <= 20.0):
        raise AdapterFehler("Ungültige Blechdicke %s mm (erlaubt 0.1–20 mm) – das Grundblech wird nicht gebaut." % dicke_mm)
    dicke_mm = float(dicke_mm)
    fehler = schleifen_pruefen(schleifen_mm)
    if fehler:
        raise AdapterFehler(fehler + " Das Grundblech wird nicht gebaut.")
    ff = getattr(comp.features, "flangeFeatures", None)
    if ff is None or not hasattr(ff, "createBaseFlangeInput"):
        raise AdapterFehler("FlangeFeatures.createBaseFlangeInput fehlt in dieser Fusion-Version – kein Grundblech möglich.")
    rb = Rueckbau("Grundblech")
    root = design().rootComponent
    root_vorher = None if _gleiche(comp, root) else root.bRepBodies.count
    try:
        regel_alt = comp.activeSheetMetalRule
    except Exception:
        regel_alt = None
    regel_gesetzt, regel, regel_neu = False, None, False
    try:
        with _Aktiviert(_occurrence_von(comp)):
            regel, regel_neu = regel_fuer_dicke(comp, dicke_mm)
            comp.activeSheetMetalRule = regel
            regel_gesetzt = True
            if not _gleiche(comp.activeSheetMetalRule, regel):
                raise AdapterFehler("Die Blechregel liess sich der Komponente nicht zuweisen.")
            vorher = comp.bRepBodies.count
            sk = rb.merke(comp.sketches.add(comp.xYConstructionPlane))
            for poly in schleifen_mm:
                n = len(poly)
                for i in range(n):
                    a_, b_ = poly[i], poly[(i + 1) % n]
                    pa, pb = adsk.core.Point3D.create(a_[0] / 10.0, a_[1] / 10.0, 0), adsk.core.Point3D.create(b_[0] / 10.0, b_[1] / 10.0, 0)
                    if len(a_) >= 4:          # Bogen durch (mx, my) – gekrümmte Kante im Grundriss
                        sk.sketchCurves.sketchArcs.addByThreePoints(pa, adsk.core.Point3D.create(a_[2] / 10.0, a_[3] / 10.0, 0), pb)
                    else:
                        sk.sketchCurves.sketchLines.addByTwoPoints(pa, pb)
            _testfehler("grundblech_skizze")
            prof = None
            for i in range(sk.profiles.count):
                p_ = sk.profiles.item(i)
                try:
                    schleifen = p_.profileLoops.count
                except Exception:
                    schleifen = 1
                if schleifen == len(schleifen_mm):
                    prof = p_
                    break
            if prof is None:
                raise AdapterFehler("Aus dem Verlauf entstand keine geschlossene Fläche in der Skizze (%d Profil(e))." % sk.profiles.count)
            # Dokumentierte Form: createBaseFlangeInput(profile) – OHNE Dickenparameter (die Dicke kommt aus der aktiven Blechregel).
            # Die Listen-Formen sind nur Rückfall für abweichende Preview-Stände; alle Antworten stehen im Fehlertext.
            antworten, feat = [], None
            for name in ("Profil", "Liste", "ObjectCollection"):
                arg = prof
                if name == "Liste":
                    arg = [prof]
                elif name == "ObjectCollection":
                    arg = adsk.core.ObjectCollection.create()
                    arg.add(prof)
                try:
                    inp = ff.createBaseFlangeInput(arg)
                except Exception as e:
                    antworten.append("%s: %s" % (name, (str(e).strip().splitlines() or [type(e).__name__])[-1]))
                    continue
                if inp is None:
                    antworten.append("%s: Fusion lieferte keine Eingabe" % name)
                    continue
                _eigenschaften_einmal("BaseFlangeInput", inp)
                try:
                    feat = rb.merke(ff.add(inp))
                except Exception as e:
                    antworten.append("%s add: %s" % (name, (str(e).strip().splitlines() or [type(e).__name__])[-1]))
                    continue
                if feat is not None:
                    break                   # genau EIN Feature – kein weiterer Versuch, auch wenn der Körper woanders entstand
                antworten.append("%s add: kein Feature" % name)
            if feat is None:
                raise AdapterFehler("Das Grundblech liess sich nicht erzeugen. Fusion meldet: " + " | ".join(antworten))
            _testfehler("grundblech_feature")
            if comp.bRepBodies.count <= vorher:
                woanders = ""
                if root_vorher is not None and root.bRepBodies.count > root_vorher:
                    woanders = " – er entstand in der Root-Komponente"
                raise AdapterFehler("Der Basisflansch liegt nicht in der Zielkomponente «%s»%s." % (getattr(comp, "name", "?"), woanders))
            body = comp.bRepBodies.item(comp.bRepBodies.count - 1)
            probleme = grundblech_pruefen(comp, body, dicke_mm, root_vorher)
            if probleme:
                raise AdapterFehler("Das Grundblech ist fehlerhaft: " + " ".join(probleme))
            logger.info("Grundblech erzeugt", komponente=getattr(comp, "name", "?"), dicke_mm=dicke_mm, regel=getattr(regel, "name", "?"))
            return body
    except Exception as e:
        if regel_gesetzt and regel_alt is not None:
            try:
                comp.activeSheetMetalRule = regel_alt
            except Exception:
                logger.warnung("Vorherige Blechregel nicht wiederhergestellt")
        # Eine in DIESEM Aufruf neu angelegte Regel gehört zum Rückbau. Ist sie noch aktiv (neue Komponente ohne vorherige Regel), wird sie gelöscht,
        # sobald die Komponente entfernt ist (komponente_entfernen).
        if regel_neu and regel is not None:
            if regel_alt is not None or not regel_gesetzt:
                rb.objekte.insert(0, regel)            # zuerst angelegt → zuletzt gelöscht (umgekehrte Reihenfolge)
            else:
                _NACH_KOMPONENTE.append((getattr(comp, "entityToken", None), regel))
        rb.abbrechen(e)


def zylinderradien_mm(body):
    """Radien (mm) der Zylinderflächen eines Körpers, sortiert."""
    r = []
    for f in body.faces:
        if flaechentyp(f) == "zylinder":
            try:
                r.append(round(f.geometry.radius * 10.0, 4))
            except Exception:
                pass
    return sorted(set(r))


def _signatur(fn):
    """Tatsächliche Signatur einer Fusion-API-Methode (Python-Hülle in adsk/fusion.py) – für die Ursachenanalyse im Live-Test."""
    import inspect
    try:
        s = str(inspect.signature(fn))
    except Exception:
        s = "?"
    try:
        d = " ".join((getattr(fn, "__doc__", "") or "").split())[:240]
    except Exception:
        d = ""
    return s + ((" – " + d) if d else "")


def blech_gerollt(comp, radius_mm, winkel_grad, breite_mm, dicke_mm):
    """PROTOTYP (Korrekturauftrag Phase 3/8): gerolltes Blechsegment als ECHTER Blechkörper – Konturflansch aus einem offenen Kreisbogen
    (Radius auf der Skizzenseite, Bogenwinkel) über die Breite entlang Y, Blechregel mit Soll-Dicke. Fusions API für den Konturflansch ist
    unklar dokumentiert (Preview); es werden mehrere Aufrufformen versucht und ALLE Antworten gemeldet. Ergebnisprüfung: Blechkörper, zwei
    Zylinderflächen mit Radiusdifferenz = Dicke. Jeder Fehler baut zurück. → Körper. NICHT live geprüft."""
    import math
    if not (radius_mm > 2 * dicke_mm > 0 and 0 < winkel_grad < 360 and breite_mm > 0):
        raise AdapterFehler("Gerolltes Blech: ungültige Masse (Radius > 2 × Dicke, 0 < Winkel < 360°, Breite > 0).")
    ff = getattr(comp.features, "flangeFeatures", None)
    if ff is None:
        raise AdapterFehler("FlangeFeatures fehlt – kein gerolltes Blech möglich.")
    rb = Rueckbau("Gerolltes Blech")
    regel_alt = getattr(comp, "activeSheetMetalRule", None)
    try:
        with _Aktiviert(_occurrence_von(comp)):
            regel, regel_neu = regel_fuer_dicke(comp, dicke_mm)
            if regel_neu and regel_alt is not None:
                rb.merke(regel)
            comp.activeSheetMetalRule = regel
            vorher = comp.bRepBodies.count
            sk = rb.merke(comp.sketches.add(comp.xZConstructionPlane))
            mitte = adsk.core.Point3D.create(0, 0, 0)
            start = adsk.core.Point3D.create(radius_mm / 10.0, 0, 0)
            bogen = sk.sketchCurves.sketchArcs.addByCenterStartSweep(mitte, start, math.radians(winkel_grad))
            antworten, feat = [], None
            breite = _vi_mm(breite_mm)
            formen = []
            # Live 0.4.57: Path.create(native Kurve) → «getObjectPath(sketchCurve …)» in einer AKTIVIERTEN Unterkomponente. Deshalb zusätzlich die
            # Kurve im Kontext der Occurrence (Proxy). Alle Formen werden versucht, alle Antworten gemeldet (Ursachenanalyse, nicht live geprüft).
            occ = _occurrence_von(comp)
            kurven = [("Bogen", bogen)]
            if occ is not None:
                try:
                    kurven.append(("Bogen-Proxy", bogen.createForAssemblyContext(occ)))
                except Exception as e:
                    antworten.append("Proxy: %s" % ((str(e).strip().splitlines() or ["?"])[-1][:100]))
            for kn, k in kurven:
                try:
                    formen.append(("Path(%s)" % kn, adsk.fusion.Path.create(k, adsk.fusion.ChainedCurveOptions.noChainedCurves)))
                except Exception as e:
                    antworten.append("Path(%s): %s" % (kn, (str(e).strip().splitlines() or ["?"])[-1][:100]))
            pfade = [(n, f) for n, f in formen]
            for kn, k in kurven:
                oc = adsk.core.ObjectCollection.create()
                oc.add(k)
                formen += [(kn, k), ("ObjectCollection(%s)" % kn, oc), ("Liste(%s)" % kn, [k])]
            formen += [("Liste(%s)" % n, [f]) for n, f in pfade]
            # Live 0.4.59 – tatsächliche Signatur: createContourFlangeInput(profiles: list[Profile], distance: ValueInput). Ein offener Bogen ergibt
            # in sketch.profiles KEIN Profil; das offene Profil liefert Component.createOpenProfile(curves, chainCurves). Diese Form zuerst.
            try:
                offen = comp.createOpenProfile(bogen, False)
                formen.insert(0, ("Liste(offenes Profil)", [offen]))
            except Exception as e:
                antworten.append("createOpenProfile: %s" % ((str(e).strip().splitlines() or ["?"])[-1][:100]))
            for methode in ("createContourFlangeInput", "createBaseFlangeInput"):
                fn = getattr(ff, methode, None)
                if fn is None:
                    antworten.append("%s fehlt" % methode)
                    continue
                sig = _signatur(fn)
                antworten.insert(0, "Signatur %s: %s" % (methode, sig))
                logger.info("API-Signatur", methode=methode, signatur=sig)
                for name, arg in formen:
                    for mit_breite in (True, False):
                        try:
                            inp = fn(arg, breite) if mit_breite else fn(arg)
                        except Exception as e:
                            antworten.append("%s(%s%s): %s" % (methode, name, ", Breite" if mit_breite else "", (str(e).strip().splitlines() or ["?"])[-1][:100]))
                            continue
                        if inp is None:
                            continue
                        _eigenschaften_einmal("Konturflansch-Eingabe " + methode, inp)
                        if not mit_breite:
                            setze(inp, ["distance", "setDistance", "setDistanceExtent", "extent", "width"], breite)
                        try:
                            feat = rb.merke(ff.add(inp))
                        except Exception as e:
                            antworten.append("%s(%s) add: %s" % (methode, name, (str(e).strip().splitlines() or ["?"])[-1][:100]))
                            continue
                        if feat is not None:
                            break
                    if feat is not None:
                        break
                if feat is not None:
                    break
            if feat is None or comp.bRepBodies.count <= vorher:
                raise AdapterFehler("Fusion hat kein gerolltes Blech erzeugt – Konturflansch mit keiner der versuchten Aufrufformen möglich "
                                    "(Ursache offen: API-Verwendung oder in dieser Fusion-Version nicht unterstützt). Antworten: " + " | ".join(antworten[:24]))
            _testfehler("gerollt_feature")
            body = comp.bRepBodies.item(comp.bRepBodies.count - 1)
            radien = zylinderradien_mm(body)
            probleme = koerper_pruefen(body)
            if getattr(body, "isSheetMetal", None) is False:
                probleme.append("kein Blechkörper")
            if len(radien) != 2 or abs(abs(radien[1] - radien[0]) - dicke_mm) > 0.005:
                probleme.append("Zylinderradien %s statt Radiusdifferenz %.2f mm" % (radien, dicke_mm))
            if probleme:
                raise AdapterFehler("Gerolltes Blech fehlerhaft: " + "; ".join(probleme))
            logger.info("Gerolltes Blech erzeugt (Prototyp)", radien=radien, winkel=winkel_grad, breite=breite_mm)
            return body
    except Exception as e:
        rb.abbrechen(e)


# ------------------------------------------------------------------ Bauweise «eigene Geometrie» (Profil-Engine, Auftrag Kantenwerkzeug) – NICHT live geprüft
PROFIL_ATTR = "profil"


def _p3(o, x, y, p):
    """2D-Profilpunkt (mm) → Fusion-Point3D (cm) im Rahmen O/X/Y (mm, Einheitsvektoren)."""
    q = [o[i] + p[0] * x[i] + p[1] * y[i] for i in range(3)]
    return adsk.core.Point3D.create(q[0] / 10.0, q[1] / 10.0, q[2] / 10.0)


def _umriss_zeichnen(sk, umriss, o, x, y):
    linien, boegen = sk.sketchCurves.sketchLines, sk.sketchCurves.sketchArcs
    for el in umriss:
        if el[0] == "linie":
            linien.addByTwoPoints(sk.modelToSketchSpace(_p3(o, x, y, el[1])), sk.modelToSketchSpace(_p3(o, x, y, el[2])))
        else:
            boegen.addByThreePoints(sk.modelToSketchSpace(_p3(o, x, y, el[1])), sk.modelToSketchSpace(_p3(o, x, y, el[2])),
                                    sk.modelToSketchSpace(_p3(o, x, y, el[3])))


def _profil_waehlen(sk, flaeche_mm2):
    bester, abw = None, None
    for i in range(sk.profiles.count):
        pr = sk.profiles.item(i)
        try:
            a = pr.areaProperties().area * 100.0
        except Exception:
            continue
        d = abs(a - flaeche_mm2)
        if abw is None or d < abw:
            bester, abw = pr, d
    if bester is None or abw > max(0.01, 1e-4 * flaeche_mm2):
        raise AdapterFehler("Der Querschnitt ergab in der Skizze keine passende geschlossene Fläche (Soll %.2f mm²)." % flaeche_mm2)
    return bester


def _extrudieren_geprueft(comp, prof, laenge_mm, operation, koerper, soll_mm3, rb):
    """Extrusion um laenge_mm; Richtung so gewählt, dass das Volumen um soll_mm3 wächst (±0.1 %). Falsche Richtung wird verworfen."""
    ef = comp.features.extrudeFeatures
    vol0 = _comp_volumen(comp) or 0.0
    versuche = []
    for vz in (1.0, -1.0):
        ei = ef.createInput(prof, operation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(vz * laenge_mm / 10.0))
        if koerper is not None:
            try:
                ei.participantBodies = [koerper]
            except Exception:
                pass
        try:
            f_ = ef.add(ei)
        except Exception as e:
            versuche.append("Richtung %+g: %s" % (vz, (str(e).strip().splitlines() or ["?"])[-1][:120]))
            continue
        dv = ((_comp_volumen(comp) or 0.0) - vol0) * 1000.0
        if abs(dv - soll_mm3) <= max(0.05, 1e-3 * soll_mm3):
            return rb.merke(f_)
        versuche.append("Richtung %+g: Volumen %+.3f mm³ statt %+.3f mm³" % (vz, dv, soll_mm3))
        p_ = _loeschen(f_)
        if p_:
            raise AdapterFehler("Verworfene Extrusion nicht entfernbar: " + p_)
    raise AdapterFehler("Die Profil-Extrusion passt nicht (%s)." % "; ".join(versuche))


def _flaechenarten_pruefen(body):
    """Nur Ebenen und Zylinder (mathematisch abwickelbar) dürfen entstehen – sonst ist die eigene Geometrie fehlerhaft."""
    typen = sorted({flaechentyp(f) for f in body.faces})
    falsch = [t for t in typen if t not in ("eben", "zylinder")]
    return ["unerwartete Flächenart(en) %s im Profilkörper" % ", ".join(falsch)] if falsch else []


def profil_attribut(body):
    try:
        a = body.attributes.itemByName(ATTR_GRUPPE, PROFIL_ATTR)
        return json.loads(a.value) if a else None
    except Exception:
        return None


def _profil_attribut_setzen(body, daten):
    try:
        a = body.attributes.itemByName(ATTR_GRUPPE, PROFIL_ATTR)
        if a:
            a.deleteMe()
        if daten is not None:
            body.attributes.add(ATTR_GRUPPE, PROFIL_ATTR, json.dumps(daten))
    except Exception:
        logger.warnung("Profil-Attribut nicht gesetzt")


def profil_koerper(comp, profil, dicke_mm, ri_mm, k, breite_mm, name="Profilteil"):
    """PROTOTYP: neuer Körper aus einem Profil (z. B. Zylindersegment: core/profil_engine.segment_profil) – Querschnitt in der XZ-Ebene, Extrusion
    entlang Y um breite_mm. Geprüft: Querschnitt ohne Selbstschnitt, Volumen = exakt, nur Ebenen/Zylinder mit den Soll-Radien. Das Profil wird am
    Körper gespeichert (eigene Abwicklung). KEIN Fusion-Blechkörper. → Körper. Testfehler: eigen_nach_extrusion. NICHT live geprüft."""
    from ..core import profil_engine as pe
    try:
        q = pe.querschnitt(profil, dicke_mm, ri_mm, k)
    except pe.ProfilFehler as e:
        raise AdapterFehler("Profil: %s" % e)
    probleme = pe.pruefen(q)
    if probleme:
        raise AdapterFehler("Profil nicht baubar: " + "; ".join(probleme))
    rb = Rueckbau("Profilteil «%s»" % name)
    o, x, y = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    try:
        with _Aktiviert(_occurrence_von(comp)):
            n0 = comp.bRepBodies.count
            sk = rb.merke(comp.sketches.add(comp.xZConstructionPlane))
            _umriss_zeichnen(sk, q["umriss"], o, x, y)
            prof = _profil_waehlen(sk, q["flaeche_mm2"])
            feat = _extrudieren_geprueft(comp, prof, breite_mm, adsk.fusion.FeatureOperations.NewBodyFeatureOperation, None, q["flaeche_mm2"] * breite_mm, rb)
            _testfehler("eigen_nach_extrusion")
            if comp.bRepBodies.count != n0 + 1:
                raise AdapterFehler("Die Extrusion ergab %d statt 1 neuen Körper." % (comp.bRepBodies.count - n0))
            body = comp.bRepBodies.item(comp.bRepBodies.count - 1)
            bb = body.boundingBox
            e = (0.0, 1.0, 0.0) if bb.maxPoint.y > -bb.minPoint.y else (0.0, -1.0, 0.0)
            vergleich = pe.rueckvergleich(q, breite_mm, body.volume * 1000.0, zylinderradien_mm(body))
            probleme = koerper_pruefen(body) + _flaechenarten_pruefen(body) + ([] if vergleich["ok"] else vergleich["texte"])
            if probleme:
                raise AdapterFehler("Profilteil fehlerhaft: " + "; ".join(probleme))
            try:
                body.name = name
            except Exception:
                pass
            _profil_attribut_setzen(body, {"profil": profil, "t": dicke_mm, "ri": ri_mm, "k": k, "breite": breite_mm, "O": o, "X": x, "Y": y, "E": e})
            markieren(feat, {"eigeneGeometrie": 1, "profil": profil})
            logger.info("Profilteil erzeugt (eigene Geometrie)", name=name, zuschnitt=round(q["zuschnitt"], 3), breite=breite_mm)
            return body
    except Exception as ex:
        rb.abbrechen(ex)


def _ende_des_profils(attr, edge, t):
    """Liegt die Kante am Ende oder Anfang der gespeicherten Profil-Mittellinie? → (seite, vorzeichen) oder (None, None)."""
    from ..core import bend_geometry as bg
    import math
    if not attr or not attr.get("X"):
        return None, None
    res = bg.berechne(0.0, attr["profil"], attr["t"], attr["ri"], attr["k"])
    pfad = res["pfad"]
    o, x, y, e = attr["O"], attr["X"], attr["Y"], attr["E"]
    p0, p1 = _punkt_mm(edge.startVertex.geometry), _punkt_mm(edge.endVertex.geometry)
    m = [(a + b) / 2.0 for a, b in zip(p0, p1)]
    th_end = 0.0
    for el in pfad:
        if el["typ"] == "bogen":
            th_end += math.radians(el["winkel"])
    for seite, p2, th in (("ende", pfad[-1]["p2"], th_end), ("anfang", pfad[0]["p1"], 0.0)):
        q = [o[i] + p2[0] * x[i] + p2[1] * y[i] for i in range(3)]
        w = [m[i] - q[i] for i in range(3)]
        w = [w[i] - sum(w[j] * e[j] for j in range(3)) * e[i] for i in range(3)]
        if math.sqrt(sum(c * c for c in w)) <= t / 2.0 + 0.05:
            links = [-math.sin(th) * x[i] + math.cos(th) * y[i] for i in range(3)]
            return seite, links
    return None, None


def eigene_folge(edge, ops, dicke_mm, ri_mm, k, markierung, hinweise=None, prototyp=False):
    """Bauweise «eigene Geometrie»: Kantenoperationen (Aufkantung, Umschlag, Folgen = Einfach-/Doppelfalz) als EIN Querschnitt aus Bögen und Linien senkrecht zu
    einer GERADEN Kante, entlang der Kante extrudiert und mit dem Körper vereinigt. Vorher geprüft: Matrix (Flächenklasse × Kantentyp, Bauweise eigen),
    Normale entlang der Kante konstant (Mantellinie), freie Aussenkante, Querschnitt ohne Selbstschnitt. Nachher: Volumenzuwachs exakt, nur
    Ebenen/Zylinder, Körper gültig. Atomar mit Rückbau. Das Profil des Körpers wird für die eigene Abwicklung fortgeschrieben, wenn die Kante am
    Profilende liegt. → erzeugte Objekte. Testfehler: eigen_nach_extrusion. NICHT live geprüft."""
    if dicke_mm is None or ri_mm is None or k is None:
        raise AdapterFehler("Für die eigene Geometrie fehlen Materialwerte (%s) – im Materialprofil eintragen." % ", ".join(
            n for n, w in (("Dicke", dicke_mm), ("Innenradius", ri_mm), ("K-Faktor", k)) if w is None))
    from ..core import geometrie_referenz as gr
    from ..core import profil_engine as pe
    from ..core import unterstuetzung as u
    hinweise = hinweise if hinweise is not None else []
    f = bezugsflaeche(edge)
    fk = u.flaechenklasse(flaechentyp(f) if f is not None else "unbekannt")
    kt = u.kantentyp(_kurventyp(edge))
    from ..core import experimentell
    for art in sorted({o_["typ"] for o_ in ops} & set(u.OPS)):
        grund = u.pruefen_bauweise(art, fk, kt, "eigen", experimentell.erlaubt(prototyp, art, fk, kt))
        if grund:
            raise AdapterFehler(grund)
    if kt != "gerade":
        raise AdapterFehler("Eigene Geometrie nur entlang einer geraden Kante (prismatisches Profil).")
    rahmen = rahmen_entlang(edge, f, 7)
    ok, txt, drehung = gr.orientierung_entlang(rahmen)
    if drehung is None or drehung > 0.05:
        raise AdapterFehler("Die Flächennormale dreht sich entlang der Kante um %.3f° – die Kante ist keine Mantellinie, ein Profil schlösse nicht überall "
                            "tangential an (Bearbeitung abgelehnt)." % (drehung or -1))
    andere = [g for g in edge.faces if not _gleiche(g, f)]
    if len(andere) != 1 or flaechentyp(andere[0]) != "eben":
        raise AdapterFehler("Die Kante ist keine freie Aussenkante mit ebener Stirnfläche – das Profil hätte keinen sauberen Anschluss.")
    start = edge.startVertex.geometry
    n = tuple(flaechennormale(f, start))
    uu = _einheit(tuple(flaechennormale(andere[0], start)))
    p0, p1 = _v(start), _v(edge.endVertex.geometry)
    e_ = _einheit(_plus(p1, p0, 1.0, -1.0))
    if abs(_skal(uu, n)) > 0.05 or abs(_skal(uu, e_)) > 0.05:
        raise AdapterFehler("Die Stirnfläche steht nicht senkrecht auf der Blechfläche – kein sauberer Profilanschluss.")
    t = dicke_mm or blechdicke_mm(edge.body)
    if not t:
        raise AdapterFehler("Blechdicke unbekannt – für die eigene Geometrie Materialprofil wählen.")
    try:
        q = pe.querschnitt(pe.ops_zu_profil(ops, t, ri_mm), t, ri_mm, k)
    except pe.ProfilFehler as ex:
        raise AdapterFehler("Profil: %s" % ex)
    probleme = pe.pruefen(q)
    if probleme:
        raise AdapterFehler("Profil nicht baubar: " + "; ".join(probleme))
    o = tuple(c * 10.0 - nn * t / 2.0 for c, nn in zip(p0, n))
    body = edge.body
    comp = body.parentComponent
    attr = profil_attribut(body)
    seite, links = _ende_des_profils(attr, edge, t) if attr else (None, None)
    war_blech = ist_blech(body)
    # Abwicklung VOR dem Bau sicherstellen (Korrektur 0.4.49, Phase 2): entweder Fusion-Blechkörper (native Abwicklung wird nach dem Bau geprüft)
    # oder Profilteil, dessen gespeichertes Profil durch die Erweiterung das GANZE Teil beschreibt. Sonst gäbe es keine verlässliche Abwicklung.
    if not war_blech and not (attr and seite == "ende"):
        raise AdapterFehler("Der Körper ist weder ein Fusion-Blechkörper noch ein Profilteil, dessen Ende an dieser Kante liegt – nach der eigenen Geometrie "
                            "gäbe es keine verlässliche Abwicklung des ganzen Teils. Nichts gebaut.")
    laenge = edge.length * 10.0
    rb = Rueckbau("Eigene Geometrie an der Kante")
    try:
        pi = comp.constructionPlanes.createInput()
        pi.setByDistanceOnPath(edge, adsk.core.ValueInput.createByReal(0.0))
        ebene = rb.merke(comp.constructionPlanes.add(pi))
        sk = rb.merke(comp.sketches.add(ebene))
        _umriss_zeichnen(sk, q["umriss"], o, uu, n)
        prof = _profil_waehlen(sk, q["flaeche_mm2"])
        n0 = comp.bRepBodies.count
        feat = _extrudieren_geprueft(comp, prof, laenge, adsk.fusion.FeatureOperations.JoinFeatureOperation, body, q["flaeche_mm2"] * laenge, rb)
        _testfehler("eigen_nach_extrusion")
        if comp.bRepBodies.count != n0:
            raise AdapterFehler("Das Profil hat sich nicht mit dem Körper vereinigt (%d statt %d Körper)." % (comp.bRepBodies.count, n0))
        neu = koerper_neu(getattr(body, "entityToken", None)) or comp.bRepBodies.item(0)
        probleme = koerper_pruefen(neu)
        art, grund = abwickelbarkeit_koerper(neu)
        if art != "exakt":
            probleme.append("Abwickelbarkeit nach dem Bau: %s (%s)" % (art, grund))
        if probleme:
            raise AdapterFehler("Ergebnis fehlerhaft: " + "; ".join(probleme))
        markieren(feat, dict(markierung or {}, eigeneGeometrie=1, ops=ops))
        if war_blech:
            hinweise.append(_native_abwicklung_absichern(comp, neu, rb))
        else:
            vz = 1.0 if _skal(n, tuple(links)) > 0 else -1.0
            attr_alt = dict(attr)
            attr["profil"] = pe.anhaengen(attr["profil"], ops, t, ri_mm, vz)
            _profil_attribut_setzen(neu, attr)
            try:
                _testfehler("eigen_validierung_abwicklung")
                _zs, vergleich = eigene_abwicklung(neu)
            except Exception:
                _profil_attribut_setzen(neu, attr_alt)
                raise
            hinweise.append("Eigene Abwicklung des GANZEN Teils geprüft: " + " | ".join(vergleich["texte"]))
        hinweise.append("Eigene Geometrie (Profil entlang der Kante): %d Biegung(en); Zuschnitt-Zugabe THEORETISCH %.2f mm (Modell ri + k·t, ri %.2f mm, "
                        "k %.2f – nicht praktisch verifiziert); Flächen nur Ebenen/Zylinder = mathematisch abwickelbar." % (
                            len(q["biegungen"]), q["zuschnitt"], ri_mm, k))
        if q["biegungen"] and abs(q["biegungen"][0]["winkel"]) < 175:
            import math
            mehr = (ri_mm + t) * math.tan(math.radians(abs(q["biegungen"][0]["winkel"])) / 2.0)
            hinweise.append("ACHTUNG Aussenmass: Höhen sind Aussenmasse, die Biegung beginnt bei der eigenen Geometrie aber noch AN der Kante (kein "
                            "Rückschnitt des Grundblechs) – das Teil ist dadurch aussen %.2f mm grösser als das Grundblech. Rückschnitt folgt." % mehr)
        return list(rb.objekte)
    except Exception as ex:
        rb.abbrechen(ex)


def _native_abwicklung_absichern(comp, body, rb):
    """Nach eigener Geometrie an einem Fusion-Blechkörper: Blechsemantik prüfen; GIBT es schon eine Abwicklung, wird sie (von Fusion nachgeführt)
    als DXF ausgegeben und STRENG geprüft. Gibt es keine, wird KEINE Prüf-Abwicklung mehr angelegt: Live 0.4.56 zeigte, dass das Löschen einer
    per API erzeugten Abwicklung (FlatPattern.deleteMe) die Komponente beschädigt (Component.flatPattern wirft «res», createFlatPattern meldet
    «already exists», Stückliste scheitert). Die native Abwicklung entsteht dann erst über «Abwicklung & DXF». Jeder Fehler wirft AdapterFehler →
    der Aufrufer baut alles zurück. → Text für den Bericht. NICHT live geprüft."""
    import os
    import tempfile
    from ..manufacturing import dxf_pruefung
    if not ist_blech(body):
        raise AdapterFehler("Nach der eigenen Geometrie ist der Körper KEIN Fusion-Blechkörper mehr (Blechsemantik verloren) – eine vollständige eigene "
                            "Abwicklung des ganzen Teils gibt es nicht, deshalb wird zurückgebaut.")
    fp, lesbar = _flatpattern_lesen(comp)
    if not lesbar:
        raise AdapterFehler(ABWICKLUNG_BESCHAEDIGT % getattr(comp, "name", "?"))
    if fp is None:
        return ("Blechkörper bleibt Fusion-Blech; native Abwicklung NICHT geprüft (es gibt noch keine – sie entsteht über «Abwicklung & DXF», "
                "eine Prüf-Abwicklung wird nicht mehr angelegt)")
    _testfehler("eigen_validierung_abwicklung")
    m = abwicklung_masse(fp)
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_pruef_"), "pruefung.dxf")
    dxf_abwicklung(fp, pfad)
    _testfehler("eigen_validierung_dxf")
    pr = dxf_pruefung.pruefe_datei_streng(pfad, m["breite"], m["laenge"])
    if not pr["ok"]:
        raise AdapterFehler("DXF der Abwicklung nach der eigenen Geometrie besteht die strenge Prüfung nicht: " + "; ".join(pr["probleme"]))
    return "Blechkörper bleibt Fusion-Blech; vorhandene Abwicklung %.1f × %.1f mm nachgeführt und DXF streng geprüft (%s)" % (
        m["breite"], m["laenge"], dxf_pruefung.zusammenfassung(pr))


def eigene_abwicklung(body):
    """Eigene 2D-Abwicklung eines Profilteils (unabhängig von Fusion Flat Pattern) mit Rückvergleich gegen den 3D-Körper.
    → (zuschnitt für dxf_writer.elemente_dxf, Rückvergleich). Ohne gespeichertes Profil: AdapterFehler («nicht unterstützt»). NICHT live geprüft."""
    from ..core import profil_engine as pe
    attr = profil_attribut(body)
    if not attr:
        raise AdapterFehler("Für diesen Körper gibt es keine eigene Abwicklung (kein Profilteil der eigenen Geometrie).")
    q = pe.querschnitt(attr["profil"], attr["t"], attr["ri"], attr["k"])
    vergleich = pe.rueckvergleich(q, attr["breite"], body.volume * 1000.0, zylinderradien_mm(body))
    art, grund = abwickelbarkeit_koerper(body)
    if art != "exakt":
        raise AdapterFehler("Eigene Abwicklung verweigert – der Körper ist nicht mathematisch abwickelbar: %s." % grund)
    if not vergleich["ok"]:
        raise AdapterFehler("Eigene Abwicklung passt nicht zum 3D-Körper (Körper nachträglich verändert?): " + "; ".join(vergleich["texte"]))
    return pe.abwicklung(q, attr["breite"], getattr(body, "name", "Profilteil")), vergleich


def grundblech_bauen(comp, laenge_mm, breite_mm, dicke_mm=1.0):
    """Rechteckiges Grundblech (Ecke im Ursprung, X = Länge, Y = Breite). Nicht live geprüft."""
    return blech_aus_profil(comp, [[(0, 0), (laenge_mm, 0), (laenge_mm, breite_mm), (0, breite_mm)]], dicke_mm)


def _oberseite(body):
    bester = None
    for f in body.faces:
        try:
            if isinstance(f.geometry, adsk.core.Plane) and flaechennormale(f)[2] > 0.99 and (bester is None or f.area > bester.area):
                bester = f
        except Exception:
            continue
    if bester is None:
        raise AdapterFehler("Die Oberseite des Grundblechs wurde nicht gefunden.")
    return bester


def kanten_nach_ketten(body, ketten, tol_mm=0.05):
    """Randkanten der Oberseite den Strecken eines Grundrissverlaufs zuordnen. ketten: {name: [((x1, y1), (x2, y2)), …]} in mm.
    → {name: [entityToken …]} in Reihenfolge der Strecken. Eine Strecke ohne passende Kante ist ein Fehler. Nicht live geprüft."""
    kanten = []
    for e in _oberseite(body).edges:
        try:
            p, q = e.startVertex.geometry, e.endVertex.geometry
            kanten.append((e, (p.x * 10, p.y * 10), (q.x * 10, q.y * 10)))
        except Exception:
            continue

    def gleich(a, b):
        return abs(a[0] - b[0]) <= tol_mm and abs(a[1] - b[1]) <= tol_mm
    out = {}
    for name, segmente in ketten.items():
        tokens = []
        for nr, (a, b) in enumerate(segmente, 1):
            treffer = [e for e, p, q in kanten if (gleich(a, p) and gleich(b, q)) or (gleich(a, q) and gleich(b, p))]
            if len(treffer) != 1:
                raise AdapterFehler("Für Strecke %d (%s) wurde %s Kante am Grundblech gefunden." % (nr, name, "keine" if not treffer else "mehr als eine"))
            tokens.append(treffer[0].entityToken)
        out[name] = tokens
    return out


def kanten_folge_bauen(tokens, ops, dicke_mm, markierung, hinweise, ohne_gehrung_frage=None):
    """Kantenfolge an mehreren Kanten (entityTokens): zusammenhängende Kanten gemeinsam (Gehrung an den Ecken), sonst je Kante. → Liste Features.
    Scheitert der gemeinsame Bau, wird NUR dann je Kante (ohne Gehrung) gebaut, wenn ohne_gehrung_frage(text) True liefert (Rückfrage an den
    Benutzer); ohne Frage-Funktion oder bei Nein wird abgebrochen. Nicht live geprüft."""
    def kante(t):
        k = _kante_aufloesen(t, None)
        if k is None:
            raise AdapterFehler("Eine Kante ist nach dem vorherigen Schritt nicht mehr auffindbar.")
        return k
    kanten = [kante(t) for t in tokens]
    erz = []
    for gruppe in gruppen_bilden(kanten):
        if len(gruppe) >= 2 and (ops[0]["typ"] != "umschlag" or len(ops) == 1):
            try:
                erz += folge_anbringen_gruppe([kante(tokens[i]) for i in gruppe], ops, dicke_mm, markierung, hinweise)
                continue
            except AdapterFehler as e:
                nrn = "+".join(str(i + 1) for i in gruppe)
                grund = str(e).splitlines()[0][:400]
                if not (ohne_gehrung_frage and ohne_gehrung_frage(gehrung_frage_text(nrn, grund))):
                    raise AdapterFehler("Kanten %s: gemeinsamer Flansch mit Gehrung nicht möglich, Bau ohne Gehrung nicht freigegeben. Grund: %s" % (nrn, grund),
                                        rueckbau_ok=e.rueckbau_ok)
                hinweise.append("Kanten %s: gemeinsamer Flansch (Gehrung) nicht möglich – auf deine Bestätigung je Kante OHNE Gehrung gebaut (Ecken stumpf). Grund: %s" % (
                    nrn, grund))
        for i in gruppe:
            erz += folge_anbringen(kante(tokens[i]), ops, dicke_mm, markierung, hinweise)
    return erz


def gehrung_frage_text(nrn, grund):
    return ("Kanten %s: Fusion kann den gemeinsamen Flansch mit Gehrung nicht bauen (alles wurde zurückgebaut).\n\nGrund: %s\n\n"
            "Stattdessen je Kante OHNE Gehrung bauen? Die Ecken bleiben stumpf (kein Gehrungsschnitt, Spalt oder Überlappung möglich)." % (nrn, grund))


def grundblech_kante(body, seite_y="max"):
    """Lange Randkante (parallel zur X-Achse) der Oberseite eines Grundblechs: an der Seite Y = max (Standard) bzw. min. Nicht live geprüft."""
    bester = None
    for f in body.faces:
        try:
            if isinstance(f.geometry, adsk.core.Plane) and flaechennormale(f)[2] > 0.99 and (bester is None or f.area > bester.area):
                bester = f
        except Exception:
            continue
    if bester is None:
        raise AdapterFehler("Die Oberseite des Grundblechs wurde nicht gefunden.")
    kanten = [e for e in bester.edges if _kurventyp(e) == "linie" and abs(e.boundingBox.maxPoint.y - e.boundingBox.minPoint.y) < 1e-6]
    if not kanten:
        raise AdapterFehler("Keine lange Randkante am Grundblech gefunden.")
    return (max if seite_y == "max" else min)(kanten, key=lambda e: e.boundingBox.minPoint.y)


def zeitleiste_stand():
    """Anzahl der Zeitleisten-Einträge (für zeitleiste_gruppieren). Nicht live geprüft."""
    try:
        return design().timeline.count
    except Exception:
        return None


def zeitleiste_gruppieren(von, name):
    """Alles, was seit `von` in der Zeitleiste entstand, zu EINER Gruppe zusammenfassen (ein Strg+Z, übersichtlich benannt). → True/False;
    ein Fehler hier ändert nie das Modell. Nicht live geprüft (Timeline.timelineGroups.add)."""
    try:
        if von is None:
            return False
        tl = design().timeline
        bis = tl.count - 1
        if bis - von < 1:
            return False
        g = tl.timelineGroups.add(von, bis)
        g.name = name
        return True
    except Exception:
        logger.warnung("Zeitleisten-Gruppe nicht angelegt")
        return False


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
def _gauss_max(face, n=3):
    """Grösste |Gausssche Krümmung| (1/mm²) auf einem n×n-Raster des Parameterbereichs (Rastermitten, Ränder ausgespart) – Stichprobe für
    Freiformflächen. Einheit: Fusion liefert Krümmungen in 1/cm → k1·k2 in 1/cm² → ÷ 100 = 1/mm². → (gmax oder None, Anzahl nicht auswertbarer
    Punkte). Jeder ausgefallene Punkt ist eine Unsicherheit (nicht stillschweigend übergangen). Nicht live geprüft."""
    ausfall, gmax = 0, None
    try:
        ev = face.evaluator
        rng = ev.parametricRange()
        u0, v0, u1, v1 = rng.minPoint.x, rng.minPoint.y, rng.maxPoint.x, rng.maxPoint.y
    except Exception:
        return None, n * n
    for i in range(n):
        for j in range(n):
            try:
                p = adsk.core.Point2D.create(u0 + (u1 - u0) * (i + 0.5) / n, v0 + (v1 - v0) * (j + 0.5) / n)
                ok, _r, k1, k2 = ev.getCurvature(p)
                if not ok:
                    ausfall += 1
                    continue
                g = abs(k1 * k2) / 100.0
                gmax = g if gmax is None else max(gmax, g)
            except Exception:
                ausfall += 1
    return gmax, ausfall


def abwickelbarkeit_koerper(body):
    """Exakt / angenähert / nicht / unsicher nach den Flächentypen des GANZEN Körpers (auch Übergänge zwischen Flächentypen) über
    core/geometrie_referenz.abwickelbarkeit. Nicht erkannte Flächen und ausgefallene Stichproben → 'unsicher' (nie 'exakt'). → (art, Begründung)."""
    from ..core import geometrie_referenz as gr
    typen, gmax, unsicher = [], None, False
    try:
        flaechen = list(body.faces)
    except Exception:
        return "unsicher", "Flächen des Körpers nicht lesbar"
    for f in flaechen:
        t = flaechentyp(f)
        typen.append(t)
        if t == "freiform":
            g, ausfall = _gauss_max(f)
            unsicher = unsicher or ausfall > 0 or g is None
            if g is not None:
                gmax = g if gmax is None else max(gmax, g)
    return gr.abwickelbarkeit(typen, gmax, stichprobe_unsicher=unsicher)


def _ist_seitenflaeche(f, t_cm):
    """Stirn-/Seitenfläche eines Blechs: ihre Breite (Fläche / längste Kante) ist nicht grösser als die Blechdicke. Nicht live geprüft."""
    try:
        laengste = max(e.length for e in f.edges)
        return laengste > 0 and f.area / laengste <= t_cm * 1.05
    except Exception:
        return False


def stationaere_flaeche_waehlen(body):
    """Feste Regel statt Zufall: die grösste EBENE Fläche des Blechkörpers; bei gleicher Grösse (Ober-/Unterseite) die mit der Normale am
    weitesten nach +Z, dann die mit dem kleinsten Punkt (x, y, z). → Fläche oder None."""
    kandidaten = []
    t_cm = (blechdicke_mm(body) or 0.0) / 10.0
    for f in body.faces:
        try:
            if not isinstance(f.geometry, adsk.core.Plane):
                continue
            if t_cm and _ist_seitenflaeche(f, t_cm):
                continue                     # Live 0.4.60: «stationaryFace is not valid, a side face may have been selected»
            n = flaechennormale(f)
            p = f.pointOnFace
            kandidaten.append(((-round(f.area, 6), -round(n[2], 6), round(p.x, 6), round(p.y, 6), round(p.z, 6)), f))
        except Exception:
            continue
    if not kandidaten:
        return None
    kandidaten.sort(key=lambda x: x[0])
    return kandidaten[0][1]


def abwicklung(comp, stationaere_flaeche=None, body=None, fusion_entscheidet=False):
    """Abwicklung der Komponente: eine vorhandene wird verwendet (Fusion führt sie selbst nach), sonst neu erzeugt. Vorher geprüft: gültiger
    Blechkörper in GENAU dieser Komponente, stationäre Fläche gehört zu diesem Körper und ist eben. Ohne Fläche: feste Auswahlregel
    (stationaere_flaeche_waehlen). → (FlatPattern, neu erzeugt). API: Component.flatPattern/createFlatPattern(BRepFace). Nicht live geprüft."""
    fp, lesbar = _flatpattern_lesen(comp)
    if not lesbar:
        raise AdapterFehler(ABWICKLUNG_BESCHAEDIGT % getattr(comp, "name", "?"))
    if fp:
        logger.info("Abwicklung bereits vorhanden – sie wird verwendet", komponente=getattr(comp, "name", "?"))
        return fp, False
    if not hasattr(comp, "createFlatPattern"):
        raise AdapterFehler("Diese Fusion-Version kann per API keine Abwicklung erzeugen.")
    if body is None and stationaere_flaeche is not None:
        body = stationaere_flaeche.body
    if body is None:
        bleche = [b for b in comp.bRepBodies if ist_blech(b)]
        if not bleche:
            raise AdapterFehler("Kein gültiger Blechkörper in der Komponente «%s» – keine Abwicklung möglich." % getattr(comp, "name", "?"))
        if len(bleche) > 1:
            raise AdapterFehler("Die Komponente «%s» hat %d Blechkörper – bitte die feststehende Fläche des gewünschten Körpers wählen." % (getattr(comp, "name", "?"), len(bleche)))
        body = bleche[0]
    if not _gleiche(body.parentComponent, comp):
        raise AdapterFehler("Der Körper gehört nicht zur Komponente «%s» – keine Abwicklung." % getattr(comp, "name", "?"))
    if not ist_blech(body):
        raise AdapterFehler("Kein gültiger Blechkörper: «%s» ist kein Blech (Fusion-Arbeitsbereich «Blech»)." % getattr(body, "name", "?"))
    probleme = koerper_pruefen(body)
    if probleme:
        raise AdapterFehler("Kein gültiger Blechkörper: " + " ".join(probleme))
    art, grund = abwickelbarkeit_koerper(body)
    if art == "unsicher" and fusion_entscheidet:
        # Eigener, ausdrücklich gewählter Prüfmodus: Fusion versucht die Abwicklung, OHNE mathematischen Nachweis der Abwickelbarkeit.
        logger.warnung("Abwicklung im Prüfmodus «Fusion entscheidet» (kein Nachweis)", grund=grund)
    elif art != "exakt":
        # Keine verzerrte Abwicklung als exakte DXF: Näherungsverfahren sind nicht umgesetzt; «unsicher» nur im Prüfmodus «Fusion entscheidet».
        raise AdapterFehler("%s: %s. Es wird keine Abwicklung/DXF erzeugt%s." % (
            "Abwickelbarkeit nicht nachgewiesen" if art == "unsicher" else "Nicht verzerrungsfrei abwickelbar (mathematisch)", grund,
            " (eine Näherungsabwicklung mit Verzerrungsangabe ist ein eigener, noch fehlender Modus)" if art == "naeherung" else
            (" – nur im Prüfmodus «Fusion entscheidet» möglich, dann ohne Nachweis gekennzeichnet" if art == "unsicher" else "")))
    if stationaere_flaeche is None:
        stationaere_flaeche = stationaere_flaeche_waehlen(body)
        if stationaere_flaeche is None:
            raise AdapterFehler("Stationäre Fläche fehlt: Der Blechkörper hat keine ebene Hauptfläche (nur Seitenflächen) – Fusion verlangt eine "
                                "ebene feststehende Fläche. Ein rein gerolltes Segment hat keine; dafür gibt es die eigene Abwicklung.")
        logger.info("Stationäre Fläche nach fester Regel gewählt (grösste ebene Fläche, Normale +Z zuerst)")
    else:
        if not _gleiche(stationaere_flaeche.body, body):
            raise AdapterFehler("Stationäre Fläche ungeeignet: Sie gehört zu einem anderen Körper.")
        if not isinstance(stationaere_flaeche.geometry, adsk.core.Plane):
            raise AdapterFehler("Stationäre Fläche ungeeignet: Sie ist nicht eben.")
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
    """Abwicklung als DXF exportieren und den Export WIRKLICH prüfen (execute() ausgeführt, Datei neu geschrieben und nicht leer).
    Optionen ausdrücklich: Splines bleiben Splines (isSplineConvertedToPolyline = False, falls die Eigenschaft existiert). Einheit/Massstab legt
    Fusion fest (Massstab 1:1; die Einheit folgt laut Erfahrung den Dokumenteinheiten – die Gegenprobe dxf_pruefung meldet cm statt mm als
    Fehler). Eine alte Datei gleichen Namens wird vorher entfernt, damit sie nie als neuer Export gilt. Nicht live geprüft."""
    import os
    em = design().exportManager
    if not hasattr(em, "createDXFFlatPatternExportOptions"):
        raise AdapterFehler("Diese Fusion-Version kann die Abwicklung nicht als DXF exportieren.")
    ordner = os.path.dirname(os.path.abspath(dateipfad))
    if not os.path.isdir(ordner):
        raise AdapterFehler("Exportordner fehlt: %s" % ordner)
    if not os.access(ordner, os.W_OK):
        raise AdapterFehler("In den Exportordner kann nicht geschrieben werden: %s" % ordner)
    if os.path.exists(dateipfad):
        try:
            os.remove(dateipfad)
        except OSError as e:
            raise AdapterFehler("Die alte DXF-Datei lässt sich nicht ersetzen (%s): %s" % (e, dateipfad))
    opt = em.createDXFFlatPatternExportOptions(dateipfad, fp)
    if opt is None:
        raise AdapterFehler("Fusion hat keine DXF-Exportoptionen geliefert.")
    gesetzt = setze(opt, ["isSplineConvertedToPolyline"], False)
    logger.info("DXF-Exportoptionen", splines_als_splines=gesetzt, pfad=os.path.basename(dateipfad))
    try:
        ok = em.execute(opt)
    except Exception as e:
        raise AdapterFehler("Der DXF-Export ist fehlgeschlagen (Fusion: %s): %s" % ((str(e).strip().splitlines() or ["?"])[-1], dateipfad))
    if not ok or not os.path.exists(dateipfad) or os.path.getsize(dateipfad) == 0:
        raise AdapterFehler("Fusion hat die DXF-Datei nicht erzeugt: %s" % dateipfad)
    return dateipfad


# ------------------------------------------------------------------ Rundblech als Drehkörper
def drehkoerper(comp, kontur_mm, name, winkel_grad=360.0):
    """Geschlossene Querschnittskontur (r, z in mm) um die Z-Achse drehen → neuer Körper (KEIN Blechkörper).
    Ohne Einschnitte; Abwicklung/Umformung beurteilt forming/forming.py."""
    sk = comp.sketches.add(comp.xZConstructionPlane)
    sk.name = name
    linien = sk.sketchCurves.sketchLines
    # Skizze auf XZ: Skizzen-x = Welt-x, Skizzen-y = −Welt-z (Fusion-Konvention); Profil liegt bei x ≥ 0.
    # Punkt (r, z, mr, mz): Segment zum nächsten Punkt als Bogen durch (mr, mz) – ergibt beim Drehen Kugel-/Torusflächen (Testkörper doppelt gekrümmt).
    def P(r, z):
        return adsk.core.Point3D.create(units.mm_zu_cm(r), -units.mm_zu_cm(z), 0)
    for k, a_ in enumerate(kontur_mm):
        b_ = kontur_mm[(k + 1) % len(kontur_mm)]
        a, b = P(a_[0], a_[1]), P(b_[0], b_[1])
        if a.distanceTo(b) <= 1e-7:
            continue
        if len(a_) >= 4:
            sk.sketchCurves.sketchArcs.addByThreePoints(a, P(a_[2], a_[3]), b)
        else:
            linien.addByTwoPoints(a, b)
    if sk.profiles.count < 1:
        raise AdapterFehler("Querschnitt des Rundblechs ist nicht geschlossen.")
    prof = max(list(sk.profiles), key=lambda p: p.areaProperties().area)
    rv = comp.features.revolveFeatures
    inp = rv.createInput(prof, comp.zConstructionAxis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.setAngleExtent(False, adsk.core.ValueInput.createByString("%g deg" % winkel_grad))     # < 360: Teilzylinder/-kegel mit geraden Mantelkanten
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
def occurrence_von(comp):
    """Öffentlich: Occurrence einer Komponente (None = Root)."""
    return _occurrence_von(comp)


def quader_komponente(parent, name, x_mm, y_mm, z_mm, parameter=None):
    """Neue Komponente mit einem Quader (Ursprung in der Ecke; Höhe optional über einen neuen Benutzerparameter) – für Testdetails/Live-Test.
    Nicht live geprüft."""
    occ = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    hoehe = adsk.core.ValueInput.createByString("%g mm" % z_mm)
    if parameter:
        up = design().userParameters
        if up.itemByName(parameter) is None:
            up.add(parameter, adsk.core.ValueInput.createByString("%g mm" % z_mm), "mm", "Live-Test")
        hoehe = adsk.core.ValueInput.createByString(parameter)
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(x_mm / 10.0, y_mm / 10.0, 0))
    comp.features.extrudeFeatures.addSimple(sk.profiles.item(0), hoehe, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    return comp


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
    neue_param = [p.name for p in design().userParameters if p.name not in param_vorher]
    if len(neu) != 1:
        probleme = entfernen_bericht(neu) + parameter_entfernen(neue_param)
        raise AdapterFehler("Import lieferte %d neue Komponenten (erwartet 1)%s." % (len(neu), " – wieder entfernt" if not probleme else
                                                                                 " – ACHTUNG: nicht vollständig entfernt (%s)" % "; ".join(probleme)),
                            rueckbau_ok=not probleme)
    return neu[0], neue_param


def parameter_entfernen(namen):
    """Beim Import neu entstandene Benutzerparameter löschen (nur diese). → Liste der Probleme. deleteMe() → False = noch benutzt/nicht gelöscht."""
    probleme = []
    try:
        up = design().userParameters
    except Exception:
        return ["Benutzerparameter nicht lesbar"]
    for n in namen or []:
        try:
            p = up.itemByName(n)
            if p is None:
                continue
            if p.deleteMe() is False or up.itemByName(n) is not None:
                probleme.append("Parameter «%s» noch vorhanden" % n)
        except Exception as e:
            probleme.append("Parameter «%s»: %s" % (n, (str(e).strip().splitlines() or ["?"])[-1][:80]))
    return probleme


def detail_einsetzen(f3d, ziel_comp, T_mm, nach_import=None, integrieren_token=None):
    """3D-Detail ATOMAR einsetzen: importieren → ausrichten (T_mm, 4×4 mm) → nach_import(occ, neue_param) (Parameter, Markierung, Prüfungen;
    liefert ein dict) → optional in den Zielkörper integrieren. Jeder Fehler in jeder Phase entfernt die importierte Occurrence und die beim Import
    neu entstandenen Parameter wieder (Integration baut ihre Basis-/Kombinieren-Features selbst zurück). → dict mit occ, neue_param, cf, warnungen
    und den Werten aus nach_import. Testfehler-Stellen: detail_import, detail_ausrichten, detail_parameter, detail_basis, detail_kombinieren.
    Nicht live geprüft."""
    erg = {"occ": None, "neue_param": [], "cf": None, "warnungen": []}
    phase = "Import"
    try:
        occ, neue_param = detail_importieren(f3d, ziel_comp)
        erg.update(occ=occ, neue_param=neue_param)
        _testfehler("detail_import")
        phase = "Ausrichten"
        occ.transform = matrix_fusion(T_mm)
        _testfehler("detail_ausrichten")
        phase = "Parameter setzen"
        if nach_import is not None:
            erg.update(nach_import(occ, neue_param) or {})
        _testfehler("detail_parameter")
        if integrieren_token:
            phase = "Integration"
            ziel_body = koerper_neu(integrieren_token)
            if ziel_body is None:
                raise AdapterFehler("Der Zielkörper ist nach dem Import nicht mehr auffindbar.")
            erg["cf"], erg["warnungen"] = detail_integrieren(occ, ziel_body, neue_param)
            erg["occ"] = None
        return erg
    except Exception as e:
        logger.ausnahme("Detail einsetzen", phase=phase)
        probleme = (entfernen_bericht([erg["occ"]]) if erg["occ"] is not None else []) + parameter_entfernen(erg["neue_param"])
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % ((str(e).strip().splitlines() or [type(e).__name__])[-1])
        raise AdapterFehler("%s: %s%s" % (phase, text, (" – Import wieder entfernt." if erg["occ"] is not None or erg["neue_param"] else "") if not probleme else
                                          " – ACHTUNG: Rückbau unvollständig (%s), bitte mit Strg+Z zurücknehmen." % "; ".join(probleme)),
                            rueckbau_ok=not probleme)


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
    war_blech = ist_blech(ziel_body)
    try:
        tbm = adsk.fusion.TemporaryBRepManager.get()
        kopien = [tbm.copy(b) for b in werkzeuge]
        bf = comp.features.baseFeatures.add()
        erzeugt.append(bf)
        _testfehler("detail_basis")
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
        _testfehler("detail_kombinieren")
        body = koerper_neu(token)
        if body is None:
            raise AdapterFehler("Zielkörper nach dem Vereinigen nicht auffindbar.")
        for p in koerper_pruefen(body):
            raise AdapterFehler("Nach dem Vereinigen: " + p)
        if abs(body.volume - vol_vorher) < 1e-9:
            raise AdapterFehler("Das Detail hat den Körper nicht verändert (kein Volumenzuwachs) – Position/Ausrichtung prüfen.")
        if war_blech and not ist_blech(body):
            # Ein Kombinieren-Erfolg beweist keinen gültigen Blechkörper: die Integration wird zurückgenommen (Korrekturauftrag Phase 6).
            raise AdapterFehler("Nach dem Vereinigen ist der Zielkörper kein Blechkörper mehr – Integration zurückgenommen. Das Detail bitte ohne Integration "
                                "(eigene Komponente) einsetzen.")
        elif ist_blech(body):
            warnungen.append("Zielkörper ist ein Blechkörper: bitte Abwicklung/Biegezonen nach dem Vereinigen prüfen (nicht live geprüft).")
    except Exception as e:
        logger.ausnahme("Detail-Integration")
        zurueck = entfernen(erzeugt)
        text = str(e) if isinstance(e, AdapterFehler) else "Fusion meldet: %s" % (str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__)
        raise AdapterFehler(text + (" – die Änderungen wurden zurückgenommen." if zurueck else
                                    " – ACHTUNG: Rückbau unvollständig, bitte mit Strg+Z zurücknehmen."), rueckbau_ok=zurueck)
    # Aufräumen erst nach Erfolg: die Kopie im Basis-Feature hängt nicht an der Import-Komponente. Ergebnis geprüft (deleteMe → False = Fehlschlag).
    p_ = _loeschen(occ)
    if p_:
        warnungen.append("Die leere Import-Komponente liess sich nicht entfernen (%s) – bitte von Hand löschen." % p_)
    for p_ in parameter_entfernen(neue_param):
        warnungen.append("Beim Import entstandener Parameter bleibt stehen (%s)." % p_)
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


def kollision_pruefen(occ, andere_koerper):
    """Kollision des eingesetzten Details mit anderen Körpern. Zuerst ECHTE Volumenüberschneidung (Design.analyzeInterference); geht das nicht,
    nur die grobe Vorprüfung über Begrenzungsrahmen – ausdrücklich so gekennzeichnet. → {'art': 'volumen'|'grob', 'treffer': [(name, mm³ oder None)]}.
    Nicht live geprüft (createInterferenceInput/analyzeInterference)."""
    try:
        d = design()
        coll = adsk.core.ObjectCollection.create()
        coll.add(occ)
        for b in andere_koerper:
            coll.add(b)
        ii = d.createInterferenceInput(coll)
        try:
            ii.areCoincidentFacesIncluded = False
        except Exception:
            pass
        res = d.analyzeInterference(ii)
        namen = {getattr(b, "name", "?") for b in andere_koerper}
        treffer = []
        for r in res:
            n1, n2 = getattr(r.entityOne, "name", "?"), getattr(r.entityTwo, "name", "?")
            gegen = n2 if n1 not in namen else n1
            try:
                vol = r.interferenceBody.volume * 1000.0
            except Exception:
                vol = None
            treffer.append((gegen, vol))
        return {"art": "volumen", "treffer": treffer}
    except Exception:
        logger.warnung("Volumen-Interferenz nicht möglich – nur grobe Vorprüfung (Begrenzungsrahmen)")
        return {"art": "grob", "treffer": [(n, None) for n in kollision(occ, andere_koerper)]}


def _messobjekte(o):
    """MeasureManager misst BRep-Objekte, KEINE Occurrence (Live 0.4.57: «Abstand Detail↔Fläche nicht messbar»). Occurrence → ihre Körper (Proxys im
    Baugruppenkontext); Fläche/Körper einer Unterkomponente ohne Kontext → zusätzlich als Proxy über deren Occurrence."""
    if o is None:
        return []
    if hasattr(o, "transform") and hasattr(o, "bRepBodies") and hasattr(o, "component"):
        try:
            return [o.bRepBodies.item(i) for i in range(o.bRepBodies.count)]
        except Exception:
            return []
    out = [o]
    try:
        if getattr(o, "assemblyContext", None) is None:
            comp = o.body.parentComponent if hasattr(o, "body") else getattr(o, "parentComponent", None)
            occ = _occurrence_von(comp) if comp is not None else None
            if occ is not None:
                out.insert(0, o.createForAssemblyContext(occ))
    except Exception:
        pass
    return out


def abstand_mm(a, b, gruende=None):
    """Kleinster Abstand zweier Fusion-Objekte (Körper, Occurrence, Fläche) in mm über den MeasureManager; 0 = Berührung oder Überschneidung.
    None = nicht messbar; die Fusion-Antworten stehen dann in `gruende` (Liste, optional). Nicht live geprüft."""
    gruende = gruende if gruende is not None else []
    xa, xb = _messobjekte(a), _messobjekte(b)
    if not xa or not xb:
        gruende.append("keine messbaren Objekte (%s / %s)" % (type(a).__name__, type(b).__name__))
        return None
    bester = None
    for x in xa:
        for y in xb:
            try:
                v = app().measureManager.measureMinimumDistance(x, y).value * 10.0
            except Exception as e:
                gruende.append("%s↔%s: %s" % (type(x).__name__, type(y).__name__, (str(e).strip().splitlines() or ["?"])[-1][:100]))
                continue
            bester = v if bester is None else min(bester, v)
    return bester


def kollision(occ, andere_koerper):
    """GROBE Vorprüfung über Begrenzungsrahmen-Überlappung (Rückfall von kollision_pruefen; sagt nichts über echte Überschneidung)."""
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


# ------------------------------------------------------------------ Profil lesen (Vorlage lernen) – nur lesen, NICHT live geprüft
def _zahl_aus(obj):
    """Wert eines ModelParameter/ValueInput/Zahl in Fusion-Einheiten (cm bzw. rad) oder None."""
    if obj is None:
        return None
    for n in ("value", "realValue"):
        v = getattr(obj, n, None)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return float(obj)
    return None


def _feature_werte(ent, art):
    """Winkel (Grad), Länge, Radius (mm) eines Flansch-/Saum-Features: erst über Eigenschaften des Features, dann über seine Parameter."""
    erg = {"winkel_grad": None, "laenge_mm": None, "radius_mm": None}
    for feld, namen in (("winkel_grad", ("angle", "flangeAngle")), ("laenge_mm", ("distance", "height", "length", "flangeHeight")),
                        ("radius_mm", ("bendRadius", "radius"))):
        for n in namen:
            v = _zahl_aus(getattr(ent, n, None))
            if v is not None:
                erg[feld] = math.degrees(v) if feld == "winkel_grad" else v * 10.0
                break
    if None in (erg["laenge_mm"],) or (art == "flansch" and erg["winkel_grad"] is None):
        try:
            from ..core import lernen
            token = ent.entityToken
            for p in design().allParameters:
                try:
                    if p.createdBy is None or p.createdBy.entityToken != token:
                        continue
                except Exception:
                    continue
                feld = lernen.feld_zu_rolle("%s %s" % (getattr(p, "role", ""), getattr(p, "name", "")))
                v = _zahl_aus(p)
                if feld == "winkel" and erg["winkel_grad"] is None and v is not None:
                    erg["winkel_grad"] = math.degrees(v)
                elif feld == "laenge" and erg["laenge_mm"] is None and v is not None:
                    erg["laenge_mm"] = v * 10.0
                elif feld == "radius" and erg["radius_mm"] is None and v is not None:
                    erg["radius_mm"] = v * 10.0
        except Exception as ex:
            logger.warnung("Parameter des Features nicht lesbar", fehler=ex)
    return erg


def profil_features_lesen():
    """Flansch- und Saum-Features der Zeitleiste in Reihenfolge → (Liste für core.lernen, Hinweise). Verändert nichts."""
    d = design()
    tl = d.timeline
    out, hinweise = [], []
    for i in range(tl.count):
        try:
            ent = tl.item(i).entity
            typ = str(getattr(ent, "objectType", "")).lower()
        except Exception:
            continue
        if "hem" in typ and "feature" in typ:
            art = "umschlag"
        elif "flange" in typ and "contour" not in typ and "feature" in typ:
            art = "flansch"
        else:
            if "contourflange" in typ:
                hinweise.append("«%s» (Konturflansch) wird nicht gelesen." % getattr(ent, "name", "Feature"))
            continue
        werte = _feature_werte(ent, art)
        try:
            gesp = bool(getattr(ent, "isFlipped", False))
        except Exception:
            gesp = False
        out.append(dict(werte, art=art, name=getattr(ent, "name", "Feature %d" % (i + 1)), gespiegelt=gesp))
        if len(out) <= 3:       # Diagnose für die erste Rückmeldung: welche Eigenschaften/Parameter hat Fusion tatsächlich?
            logger.info("Profil lesen", art=art, typ=typ, eigenschaften=_namen(ent), werte=werte)
    return out, hinweise


def _koerper_token(body):
    try:
        return (getattr(body, "nativeObject", None) or body).entityToken
    except Exception:
        return None


def kante_gehoert_zu(edge, body):
    """Liegt die Kante auf dem gewählten Körper? True/False; None, wenn es sich nicht feststellen lässt (z. B. veraltete Verweise während der
    Vorschau) – dann wird die Kante nicht beanstandet. Vergleich über den entityToken des nativen Körpers."""
    a, b = _koerper_token(getattr(edge, "body", None)), _koerper_token(body)
    if a is None or b is None:
        return None
    return a == b


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


def ordner_pfad(pfad_namen, anlegen=True):
    """Ordner «a/b/c» im aktiven Fusion-Projekt (ab der Wurzel); fehlende Ebenen werden angelegt. → (Ordner, [neu angelegte Namen]). Nicht live geprüft."""
    projekt = adsk.core.Application.get().data.activeProject
    if projekt is None:
        raise AdapterFehler("Kein aktives Projekt in Fusion. Bitte zuerst im Datenfenster das Projekt öffnen.")
    ordner, neu = projekt.rootFolder, []
    for name in pfad_namen:
        sub = _unterordner(ordner, name)
        if sub is None:
            if not anlegen:
                raise AdapterFehler("Der Ordner «%s» wurde nicht gefunden." % "/".join(pfad_namen))
            sub = ordner.dataFolders.add(name)
            neu.append(name)
        ordner = sub
    return ordner, neu


def ordner_liste(tiefe=2):
    """Vorhandene Ordner des aktiven Projekts (bis `tiefe` Ebenen) als Namenslisten – zur Auswahl. Nicht live geprüft."""
    projekt = adsk.core.Application.get().data.activeProject
    if projekt is None:
        return []
    alle = []
    _ordner_rekursiv(projekt.rootFolder, tiefe - 1, [], alle)
    return sorted([pfad for _, pfad in alle], key=lambda p: [x.lower() for x in p])


def dokument_in_ordner_speichern(pfad_namen):
    """Aktives Dokument im Ordner «a/b/c» ablegen (Ordner werden bei Bedarf angelegt). Ungespeichert: saveAs; schon dort: nichts; sonst eine KOPIE. → Text. Nicht live geprüft."""
    ziel, neu = ordner_pfad(pfad_namen, True)
    text = ("Ordner angelegt: %s. " % "/".join(neu)) if neu else ""
    doc = adsk.core.Application.get().activeDocument
    datei = doc.dataFile
    if datei is not None and datei.parentFolder is not None and datei.parentFolder.id == ziel.id:
        return text + "Das Dokument liegt schon im Ordner «%s»." % "/".join(pfad_namen)
    if not doc.saveAs(doc.name, ziel, "", ""):
        raise AdapterFehler("Fusion hat das Dokument nicht gespeichert.")
    return text + (("Das Dokument wurde im Ordner «%s» gespeichert." % "/".join(pfad_namen)) if datei is None else
                   "Eine Kopie wurde im Ordner «%s» gespeichert (die bisherige Datei bleibt, wo sie war)." % "/".join(pfad_namen))


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

"""Zentrale Geometrie-Referenz (reine Rechnung, ohne Fusion testbar).

Jede Bearbeitung (Flansch, Umschlag, Versatz, Abwicklung, 3D-Detail) beschreibt ihren Ansatzort mit EINER Referenz statt eigener Ad-hoc-Logik:
gewählte Fläche/Kante, Ankerpunkt, Flächen- und Kurventyp, LOKALE Normale und Tangente (nie stillschweigend global Z), lokaler Rahmen,
Seite der Bearbeitung, Krümmung, Blechdicke/-regel und eine Kennung, mit der veraltete Auswahlen erkannt werden.
Die Fusion-Seite (geometry/fusion_adapter.referenz_aus_fusion) füllt die Referenz; Auswahl/UI und Rechnung bleiben getrennt.

Begriffe (Nachtauftrag 4.11.2026): A gekrümmte KANTE (Kreis/Bogen/Kurve, Fläche kann eben sein), B gekrümmte FLÄCHE (Zylinder, Kegel, …),
C gekrümmter BLECHKÖRPER (gerollte/gebogene Schale mit Dicke).
Längen in mm, Richtungen als Einheitsvektoren (Tupel)."""
import math

from ..details import frames

FLAECHENTYPEN = ("eben", "zylinder", "kegel", "kugel", "torus", "freiform", "unbekannt")
KURVENTYPEN = ("linie", "kreis", "bogen", "ellipse", "spline", "andere")
EINFACH_GEKRUEMMT = ("zylinder", "kegel")          # abwickelbar (Gausssche Krümmung 0)
DOPPELT_GEKRUEMMT = ("kugel", "torus")             # nicht exakt abwickelbar


def _skal(a, b):
    return sum(x * y for x, y in zip(a, b))


def _plus(a, b, fb=1.0):
    return tuple(x + fb * y for x, y in zip(a, b))


def _einheit(v):
    L = math.sqrt(_skal(v, v))
    if L < 1e-12:
        raise ValueError("Nullvektor")
    return tuple(x / L for x in v)


# ------------------------------------------------------------------ Referenz
def referenz(flaeche_typ, punkt, normale, tangente=None, kurve_typ=None, kruemmung=None, seite=1, dicke_mm=None, regel=None, kennung=None):
    """Referenz bauen. normale = LOKALE Flächennormale am Punkt (Aussenseite), tangente = Kantenrichtung bzw. erste Flächenrichtung am Punkt.
    kruemmung: {'k1', 'k2'} (1/mm, Hauptkrümmungen) oder None. seite: +1 = auf der Normalenseite bearbeiten, −1 = Gegenseite.
    kennung: {'flaeche': token, 'kante': token, 'flaeche_mm2', 'kante_mm'} für die Veraltet-Prüfung. → dict mit 'rahmen' (lokales System)."""
    if flaeche_typ not in FLAECHENTYPEN:
        raise ValueError("Unbekannter Flächentyp «%s»" % flaeche_typ)
    n = _einheit(normale)
    if tangente is None:                                   # irgendeine Senkrechte, aber reproduzierbar
        hilf = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
        tangente = frames.kreuz(n, hilf)
    r = frames.rahmen_aus_normale(punkt, n, tangente)
    if seite < 0:
        r = {"origin": r["origin"], "x": r["x"], "y": [-c for c in r["y"]], "z": [-c for c in r["z"]]}
    return {"flaeche": flaeche_typ, "kurve": kurve_typ, "punkt": tuple(punkt), "normale": n, "rahmen": r, "seite": 1 if seite >= 0 else -1,
            "kruemmung": kruemmung, "dicke_mm": dicke_mm, "regel": regel, "kennung": dict(kennung or {})}


def klasse(ref):
    """Fall A/B/C bzw. 'eben' für Meldungen und die Unterstützungsmatrix: 'eben_gerade' | 'gekruemmte_kante' | 'zylinder' | 'kegel' | 'freiform'."""
    f, k = ref["flaeche"], ref.get("kurve")
    if f == "eben":
        return "eben_gerade" if k in (None, "linie") else "gekruemmte_kante"
    if f in ("zylinder", "kegel"):
        return f
    return "freiform"


def ist_veraltet(alt, neu, tol_mm=0.01):
    """Ist eine gemerkte Referenz noch dieselbe Auswahl? → Liste der Gründe (leer = gültig). Vergleicht Kennung (Tokens), Flächengrösse,
    Kantenlänge und Flächentyp – eine veränderte Fläche wird nicht stillschweigend weiterverwendet."""
    gruende = []
    if neu is None:
        return ["Die gewählte Fläche/Kante existiert nicht mehr."]
    a, b = alt.get("kennung", {}), neu.get("kennung", {})
    for k in ("flaeche", "kante"):
        if a.get(k) and b.get(k) and a[k] != b[k]:
            gruende.append("Die gewählte %s ist eine andere geworden." % ("Fläche" if k == "flaeche" else "Kante"))
    if alt.get("flaeche") != neu.get("flaeche"):
        gruende.append("Flächentyp geändert (%s → %s)." % (alt.get("flaeche"), neu.get("flaeche")))
    for k, was in (("flaeche_mm2", "Flächengrösse"), ("kante_mm", "Kantenlänge")):
        if a.get(k) is not None and b.get(k) is not None and abs(a[k] - b[k]) > max(tol_mm, 1e-6 * abs(a[k])):
            gruende.append("%s geändert (%.3f → %.3f)." % (was, a[k], b[k]))
    return gruende


# ------------------------------------------------------------------ analytische Normalen (Gegenprobe für Live-Tests, Fixtures)
def zylinder_normale(achse_punkt, achse_richtung, p):
    """Aussennormale eines Zylinders an p (radial, senkrecht zur Achse)."""
    d = _einheit(achse_richtung)
    w = _plus(p, achse_punkt, -1.0)
    return _einheit(_plus(w, d, -_skal(w, d)))


def kegel_normale(spitze, achse_richtung, halbwinkel_grad, p):
    """Aussennormale eines Kegels (Spitze, Achse zur Öffnung hin, halber Öffnungswinkel) an p: radial gekippt um den Halbwinkel."""
    d = _einheit(achse_richtung)
    w = _plus(p, spitze, -1.0)
    radial = _einheit(_plus(w, d, -_skal(w, d)))
    a = math.radians(halbwinkel_grad)
    return _einheit(_plus(tuple(math.cos(a) * x for x in radial), d, -math.sin(a)))


def winkel_grad(a, b):
    c = max(-1.0, min(1.0, _skal(_einheit(a), _einheit(b))))
    return math.degrees(math.acos(c))


# ------------------------------------------------------------------ Abwickelbarkeit
def gauss(k1, k2):
    return k1 * k2


def abwickelbarkeit(flaechentypen, freiform_gauss_max=None, tol=1e-7):
    """Lässt sich ein Körper aus diesen Flächentypen EXAKT abwickeln? → ('exakt' | 'naeherung' | 'nicht', Begründung).
    eben/zylinder/kegel: exakt (Gausssche Krümmung 0). kugel/torus: nicht (doppelt gekrümmt). freiform: nur 'naeherung', wenn die gemessene
    Gausssche Krümmung (1/mm²) an allen Stichproben ≈ 0 ist – sonst 'nicht'. 'unbekannt' gilt als 'nicht' (keine Aussage = keine exakte DXF)."""
    typen = set(flaechentypen)
    doppelt = sorted(typen & set(DOPPELT_GEKRUEMMT))
    if doppelt:
        return "nicht", "doppelt gekrümmte Fläche(n) (%s): Gausssche Krümmung ≠ 0, nicht verzerrungsfrei abwickelbar" % ", ".join(doppelt)
    if "unbekannt" in typen:
        return "nicht", "Flächentyp unbekannt – keine Aussage zur Abwickelbarkeit"
    if "freiform" in typen:
        if freiform_gauss_max is not None and abs(freiform_gauss_max) < tol:
            return "naeherung", "Freiformfläche mit Gaussscher Krümmung ≈ 0 an den Stichproben (max. %.2e 1/mm²) – abwickelbar, Exaktheit nicht belegt" % freiform_gauss_max
        return "nicht", "Freiformfläche mit Gaussscher Krümmung ≠ 0 (max. %s 1/mm²)" % ("?" if freiform_gauss_max is None else "%.2e" % freiform_gauss_max)
    return "exakt", "nur ebene, zylindrische und konische Flächen (abwickelbar)"


# ------------------------------------------------------------------ Versatz-Richtung eindeutig definieren
VERSATZARTEN = {
    "tangential": "Biegelinie in der Blechebene senkrecht zur Kante verschoben (+ = nach innen zum Blech, − = nach aussen)",
    "normal": "konstanter Abstand entlang der lokalen Flächennormale",
    "radial": "radial zur Zylinder-/Kegelachse",
}


def versatz_definition(ref, versatz_mm, art="tangential"):
    """Welche Richtung meint ein Versatz an dieser Referenz? → (Richtung als Einheitsvektor im Raum, Text für den Benutzer) oder ValueError, wenn die
    Kombination fachlich nicht eindeutig/unterstützt ist. Der Biegelinien-Versatz (tangential) ist nur in einer EBENEN Blechfläche definiert."""
    if art not in VERSATZARTEN:
        raise ValueError("Unbekannte Versatzart «%s»" % art)
    r = ref["rahmen"]
    if art == "tangential":
        if ref["flaeche"] != "eben":
            raise ValueError("Ein Biegelinien-Versatz ist nur an Kanten EBENER Blechflächen definiert – die Fläche ist «%s». Auf gekrümmten Flächen "
                             "müsste der Streifen der Krümmung folgen; das baut das Add-in nicht (keine verzerrte Ersatzgeometrie)." % ref["flaeche"])
        richtung = tuple(r["y"])
    elif art == "normal":
        richtung = tuple(r["z"])
    else:
        if ref["flaeche"] not in ("zylinder", "kegel"):
            raise ValueError("Ein radialer Versatz braucht eine Zylinder- oder Kegelfläche (gewählt: «%s»)." % ref["flaeche"])
        richtung = tuple(r["z"])
    text = "Versatz %+g mm: %s; Bezug: lokale Richtung an der gewählten %s (nicht global X/Y/Z)." % (
        versatz_mm, VERSATZARTEN[art], "Kante" if ref.get("kurve") else "Fläche")
    return richtung, text

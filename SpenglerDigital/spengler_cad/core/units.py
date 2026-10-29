"""Einheiten: intern rechnet das Add-in in mm und Grad.

Fusion rechnet in seiner API intern in cm (Längen) und Bogenmass (Winkel).
Jede Übergabe an Fusion läuft über diese Funktionen – nie über verstreute
Faktoren im Code.
"""
import math
import re

MM_PRO_CM = 10.0

LAENGEN_EINHEITEN = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}
WINKEL_EINHEITEN = {"deg": 1.0, "°": 1.0, "grad": 1.0, "rad": 180.0 / math.pi}


class EinheitFehler(ValueError):
    pass


def mm_zu_cm(mm):
    return float(mm) / MM_PRO_CM


def cm_zu_mm(cm):
    return float(cm) * MM_PRO_CM


def grad_zu_rad(g):
    return math.radians(float(g))


def rad_zu_grad(r):
    return math.degrees(float(r))


_WERT = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([a-z°]*)\s*$", re.I)


def laenge_mm(text, standard="mm"):
    """'25', '25 mm', '2.5cm', '0,025 m' → mm. Wirft EinheitFehler bei Unsinn."""
    if isinstance(text, (int, float)):
        return float(text) * LAENGEN_EINHEITEN[standard]
    m = _WERT.match(str(text))
    if not m:
        raise EinheitFehler("«%s» ist keine Länge (Beispiel: 25 mm)" % text)
    einheit = (m.group(2) or standard).lower()
    if einheit not in LAENGEN_EINHEITEN:
        raise EinheitFehler("Unbekannte Längeneinheit «%s» (erlaubt: mm, cm, m, in)" % m.group(2))
    return float(m.group(1).replace(",", ".")) * LAENGEN_EINHEITEN[einheit]


def winkel_grad(text, standard="deg"):
    if isinstance(text, (int, float)):
        return float(text) * WINKEL_EINHEITEN[standard]
    m = _WERT.match(str(text))
    if not m:
        raise EinheitFehler("«%s» ist kein Winkel (Beispiel: 90°)" % text)
    einheit = (m.group(2) or standard).lower()
    if einheit not in WINKEL_EINHEITEN:
        raise EinheitFehler("Unbekannte Winkeleinheit «%s» (erlaubt: deg, °, rad)" % m.group(2))
    return float(m.group(1).replace(",", ".")) * WINKEL_EINHEITEN[einheit]


def fusion_ausdruck_mm(mm):
    """Wert als Fusion-Ausdruck mit expliziter Einheit – unabhängig von den Dokumenteinheiten."""
    return "%s mm" % _zahl(mm)


def fusion_ausdruck_grad(g):
    return "%s deg" % _zahl(g)


def _zahl(v):
    v = round(float(v), 6)
    return ("%f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def anzeigen_mm(mm, stellen=1):
    """Werkstattgerechte Anzeige: 1'234.5 mm (Schweizer Tausendertrennung)."""
    s = ("{:,.%df}" % stellen).format(float(mm)).replace(",", "'")
    return s + " mm"

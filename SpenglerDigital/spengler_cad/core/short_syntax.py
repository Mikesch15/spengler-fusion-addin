"""Kurzschrift für Kantenoperationen – gleich wie in der App (kern/details.js) und im Prototyp 0.1.

Folge ab der gewählten Blechkante: Winkel Schenkel Winkel Schenkel …
  90      Abkanten 90° zur Sichtseite (+), -90 nach hinten
  U+ / U- Umschlag 180° zur Sichtseite / nach hinten
  90r5    Innenradius 5 mm für diese Biegung (sonst Materialstandard)
Erweiterung für Vorlagen: Schenkel, Winkel und Radius dürfen Parameternamen oder
Ausdrücke ohne Leerzeichen sein, z. B. «90 H U+ u+4*t» oder «{w} H» (Winkel als Ausdruck in {}).

Die Kurzschrift ist nur eine Eingabeform. Gespeichert wird immer die strukturierte
Operationsliste (siehe models.py); dieselbe Kern-Engine bedient Standard- und Expertenmodus.
"""
import re

from .expressions import AusdruckFehler, berechne

_WINKEL = re.compile(r"^(U[+-]?|[+-]?\d+(?:[.,]\d+)?|\{[^{}]+\})(?:r(.+))?$", re.I)
_ZAHL = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


class KurzschriftFehler(ValueError):
    pass


def _zahl_oder_ausdruck(s):
    s = s.strip()
    if _ZAHL.match(s):
        return float(s.replace(",", "."))
    return s  # Ausdruck, wird erst beim Auflösen berechnet


def zerlege(text):
    """Kurzschrift → Liste von Operationen (Werte als Zahl oder Ausdruckstext).

    Operation: {"typ": "flansch"|"umschlag", "winkel": .., "laenge": .., "radius": None|..}
    Winkel beim Umschlag: +180 / -180.
    """
    t = [x for x in re.split(r"[\s;]+", str(text).replace("−", "-").strip()) if x]
    if not t:
        raise KurzschriftFehler("Die Abkantfolge ist leer.")
    if len(t) % 2:
        raise KurzschriftFehler("Je Biegung braucht es einen Winkel und eine Schenkellänge, z. B. «90 25 U+ 7».")
    ops = []
    for i in range(0, len(t), 2):
        m = _WINKEL.match(t[i])
        if not m:
            raise KurzschriftFehler("«%s» ist kein Winkel (Zahl, U+, U- oder {Ausdruck})." % t[i])
        w = m.group(1)
        umschlag = w.upper().startswith("U")
        if umschlag:
            winkel = -180.0 if w.endswith("-") else 180.0
        elif w.startswith("{"):
            winkel = w[1:-1].strip()
        else:
            winkel = float(w.replace(",", "."))
        laenge = _zahl_oder_ausdruck(t[i + 1])
        if isinstance(laenge, float) and laenge <= 0:
            raise KurzschriftFehler("«%s» ist keine gültige Schenkellänge (muss grösser als 0 sein)." % t[i + 1])
        radius = _zahl_oder_ausdruck(m.group(2)) if m.group(2) else None
        ops.append({"typ": "umschlag" if umschlag else "flansch", "winkel": winkel, "laenge": laenge, "radius": radius})
    return ops


def _txt(v):
    if isinstance(v, (int, float)):
        v = round(float(v), 3)
        return str(int(v)) if v == int(v) else ("%g" % v)
    return str(v)


def als_text(ops):
    """Operationsliste → Kurzschrift (Umkehrung von zerlege)."""
    teile = []
    for op in ops:
        if op["typ"] == "umschlag":
            w = "U-" if _negativ(op["winkel"]) else "U+"
        elif isinstance(op["winkel"], str):
            w = "{%s}" % op["winkel"]
        else:
            w = _txt(op["winkel"])
        if op.get("radius") not in (None, ""):
            w += "r" + _txt(op["radius"])
        teile += [w, _txt(op["laenge"])]
    return " ".join(teile)


def _negativ(w):
    return (isinstance(w, (int, float)) and w < 0) or (isinstance(w, str) and w.strip().startswith("-"))


def aufloesen(ops, werte):
    """Ausdrücke mit Parameterwerten (mm/Grad, inkl. t, ri) berechnen → nur noch Zahlen."""
    out = []
    for i, op in enumerate(ops, 1):
        try:
            w = berechne(op["winkel"], werte)
            L = berechne(op["laenge"], werte)
            r = None if op.get("radius") in (None, "") else berechne(op["radius"], werte)
            vs = None if op.get("versatz") in (None, "") else berechne(op["versatz"], werte)
        except AusdruckFehler as e:
            raise KurzschriftFehler("Schritt %d: %s" % (i, e))
        if op["typ"] == "umschlag":
            w = -180.0 if w < 0 else 180.0
        d = {"typ": op["typ"], "winkel": w, "laenge": L, "radius": r}
        for feld in ("bezug", "lage"):      # Massbezug (Höhe von aussen/innen/tangential) und Lage der Biegung – nur wenn gewählt
            if op.get(feld):
                d[feld] = op[feld]
        if vs:      # Versatz der Biegung von der Startkante (mm, + nach innen / − nach aussen); 0 = keiner
            d["versatz"] = vs
        out.append(d)
    return out


def schritte(folge):
    """Kompatibel zum Prototyp 0.1: '90 25 U+ 7' → [{winkel, laenge, art, ri}] (nur Zahlen)."""
    try:
        ops = zerlege(folge)
    except KurzschriftFehler as e:
        raise ValueError(str(e))
    out = []
    for op in ops:
        if any(isinstance(op[k], str) for k in ("winkel", "laenge", "radius")):
            raise ValueError("Ohne Vorlage sind nur Zahlen erlaubt (keine Parameter): %s" % als_text([op]))
        out.append({"winkel": op["winkel"], "laenge": op["laenge"],
                    "art": "umschlag" if op["typ"] == "umschlag" else "abkanten", "ri": op["radius"]})
    return out

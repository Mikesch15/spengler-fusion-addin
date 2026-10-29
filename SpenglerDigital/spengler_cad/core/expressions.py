"""Sichere Parameterausdrücke für Vorlagen, z. B. «H + 2*t» oder «max(u, 3*t)».

Kein eval(): nur Zahlen, Parameternamen, + - * / ** %, Klammern und eine kleine
Funktionsliste. Unbekannte Namen sind ein Fehler – es wird nichts geraten.
"""
import ast
import math
import re

FUNKTIONEN = {
    "min": min, "max": max, "abs": abs, "round": round,
    "sqrt": math.sqrt, "sin": lambda g: math.sin(math.radians(g)),
    "cos": lambda g: math.cos(math.radians(g)), "tan": lambda g: math.tan(math.radians(g)),
}
KONSTANTEN = {"pi": math.pi}
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RESERVIERT = set(FUNKTIONEN) | set(KONSTANTEN) | {"t", "ri", "k"}


class AusdruckFehler(ValueError):
    pass


def gueltiger_name(name):
    return bool(NAME.match(name or "")) and name not in FUNKTIONEN and name not in KONSTANTEN


def namen_in(text):
    """Alle Variablennamen eines Ausdrucks (für Abhängigkeitsprüfung)."""
    try:
        baum = ast.parse(str(text).replace(",", "."), mode="eval")
    except SyntaxError as e:
        raise AusdruckFehler("Ausdruck «%s» ist nicht lesbar: %s" % (text, e.msg))
    out = set()
    for n in ast.walk(baum):
        if isinstance(n, ast.Name) and n.id not in FUNKTIONEN and n.id not in KONSTANTEN:
            out.add(n.id)
    return out


def berechne(text, werte):
    """Ausdruck mit den Werten {name: zahl} auswerten → float."""
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    s = str(text).strip()
    if not s:
        raise AusdruckFehler("Leerer Ausdruck")
    # Dezimalkomma nur zwischen Ziffern ersetzen (Funktionsargumente bleiben)
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    try:
        baum = ast.parse(s, mode="eval")
    except SyntaxError as e:
        raise AusdruckFehler("Ausdruck «%s» ist nicht lesbar: %s" % (text, e.msg))
    try:
        v = _knoten(baum.body, werte)
    except ZeroDivisionError:
        raise AusdruckFehler("Ausdruck «%s»: Division durch 0" % text)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        raise AusdruckFehler("Ausdruck «%s» ergibt keine gültige Zahl" % text)
    return float(v)


_OPS = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b,
}


def _knoten(n, werte):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        return n.value
    if isinstance(n, ast.Name):
        if n.id in KONSTANTEN:
            return KONSTANTEN[n.id]
        if n.id not in werte:
            raise AusdruckFehler("Unbekannter Parameter «%s»" % n.id)
        return float(werte[n.id])
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _knoten(n.left, werte), _knoten(n.right, werte)
        if isinstance(n.op, ast.Pow) and abs(b) > 10:
            raise AusdruckFehler("Exponent zu gross")
        return _OPS[type(n.op)](a, b)
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
        v = _knoten(n.operand, werte)
        return v if isinstance(n.op, ast.UAdd) else -v
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNKTIONEN and not n.keywords:
        return FUNKTIONEN[n.func.id](*[_knoten(a, werte) for a in n.args])
    raise AusdruckFehler("Im Ausdruck nicht erlaubt: %s" % type(n).__name__)

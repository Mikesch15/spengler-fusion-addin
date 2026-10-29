"""Vorlagen-Engine: Parameterwerte zusammenstellen, Ausdrücke auflösen, Kurzschrift ↔ Vorlage.

Standard- und Expertenmodus benutzen beide diese Engine. Standardmodus: nur Parameterwerte;
Expertenmodus: zusätzlich Operationsfolge bearbeiten (Liste oder Kurzschrift).
"""
from . import short_syntax
from .expressions import AusdruckFehler, namen_in
from .models import kopie, neue_kantenvorlage, parameter
from .validation import MATERIAL_NAMEN, pruefe_aufgeloest, pruefe_kantenvorlage, pruefe_werte


class VorlagenFehler(ValueError):
    pass


def materialwerte(material):
    """t, ri, k aus dem Materialprofil. Fehlende Werte fehlen – es wird nichts angenommen."""
    w = {}
    if material:
        if material.get("thickness") is not None:
            w["t"] = float(material["thickness"])
        if material.get("innerRadius") is not None:
            w["ri"] = float(material["innerRadius"])
        if material.get("kFactor") is not None:
            w["k"] = float(material["kFactor"])
    return w


def werte_zusammenstellen(vorlage, eingaben, material):
    """Standardwerte + Eingaben + Materialwerte. Wirft VorlagenFehler mit allen Problemen."""
    werte = {}
    for p in vorlage.get("parameters", []):
        if p.get("variable", True) and p["name"] in (eingaben or {}):
            werte[p["name"]] = eingaben[p["name"]]
        elif p.get("default") is not None:
            werte[p["name"]] = p["default"]
    fehler = pruefe_werte(vorlage.get("parameters", []), werte)
    if fehler:
        raise VorlagenFehler("\n".join(fehler))
    werte = {k: float(v) for k, v in werte.items()}
    werte.update(materialwerte(material))
    return werte


def benoetigte_materialwerte(vorlage):
    namen = set()
    for op in vorlage.get("operations", []):
        for f in ("winkel", "laenge", "radius"):
            if isinstance(op.get(f), str):
                try:
                    namen |= namen_in(op[f])
                except AusdruckFehler:
                    pass
    return namen & MATERIAL_NAMEN


def aufloesen(vorlage, eingaben, material):
    """→ (operationen_als_zahlen, warnungen). Wirft VorlagenFehler bei ungültiger Vorlage/Werten."""
    fehler, warn = pruefe_kantenvorlage(vorlage)
    if fehler:
        raise VorlagenFehler("Vorlage «%s» ist ungültig:\n%s" % (vorlage.get("name"), "\n".join(fehler)))
    fehlend = benoetigte_materialwerte(vorlage) - set(materialwerte(material))
    if fehlend:
        raise VorlagenFehler("Die Vorlage braucht Materialwerte, die im gewählten Materialprofil fehlen: %s." % ", ".join(sorted(fehlend))
                             + " (t = Dicke, ri = Innenradius, k = K-Faktor – unter Einstellungen → Materialien ergänzen)")
    werte = werte_zusammenstellen(vorlage, eingaben, material)
    try:
        ops = short_syntax.aufloesen(vorlage["operations"], werte)
    except short_syntax.KurzschriftFehler as e:
        raise VorlagenFehler(str(e))
    f2, w2 = pruefe_aufgeloest(ops, werte.get("t"))
    if f2:
        raise VorlagenFehler("\n".join(f2))
    return ops, warn + w2


def vorlage_aus_kurzschrift(name, text, standardwerte=None):
    """Expertenmodus: aus einer Kurzschrift eine neue Vorlage. Parameternamen werden als Parameter angelegt,
    deren Wert der Benutzer bestimmt (standardwerte) – es wird kein Wert erfunden."""
    ops = short_syntax.zerlege(text)
    namen = set()
    for op in ops:
        for f in ("winkel", "laenge", "radius"):
            if isinstance(op.get(f), str):
                namen |= namen_in(op[f])
    namen -= MATERIAL_NAMEN
    params = []
    for n in sorted(namen):
        params.append(parameter(n, n, "deg" if _ist_winkelname(n, ops) else "mm", (standardwerte or {}).get(n)))
    return neue_kantenvorlage(name, operations=ops, parameters=params)


def _ist_winkelname(n, ops):
    for op in ops:
        if isinstance(op.get("winkel"), str):
            try:
                if n in namen_in(op["winkel"]):
                    return True
            except AusdruckFehler:
                pass
    return False


# ------------------------------------------------------------------ Expertenmodus: Operationen bearbeiten
def op_hinzufuegen(vorlage, op, index=None):
    v = kopie(vorlage)
    ops = v["operations"]
    ops.insert(len(ops) if index is None else index, op)
    return v


def op_entfernen(vorlage, index):
    v = kopie(vorlage)
    del v["operations"][index]
    return v


def op_verschieben(vorlage, index, richtung):
    v = kopie(vorlage)
    ops = v["operations"]
    j = index + richtung
    if 0 <= index < len(ops) and 0 <= j < len(ops):
        ops[index], ops[j] = ops[j], ops[index]
    return v


def op_aendern(vorlage, index, **felder):
    v = kopie(vorlage)
    v["operations"][index].update(felder)
    return v

"""Experimentelle Freigabe ungetesteter Prototypen – getrennt von den normalen Einstellungen (Korrektur 0.4.49, Phase 3).

Im normalen Produktionsmodus ist JEDER Prototyp der Unterstützungsmatrix gesperrt; weder die Oberfläche noch die Einstellungsdatei schalten ihn frei.
Nur ein Entwickler-Override über die Umgebungsvariable SPENGLER_CAD_EXPERIMENTELL gibt EXAKT benannte Fälle frei, z. B.
    SPENGLER_CAD_EXPERIMENTELL="flansch/zylinder/gerade;umschlag/zylinder/gerade"
Format je Fall: <Bearbeitung>/<Flächenklasse>/<Kantentyp> (Namen wie in core/unterstuetzung). Ungültige, unbekannte oder nicht als Prototyp geführte
Einträge werden ignoriert – sie führen nie zu einer Freigabe. Vor jeder Ausführung eines freigegebenen Falls warnt das Werkzeug ausdrücklich."""
import os

from . import unterstuetzung as u

VARIABLE = "SPENGLER_CAD_EXPERIMENTELL"


def faelle(text=None):
    """→ frozenset gültiger Prototyp-Fälle (op, flaeche, kante). text=None: aus der Umgebungsvariable."""
    roh = os.environ.get(VARIABLE, "") if text is None else (text or "")
    gut = set()
    if not isinstance(roh, str):
        return frozenset()
    for teil in roh.replace(",", ";").split(";"):
        stuecke = [x.strip() for x in teil.strip().split("/")]
        if len(stuecke) != 3:
            continue
        op, f, k = stuecke
        if op not in u.OPS or f not in u.FLAECHEN or k not in u.KANTEN:
            continue
        if u.stand(op, f, k)[0] == "prototyp" or u.eigen(op, f, k)[0] == "prototyp":
            gut.add((op, f, k))
    return frozenset(gut)


def erlaubt(freigabe, op, flaeche, kante):
    """freigabe: True (nur Live-Test/Stub-Tests), False/None, oder eine Menge exakter Fälle. → bool."""
    if freigabe is True:
        return True
    if not freigabe or isinstance(freigabe, (str, int, float)):
        return False
    try:
        return (op, flaeche, kante) in freigabe
    except TypeError:
        return False


def warnung(faelle_):
    return ("EXPERIMENTELL – NICHT LIVE GETESTET: Folgende Prototyp-Fälle sind per Entwickler-Override (%s) freigegeben: %s. Das Ergebnis ist weder in "
            "Fusion geprüft noch fachlich freigegeben. Nur in Testdokumenten verwenden. Trotzdem ausführen?" % (
                VARIABLE, ", ".join("/".join(f) for f in sorted(faelle_))))

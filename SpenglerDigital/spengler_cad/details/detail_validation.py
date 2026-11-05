"""Prüfungen für 3D-Detailvorlagen – Vorlage selbst und Passung an eine Zielkante (ohne Fusion testbar)."""
import math

from ..core.validation import pruefe_parameter


def _vektor(v):
    return isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)


def rahmen_pruefen(frame):
    """Lokales Koordinatensystem: Ursprung + drei orthonormale Achsen."""
    if not isinstance(frame, dict):
        return "Kein lokales Koordinatensystem erfasst."
    for k in ("origin", "x", "y", "z"):
        if not _vektor(frame.get(k)):
            return "Koordinatensystem unvollständig (%s fehlt)." % k
    for k in ("x", "y", "z"):
        if abs(math.sqrt(sum(c * c for c in frame[k])) - 1) > 1e-4:
            return "Achse %s ist nicht normiert." % k
    dot = lambda a, b: sum(p * q for p, q in zip(a, b))
    if max(abs(dot(frame["x"], frame["y"])), abs(dot(frame["y"], frame["z"])), abs(dot(frame["x"], frame["z"]))) > 1e-4:
        return "Achsen des Koordinatensystems stehen nicht senkrecht aufeinander."
    return None


def pruefe_detailvorlage(v):
    fehler, warn = [], []
    if not (v.get("name") or "").strip():
        fehler.append("Die Detailvorlage braucht einen Namen.")
    if not (v.get("source") or {}).get("file"):
        fehler.append("Keine Quellgeometrie gespeichert (Fusion-Komponente fehlt).")
    a = v.get("anchor") or {}
    r = rahmen_pruefen(a.get("frame"))
    if r:
        fehler.append("Anschlussreferenz: " + r)
    if not (isinstance(a.get("edgeLength"), (int, float)) and a["edgeLength"] > 0):
        fehler.append("Anschlussreferenz: Länge der Anschlusskante fehlt.")
    f, w = pruefe_parameter(v.get("parameters", []))
    fehler += f
    warn += w
    for p in v.get("parameters", []):
        if not p.get("fusionName"):
            fehler.append("Parameter «%s»: zugehöriger Fusion-Benutzerparameter fehlt." % p.get("name"))
    c = v.get("compatibility") or {}
    if c.get("edgeLengthMin") is not None and c.get("edgeLengthMax") is not None and c["edgeLengthMin"] > c["edgeLengthMax"]:
        fehler.append("Kantenlänge: Minimum ist grösser als Maximum.")
    if not v.get("parameters"):
        warn.append("Keine variablen Parameter: die Vorlage wird unverändert eingesetzt.")
    return fehler, warn


def passung(vorlage, kante, dicke=None):
    """Passt die Detailvorlage an die Zielkante? → (passt, gruende, hinweise)."""
    gruende, hinweise = [], []
    c = vorlage.get("compatibility") or {}
    typ = c.get("edgeType") or (vorlage.get("anchor") or {}).get("edgeType") or "gerade"
    if typ == "gerade" and kante.get("kurve") != "linie":
        gruende.append("Zielkante ist nicht gerade (%s)." % kante.get("kurve"))
    if not kante.get("blech", True):
        hinweise.append("Zielkante gehört nicht zu einem Blechkörper – das Detail wird als eigener Körper eingesetzt.")
    L = kante.get("laenge") or 0
    if c.get("edgeLengthMin") is not None and L < c["edgeLengthMin"] - 1e-6:
        gruende.append("Zielkante %.1f mm ist kürzer als %.1f mm." % (L, c["edgeLengthMin"]))
    if c.get("edgeLengthMax") is not None and L > c["edgeLengthMax"] + 1e-6:
        gruende.append("Zielkante %.1f mm ist länger als %.1f mm." % (L, c["edgeLengthMax"]))
    t_soll = c.get("thickness")
    t_ist = kante.get("dicke") if kante.get("dicke") is not None else dicke
    if t_soll is not None and t_ist is not None and abs(t_soll - t_ist) > (c.get("thicknessTolerance") or 0.01):
        gruende.append("Blechdicke %.2f mm passt nicht zur Vorlage (%.2f mm)." % (t_ist, t_soll))
    if t_soll is not None and t_ist is None:
        hinweise.append("Blechdicke der Zielkante unbekannt – bitte selbst prüfen (Vorlage: %.2f mm)." % t_soll)
    a_len = (vorlage.get("anchor") or {}).get("edgeLength")
    if a_len and L and abs(a_len - L) > 0.05:
        hinweise.append("Anschlusskante der Vorlage %.1f mm, Zielkante %.1f mm – nur variable Masse passen sich an." % (a_len, L))
    return (not gruende), gruende, hinweise


def parameter_zuordnen(fusion_namen, neue_namen):
    """Vorlagenparameter (Name im Quellmodell) → Name des beim Import NEU entstandenen Parameters.

    Fusion benennt beim Import um, wenn der Name im Dokument schon existiert (SD_H → SD_H_1).
    Zugeordnet wird nur eindeutig: gleicher Name oder Name_<Zahl> unter den NEUEN Parametern. → (zuordnung, offen)"""
    import re
    zuordnung, offen = {}, []
    neue = list(neue_namen)
    for n in fusion_namen:
        if n in neue:
            zuordnung[n] = n
            continue
        kandidaten = [x for x in neue if re.match(r"^%s_\d+$" % re.escape(n), x)]
        if len(kandidaten) == 1:
            zuordnung[n] = kandidaten[0]
        else:
            offen.append(n)
    return zuordnung, offen


def anpassung(vorlage, flaeche_typ, flaechenradius_mm):
    """Modus «An gekrümmte Fläche anpassen» (Prototyp, Korrekturauftrag Phase 6): KEINE freie Verformung, sondern die Vorlage muss einen Parameter mit
    der Rolle «anschlussradius» haben – er wird auf den Radius der Zielfläche gesetzt, die Vorlage modelliert die Krümmung selbst (Verformungsrichtung
    damit eindeutig: radial zur Zylinderachse). → (Parametername, Wert in mm). Wirft ValueError mit verständlichem Grund."""
    if flaeche_typ != "zylinder":
        raise ValueError("Anpassen ist nur auf Zylinderflächen definiert (gewählt: «%s») – sonst starr einsetzen." % flaeche_typ)
    if not flaechenradius_mm or flaechenradius_mm <= 0:
        raise ValueError("Der Radius der Zielfläche ist nicht lesbar.")
    rollen = [p for p in vorlage.get("parameters", []) if p.get("role") == "anschlussradius"]
    if len(rollen) != 1:
        raise ValueError("Die Detailvorlage hat %s Parameter mit der Rolle «Anschlussradius» – Anpassen braucht genau einen (beim Erfassen wählen)."
                         % ("keinen" if not rollen else "mehrere"))
    p = rollen[0]
    lo, hi = p.get("min"), p.get("max")
    if (lo is not None and flaechenradius_mm < lo) or (hi is not None and flaechenradius_mm > hi):
        raise ValueError("Zylinderradius %.1f mm liegt ausserhalb des Bereichs der Vorlage (%s … %s mm)." % (flaechenradius_mm, lo, hi))
    return p["name"], round(float(flaechenradius_mm), 4)

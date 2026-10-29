"""Rundbleche und Werkstattumformung.

Drei Fälle:
  1 «scheibe»  Kreisförmiges Blech mit aufgebogenem Rand (Rand wird gestaucht).
  2 «kragen»   Rand an rundem Ausschnitt / Rohrkragen nach aussen gestellt (Rand wird gestreckt).
  3 «kegel»    Kegelstumpf / konischer Übergang (abwickelbar, ohne Umformung).

Klar getrennt wird:
  konstruierbar  – Geometrie lässt sich modellieren (Drehkörper/Abwicklung rechnerisch möglich)
  abwickelbar    – die Fläche ist ohne Dehnung in die Ebene abwickelbar (nur Kegel/Zylinder)
  herstellbar    – mit dem gewählten Werkstattverfahren erreichbar: NUR beurteilbar, wenn im
                   Materialprofil ein eigener Erfahrungswert (Grenzwert in %) hinterlegt ist.
Die Tangentialdehnung ist reine Geometrie (Umfangsänderung), KEINE Garantie für die Umformbarkeit:
Rückfederung, Wanddickenänderung und Faltenbildung sind nicht gerechnet. Es werden nie Einschnitte
oder Lappen erzeugt, ausser der Benutzer gibt sie ausdrücklich frei.
"""
import math

VERFAHREN = {
    "stauchen": "Stauchen / Schweifen",
    "strecken": "Strecken / Schweifen",
    "manuell": "Manuelle Werkstattumformung",
    "auto": "Automatische Empfehlung",
}


def tangentiale_dehnung(r_vorher, r_nachher):
    """Umfangsänderung eines Materialrings, der von Radius r_vorher auf r_nachher kommt (−: Stauchung, +: Streckung)."""
    if r_vorher <= 0:
        raise ValueError("Radius muss grösser als 0 sein")
    return (r_nachher - r_vorher) / r_vorher


def scheibe_mit_rand(radius, randhoehe, winkel=90.0, dicke=0.0):
    """Fall 1: Scheibe (Radius bis zur Biegung, Blechmitte) mit aufgebogenem Rand.
    Flaches Material bei Radius radius+randhoehe kommt bei 90° auf radius (zylindrischer Rand),
    bei kleinerem Winkel auf radius + randhoehe·cos(winkel)."""
    if radius <= 0 or randhoehe <= 0:
        raise ValueError("Radius und Randhöhe müssen grösser als 0 sein")
    if not 0 < winkel <= 180:
        raise ValueError("Randwinkel muss zwischen 0° und 180° liegen")
    r_flach = radius + randhoehe          # Rohling (ohne Biegeradius, Blechmitte)
    r_end = radius + randhoehe * math.cos(math.radians(winkel))
    eps = tangentiale_dehnung(r_flach, max(r_end, 1e-9))
    return {"fall": "scheibe", "rohling_radius": r_flach, "rohling_durchmesser": 2 * r_flach,
            "dehnung_rand": eps, "art": "stauchen" if eps < 0 else "strecken",
            "abwickelbar": False, "konstruierbar": True,
            "zone": {"von_radius": radius, "bis_radius": r_flach}}


def kragen(loch_radius_fertig, kragenhoehe, winkel=90.0):
    """Fall 2: Kragen an rundem Ausschnitt: fertiger Innenradius (Blechmitte) loch_radius_fertig.
    Der Rand liegt flach bei loch_radius_fertig − kragenhoehe und wird auf loch_radius_fertig gestreckt (90°)."""
    if kragenhoehe <= 0 or loch_radius_fertig <= 0:
        raise ValueError("Radius und Kragenhöhe müssen grösser als 0 sein")
    r_flach = loch_radius_fertig - kragenhoehe
    if r_flach <= 0:
        return {"fall": "kragen", "konstruierbar": True, "abwickelbar": False, "art": "strecken", "dehnung_rand": None,
                "rohling_loch_radius": 0.0, "fehler": "Kragen höher als der Lochradius: aus der Fläche nicht ohne Einschnitte herstellbar."}
    r_end = loch_radius_fertig - kragenhoehe + kragenhoehe * (1 - math.cos(math.radians(winkel)))
    eps = tangentiale_dehnung(r_flach, r_end)
    return {"fall": "kragen", "rohling_loch_radius": r_flach, "dehnung_rand": eps, "art": "strecken",
            "abwickelbar": False, "konstruierbar": True, "zone": {"von_radius": r_flach, "bis_radius": loch_radius_fertig}}


def kegelstumpf(r_unten, r_oben, hoehe):
    """Fall 3: Abwicklung eines Kegelstumpfs (Blechmitte) – exakt abwickelbar.
    → Kreisringsektor mit Radien R1 < R2 und Öffnungswinkel."""
    if r_unten <= 0 or r_oben < 0 or hoehe <= 0:
        raise ValueError("Radien ≥ 0 und Höhe > 0 nötig")
    if abs(r_unten - r_oben) < 1e-9:
        return {"fall": "kegel", "zylinder": True, "abwickelbar": True, "konstruierbar": True,
                "rechteck": [2 * math.pi * r_unten, hoehe], "art": None, "dehnung_rand": 0.0}
    s = math.hypot(r_unten - r_oben, hoehe)   # Mantellinie
    rg, rk = max(r_unten, r_oben), min(r_unten, r_oben)
    R2 = s * rg / (rg - rk)
    R1 = R2 - s
    winkel = 360.0 * rg / R2
    return {"fall": "kegel", "zylinder": False, "abwickelbar": True, "konstruierbar": True, "R_innen": R1, "R_aussen": R2,
            "oeffnungswinkel": winkel, "mehrteilig_noetig": winkel > 360.0, "art": None, "dehnung_rand": 0.0}


def beurteilen(ergebnis, verfahren, material, einschnitte_erlaubt=False):
    """Herstellbarkeit mit dem gewählten Verfahren. → ergebnis ergänzt um 'herstellbar' (True/False/None) und 'hinweise'."""
    e = dict(ergebnis)
    h = []
    eps = e.get("dehnung_rand")
    lim = (material or {}).get("formingLimits") or {}
    if e.get("fehler"):
        e["herstellbar"] = False
        h.append(e["fehler"])
        if einschnitte_erlaubt:
            h.append("Einschnitte sind freigegeben, werden aber nicht automatisch erzeugt – bitte gezielt konstruieren.")
    elif e.get("abwickelbar"):
        e["herstellbar"] = True
        h.append("Abwickelbar ohne Umformung (Kegel/Zylinder): Zuschnitt aus der Abwicklung, Rundung auf der Rundmaschine.")
        if e.get("mehrteilig_noetig"):
            h.append("Öffnungswinkel über 360°: der Mantel muss aus mehreren Teilen bestehen.")
    else:
        art = e.get("art")
        if verfahren == "auto":
            verfahren = art
            h.append("Empfehlung aus der Geometrie: %s (Rand wird %s)." % (VERFAHREN[art], "kürzer" if art == "stauchen" else "länger"))
        if verfahren in ("stauchen", "strecken") and verfahren != art:
            e["herstellbar"] = False
            h.append("Der Rand muss %s werden – mit «%s» nicht herstellbar." % ("gestaucht" if art == "stauchen" else "gestreckt", VERFAHREN[verfahren]))
        else:
            grenze = lim.get("shrinkMaxPercent") if art == "stauchen" else lim.get("stretchMaxPercent")
            if grenze is None or verfahren == "manuell":
                e["herstellbar"] = None
                h.append("Herstellbarkeit nicht beurteilbar: %s" % (
                    "manuelle Werkstattumformung gewählt" if verfahren == "manuell" else "kein eigener Grenzwert im Materialprofil hinterlegt"))
            else:
                e["herstellbar"] = abs(eps) * 100 <= grenze
                h.append("Rand %s um %.1f %% (eigener Grenzwert %.1f %%, Quelle: %s)." % (
                    "gestaucht" if art == "stauchen" else "gestreckt", abs(eps) * 100, grenze, lim.get("source") or "nicht angegeben"))
        h.append("Umformzone: Radius %.1f bis %.1f mm." % (e["zone"]["von_radius"], e["zone"]["bis_radius"]))
        h.append("Theoretische Rechnung (Umfangsänderung). Keine Garantie: Faltenbildung, Rückfederung und Wanddicke sind nicht berücksichtigt.")
    if not einschnitte_erlaubt:
        h.append("Einschnitte/Lappen: nicht erlaubt – es werden keine erzeugt.")
    e["verfahren"] = verfahren
    e["hinweise"] = h
    return e


def drehprofil_scheibe(radius, randhoehe, dicke, ri, winkel=90.0):
    """Querschnitt (r, z) für einen Drehkörper: Scheibe + Rand mit Biegeradius ri (Blechmitte-Masse).
    Liefert die geschlossene Kontur mit Dicke; nutzt die Biegerechnung aus core.bend_geometry."""
    from ..core.bend_geometry import berechne, kontur
    ops = [{"typ": "schenkel", "L": radius}, {"typ": "biegung", "winkel": winkel, "ri": ri, "modus": "sharp"},
           {"typ": "schenkel", "L": randhoehe}]
    res = berechne(0.0, ops, dicke, ri, 0.5)
    return kontur(res["pfad"], dicke, 6)

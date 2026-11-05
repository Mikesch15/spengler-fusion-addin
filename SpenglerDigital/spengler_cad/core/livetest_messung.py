"""Bewertung der Messwerte des Live-Tests (reine Rechnung ohne Fusion). Der Live-Test sammelt in Fusion nur Zahlen (Volumen, Ausdehnung); ob ein Ergebnis geometrisch stimmt,
entscheidet diese Datei – mit Zahlen testbar. Messwerte: {'vol': mm³, 'min': (x, y, z) mm, 'max': (x, y, z) mm, 'flaechen': n, 'kanten': n}.

Annahmen (Test-Blech auf der XY-Ebene, Flansch an der langen Kante bei Y = min, «+» = Richtung +Z): Wo Fusions Höhenbezug (aussen/innen) das Ergebnis um bis zu 2 × Blechdicke
verschiebt, ist die Toleranz entsprechend weit. Versatz und Radius werden als UNTERSCHIED zu einem Bau ohne Versatz/Radius bewertet – so kürzen sich solche Annahmen heraus.
Ergebnisse: ('ok' | 'warnung' | 'fehler', Text). «fehler» = geometrisch klar falsch (falsche Richtung, kein Effekt, Volumen um Faktor falsch), «warnung» = ausserhalb der Toleranz."""
import math

from . import bend_geometry


def _delta(vor, nach):
    return {"vol": nach["vol"] - vor["vol"], "hoch": nach["max"][2] - vor["max"][2], "runter": vor["min"][2] - nach["min"][2],
            "y_min": nach["min"][1] - vor["min"][1], "y_max": nach["max"][1] - vor["max"][1], "x_min": nach["min"][0] - vor["min"][0], "x_max": nach["max"][0] - vor["max"][0]}


def text(m):
    return "Volumen %.0f mm³, Ausdehnung %.1f × %.1f × %.1f mm, %d Flächen" % (m["vol"], m["max"][0] - m["min"][0], m["max"][1] - m["min"][1], m["max"][2] - m["min"][2], m["flaechen"])


def pruefe_flansch(vor, nach, winkel, hoehe, dicke, laenge, ri=None):
    """Flansch an einer Kante: Richtung (+ = +Z), Höhe über dem Blech, Volumenzuwachs."""
    d = _delta(vor, nach)
    ri = dicke if ri is None else ri
    tol = 2 * dicke + ri + 1.0
    soll = hoehe * math.sin(math.radians(abs(winkel)))
    ist, gegen = (d["hoch"], d["runter"]) if winkel > 0 else (d["runter"], d["hoch"])
    erwartet_v = laenge * dicke * hoehe
    ratio = d["vol"] / erwartet_v if erwartet_v > 0 else 0
    kopf = "Höhe in %s %+.1f mm (erwartet %.1f ± %.1f), Gegenrichtung %+.1f mm, Volumen %+.0f mm³ = %.0f %% des Erwarteten (%.0f)" % (
        "+Z" if winkel > 0 else "−Z", ist, soll, tol, gegen, d["vol"], 100 * ratio, erwartet_v)
    if ist < 0.3 * soll or gegen > ist + 1.0:
        return "fehler", "Der Flansch zeigt nicht in die erwartete Richtung oder fehlt: " + kopf
    if ratio < 0.4 or ratio > 2.0:
        return "fehler", "Das Volumen des Flansches passt nicht (Dicke verdoppelt oder Material fehlt?): " + kopf
    if abs(ist - soll) > tol or ratio < 0.75 or ratio > 1.35:
        return "warnung", "Ausserhalb der Toleranz: " + kopf
    return "ok", kopf


def pruefe_umschlag(vor, nach, hem, dicke, laenge, ri=None):
    """Umschlag (180°): die Blechdicke verdoppelt sich im Bereich des Saums, die Fläche wächst nicht über die Kante hinaus, Volumenzuwachs ≈ Saumlänge × Dicke × Kante."""
    d = _delta(vor, nach)
    ri = dicke if ri is None else ri
    z_ist = nach["max"][2] - nach["min"][2]
    z_soll = 2 * dicke
    ueber = max(d["y_min"] * -1, d["y_max"], d["x_min"] * -1, d["x_max"], 0.0)          # wie weit wächst die Ausdehnung in der Ebene
    erwartet_v = laenge * dicke * hem
    ratio = d["vol"] / erwartet_v if erwartet_v > 0 else 0
    kopf = "Dicke im Saum %.2f mm (erwartet ca. %.2f bis %.2f), Zuwachs in der Ebene %.1f mm, Volumen %+.0f mm³ = %.0f %% des Erwarteten (%.0f)" % (
        z_ist, z_soll, z_soll + 2 * ri, ueber, d["vol"], 100 * ratio, erwartet_v)
    if d["vol"] <= 0 or z_ist < 1.5 * dicke:
        return "fehler", "Der Umschlag fehlt oder liegt nicht doppelt auf dem Blech: " + kopf
    if ratio < 0.5 or ratio > 2.5:
        return "fehler", "Das Volumen des Umschlags passt nicht: " + kopf
    if z_ist > z_soll + 2 * ri + 1.0 or ueber > 2 * dicke + 2 * ri + 1.0 or ratio < 0.8 or ratio > 1.8:
        return "warnung", "Ausserhalb der Toleranz: " + kopf
    return "ok", kopf


def pruefe_versatz(ohne, mit, versatz, dicke, laenge, hoehe):
    """Versatz als Unterschied zum Bau OHNE Versatz (ohne/mit = {'vor': Messung, 'nach': Messung}). + = Biegung rückt nach innen (Streifen wird abgeschnitten, Y wächst),
    − = nach aussen (Streifen wird angefügt)."""
    d0, d1 = _delta(ohne["vor"], ohne["nach"]), _delta(mit["vor"], mit["nach"])
    dy = d1["y_min"] - d0["y_min"]
    dv = d1["vol"] - d0["vol"]
    soll_v = -versatz * laenge * dicke              # + Versatz: Streifen weg → weniger Volumen
    ratio = dv / soll_v if abs(soll_v) > 1e-9 else 0
    kopf = "Lage der Kante %+.1f mm gegenüber ohne Versatz (erwartet %+.1f), Volumenunterschied %+.0f mm³ (erwartet %+.0f, %.0f %%)" % (dy, versatz, dv, soll_v, 100 * ratio)
    if abs(dy) < 0.4 * abs(versatz) or dy * versatz < 0:
        return "fehler", "Der Versatz wirkt nicht oder in die falsche Richtung: " + kopf
    if ratio < 0.3 or ratio > 3.0:
        return "fehler", "Das Volumen passt nicht zum Versatz (Dicke verdoppelt, Körper beschädigt?): " + kopf
    if abs(dy - versatz) > dicke + 2.0 or ratio < 0.6 or ratio > 1.5:
        return "warnung", "Ausserhalb der Toleranz: " + kopf
    return "ok", kopf


def pruefe_radius(standard, gross, radius):
    """Ein eingestellter Biegeradius muss das Ergebnis messbar ändern (sonst wird er von Fusion ignoriert). standard/gross = Zuwachs-Messungen {'vor','nach'} ohne bzw. mit Radius."""
    v0 = standard["nach"]["vol"] - standard["vor"]["vol"]
    v1 = gross["nach"]["vol"] - gross["vor"]["vol"]
    rel = abs(v1 - v0) / v0 if v0 > 0 else 0
    kopf = "Volumen mit Radius %g mm %+.0f mm³, ohne %+.0f mm³ (Unterschied %.1f %%)" % (radius, v1, v0, 100 * rel)
    if rel < 0.003:
        return "warnung", "Der Biegeradius hat keine messbare Wirkung (wird er ignoriert?): " + kopf
    return "ok", kopf


def pruefe_gehrung(einzeln, gemeinsam):
    """Gemeinsamer Bau gegen Einzelbau: Bei echter Gehrung unterscheiden sich Flächenzahl oder Volumen."""
    dv = gemeinsam["vol"] - einzeln["vol"]
    kopf = "gemeinsam: %.0f mm³, %d Flächen; einzeln: %.0f mm³, %d Flächen (Unterschied %+.0f mm³)" % (gemeinsam["vol"], gemeinsam["flaechen"], einzeln["vol"], einzeln["flaechen"], dv)
    if gemeinsam["flaechen"] == einzeln["flaechen"] and abs(dv) < 1.0:
        return "warnung", "Gemeinsam und einzeln gebaut sehen gleich aus – die Ecke ist nicht auf Gehrung geschnitten: " + kopf
    return "ok", kopf


def pruefe_abwicklung(breite, laenge, soll_laenge, basis_breite, hoehe, dicke, ri=None, k=0.44, flansche=1):
    """Abwicklung eines Blechs (soll_laenge × basis_breite) mit einem 90°-Flansch der Höhe `hoehe` an der Längskante: Breite = Basis + Zugabe (theoretisch, mit Innenradius und K-Faktor).
    Die Toleranz deckt Höhenbezug (aussen/innen) und unbekannten K-Faktor ab."""
    ri = dicke if ri is None else ri
    gross, klein = max(breite, laenge), min(breite, laenge)
    zugabe, _ = bend_geometry.zugabe_abwicklung([{"typ": "flansch", "winkel": 90.0, "laenge": float(hoehe), "radius": None}], dicke, ri, k, basis_mm=basis_breite)
    soll_breite = basis_breite + flansche * zugabe          # flansche: Anzahl gleicher 90°-Flansche an den Längskanten
    tol = flansche * (2 * dicke + 2.0)
    kopf = "Abwicklung %.1f × %.1f mm (erwartet %.1f × %.1f ± %.1f; theoretisch mit Ri %.1f, K %.2f)" % (gross, klein, soll_laenge, soll_breite, tol, ri, k)
    if abs(gross - soll_laenge) > 0.2 * soll_laenge or abs(klein - soll_breite) > 0.2 * soll_breite:
        return "fehler", "Die Abwicklung passt nicht zum 3D-Modell: " + kopf
    if abs(gross - soll_laenge) > 1.0 or abs(klein - soll_breite) > tol:
        return "warnung", "Ausserhalb der Toleranz: " + kopf
    return "ok", kopf


def zustand_vergleich(vorher, nachher, schluessel, vol_tol_mm3=0.5):
    """Modellzustand vor/nach einem Rückbau-Test vergleichen. → (abweichungen [(name, vorher, nachher)], nicht_messbar [name]).
    Ein nicht messbarer Wert (None, fehlender Schlüssel) ist KEIN «unverändert» – er wird eigens gemeldet und macht den Test ungültig."""
    abw, offen = [], []
    for k in tuple(schluessel) + ("vol",):
        a, b = vorher.get(k), nachher.get(k)
        if a is None or b is None:
            offen.append(k)
        elif (abs(a - b) >= vol_tol_mm3) if k == "vol" else (a != b):
            abw.append((k, a, b))
    return abw, offen

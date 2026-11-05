"""Mathematische Machbarkeitsanalyse gekrümmter Kantenbearbeitungen (Auftrag Kantenwerkzeug, Review D/E) – reine Rechnung, testbar.

Kriterium «exakt abwickelbar»: jede Fläche des fertigen Teils (Grundfläche, Biegezone, Schenkel, Falz, Übergänge) hat die Gausssche Krümmung
K = k1·k2 = 0 (Ebene, Zylinder, Kegel, Tangentenfläche). Eine einzige Fläche mit K ≠ 0 (Torus, Kugel) macht das ganze Teil nicht exakt
abwickelbar – auch wenn Grundfläche und Schenkel abwickelbar sind.

Biegezone einer Aufkantung = Fläche, die der Biegeradius-Querschnitt (Kreisbogen ri…ri+t) beim Entlangführen an der Kante überstreicht:
- entlang einer GERADEN Kante: Zylinder (K = 0),
- entlang einer KREISKANTE (Radius Rk): Torusabschnitt mit Achse = Kreisachse; K = cos θ / (r · (Rk + r cos θ)) ≠ 0 für r = Biegeradius,
  θ = Winkel im Rohrquerschnitt (nur bei θ = ±90° null – die Fläche ist also über die ganze Biegung doppelt gekrümmt).
Numerische Toleranz: |K| < 1e-9 1/mm² gilt als 0 (Rechengenauigkeit); jede physikalische Biegezone liegt um Grössenordnungen darüber
(Rk = 10 m, r = 1 mm → |K| ≈ 1e-4 1/mm²) – numerischer Fehler und echte Verzerrung sind damit klar getrennt."""
import math

K_TOL = 1e-9          # 1/mm²: darunter gilt eine Fläche numerisch als abwickelbar


def gauss_zylinder(radius):
    return 0.0


def gauss_kegel():
    return 0.0


def gauss_torus(r_achse, r_rohr, theta_rad):
    """Gausssche Krümmung des Torus (Achsabstand r_achse des Rohrmittelpunkts, Rohrradius r_rohr) im Rohrwinkel θ (0 = aussen)."""
    return math.cos(theta_rad) / (r_rohr * (r_achse + r_rohr * math.cos(theta_rad)))


def biegezone_max_gauss(kante, rk=None, ri=1.0, t=1.0, winkel_grad=90.0, n=19):
    """Grösstes |K| der Biegezone (innen und aussen) einer Aufkantung an einer Kante: 'gerade' → 0; 'kreis' (Radius rk) → Torus-Stichprobe über die
    Biegung. → |K| in 1/mm²."""
    if kante == "gerade":
        return 0.0
    if kante != "kreis" or not rk:
        return float("inf")
    kmax = 0.0
    for r in (ri, ri + t):
        for i in range(n):
            th = math.radians(-90.0 + winkel_grad * i / (n - 1.0))     # vom Anschluss an die Grundfläche bis zum Schenkelbeginn
            kmax = max(kmax, abs(gauss_torus(rk, r, th)))
    return kmax


KANDIDATEN = [
    {"nr": 1, "name": "Kreisbogenkante auf ebener Grundfläche, 90°-Aufkantung",
     "flaechen": "Grundfläche eben (K = 0), Biegezone Torusabschnitt (K ≠ 0), Schenkel Zylinder (K = 0)",
     "entwickelbar": False,
     "fertigung": "Bördeln/Aufhalsen mit Streckung bzw. Stauchung des Randes – oder segmentiert mit Einschnitten",
     "eigener_aufbau": "möglich (Drehung des Querschnitts um die Kreisachse), aber Ergebnis nicht exakt abwickelbar",
     "abwicklung": "keine exakte Abwicklung; Alternative: Zargenstreifen (Zylinder, exakt) + Naht oder Freistellungen – nur als bewusst gewählte Variante"},
    {"nr": 2, "name": "Gerade Mantelkante eines zylindrischen Blechsegments",
     "flaechen": "Grundfläche Zylinder (K = 0), Biegezone Zylinder mit Achse = Kante (K = 0), Schenkel eben (K = 0)",
     "entwickelbar": True,
     "fertigung": "Rundbiegen des Segments, Abkanten an der geraden Kante – Spenglerpraxis (z. B. Rinnen-/Rohrhalbschalen mit Abkantung)",
     "eigener_aufbau": "möglich: Querschnitt (Kreisbögen + Linien) senkrecht zur Kante, Extrusion entlang der Kante",
     "abwicklung": "exakt: Länge = Σ Schenkel + Σ (ri + k·t)·|α| (Segment selbst: (R + k·t)·φ), Breite = Kantenlänge; Rückvergleich über Volumen und Radien"},
    {"nr": 3, "name": "Gekrümmte (Kreis-)Kante auf zylindrischer Fläche (Stirnkante eines Rohrs)",
     "flaechen": "Grundfläche Zylinder (K = 0), Biegezone Torusabschnitt (K ≠ 0), Schenkel Kreisring/Kegel (K = 0)",
     "entwickelbar": False,
     "fertigung": "Bördeln mit Streckung (Kragen) – nicht verzerrungsfrei",
     "eigener_aufbau": "möglich (Drehkörper), aber nicht exakt abwickelbar",
     "abwicklung": "keine exakte Abwicklung"},
    {"nr": 4, "name": "Kreisförmige Kante eines flachen Rundblechs (Ronde mit Rand)",
     "flaechen": "Ronde eben (K = 0), Biegezone Torus (K ≠ 0), Rand Zylinder (K = 0)",
     "entwickelbar": False,
     "fertigung": "Drücken/Bördeln, Rand streckt/staucht",
     "eigener_aufbau": "möglich (Drehkörper, vorhanden: «Rundblech»), nicht exakt abwickelbar",
     "abwicklung": "keine exakte Abwicklung; Rundblech-Werkzeug weist Umformung aus"},
    {"nr": 5, "name": "Gerade Mantellinie eines konischen Blechs",
     "flaechen": "Grundfläche Kegel (K = 0), Biegezone Zylinder um die Mantellinie (K = 0), Schenkel eben (K = 0)",
     "entwickelbar": True,
     "fertigung": "Kegel rollen, an der Mantellinie abkanten",
     "eigener_aufbau": "Profil entlang der Mantellinie möglich (Tangentialebene längs der Mantellinie konstant); das konische Grundblech selbst lässt "
                       "sich nicht als Querschnitts-Extrusion bauen",
     "abwicklung": "exakt (Kegelabwicklung Kreisringsektor + Profil-Zugabe); eigene Kegelabwicklung noch nicht umgesetzt"},
]


def erster_prototyp():
    """Wahl des ersten Prototyps: exakt abwickelbar UND Grundkörper wie Aufkantung mit derselben eigenen Profilgeometrie baubar (dann ist auch die
    eigene Abwicklung des GANZEN Teils geschlossen rechenbar). → Kandidat (dict)."""
    geeignet = [k for k in KANDIDATEN if k["entwickelbar"] and "nicht als Querschnitts-Extrusion" not in k["eigener_aufbau"]]
    return geeignet[0]


def als_markdown():
    z = ["| Nr. | Kandidat | Flächen | exakt abwickelbar | Fertigung | eigener Aufbau | Abwicklung/Validierung |", "|---|---|---|---|---|---|---|"]
    for k in KANDIDATEN:
        z.append("| %d | %s | %s | %s | %s | %s | %s |" % (k["nr"], k["name"], k["flaechen"], "ja" if k["entwickelbar"] else "**nein**", k["fertigung"],
                                                          k["eigener_aufbau"], k["abwicklung"]))
    p = erster_prototyp()
    z.append("")
    z.append("**Erster Prototyp: Nr. %d – %s.** Begründung: alle Flächen K = 0 (exakt abwickelbar), Grundsegment und Aufkantung entstehen aus EINEM "
             "Querschnitt (Kreisbögen + Linien) senkrecht zur geraden Kante, die eigene Abwicklung ist damit geschlossen rechenbar und über Volumen/Radien "
             "gegen das 3D-Modell prüfbar. Nr. 1 (Bogenkante auf ebenem Blech) ist wegen der Torus-Biegezone NICHT exakt abwickelbar und wird nicht als "
             "Erfolg umgesetzt; als konstruktive Sondervarianten kommen nur bewusst wählbare Segmentierung/Freistellung oder ein separater Zargenstreifen in Frage." % (p["nr"], p["name"]))
    z.append("Beispiel Torus-Biegezone (Kreiskante R 500 mm, ri 1 mm, t 1 mm): max |K| = %.2e 1/mm² ≫ Toleranz %.0e." % (biegezone_max_gauss("kreis", 500.0, 1.0, 1.0), K_TOL))
    return "\n".join(z)

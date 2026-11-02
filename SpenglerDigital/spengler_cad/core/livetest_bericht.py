"""Auswertung des Live-Tests (ohne Fusion testbar): Ergebnisliste → Gesamtstatus und lesbarer Bericht.
Ein Ergebnis ist {"name", "status", "detail", "dauer"}; status: ok | warnung | fehler | uebersprungen."""

SYMBOL = {"ok": "✓", "warnung": "⚠", "fehler": "✗", "uebersprungen": "–"}
TEST_ID = "97.002"


def zaehlen(ergebnisse):
    z = {"ok": 0, "warnung": 0, "fehler": 0, "uebersprungen": 0}
    for e in ergebnisse:
        z[e.get("status") if e.get("status") in z else "fehler"] += 1
    return z


def gesamtstatus(ergebnisse):
    """→ 'ok' (alles ok oder nur übersprungen/Warnungen) oder 'fehler' (mindestens ein Schritt fehlgeschlagen).
    Warnungen sind Hinweise (z. B. Gehrung nicht gemeinsam gebaut) – sie stehen im Bericht, zählen aber nicht als Absturz."""
    return "fehler" if zaehlen(ergebnisse)["fehler"] else "ok"


def kurz(ergebnisse):
    z = zaehlen(ergebnisse)
    return "%d ok, %d Warnungen, %d Fehler, %d übersprungen" % (z["ok"], z["warnung"], z["fehler"], z["uebersprungen"])


def auffaelliges(ergebnisse):
    return [e for e in ergebnisse if e.get("status") in ("warnung", "fehler")]


def text(ergebnisse, kopf=""):
    zeilen = [kopf] if kopf else []
    zeilen.append("Ergebnis: " + kurz(ergebnisse))
    for i, e in enumerate(ergebnisse, 1):
        zeilen.append("%s %d. %s%s" % (SYMBOL.get(e.get("status"), "?"), i, e.get("name", ""),
                                       "  (%.1f s)" % e["dauer"] if e.get("dauer") is not None else ""))
        d = (e.get("detail") or "").strip()
        if d:
            zeilen.extend("      " + x for x in d.splitlines())
    return "\n".join(zeilen)


def meldung(ergebnisse):
    """Kurztext für das Meldungsfenster: nur Auffälliges."""
    a = auffaelliges(ergebnisse)
    if not a:
        return "Alle %d geprüften Funktionen haben in Fusion funktioniert." % len(ergebnisse)
    return "Auffällig (%d):\n" % len(a) + "\n".join("%s %s – %s" % (SYMBOL[e["status"]], e["name"], ((e.get("detail") or "").strip().splitlines() or [""])[0][:160]) for e in a)

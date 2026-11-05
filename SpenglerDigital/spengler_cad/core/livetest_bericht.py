"""Auswertung des Live-Tests (ohne Fusion testbar): Ergebnisliste → Gesamtstatus und lesbarer Bericht.
Ein Ergebnis ist {"name", "status", "detail", "dauer"}; status: ok | warnung | fehler | uebersprungen."""

SYMBOL = {"ok": "✓", "warnung": "⚠", "fehler": "✗", "uebersprungen": "–"}
WORT = {"ok": "PASS", "warnung": "PASS mit Hinweis", "fehler": "FAIL", "uebersprungen": "NICHT GETESTET"}
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
        zeilen.append("%s %s %d. %s%s" % (SYMBOL.get(e.get("status"), "?"), WORT.get(e.get("status"), "?"), i, e.get("name", ""),
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


NOTIZ_MAX, PROTOKOLL_MAX = 4000, 19800           # Grenzen der Cloud-Tabelle cad_testergebnisse (CHECK 4000 / 20000)


def cloud_notiz(ergebnisse, je_schritt=260, grenze=NOTIZ_MAX):
    """Kurzfassung für das Notizfeld: JEDER auffällige Schritt bekommt Platz (je höchstens `je_schritt` Zeichen) – früher füllte ein langer
    Schritt (gerolltes Blech) die 4000 Zeichen und spätere Schritte fehlten."""
    teile = []
    for e in auffaelliges(ergebnisse):
        d = " / ".join(x.strip() for x in (e.get("detail") or "").strip().splitlines() if x.strip())
        teile.append(("%s %s: %s" % (SYMBOL.get(e.get("status"), "?"), e.get("name", ""), d))[:je_schritt])
    return ("; ".join(teile) or "Alles ok.")[:grenze]


def cloud_protokoll(ergebnisse, kopf, log, grenze=PROTOKOLL_MAX):
    """Protokollfeld: ZUERST die vollständigen Details aller auffälligen Schritte, dann die Liste aller Schritte, zuletzt das Protokoll im
    restlichen Platz (dessen Ende, mit den Fehler-Traces). Früher: Bericht + Protokoll, vorne abgeschnitten – der Bericht ging verloren."""
    a = auffaelliges(ergebnisse)
    zeilen = [kopf, "Ergebnis: " + kurz(ergebnisse), "", "=== Auffällige Schritte (vollständig) ==="]
    for e in a:
        zeilen.append("%s %s %s" % (SYMBOL.get(e.get("status"), "?"), WORT.get(e.get("status"), "?"), e.get("name", "")))
        zeilen.extend("      " + x for x in (e.get("detail") or "").strip().splitlines())
    zeilen += ["", "=== Alle Schritte ==="]
    zeilen += ["%s %d. %s" % (SYMBOL.get(e.get("status"), "?"), i, e.get("name", "")) for i, e in enumerate(ergebnisse, 1)]
    bericht = "\n".join(z for z in zeilen if z is not None)[: grenze - 200]
    rest = grenze - len(bericht) - 60
    log = log or ""
    return bericht + "\n\n--- Protokoll (Ende, nur seit Teststart) ---\n" + (log[-rest:] if rest > 0 else "")

"""Änderungen an der App aus dem CAD: Projektstatus, Hinweis, Termine. Prüft die Eingaben nach denselben Regeln wie die App (js/92 terPruefen, js/24 Status/Hinweis), damit nur
gültige Werte in die Datenbank gehen. Reine Logik ohne Netz."""
import datetime
import re

STATUS = [("offen", "Offen"), ("in_arbeit", "In Arbeit"), ("abgeschlossen", "Abgeschlossen"), ("storniert", "Storniert")]
STATUS_TEXT = dict(STATUS)


class AenderungsFehler(ValueError):
    pass


def pruefe_status(neu, alt=None):
    if neu not in STATUS_TEXT:
        raise AenderungsFehler("Unbekannter Projektstatus «%s»." % neu)
    if neu == alt:
        raise AenderungsFehler("Der Status ist schon «%s»." % STATUS_TEXT[neu])
    return neu


def hinweis_text(text):
    """Leer heisst «kein Hinweis» und wird als None gespeichert (wie in der App)."""
    t = str(text or "").strip()
    if len(t) > 2000:
        raise AenderungsFehler("Der Hinweis ist zu lang (höchstens 2000 Zeichen).")
    return t or None


def hinweis_ergaenzt(alt, zeile, datum=None, wer=""):
    """Neue Zeile unter den bisherigen Hinweis: «4.11.2026 Mike (CAD): …»."""
    zeile = str(zeile or "").strip()
    if not zeile:
        raise AenderungsFehler("Bitte den Text zum Ergänzen eingeben.")
    d = datum or datetime.date.today()
    kopf = "%d.%d.%d%s (CAD): " % (d.day, d.month, d.year, (" " + wer) if wer else "")
    return hinweis_text(((str(alt).rstrip() + "\n") if alt else "") + kopf + zeile)


def datum_iso(text):
    """«4.11.2026», «04.11.26», «2026-11-04» → «2026-11-04»."""
    t = str(text or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", t) or None
    if m:
        j, mo, tg = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{2}|\d{4})$", t)
        if not m:
            raise AenderungsFehler("«%s» ist kein Datum. Bitte so schreiben: 4.11.2026" % t)
        tg, mo, j = int(m.group(1)), int(m.group(2)), int(m.group(3))
        j += 2000 if j < 100 else 0
    try:
        return datetime.date(j, mo, tg).isoformat()
    except ValueError:
        raise AenderungsFehler("«%s» ist kein gültiges Datum." % t)


def zeit_norm(text):
    t = str(text or "").strip()
    if not t:
        return None
    m = re.match(r"^(\d{1,2})[:.](\d{2})$", t)
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise AenderungsFehler("«%s» ist keine Uhrzeit. Bitte so schreiben: 07:30" % t)
    return "%02d:%02d" % (int(m.group(1)), int(m.group(2)))


def termin_pruefen(t, project_id):
    """Eingabe des Benutzers → Zeile für `termine` (wie die App sie schreibt). Wirft AenderungsFehler mit verständlichem Text."""
    titel = re.sub(r"\s+", " ", str(t.get("titel") or "")).strip()
    if not titel:
        raise AenderungsFehler("Bitte einen Titel eingeben.")
    if len(titel) > 200:
        raise AenderungsFehler("Der Titel ist zu lang (höchstens 200 Zeichen).")
    start = datum_iso(t.get("start_datum"))
    ende = datum_iso(t.get("ende_datum") or t.get("start_datum"))
    if ende < start:
        raise AenderungsFehler("Das Ende liegt vor dem Beginn.")
    sz, ez = zeit_norm(t.get("start_zeit")), zeit_norm(t.get("ende_zeit"))
    if ez and not sz:
        raise AenderungsFehler("Eine Ende-Zeit braucht auch eine Beginn-Zeit.")
    if ez and ende == start and ez < sz:
        raise AenderungsFehler("Das Ende liegt vor dem Beginn.")
    return {"titel": titel, "project_id": int(project_id), "start_datum": start, "ende_datum": ende, "start_zeit": sz, "ende_zeit": ez,
            "ort": str(t.get("ort") or "").strip() or None, "notiz": str(t.get("notiz") or "").strip() or None}


def termin_aenderbar(t):
    """Nur Termine, die in der App (oder hier) angelegt wurden – nicht Outlook/Google/Kalender-Abos (die der Abgleich überschreibt)."""
    return (t.get("quelle") or "app") == "app" and not t.get("abo_id")

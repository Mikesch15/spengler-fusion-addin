"""Ablagen: frei benannte Fusion-Ordner für Modelle, die zu KEINEM Kundenauftrag gehören (z. B. Wettbewerbs-, Muster- oder Eigenmodelle). Eine Ablage hat einen Namen und einen
Ordnerpfad im aktiven Fusion-Projekt («Wettbewerbe/Schweizermeisterschaft»). Ist eine Ablage aktiv oder liegt das Dokument in ihrem Ordner, arbeiten alle Befehle ohne Auftrag;
Exporte landen in einem eigenen Ordner. Reine Logik ohne Fusion."""
import re

VERBOTEN = '<>:"|?*'


class AblageFehler(ValueError):
    pass


def standard():
    return {"liste": [], "aktiv": ""}


def pfad_aus_text(text):
    """«Wettbewerbe/Schweizermeisterschaft» (auch mit \\) → ['Wettbewerbe', 'Schweizermeisterschaft']. Leere Teile entfallen, Sonderzeichen sind nicht erlaubt."""
    teile = [t.strip() for t in re.split(r"[\\/]+", str(text or "")) if t.strip()]
    if not teile:
        raise AblageFehler("Bitte den Fusion-Ordner angeben, z. B. Wettbewerbe/Schweizermeisterschaft.")
    for t in teile:
        if any(c in t for c in VERBOTEN) or t in (".", ".."):
            raise AblageFehler("Im Ordnernamen «%s» sind diese Zeichen nicht erlaubt: %s" % (t, " ".join(VERBOTEN)))
        if len(t) > 100:
            raise AblageFehler("Der Ordnername «%s…» ist zu lang." % t[:30])
    if len(teile) > 6:
        raise AblageFehler("Der Ordnerpfad ist zu tief (höchstens 6 Ebenen).")
    return teile


def pfad_text(pfad):
    return "/".join(pfad)


def hinzufuegen(ablagen, name, pfad):
    """Ablage anlegen oder (gleicher Name) ändern → neue Einstellung. Der Name darf nur einmal vorkommen."""
    name = str(name or "").strip()
    if not name:
        raise AblageFehler("Bitte einen Namen für die Ablage angeben.")
    if any(c in name for c in VERBOTEN + "/\\"):
        raise AblageFehler("Im Namen sind diese Zeichen nicht erlaubt: %s / \\" % " ".join(VERBOTEN))
    liste = [a for a in (ablagen or {}).get("liste", []) if a.get("name", "").lower() != name.lower()]
    liste.append({"name": name, "pfad": list(pfad)})
    liste.sort(key=lambda a: a["name"].lower())
    return {"liste": liste, "aktiv": (ablagen or {}).get("aktiv", "")}


def entfernen(ablagen, name):
    liste = [a for a in (ablagen or {}).get("liste", []) if a.get("name") != name]
    aktiv = (ablagen or {}).get("aktiv", "")
    return {"liste": liste, "aktiv": "" if aktiv == name else aktiv}


def finden(ablagen, name):
    return next((a for a in (ablagen or {}).get("liste", []) if a.get("name") == name), None)


def aus_dokumentpfad(ablagen, ordnernamen):
    """Liegt das Dokument in (oder unterhalb) eines Ablage-Ordners? Der längste passende Pfad gewinnt. → Ablage oder None."""
    ist = [str(n).lower() for n in ordnernamen or []]
    treffer = [a for a in (ablagen or {}).get("liste", []) if a.get("pfad") and ist[:len(a["pfad"])] == [str(p).lower() for p in a["pfad"]]]
    return max(treffer, key=lambda a: len(a["pfad"])) if treffer else None


def kontext(ablagen, ordnernamen):
    """Welche Ablage gilt gerade? Zuerst der Ordner des Dokuments, sonst die aktive. → {'name', 'pfad', 'quelle'} oder None."""
    a = aus_dokumentpfad(ablagen, ordnernamen)
    if a:
        return {"name": a["name"], "pfad": a["pfad"], "quelle": "Fusion-Ordner"}
    a = finden(ablagen, (ablagen or {}).get("aktiv", ""))
    return {"name": a["name"], "pfad": a["pfad"], "quelle": "aktiv gesetzt"} if a else None


def exportname(name):
    s = "".join(c if c.isalnum() or c in "-_ " else "_" for c in str(name or "")).strip(" ._")
    return s or "Ablage"

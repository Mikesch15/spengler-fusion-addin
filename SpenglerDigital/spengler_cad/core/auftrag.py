"""Aufträge als Ordner in Fusion: «<Nummer> <Objekt>» (z. B. «17642 Nägeligasse 1a, Bern»), optional in einem Jahresordner,
mit festen Unterordnern (Modelle, Pläne, Export – in den Einstellungen änderbar). Reine Logik ohne Fusion."""
import re

UNGUELTIG = '<>:"/\\|?*'
MUSTER = re.compile(r"^\s*(\d{3,})\s+(\S.*?)\s*$")


class AuftragsFehler(ValueError):
    pass


def standard():
    return {"wurzelOrdner": "Projekte", "jahresordner": True, "unterordner": ["Modelle", "Pläne", "Export"]}


def zerlegen(name):
    """«17642 Nägeligasse 1a, Bern» → ("17642", "Nägeligasse 1a, Bern"); sonst None."""
    m = MUSTER.match(name or "")
    return (m.group(1), m.group(2)) if m else None


def _teil_pruefen(text, was):
    text = (text or "").strip()
    if not text:
        raise AuftragsFehler("%s fehlt." % was)
    schlecht = [z for z in text if z in UNGUELTIG or ord(z) < 32]
    if schlecht:
        raise AuftragsFehler("%s enthält ein unzulässiges Zeichen (%s)." % (was, " ".join(sorted(set(schlecht)))))
    return text


def ordnername(nummer, objekt):
    nummer = _teil_pruefen(nummer, "Auftragsnummer")
    if not re.match(r"^\d{3,}$", nummer):
        raise AuftragsFehler("Die Auftragsnummer besteht aus mindestens 3 Ziffern.")
    return "%s %s" % (nummer, _teil_pruefen(objekt, "Objekt"))


def aus_pfad(namen):
    """Ordnernamen vom Stamm bis zum Ordner des Dokuments → (Nummer, Objekt) des innersten Auftragsordners, sonst None.
    Unterordner wie «Modelle» oder Jahresordner passen nicht auf das Muster und werden übersprungen."""
    for n in reversed(list(namen or [])):
        z = zerlegen(n)
        if z:
            return z
    return None


def pruefe_einstellung(a):
    """→ bereinigte Einstellung; wirft AuftragsFehler."""
    a = dict(standard(), **(a or {}))
    a["wurzelOrdner"] = (a.get("wurzelOrdner") or "").strip()
    if a["wurzelOrdner"]:
        _teil_pruefen(a["wurzelOrdner"], "Stammordner")
    sub = a.get("unterordner") or []
    if isinstance(sub, str):
        sub = sub.split(",")
    sub = [_teil_pruefen(s, "Unterordner") for s in sub if str(s).strip()]
    if len(set(s.lower() for s in sub)) != len(sub):
        raise AuftragsFehler("Unterordner dürfen nicht doppelt vorkommen.")
    a["unterordner"] = sub
    a["jahresordner"] = bool(a.get("jahresordner"))
    return a


def plan(einstellung, nummer, objekt, jahr):
    """Pfad der anzulegenden Ordner (ohne Stamm): [Jahr?, Auftrag] und Unterordner."""
    a = pruefe_einstellung(einstellung)
    name = ordnername(nummer, objekt)
    pfad = ([str(int(jahr))] if a["jahresordner"] else []) + [name]
    return {"wurzel": a["wurzelOrdner"], "pfad": pfad, "unterordner": a["unterordner"], "name": name}

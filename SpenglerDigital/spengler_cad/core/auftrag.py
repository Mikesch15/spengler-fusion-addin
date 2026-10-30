"""Aufträge als Ordner in Fusion: «<Nummer> <Objekt>» (z. B. «17642 Nägeligasse 1a, Bern»), optional in einem Jahresordner,
mit festen Unterordnern (Modelle, Pläne, Export – in den Einstellungen änderbar). Reine Logik ohne Fusion."""
import re

UNGUELTIG = '<>:"/\\|?*'
MUSTER = re.compile(r"^\s*(\d{3,})\s+(\S.*?)\s*$")


class AuftragsFehler(ValueError):
    pass


def standard():
    return {"wurzelOrdner": "Projekte", "jahresordner": True, "unterordner": ["Modelle", "Pläne", "Export"],
            "rollen": {"modelle": "Modelle", "plaene": "Pläne", "export": "Export"},   # welcher Unterordner wofür dient
            "lokalBasis": "",                                                          # Ordner auf dem PC für Exporte je Auftrag (leer = Exportordner)
            "teilnummerMitAuftrag": True}                                              # Teilenummern als «17642-01»


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


def aus_pfad_voll(namen):
    """Wie aus_pfad, zusätzlich das Jahr (ein Ordner direkt davor, der nur aus 4 Ziffern besteht) → (Nummer, Objekt, Jahr oder None) oder None."""
    namen = list(namen or [])
    for i in range(len(namen) - 1, -1, -1):
        z = zerlegen(namen[i])
        if z:
            jahr = int(namen[i - 1]) if i > 0 and re.match(r"^\d{4}$", namen[i - 1] or "") else None
            return z[0], z[1], jahr
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
    rollen = dict(standard()["rollen"], **(a.get("rollen") or {}))
    for k, v in list(rollen.items()):
        rollen[k] = _teil_pruefen(v, "Ordnername für %s" % k) if str(v or "").strip() else standard()["rollen"][k]
    for v in rollen.values():          # die Rollen-Ordner gehören immer zur Struktur
        if v.lower() not in [x.lower() for x in sub]:
            sub.append(v)
    a["rollen"] = rollen
    a["unterordner"] = sub
    a["jahresordner"] = bool(a.get("jahresordner"))
    a["lokalBasis"] = (a.get("lokalBasis") or "").strip()
    a["teilnummerMitAuftrag"] = bool(a.get("teilnummerMitAuftrag", True))
    return a


def plan(einstellung, nummer, objekt, jahr):
    """Pfad der anzulegenden Ordner (ohne Stamm): [Jahr?, Auftrag] und Unterordner."""
    a = pruefe_einstellung(einstellung)
    name = ordnername(nummer, objekt)
    pfad = ([str(int(jahr))] if a["jahresordner"] else []) + [name]
    return {"wurzel": a["wurzelOrdner"], "pfad": pfad, "unterordner": a["unterordner"], "name": name}


def teil_label(nummer, nr, mit_auftrag=True):
    """Teilenummer für Ausgaben: «17642-01», sonst die laufende Nummer."""
    if nr in (None, ""):
        return ""
    if mit_auftrag and nummer:
        try:
            return "%s-%02d" % (nummer, int(nr))
        except (TypeError, ValueError):
            pass
    return str(nr)


def lokaler_exportpfad(einstellung, nummer, objekt, jahr=None):
    """Ordner für Exporte eines Auftrags auf dem PC: <Basis>/[Jahr]/<Nummer Objekt>/<Export>; None ohne Basis oder Auftrag."""
    import os
    a = pruefe_einstellung(einstellung)
    if not a["lokalBasis"] or not nummer or not objekt:
        return None
    teile = [a["lokalBasis"]] + ([str(int(jahr))] if a["jahresordner"] and jahr else []) + [ordnername(nummer, objekt), a["rollen"]["export"]]
    return os.path.join(*teile)

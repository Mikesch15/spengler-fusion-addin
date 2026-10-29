"""JSON lesen/schreiben – atomar (temporäre Datei + os.replace), damit ein Absturz nie eine halbe Datei hinterlässt."""
import json
import os
import tempfile


class DatenFehler(RuntimeError):
    pass


def lesen(pfad, standard=None):
    if not os.path.exists(pfad):
        return standard
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError) as e:
        raise DatenFehler("Datei %s ist nicht lesbar: %s" % (pfad, e))


def schreiben(pfad, daten):
    ordner = os.path.dirname(os.path.abspath(pfad))
    os.makedirs(ordner, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=ordner)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=2, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, pfad)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def dateiname_sicher(text):
    s = "".join(c if c.isalnum() or c in "-_." else "_" for c in str(text))
    return s.strip("._") or "datei"

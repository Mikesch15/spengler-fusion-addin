"""Zustand für Start-Übersicht und Voraussetzungs-Prüfung: was ist eingerichtet (Konto, Material, Vorlagen, Auftrag, Projekt in der App …)."""
import json
import os

from ..core import auftrag as auftrag_logik
from ..diagnostics import logger
from ..storage import paths
from ..storage.material_library import MaterialBibliothek
from ..storage.settings_service import Einstellungen
from ..storage.template_repository import VorlagenRepository


def lesen(mit_app=True):
    """→ Zustand für core.start. mit_app=False fragt die App nicht (schnell, für die Prüfung beim Befehlsstart). Jeder Fehler ergibt «unbekannt», nie eine Ausnahme."""
    from . import export_command
    from ..geometry import fusion_adapter as fa
    e = Einstellungen().laden()
    z = {"angemeldet": False, "auftrag": "", "objekt": "", "projekt_in_app": None, "materialien": 0, "vorlagen": 0, "dokument_gespeichert": False,
         "fehlende_funktionen": [], "auftrag_erforderlich": bool(e.get("auftragErforderlich", True))}
    try:
        z["materialien"] = len(MaterialBibliothek().liste())
        z["vorlagen"] = len(VorlagenRepository(projekt_ordner=e.get("projectLibraryFolder") or None).liste("kantenvorlage"))
    except Exception:
        logger.ausnahme("Zustand: Bibliotheken")
    try:
        a = export_command.auftrag_angaben(e)
        z["auftrag"], z["objekt"] = a.get("auftrag") or "", a.get("objekt") or ""
        z["material_gewaehlt"] = bool((e.get("order") or {}).get("materialId")) and (e.get("order") or {}).get("auftrag") == z["auftrag"]
        z["dokument_gespeichert"] = auftrag_logik.aus_pfad_voll(fa.dokument_ordnerpfad()) is not None
    except Exception:
        logger.ausnahme("Zustand: Auftrag")
    try:
        d = json.load(open(os.path.join(paths.daten_ordner(), "selbsttest.json"), encoding="utf-8"))
        z["fehlende_funktionen"] = list(d.get("fehlt") or [])
    except Exception:
        pass
    if mit_app:
        try:
            from ..storage.cloud_client import Cloud
            c = Cloud(timeout=5)
            z["angemeldet"] = bool(c.angemeldet)
            if c.angemeldet and z["auftrag"]:
                z["projekt_in_app"] = bool(c.projekt_zu_auftrag(z["auftrag"]))
        except Exception:
            logger.warnung("Zustand: App nicht erreichbar")
    return z

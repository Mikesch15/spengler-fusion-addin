"""Datenmodelle – alle als versionierte, JSON-fähige Datensätze (dict) mit schemaVersion.

Bewusst einfache dicts statt Klassen-Serialisierung: unbekannte (neuere) Felder bleiben beim
Laden und Speichern erhalten und gehen bei einem Update nicht verloren.

Modelle:
  A  Kantenvorlage       typ "kantenvorlage"   (Operationsfolge mit Parametern)
  B  3D-Detailvorlage    typ "detailvorlage"   (eigenes Fusion-Modell + Anschlussreferenz)
  C  Bauplan             typ "bauplan"         (OperationPlan, nur zur Laufzeit/Protokoll)
  D  Materialprofil      typ "materialprofil"
  E  Bauergebnis         BuildResult (Laufzeit)
  F  Einstellungen       typ "einstellungen"
Längen in mm, Winkel in Grad. Umrechnung für Fusion nur in core/units.py.
"""
import copy
import datetime
import uuid

SCHEMA = {
    "kantenvorlage": 1,
    "detailvorlage": 1,
    "materialprofil": 1,
    "einstellungen": 1,
    "bibliothek_export": 1,
}

KATEGORIE_OHNE = "Ohne Kategorie"
EINHEITEN_PARAMETER = ("mm", "deg", "")


def jetzt():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def neue_id(prefix):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


# ------------------------------------------------------------------ A Kantenvorlage
def neue_kantenvorlage(name, operations=None, parameters=None, **extra):
    v = {
        "schemaVersion": SCHEMA["kantenvorlage"],
        "typ": "kantenvorlage",
        "id": neue_id("kv"),
        "name": name,
        "description": "",
        "category": KATEGORIE_OHNE,
        "favorite": False,
        "version": 1,                 # Vorlagenversion, steigt bei jeder gespeicherten Änderung
        "created": jetzt(),
        "modified": jetzt(),
        "parameters": parameters or [],
        "operations": operations or [],
        "connection": {               # Anschlussreferenz
            "edgeType": "gerade",     # gerade | gekruemmt | beliebig
            "side": "sichtseite",     # Bezug für + / -
        },
        "constraints": {              # Material-/Dickenabhängigkeiten (alle optional)
            "thicknessMin": None, "thicknessMax": None, "materials": [], "edgeLengthMin": None,
        },
        "manufacturing": {            # Fertigungsregeln
            "cutsAllowed": False,     # Einschnitte/Lappen nur mit ausdrücklicher Freigabe
            "relief": {"type": "fusion"},  # fusion (Blechregel) | keine | rechteck | rund
        },
        "metadata": {"author": "", "notes": ""},
    }
    v.update(extra)
    return v


def parameter(name, label="", einheit="mm", standard=None, minimum=None, maximum=None, beschreibung="", variabel=True):
    """Parameter einer Vorlage. standard=None heisst: der Benutzer muss den Wert eingeben."""
    return {"name": name, "label": label or name, "unit": einheit, "default": standard,
            "min": minimum, "max": maximum, "description": beschreibung, "variable": bool(variabel)}


def operation(typ, winkel, laenge, radius=None, **extra):
    op = {"typ": typ, "winkel": winkel, "laenge": laenge, "radius": radius}
    op.update(extra)
    return op


# ------------------------------------------------------------------ B 3D-Detailvorlage
def neue_detailvorlage(name, **extra):
    v = {
        "schemaVersion": SCHEMA["detailvorlage"],
        "typ": "detailvorlage",
        "id": neue_id("dv"),
        "name": name,
        "description": "",
        "category": KATEGORIE_OHNE,
        "favorite": False,
        "version": 1,
        "created": jetzt(),
        "modified": jetzt(),
        "source": {                       # Strategie für Quellgeometrie
            "strategy": "fusion-archiv",  # Komponente als .f3d im Benutzerdatenordner
            "file": None,                 # relativ zum Detailordner
            "componentName": "",
            "fusionVersion": "",
        },
        "anchor": {                       # Anschlusskante und lokales Koordinatensystem (Quellmodell, mm)
            "kind": "kante",
            "edgeLength": None,
            "edgeType": "gerade",
            "frame": None,                # {"origin":[x,y,z], "x":[..], "y":[..], "z":[..]}
        },
        "parameters": [],                 # wie Kantenvorlage + "fusionName" (Benutzerparameter im Quellmodell)
        "fixedParameters": [],            # dokumentierte feste Masse (nur Anzeige)
        "featureMapping": [],             # Zeitachsen-Features des Quellmodells (Namen), soweit erfasst
        "compatibility": {"thickness": None, "thicknessTolerance": 0.01, "edgeLengthMin": None,
                          "edgeLengthMax": None, "materials": [], "edgeType": "gerade"},
        "preview": {"image": None, "text": ""},
        "metadata": {"author": "", "notes": ""},
    }
    v.update(extra)
    return v


# ------------------------------------------------------------------ D Materialprofil
def neues_materialprofil(name, dicke_mm, **extra):
    """Nur was der Benutzer eingibt – keine erfundenen Fertigungswerte (Radius, K-Faktor, Dichte optional)."""
    m = {
        "schemaVersion": SCHEMA["materialprofil"],
        "typ": "materialprofil",
        "id": neue_id("mat"),
        "name": name,
        "material": "",
        "thickness": float(dicke_mm),
        "density": None,              # kg/dm³, optional – nur dann Gewichtsschätzung
        "innerRadius": None,          # mm, optional (für theoretische Abwicklung)
        "kFactor": None,              # optional (für theoretische Abwicklung)
        "sheetMetalRule": "",         # Name der Fusion-Blechregel (verbindliche Abwicklung)
        "notes": "",
        "sheets": [],                 # Tafelformate [[Breite, Länge], …] mm
        "coils": [],                  # Rollenbreiten [mm, …]
        "formingLimits": {            # empirische Grenzwerte – nur benutzerdefiniert
            "shrinkMaxPercent": None, "stretchMaxPercent": None, "source": "",
        },
        "created": jetzt(),
        "modified": jetzt(),
    }
    m.update(extra)
    return m


# ------------------------------------------------------------------ F Einstellungen
def standard_einstellungen():
    """Programmeinstellungen. Enthält KEINE Fertigungswerte (Material, Radien) – die legt der Benutzer an."""
    return {
        "schemaVersion": SCHEMA["einstellungen"],
        "typ": "einstellungen",
        "ui": {"mode": "standard", "showHelpHints": True},
        "defaultMaterialId": None,
        "units": {"length": "mm", "angle": "deg"},
        "export": {
            "layerContour": "ZUSCHNITT",
            "layerBendUp": "BIEGUNG_OBEN",
            "layerBendDown": "BIEGUNG_UNTEN",
            "layerText": "TEXT",
            "fileNamePattern": "{bauteil}_{material}_{dicke}mm",
            "folder": "",
        },
        "nesting": {"kerf": 0.0, "margin": 0.0, "rotationAllowed": False},
        "forming": {"cutsAllowed": False, "defaultProcess": "manuell"},
        "backup": {"autoBeforeMigration": True, "keepAutomatic": 20},
        # Etikettenbogen A4 – Druckformat (wie im CAD-Programm), kein Fertigungswert; vom Bogen des Herstellers ablesen
        "labels": {"spalten": 3, "zeilen": 8, "breite": 70.0, "hoehe": 37.0, "oben": 0.0, "links": 0.0, "abstandX": 0.0, "abstandY": 0.0},
        "order": {"objekt": "", "auftrag": ""},   # zuletzt verwendete Angaben für Stückliste/Etiketten
        "projectLibraryFolder": "",
        "cloud": {"syncOnStart": True, "updateCheckOnStart": True},   # Spengler-Digital-App (nur wenn angemeldet)
    }


# ------------------------------------------------------------------ C Bauplan / E Bauergebnis
def neuer_bauplan(vorlage, werte, material, ziele):
    return {
        "typ": "bauplan",
        "templateId": vorlage.get("id") if vorlage else None,
        "templateVersion": vorlage.get("version") if vorlage else None,
        "templateName": vorlage.get("name") if vorlage else "Direkteingabe",
        "values": dict(werte),
        "material": {"id": material.get("id"), "name": material.get("name"), "thickness": material.get("thickness")} if material else None,
        "targets": ziele,        # [{ref, beschreibung, eignung, gruende}]
        "operations": [],        # aufgelöste Operationen (Zahlen)
        "validation": {"errors": [], "warnings": []},
        "theory": None,          # theoretische Abwicklungszugabe
    }


class BuildResult(object):
    """Ergebnis einer Ausführung: erfolgreich / mit Warnungen / fehlgeschlagen."""

    def __init__(self):
        self.ausgefuehrt = []    # Beschreibung je erzeugter Operation
        self.warnungen = []
        self.fehler = []
        self.geometrie = []      # betroffene Geometrie (Text/IDs)
        self.diagnose = {}
        self.zurueckgesetzt = False

    @property
    def status(self):
        if self.fehler:
            return "fehler"
        return "warnung" if self.warnungen else "erfolg"

    def als_dict(self):
        return {"status": self.status, "ausgefuehrt": self.ausgefuehrt, "warnungen": self.warnungen,
                "fehler": self.fehler, "geometrie": self.geometrie, "diagnose": self.diagnose,
                "zurueckgesetzt": self.zurueckgesetzt}

    def text(self):
        z = {"erfolg": "Erfolgreich", "warnung": "Ausgeführt mit Warnungen", "fehler": "Fehlgeschlagen"}[self.status]
        teile = [z]
        if self.ausgefuehrt:
            teile.append("Ausgeführt: " + "; ".join(self.ausgefuehrt))
        if self.warnungen:
            teile.append("Warnungen: " + "; ".join(self.warnungen))
        if self.fehler:
            teile.append("Fehler: " + "; ".join(self.fehler))
        if self.zurueckgesetzt:
            teile.append("Die bereits erzeugten Schritte wurden wieder entfernt.")
        return "\n".join(teile)


def kopie(d):
    return copy.deepcopy(d)

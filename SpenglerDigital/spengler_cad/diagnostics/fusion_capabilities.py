"""Welche Fusion-API-Funktionen sind in DIESER Fusion-Version vorhanden?

Die Blech-API (Flansch, Saum) ist bei Autodesk als «Preview» gekennzeichnet und kann sich ändern.
Befehle, deren API fehlt, werden nicht ausgeführt, sondern erklären, was fehlt.
Die Prüfung liest nur Attribute – sie verändert nichts.
"""
from . import logger

PRUEFUNGEN = {
    # Schlüssel: (Beschreibung, Pfad ab design.rootComponent.features bzw. Objekt, Attribut)
    "flansch": ("Flansch an Kante (FlangeFeatures.createEdgeFlangeInput)", "features.flangeFeatures", "createEdgeFlangeInput"),
    "saum": ("Saum/Umschlag (HemFeatures)", "features.hemFeatures", "createHemFeatureInput"),
    "drehen": ("Drehkörper (RevolveFeatures)", "features.revolveFeatures", "createInput"),
    "abwicklung": ("Abwicklung (Component.createFlatPattern)", "", "createFlatPattern"),
    "dxf_abwicklung": ("DXF der Abwicklung (ExportManager.createDXFFlatPatternExportOptions)", "@export", "createDXFFlatPatternExportOptions"),
    "f3d_export": ("Komponente als .f3d exportieren", "@export", "createFusionArchiveExportOptions"),
    "f3d_import": ("Fusion-Archiv importieren", "@import", "createFusionArchiveImportOptions"),
    "attribute": ("Attribute an Features/Occurrences", "", "attributes"),
    "palette": ("HTML-Palette", "@ui", "palettes"),
}


def _aufloesen(obj, pfad):
    for teil in [p for p in pfad.split(".") if p]:
        obj = getattr(obj, teil, None)
        if obj is None:
            return None
    return obj


def pruefen(app):
    """→ {schluessel: (vorhanden: bool, beschreibung)}"""
    out = {}
    try:
        design = app.activeProduct
        root = getattr(design, "rootComponent", None)
    except Exception:
        root = None
    for k, (text, pfad, attr) in PRUEFUNGEN.items():
        try:
            if pfad == "@export":
                basis = getattr(getattr(app.activeProduct, "exportManager", None), attr, None) if root is not None else None
                ok = basis is not None
            elif pfad == "@import":
                ok = getattr(app.importManager, attr, None) is not None
            elif pfad == "@ui":
                ok = getattr(app.userInterface, attr, None) is not None
            else:
                basis = _aufloesen(root, pfad) if root is not None else None
                ok = basis is not None and hasattr(basis, attr)
        except Exception:
            ok = False
        out[k] = (bool(ok), text)
    logger.info("Fähigkeiten", **{k: v[0] for k, v in out.items()})
    return out


def text(faehigkeiten):
    return "\n".join("%s %s" % ("✓" if ok else "✗", t) for ok, t in faehigkeiten.values())

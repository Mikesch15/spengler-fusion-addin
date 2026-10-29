"""Selbsttest IN Fusion (Hilfe → «Selbsttest»): legt ein NEUES, leeres Konstruktionsdokument an und prüft dort
die API-Wege des Add-ins, die ohne eigenes Blechmodell prüfbar sind. Das Dokument des Benutzers wird nicht
verändert. Ergebnis als Text + Protokoll – dieses bitte schicken.

Geprüft:
  1 Fähigkeiten (welche API-Funktionen vorhanden sind)
  2 Rundblech: Drehkörper aus Querschnitt
  3 3D-Detail: Komponente mit Benutzerparameter → .f3d exportieren → wieder importieren → ausrichten →
    Parameter setzen (der komplette Weg von «3D-Detail erfassen/anwenden», ohne Benutzerdaten zu verändern)
  4 Einheiten: 25 mm in Fusion = 2.5 cm
Nicht geprüft (braucht ein Blechmodell des Benutzers): Flansch/Umschlag an Kanten, Abwicklung, DXF der Abwicklung.
"""
import os
import tempfile
import traceback

import adsk.core
import adsk.fusion

from . import fusion_capabilities, logger


def ausfuehren():
    app = adsk.core.Application.get()
    erg = []

    def schritt(name, f):
        try:
            r = f()
            erg.append("✓ %s%s" % (name, (": " + r) if r else ""))
        except Exception as e:
            logger.ausnahme("Selbsttest " + name)
            erg.append("✗ %s: %s" % (name, str(e).strip().splitlines()[-1] if str(e).strip() else traceback.format_exc().splitlines()[-1]))

    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = design.rootComponent
    from .. import VERSION
    erg.append("Add-in %s, Fusion %s, geladen aus:\n%s" % (VERSION, app.version, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    f = fusion_capabilities.pruefen(app)
    erg.append("Fähigkeiten:\n" + fusion_capabilities.text(f))

    def einheiten():
        p = design.userParameters.add("SD_TEST", adsk.core.ValueInput.createByString("25 mm"), "mm", "Selbsttest")
        if abs(p.value - 2.5) > 1e-9:
            raise RuntimeError("25 mm ergab %s cm" % p.value)
        p.deleteMe()
        return "25 mm = 2.5 cm"
    schritt("Einheiten", einheiten)

    def rundblech():
        from ..forming import forming as fo
        from ..geometry import fusion_adapter as fa
        feat = fa.drehkoerper(root, fo.drehprofil_scheibe(100, 20, 0.7, 1.0), "Selbsttest Rundblech")
        bb = feat.bodies.item(0).boundingBox
        d = (bb.maxPoint.x - bb.minPoint.x) * 10
        if abs(d - 2 * 100.35) > 0.5:
            raise RuntimeError("Durchmesser %.2f mm statt ca. 200.7 mm" % d)
        return "Ø %.2f mm" % d
    schritt("Rundblech (Drehkörper)", rundblech)

    def detail():
        from ..details import frames
        from ..geometry import fusion_adapter as fa
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = "SD Selbsttest Detail"
        design.userParameters.add("SD_H", adsk.core.ValueInput.createByString("20 mm"), "mm", "")
        sk = comp.sketches.add(comp.xYConstructionPlane)
        sk.sketchCurves.sketchLines.addTwoPointRectangle(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(5, 1, 0))
        comp.features.extrudeFeatures.addSimple(sk.profiles.item(0), adsk.core.ValueInput.createByString("SD_H"),
                                                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        tmp = os.path.join(tempfile.mkdtemp(prefix="spengler_selbsttest_"), "detail.f3d")
        fa.komponente_exportieren(comp, tmp)
        from ..details.detail_validation import parameter_zuordnen
        neu, neue_param = fa.detail_importieren(tmp, root)
        anker = frames.rahmen_aus_kante([0, 0, 0], [50, 0, 0], [0, 0, 1])
        ziel = frames.rahmen_aus_kante([0, 100, 0], [0, 150, 0], [0, 0, 1])
        neu.transform = fa.matrix_fusion(frames.ausrichtung(anker, ziel))
        t = neu.transform.translation
        pos = "Ursprung nach Ausrichtung (%.1f, %.1f, %.1f) mm" % (t.x * 10, t.y * 10, t.z * 10)
        namen = [p.name for p in design.userParameters]
        zuordnung, offen = parameter_zuordnen(["SD_H"], neue_param)
        if "SD_H" not in zuordnung:
            raise RuntimeError("importierter Parameter nicht eindeutig gefunden (neu: %s)" % neue_param)
        gesetzt, fehlend = fa.parameter_setzen({zuordnung["SD_H"]: "30 mm"})
        if design.userParameters.itemByName("SD_H").expression != "20 mm":
            raise RuntimeError("der VORHANDENE Parameter SD_H wurde verändert")
        return "%s; Benutzerparameter nach Import: %s; neu beim Import: %s; gesetzt %s (Original SD_H unverändert), fehlend %s; Körper importiert: %d" % (
            pos, ", ".join(namen), ", ".join(neue_param) or "–", gesetzt, fehlend + offen, neu.component.bRepBodies.count)
    schritt("3D-Detail Export/Import/Ausrichtung/Parameter", detail)

    erg.append("\nNicht geprüft (braucht Ihr Blechmodell): Flansch/Umschlag, Abwicklung, DXF – siehe Testanleitung (docs/Testanleitung.pdf).")
    erg.append("Das Testdokument «%s» kann ohne Speichern geschlossen werden." % doc.name)
    text = "\n".join(erg)
    logger.info("Selbsttest", ergebnis=text)
    return text

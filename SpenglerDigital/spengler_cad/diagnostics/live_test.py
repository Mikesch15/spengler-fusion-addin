"""Live-Test IN Fusion: baut in NEUEN, leeren Dokumenten ein Test-Blech (100 × 60 mm) und probiert die Fusion-Funktionen des Add-ins durch, die ohne
Fusion nicht prüfbar sind (Flansch, Umschlag, Gehrung, Versatz, Abwicklung, DXF …). Jeder Schritt läuft für sich und wird abgefangen – ein Fehler
stoppt den Test nicht. Die Dokumente des Benutzers werden nie verändert; alle Testdokumente werden am Ende ungespeichert geschlossen.
NICHT live geprüft (das IST der Live-Test); Fusion-Wege für das Test-Blech sind Annahmen und im Bericht nachvollziehbar."""
import os
import tempfile
import time
import traceback

import adsk.core
import adsk.fusion

from ..core import livetest_bericht as bericht
from ..geometry import fusion_adapter as fa
from . import fusion_capabilities, logger

LAENGE, BREITE = 100.0, 60.0     # mm
FLANSCH = 20.0                   # mm


class _Ctx(object):
    """Test-Blech des laufenden Schritts."""
    def __init__(self, design, root, body, dicke):
        self.design, self.root, self.body, self.dicke = design, root, body, dicke
        self.seite = "oben"


def _letzte_zeile(e):
    s = str(e).strip()
    return s.splitlines()[-1] if s else type(e).__name__


# ------------------------------------------------------------------ Test-Blech
def _neues_dokument(app):
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    return doc, design, design.rootComponent


def _blech_bauen(design, root):
    """Test-Blech mit derselben Funktion wie der Befehl «Blech aus Massaufnahme» (fa.grundblech_bauen)."""
    return fa.grundblech_bauen(root, LAENGE, BREITE, 1.0)


def _oberflaeche(body, seite="oben"):
    """Grösste ebene Fläche, deren Normale nach +Z (oben) bzw. −Z (unten) zeigt."""
    bester, flaeche = None, 0.0
    for f in body.faces:
        try:
            g = f.geometry
            if not isinstance(g, adsk.core.Plane):
                continue
            nz = fa.flaechennormale(f)[2]
            if (seite == "oben" and nz > 0.99) or (seite == "unten" and nz < -0.99):
                if f.area > flaeche:
                    bester, flaeche = f, f.area
        except Exception:
            continue
    if bester is None:
        raise RuntimeError("Keine ebene %sfläche am Test-Blech gefunden." % seite)
    return bester


def _rand_kanten(ctx, seite=None):
    """Gerade Randkanten der Ober-/Unterseite, lange (X) zuerst; → Liste."""
    f = _oberflaeche(ctx.root.bRepBodies.item(0), seite or ctx.seite)
    kanten = []
    for e in f.edges:
        if fa._kurventyp(e) == "linie":
            kanten.append(e)
    kanten.sort(key=lambda e: (-round(fa._kantenlaenge_mm(e)), e.boundingBox.minPoint.y, e.boundingBox.minPoint.x))
    return kanten


def _teilen_ecke(a, b):
    ps = [(v.geometry.x, v.geometry.y, v.geometry.z) for v in (a.startVertex, a.endVertex)]
    qs = [(v.geometry.x, v.geometry.y, v.geometry.z) for v in (b.startVertex, b.endVertex)]
    return any(max(abs(p[i] - q[i]) for i in range(3)) < 1e-6 for p in ps for q in qs)


def _eckkanten(ctx):
    """Zwei benachbarte Kanten (eine lange, eine kurze, die sich in einer Ecke treffen)."""
    k = _rand_kanten(ctx)
    for a in k:
        for b in k:
            if a is not b and _teilen_ecke(a, b) and abs(fa._kantenlaenge_mm(a) - fa._kantenlaenge_mm(b)) > 1:
                return [a, b]
    raise RuntimeError("Keine zwei benachbarten Kanten gefunden.")


def _volumen(ctx):
    return ctx.root.bRepBodies.item(0).physicalProperties.volume * 1000.0    # cm³ → mm³


def _plausibel(zuwachs, erwartet, unten=0.4, oben=2.0):
    return erwartet <= 0 or unten <= zuwachs / erwartet <= oben


def _op(typ="flansch", winkel=90.0, laenge=FLANSCH, radius=None, versatz=None):
    return {"typ": typ, "winkel": winkel, "laenge": laenge, "radius": radius, "bezug": None, "lage": None, "versatz": versatz}


def _flansch_versuch(ctx, **kw):
    """Flansch an der ersten langen Kante; probiert Ober- und Unterseite, merkt sich, was Fusion annimmt."""
    fehler = []
    for seite in (ctx.seite, "unten" if ctx.seite == "oben" else "oben"):
        try:
            ctx.seite = seite
            kante = _rand_kanten(ctx)[0]
            return fa.flansch(kante, **kw), kante, seite
        except Exception as e:
            fehler.append("%s: %s" % (seite, _letzte_zeile(e)))
    raise RuntimeError(" | ".join(fehler))


# ------------------------------------------------------------------ Schritte
def t_blech(ctx):
    d = fa.blechdicke_mm(ctx.body)
    return "Test-Blech %.0f × %.0f mm, Dicke laut Blechregel %s mm, Volumen %.0f mm³, %d Flächen, %d Kanten" % (
        LAENGE, BREITE, ("%.2f" % d) if d else "unbekannt", _volumen(ctx), ctx.body.faces.count, ctx.body.edges.count)


def t_flansch(ctx):
    v0 = _volumen(ctx)
    feat, kante, seite = _flansch_versuch(ctx, winkel=90, laenge_mm=FLANSCH)
    zu = _volumen(ctx) - v0
    erwartet = fa._kantenlaenge_mm(kante) * FLANSCH * (ctx.dicke or 1.0)
    txt = "Kante der %sseite, Volumen +%.0f mm³ (erwartet ca. %.0f)" % (seite, zu, erwartet)
    if not _plausibel(zu, erwartet):
        raise _Warnung(txt + " – Volumen weicht stark ab")
    return txt


def t_flansch_hinten(ctx):
    v0 = _volumen(ctx)
    kante = _rand_kanten(ctx)[0]
    fa.flansch(kante, winkel=-90, laenge_mm=FLANSCH)
    return "Flansch nach hinten (−90°), Volumen +%.0f mm³" % (_volumen(ctx) - v0)


def t_flansch_winkel(ctx):
    erg = []
    for w in (45, 135):
        feat, _, _ = _flansch_versuch(ctx, winkel=w, laenge_mm=15)
        erg.append("%d° ok" % w)
        fa.entfernen([feat])
    return ", ".join(erg)


def t_flansch_radius(ctx):
    fa.flansch(_rand_kanten(ctx)[0], winkel=90, laenge_mm=FLANSCH, radius_mm=3.0)
    return "Biegeradius 3 mm angenommen und Flansch gebaut"


def t_winkelfalz(ctx):
    """Winkelfalz 35 mm: Flansch 90° + zweiter Flansch 135° (wie in der Praxis gemeldet) an EINER Kante."""
    hin = []
    erz = fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, 35), _op("flansch", 135, 10)], ctx.dicke, {"livetest": 1}, hin)
    return "%d Schritte gebaut%s" % (len(erz), ("; Hinweise: " + " / ".join(hin)) if hin else "")


def t_umschlag(ctx):
    kante = _rand_kanten(ctx)[0]
    feat = fa.umschlag(kante, 10.0, False, None, None, ctx.dicke)
    return "Umschlag 10 mm gebaut (%s)" % type(feat).__name__


def t_umschlag_radius(ctx):
    kante = _rand_kanten(ctx)[0]
    fa.umschlag(kante, 10.0, False, 2.0, None, ctx.dicke)
    return "Umschlag 10 mm mit Radius/Abstand 2 mm gebaut"


def t_gehrung_flansch(ctx):
    """Zwei Eckkanten gemeinsam (Gehrung) gegen zwei Einzelflansche: Volumen und Flächenzahl verglichen."""
    kanten = _eckkanten(ctx)
    v0, f0 = _volumen(ctx), ctx.body.faces.count
    feat = fa.flansch(kanten, winkel=90, laenge_mm=FLANSCH)
    vg, fg = _volumen(ctx) - v0, ctx.root.bRepBodies.item(0).faces.count
    mit = None
    try:
        mit = getattr(feat, "isMiteredCorners", None)
    except Exception:
        pass
    fa.entfernen([feat])
    einzel = []
    for k in _eckkanten(ctx):
        einzel.append(fa.flansch(k, winkel=90, laenge_mm=FLANSCH))
    ve, fe = _volumen(ctx) - v0, ctx.root.bRepBodies.item(0).faces.count
    txt = "gemeinsam: +%.0f mm³, %d Flächen (isMiteredCorners=%s); einzeln: +%.0f mm³, %d Flächen (vorher %d)" % (vg, fg, mit, ve, fe, f0)
    if fg == fe and abs(vg - ve) < 1.0:
        raise _Warnung(txt + " – gemeinsam und einzeln sehen gleich aus: Gehrung wird NICHT geschnitten")
    return txt


def _gruppe(ctx, ops, name):
    kanten = _eckkanten(ctx)
    hin = []
    erz = fa.folge_anbringen_gruppe(kanten, ops, ctx.dicke, {"livetest": 1}, hin)
    txt = "%s an 2 Eckkanten: %d Features" % (name, len(erz))
    if hin:
        raise _Warnung(txt + "\n" + "\n".join(hin))
    return txt


def t_gehrung_winkelfalz(ctx):
    return _gruppe(ctx, [_op("flansch", 90, 35), _op("flansch", 135, 10)], "Winkelfalz 35")


def t_gehrung_umschlag(ctx):
    return _gruppe(ctx, [_op("umschlag", 180, 10)], "Umschlag")


def t_versatz(ctx):
    erg = []
    for v in (5.0, -5.0):
        hin = []
        v0 = _volumen(ctx)
        erz = fa.folge_anbringen(_rand_kanten(ctx)[0], [_op("flansch", 90, FLANSCH, versatz=v)], ctx.dicke, {"livetest": 1}, hin)
        zu = _volumen(ctx) - v0
        erwartet = fa._kantenlaenge_mm(_rand_kanten(ctx)[0]) * FLANSCH * (ctx.dicke or 1.0)
        erg.append("%+g mm: ok, Volumen %+.0f mm³ (Blechdicke %.2f)%s" % (v, zu, ctx.dicke or 0, ("; " + " / ".join(hin)) if hin else ""))
        if zu > 3 * erwartet:
            erg[-1] += " – Volumen viel zu gross (Dicke verdoppelt?)"
        fa.entfernen(erz)
    if any("zu gross" in x for x in erg):
        raise _Warnung("\n".join(erg))
    return "; ".join(erg)


def t_abwicklung(ctx):
    feat, _, _ = _flansch_versuch(ctx, winkel=90, laenge_mm=FLANSCH)
    stat = _oberflaeche(ctx.root.bRepBodies.item(0), "oben")
    fp, neu = fa.abwicklung(ctx.root, stat)
    m = fa.abwicklung_masse(fp)
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "abwicklung.dxf")
    fa.dxf_abwicklung(fp, pfad)
    gross, klein = max(m["laenge"], m["breite"]), min(m["laenge"], m["breite"])
    txt = "Abwicklung %.1f × %.1f mm (erwartet ca. %.0f × %.0f), DXF %d Byte" % (gross, klein, LAENGE, BREITE + FLANSCH, os.path.getsize(pfad))
    if abs(gross - LAENGE) > 3 or not (BREITE + FLANSCH - 6 <= klein <= BREITE + FLANSCH + 2):
        raise _Warnung(txt + " – Mass weicht ab")
    return txt


def t_bildschirmfoto(ctx):
    pfad = os.path.join(tempfile.mkdtemp(prefix="spengler_livetest_"), "foto.png")
    ok = adsk.core.Application.get().activeViewport.saveAsImageFile(pfad, 320, 240)
    if not ok or not os.path.exists(pfad) or os.path.getsize(pfad) == 0:
        raise RuntimeError("Bildschirmfoto wurde nicht erzeugt.")
    return "Bildschirmfoto %d Byte" % os.path.getsize(pfad)


def t_ordnerpfad(ctx):
    pfad = fa.dokument_ordnerpfad()
    n = fa.dokument_name()
    return "Dokument «%s», Ordnerpfad %s" % (n, "/".join(pfad) if pfad else "(ungespeichert, leer)")


def _bauteil(ctx, verlauf, ring, seiten, name):
    """Bauteil im Grundriss wie der Befehl «Bauteil erstellen»: Band aus dem Verlauf, Grundblech, Kantenfolgen an den Ketten."""
    from ..core import bauteil, models
    v = models.neue_bauteilvorlage("Livetest")
    v["breite"] = "100"
    v["verlauf"] = {"art": "grundriss", "beispiel": verlauf, "seite": "links"}
    v["seiten"] = bauteil.seiten_aus_texten(seiten)
    p = bauteil.plan(v, {}, {"thickness": 1.0, "innerRadius": 1.0, "kFactor": 0.4}, verlauf, None, True, ring)
    g = p["geometrie"]
    body = fa.blech_aus_profil(ctx.root, g["schleifen"], 1.0)
    ketten = fa.kanten_nach_ketten(body, g["ketten"])
    hin, txt = [], [p["text"]]
    for seite, ops in p["seiten"].items():
        if ops and seite in ketten:
            erz = fa.kanten_folge_bauen(ketten[seite], ops, ctx.dicke, {"livetest": 1}, hin)
            txt.append("%s: %d Feature(s) an %d Kante(n)" % (seite, len(erz), len(ketten[seite])))
    if hin:
        raise _Warnung("%s – %s: %s" % (name, "\n".join(txt), "\n".join(hin)))
    return "%s: %s" % (name, "; ".join(txt))


def t_bauteil_l(ctx):
    return _bauteil(ctx, "300 L90 200", False, {"verlauf": "90 20"}, "L-förmiger Verlauf, Flansch an der Verlaufskante (Gehrung an der Ecke)")


def t_bauteil_ring(ctx):
    return _bauteil(ctx, "300 L90 200 L90 300 L90 200 L90", True, {"verlauf": "90 20", "gegen": "90 15"}, "Ring mit Flansch an beiden Kanten")


class _Warnung(Exception):
    """Schritt lief, aber das Ergebnis ist auffällig."""


SCHRITTE = [
    ("Test-Blech (Basisflansch)", t_blech, False),
    ("Flansch 90° (Kante des Test-Blechs)", t_flansch, True),
    ("Flansch nach hinten (−90°)", t_flansch_hinten, True),
    ("Flansch 45° und 135°", t_flansch_winkel, True),
    ("Flansch mit Biegeradius 3 mm", t_flansch_radius, True),
    ("Winkelfalz 35 mm an einer Kante", t_winkelfalz, True),
    ("Umschlag 10 mm an einer Kante", t_umschlag, True),
    ("Umschlag mit Radius = Abstand 2 mm", t_umschlag_radius, True),
    ("Gehrung: Flansch an 2 Eckkanten", t_gehrung_flansch, True),
    ("Gehrung: Winkelfalz 35 an 2 Eckkanten", t_gehrung_winkelfalz, True),
    ("Gehrung: Umschlag an 2 Eckkanten", t_gehrung_umschlag, True),
    ("Versatz +5 mm und −5 mm", t_versatz, True),
    ("Abwicklung und DXF", t_abwicklung, True),
    ("Bauteil: L-förmiger Grundrissverlauf", t_bauteil_l, False),
    ("Bauteil: geschlossener Ring", t_bauteil_ring, False),
    ("Bildschirmfoto der Ansicht", t_bildschirmfoto, False),
    ("Ordnerpfad des Dokuments lesen", t_ordnerpfad, False),
]


def _alles_schliessen(dokumente):
    for d in reversed(dokumente):
        try:
            d.close(False)
        except Exception:
            logger.warnung("Testdokument nicht geschlossen")


def ausfuehren(fortschritt=None):
    """Alle Schritte nacheinander. → (Ergebnisliste, Kopfzeile). fortschritt(text) wird je Schritt aufgerufen (darf fehlen)."""
    app = adsk.core.Application.get()
    try:
        original = app.activeDocument
    except Exception:
        original = None
    from .. import VERSION
    kopf = "Live-Test Add-in %s, Fusion %s, %s" % (VERSION, app.version, time.strftime("%d.%m.%Y %H:%M"))
    erg, dokumente = [], []
    f = fusion_capabilities.pruefen(app)
    fehlt = [t for ok, t in f.values() if not ok]
    erg.append({"name": "Fähigkeiten der Fusion-Version", "status": "warnung" if fehlt else "ok",
                "detail": ("Fehlt: " + "; ".join(fehlt)) if fehlt else "alle geprüften Funktionen vorhanden", "dauer": None})
    blech_ok = True
    try:
        for nr, (name, funktion, braucht_blech) in enumerate(SCHRITTE, 1):
            if fortschritt:
                try:
                    fortschritt("Schritt %d von %d: %s" % (nr, len(SCHRITTE), name))
                except Exception:
                    pass
            if braucht_blech and not blech_ok:
                erg.append({"name": name, "status": "uebersprungen", "detail": "Test-Blech konnte nicht erzeugt werden", "dauer": None})
                continue
            t0, status, detail = time.time(), "ok", ""
            try:
                doc, design, root = _neues_dokument(app)
                dokumente.append(doc)
                if braucht_blech or funktion is t_blech:
                    body = _blech_bauen(design, root)
                    ctx = _Ctx(design, root, body, fa.blechdicke_mm(body) or 1.0)
                else:
                    ctx = _Ctx(design, root, None, 1.0)
                detail = funktion(ctx) or ""
            except _Warnung as w:
                status, detail = "warnung", str(w)
            except Exception as e:
                status, detail = "fehler", _letzte_zeile(e)
                logger.ausnahme("Live-Test " + name)
                if funktion is t_blech:
                    blech_ok = False
                    detail += "\n" + "\n".join(traceback.format_exc().splitlines()[-3:-1])
            erg.append({"name": name, "status": status, "detail": detail, "dauer": time.time() - t0})
            try:
                adsk.doEvents()
            except Exception:
                pass
        # Rundblech und 3D-Detail (eigener Selbsttest, öffnet selbst ein Dokument)
        t0 = time.time()
        try:
            from . import selftest
            text = selftest.ausfuehren()
            dokumente.append(app.activeDocument)
            schlecht = [z for z in text.splitlines() if z.startswith("✗")]
            erg.append({"name": "Rundblech und 3D-Detail (Export/Import/Ausrichtung)", "status": "fehler" if schlecht else "ok",
                        "detail": "\n".join(schlecht) if schlecht else "ok", "dauer": time.time() - t0})
        except Exception as e:
            erg.append({"name": "Rundblech und 3D-Detail", "status": "fehler", "detail": _letzte_zeile(e), "dauer": time.time() - t0})
            logger.ausnahme("Live-Test Rundblech/Detail")
    finally:
        _alles_schliessen(dokumente)
        try:
            if original is not None:
                original.activate()
        except Exception:
            pass
    return erg, kopf

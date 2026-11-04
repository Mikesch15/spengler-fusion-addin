"""Kleine Fusion-ATTRAPPEN für Blech-Abläufe (Regel, Komponente, Skizze, Basisflansch, Löschen). Sie bilden nur das nach, was die
Ablauf-Logik des Adapters braucht – sie beweisen NICHT, dass Fusion so rechnet. KEIN Fusion-Live-Test."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))


class Liste(object):
    def __init__(self, elemente=None):
        self.elemente = list(elemente or [])

    @property
    def count(self):
        return len(self.elemente)

    def item(self, i):
        return self.elemente[i]

    def __iter__(self):
        return iter(list(self.elemente))


class Objekt(object):
    """Löschbares Fusion-Objekt. ergebnis: Rückgabe von deleteMe (True/False) oder Exception."""
    def __init__(self, name="", ergebnis=True, behaelter=None):
        self.name, self.isValid, self._ergebnis, self._behaelter = name, True, ergebnis, behaelter
        self.entityToken = "tok-%s-%d" % (name, id(self))

    def deleteMe(self):
        if isinstance(self._ergebnis, Exception):
            raise self._ergebnis
        if self._ergebnis:
            self.isValid = False
            if self._behaelter is not None and self in self._behaelter.elemente:
                self._behaelter.elemente.remove(self)
        return self._ergebnis


class Wert(object):
    def __init__(self, mm, setzbar=True):
        self.value, self._setzbar = mm / 10.0, setzbar

    @property
    def expression(self):
        return "%g mm" % (self.value * 10)

    @expression.setter
    def expression(self, text):
        if self._setzbar:
            self.value = float(re.match(r"\s*([\d.]+)", text).group(1)) / 10.0


class Regel(Objekt):
    def __init__(self, name, mm, setzbar=True):
        Objekt.__init__(self, name)
        self.thickness = Wert(mm, setzbar)
        self.entityToken = "regel-" + name


class Regeln(Liste):
    def __init__(self, regeln=(), setzbar=True):
        Liste.__init__(self, regeln)
        self.kopien, self._setzbar = [], setzbar

    def addByCopy(self, quelle, name):
        r = Regel(name, quelle.thickness.value * 10, self._setzbar)
        self.elemente.append(r)
        self.kopien.append((quelle.name, name))
        return r


class Punkt(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z


class Box(object):
    def __init__(self, z0, z1):
        self.minPoint, self.maxPoint = Punkt(0, 0, z0), Punkt(10, 6, z1)


class Koerper(Objekt):
    def __init__(self, comp, dicke_mm, behaelter):
        Objekt.__init__(self, "Körper", behaelter=behaelter)
        self.parentComponent, self.isSolid, self.isSheetMetal = comp, True, True
        self.boundingBox = Box(0.0, dicke_mm / 10.0)
        self.faces, self.volume = [], 6.0 * dicke_mm / 10.0


class Profil(object):
    def __init__(self, schleifen):
        self.profileLoops = Liste([object()] * schleifen)


class Skizze(Objekt):
    def __init__(self, behaelter):
        Objekt.__init__(self, "Skizze", behaelter=behaelter)
        self.linien = 0
        skizze = self

        class Linien(object):
            def addByTwoPoints(self, a, b):
                skizze.linien += 1
                return object()

        class Kurven(object):
            sketchLines = Linien()
        self.sketchCurves = Kurven()
        self.schleifen = 1

    @property
    def profiles(self):
        return Liste([Profil(self.schleifen)] if self.linien >= 3 else [])


class Flansche(object):
    """createBaseFlangeInput/add. ziel: Komponente, in der der Körper entsteht (Standard: die eigene); dicke_mm: erzwungene falsche Dicke."""
    def __init__(self, comp):
        self.comp, self.ziel, self.dicke_mm, self.aufrufe, self.features = comp, None, None, [], []

    def createBaseFlangeInput(self, *args):
        self.aufrufe.append(args)
        if len(args) != 1:
            raise TypeError("createBaseFlangeInput() takes 1 argument")
        return object()

    def add(self, inp):
        ziel = self.ziel or self.comp
        regel = self.comp.activeSheetMetalRule
        dicke = self.dicke_mm if self.dicke_mm is not None else regel.thickness.value * 10
        k = Koerper(ziel, dicke, ziel.bRepBodies)
        ziel.bRepBodies.elemente.append(k)
        f = Objekt("Basisflansch")
        orig = f.deleteMe

        def loeschen():
            if k in ziel.bRepBodies.elemente:
                ziel.bRepBodies.elemente.remove(k)
            k.isValid = False
            return orig()
        f.deleteMe = loeschen
        self.features.append(f)
        return f


class Komponente(object):
    def __init__(self, name, regel=None, koerper=0):
        self.name, self.entityToken, self.activeSheetMetalRule = name, "comp-" + name, regel
        self.bRepBodies = Liste()
        for _ in range(koerper):
            self.bRepBodies.elemente.append(Koerper(self, 1.0, self.bRepBodies))
        self.skizzen = Liste()
        comp = self

        class Skizzen(object):
            def add(self, ebene):
                s = Skizze(comp.skizzen)
                comp.skizzen.elemente.append(s)
                return s
        self.sketches = Skizzen()
        self.xYConstructionPlane = object()

        class Features(object):
            pass
        self.features = Features()
        self.features.flangeFeatures = Flansche(self)


class Occ(object):
    def __init__(self, design, comp, aktivierbar=True):
        self.design, self.component, self.aktivierbar, self.isValid = design, comp, aktivierbar, True

    def activate(self):
        if self.aktivierbar:
            self.design.activeOccurrence = self
            self.design.aktivierungen.append(self.component.name)
        return self.aktivierbar


class Design(object):
    def __init__(self, design_regeln=(), bibliothek=(), setzbar=True):
        self.rootComponent = Komponente("Root")
        self.occs = []
        self.activeOccurrence = None
        self.aktivierungen = []
        self.designSheetMetalRules = Regeln(design_regeln, setzbar)
        self.librarySheetMetalRules = Regeln(bibliothek or [Regel("Stahl 1 mm (Bibliothek)", 1.0)])
        d = self

        def nach_comp(comp):
            return [o for o in d.occs if o.component is comp]
        self.rootComponent.allOccurrencesByComponent = nach_comp
        self.rootComponent.allOccurrences = self.occs

    def activateRootComponent(self):
        self.activeOccurrence = None
        self.aktivierungen.append("Root")
        return True

    def neue_komponente(self, name, aktivierbar=True, regel=None, koerper=0):
        c = Komponente(name, regel, koerper)
        self.occs.append(Occ(self, c, aktivierbar))
        return c

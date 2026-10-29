"""ATTRAPPE der Fusion-API – nur für automatische Import-/Startprüfungen ausserhalb von Fusion.
Sie bildet KEIN Fusion-Verhalten nach: jedes Attribut liefert wieder eine Attrappe. Tests damit beweisen
nur, dass der Code lädt und ohne Python-Fehler (Tippfehler, fehlende Namen) durch die Abläufe kommt."""
import sys

AUFRUFE = []


class Attrappe(object):
    def __init__(self, *a, **k):
        self._name = k.get("_name", "attrappe")

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return Attrappe(_name=n)

    def __call__(self, *a, **k):
        AUFRUFE.append((self._name, a))
        return Attrappe(_name=self._name + "()")

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def __bool__(self):
        return True

    def __float__(self):
        return 1.0

    def __int__(self):
        return 1

    __index__ = __int__

    def __eq__(self, o):
        return self is o

    def __hash__(self):
        return id(self)

    def __lt__(self, o):
        return False

    __gt__ = __le__ = __ge__ = __lt__

    def __str__(self):
        return "Attrappe(%s)" % self._name

    def __add__(self, o):
        return 1.0

    __sub__ = __mul__ = __truediv__ = __radd__ = __rsub__ = __rmul__ = __rtruediv__ = __add__


class _Meta(type):
    def __getattr__(cls, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return Attrappe(_name=n)


class _Modul(object):
    def __init__(self, name):
        self.__name__ = name
        self._klassen = {}

    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        if n not in self._klassen:
            k = _Meta(n, (Attrappe,), {})
            for statisch in ("get", "cast", "create", "createByString", "createByReal", "createWithArray"):
                setattr(k, statisch, staticmethod(lambda *a, **kw: Attrappe(_name=n)))
            self._klassen[n] = k
        return self._klassen[n]


core = _Modul("adsk.core")
fusion = _Modul("adsk.fusion")
sys.modules["adsk.core"] = core
sys.modules["adsk.fusion"] = fusion

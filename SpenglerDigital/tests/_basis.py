"""Gemeinsame Hilfen für die Tests (ohne Fusion). Jeder Test bekommt einen eigenen, leeren Datenordner."""
import os
import shutil
import sys
import tempfile
import unittest

ADDIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ADDIN not in sys.path:
    sys.path.insert(0, ADDIN)
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class DatenTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="spengler_test_")
        self._alt = os.environ.get("SPENGLER_CAD_DATEN")
        os.environ["SPENGLER_CAD_DATEN"] = self.ordner

    def tearDown(self):
        if self._alt is None:
            os.environ.pop("SPENGLER_CAD_DATEN", None)
        else:
            os.environ["SPENGLER_CAD_DATEN"] = self._alt
        shutil.rmtree(self.ordner, ignore_errors=True)


def test_material(**extra):
    """Technisches Testmaterial – NUR für Tests, nie in der produktiven Bibliothek."""
    from spengler_cad.core.models import neues_materialprofil
    m = neues_materialprofil("TEST Blech 0.7", 0.7, innerRadius=1.0, kFactor=0.4, density=7.2)
    m.update(extra)
    return m


def datei_inhalt(pfad, binaer=False):
    with open(pfad, "rb" if binaer else "r", **({} if binaer else {"encoding": "utf-8"})) as f:
        return f.read()

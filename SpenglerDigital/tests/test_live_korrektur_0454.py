"""Regression aus dem Live-Test 0.4.53 (Kanten bearbeiten, eigene Geometrie): «NoneType * float», weil der Bauplan Innenradius/K-Faktor des
Materials verlor; und Textfelder, die HTML roh zeigten (.text statt .formattedText). Ohne Fusion."""
import os
import re
import unittest

from _basis import DatenTest  # noqa: F401
from spengler_cad.core import models

CMD = os.path.join(os.path.dirname(__file__), "..", "spengler_cad", "commands")


class BauplanMaterial(unittest.TestCase):
    def test_innenradius_und_k_faktor_bleiben_im_plan(self):
        p = models.neuer_bauplan({"id": "v", "name": "V", "version": 1}, {}, {"id": "m", "name": "Test", "thickness": 1.0, "innerRadius": 1.0,
                                                                            "kFactor": 0.44}, [])
        self.assertEqual((p["material"]["innerRadius"], p["material"]["kFactor"]), (1.0, 0.44))


class EigeneFolgeOhneWerte(unittest.TestCase):
    def test_klare_meldung_statt_typfehler(self):
        from spengler_cad.commands import bauteil_command
        fa = bauteil_command.fa
        with self.assertRaises(fa.AdapterFehler) as e:
            fa.eigene_folge(None, [], 1.0, 1.0, None, {})
        self.assertIn("K-Faktor", str(e.exception))


class Textfelder(unittest.TestCase):
    def test_kein_html_ueber_text_gesetzt(self):
        for n in os.listdir(CMD):
            if n.endswith(".py"):
                s = open(os.path.join(CMD, n), encoding="utf-8").read()
                self.assertFalse(re.search(r'itemById\("[^"]+"\)\.text\s*=', s), "%s setzt .text (zeigt HTML roh) – formattedText verwenden" % n)

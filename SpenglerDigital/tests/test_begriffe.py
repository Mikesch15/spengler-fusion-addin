"""Restpunkt 2 (Review 0.4.49): Benutzertexte und Doku versprechen keine praktisch verifizierte «exakte» Abwicklung oder Zuschnittlänge und keine
Prototyp-Freigabe über die Einstellungen. Mathematische Verwendungen («exakt benannte Fälle», interner Kennwert 'exakt') bleiben erlaubt."""
import os
import re
import unittest

from _basis import DatenTest, test_material  # noqa: F401

HIER = os.path.dirname(os.path.abspath(__file__))
ADDIN = os.path.dirname(HIER)

# Formulierungen, die Fertigungsgenauigkeit suggerieren bzw. eine veraltete Freigabe beschreiben
VERBOTEN = [r"exakte\s+Abwicklung", r"exaktes\s+Profil", r"exakter\s+Querschnitt", r"eigene\s+exakte", r"exakt\s+abwickelbar", r"exakter\s+Zuschnitt",
            r"exakte\s+Zuschnitt", r"Prototypen\s+zulassen", r"Freigabe\s+in\s+den\s+Einstellungen", r"Einstellungen\s+nach\s+bestandenem"]
# Benutzersichtbare Quellen und aktuelle Doku (Verlaufsberichte BERICHT_*/ABSCHLUSSBERICHT_* sind Historie)
DATEIEN = ["spengler_cad/commands/edge_apply_command.py", "spengler_cad/commands/export_command.py", "spengler_cad/core/operation_plan.py",
           "spengler_cad/core/unterstuetzung.py", "spengler_cad/core/profil_engine.py", "spengler_cad/core/machbarkeit_gekruemmt.py",
           "spengler_cad/geometry/fusion_adapter.py", "spengler_cad/ui/help_content.py", "spengler_cad/diagnostics/live_test_gekruemmt.py",
           "spengler_cad/diagnostics/live_test_kantenwerkzeug.py", "docs/Benutzerhandbuch.md", "docs/Testanleitung.md", "docs/ANFORDERUNGEN_STATUS.md"]


class Begriffe(unittest.TestCase):
    def test_keine_irrefuehrenden_formulierungen(self):
        treffer = []
        for rel in DATEIEN:
            with open(os.path.join(ADDIN, rel), encoding="utf-8") as f:
                for nr, z in enumerate(f, 1):
                    for muster in VERBOTEN:
                        if re.search(muster, z, re.I):
                            treffer.append("%s:%d «%s»" % (rel, nr, re.search(muster, z, re.I).group(0)))
        self.assertEqual(treffer, [], "irreführende Formulierungen:\n" + "\n".join(treffer))

    def test_ui_bauplan_und_warnungen(self):
        from spengler_cad.core import operation_plan as op
        from spengler_cad.core import unterstuetzung as u
        from test_operation_plan import kante
        from test_templates import testvorlage
        t = op.beschreibung(op.erstelle(testvorlage(), {"H": 25}, test_material(innerRadius=1.0, kFactor=0.4), [kante()], "eigen"))
        self.assertIn("mathematisch abwickelbar", t)
        self.assertIn("theoretisch", t.lower())
        self.assertNotRegex(t, r"(?i)exakt")
        g = u.pruefen_bauweise("flansch", "zylinder", "gerade", "eigen")
        self.assertIn("Entwickler-Override", g)
        self.assertNotIn("Einstellungen", g)
        with open(os.path.join(ADDIN, "spengler_cad/commands/edge_apply_command.py"), encoding="utf-8") as f:
            quelle = f.read()
        tooltip = re.search(r'bw\.tooltip = \((.*?)\)\n', quelle, re.S).group(1)
        self.assertIn("THEORETISCHEM Zuschnitt", tooltip)
        self.assertNotRegex(tooltip, r"(?i)exakt")
        for auswahl in re.findall(r'bw\.listItems\.add\("([^"]+)"', quelle):
            self.assertNotRegex(auswahl, r"(?i)exakt", auswahl)

    def test_mathematische_verwendung_bleibt_erlaubt(self):
        self.assertFalse(any(re.search(m, "Override für exakt benannte Fälle", re.I) for m in VERBOTEN))
        self.assertFalse(any(re.search(m, "art != 'exakt'", re.I) for m in VERBOTEN))

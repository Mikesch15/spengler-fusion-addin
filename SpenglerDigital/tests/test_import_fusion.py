"""Syntax- und Importprüfung aller Module sowie Start/Stop des Add-ins mit einer Fusion-ATTRAPPE.
Das ersetzt KEINEN Test in Fusion (siehe tests/fusion/LIVE_TESTS.md)."""
import os
import py_compile
import sys
import unittest

from _basis import ADDIN, DatenTest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fusion_stub"))
import adsk  # noqa: E402  (Attrappe)


def alle_module():
    for wurzel, _, namen in os.walk(os.path.join(ADDIN, "spengler_cad")):
        for n in namen:
            if n.endswith(".py"):
                rel = os.path.relpath(os.path.join(wurzel, n), ADDIN)[:-3].replace(os.sep, ".")
                yield rel[:-9] if rel.endswith(".__init__") else rel


class ImportTest(DatenTest):
    def test_syntax(self):
        for wurzel, _, namen in os.walk(ADDIN):
            for n in namen:
                if n.endswith(".py"):
                    py_compile.compile(os.path.join(wurzel, n), doraise=True)

    def test_alle_module_importierbar(self):
        import importlib
        mods = list(alle_module())
        self.assertGreater(len(mods), 30)
        for m in mods:
            importlib.import_module(m)

    def test_start_und_stop(self):
        import importlib
        import SpenglerDigital
        importlib.reload(SpenglerDigital)
        del adsk.AUFRUFE[:]
        SpenglerDigital.run({})
        boxen = [a for n, a in adsk.AUFRUFE if n == "messageBox"]
        self.assertEqual(boxen, [], "Start meldete: %r" % boxen)
        namen = [n for n, _ in adsk.AUFRUFE]
        self.assertGreaterEqual(namen.count("addButtonDefinition"), 8)
        SpenglerDigital.stop({})
        # Erneutes Ausführen lädt den Programmcode NEU (Fusion hält Module sonst bis zum Neustart im Speicher)
        import spengler_cad
        spengler_cad._alter_stand = True
        SpenglerDigital.run({})
        import spengler_cad as neu
        self.assertFalse(hasattr(neu, "_alter_stand"))
        SpenglerDigital.stop({})

    def test_dialoge_aufbauen(self):
        """Jeder Befehlsdialog lässt sich mit der Attrappe aufbauen (keine Python-Fehler in den Abläufen)."""
        from spengler_cad.commands import detail_generator_command as d, edge_apply_command as e, export_command as x, forming_command as f, settings_command as s
        args = adsk.core.CommandCreatedEventArgs()
        for fn in (e.erstellt, d.erfassen_erstellt, d.anwenden_erstellt, f.erstellt, x.abw_erstellt, x.zus_erstellt, s.hilfe_erstellt):
            del adsk.AUFRUFE[:]
            fn(args)
            self.assertFalse([a for n, a in adsk.AUFRUFE if n == "messageBox"], fn.__name__)


if __name__ == "__main__":
    unittest.main()

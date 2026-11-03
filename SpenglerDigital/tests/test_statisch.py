"""Statische Prüfung: keine nicht definierten Namen im Add-in (so ein Fehler – ein Aufruf einer Funktion, die es nicht gibt – bricht erst in Fusion ab; Live 3.11., Bericht 98.487)."""
import os
import subprocess
import sys
import unittest

ADDIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Statisch(unittest.TestCase):
    def test_keine_undefinierten_namen(self):
        try:
            import pyflakes  # noqa: F401
        except ImportError:
            self.skipTest("pyflakes nicht installiert (pip install pyflakes)")
        r = subprocess.run([sys.executable, "-m", "pyflakes", os.path.join(ADDIN, "spengler_cad")], capture_output=True, text=True)
        schlecht = [z for z in (r.stdout + r.stderr).splitlines() if "undefined name" in z]
        self.assertEqual(schlecht, [], "\n".join(schlecht))


if __name__ == "__main__":
    unittest.main()

"""Alle automatischen Tests ohne Fusion: python3 tests/run_all.py  (Ausgabe: Anzahl, Fehler)."""
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
sys.path.insert(0, os.path.dirname(HIER))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(HIER, pattern="test_*.py", top_level_dir=HIER)
    r = unittest.TextTestRunner(verbosity=2 if "-v" in sys.argv else 1).run(suite)
    print("\nERGEBNIS: %d Tests, %d Fehler, %d Ausfälle, %d übersprungen" % (r.testsRun, len(r.errors), len(r.failures), len(r.skipped)))
    sys.exit(0 if r.wasSuccessful() else 1)

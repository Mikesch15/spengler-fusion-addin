"""Korrektur 0.4.49 Phase 3: ungetestete Prototypen bleiben im Produktionsmodus gesperrt – reine Logik, KEIN Fusion-Test."""
import os
import unittest

from _basis import DatenTest, test_material
from spengler_cad.core import experimentell as ex
from spengler_cad.core import operation_plan as op
from test_operation_plan import kante
from test_templates import testvorlage


class Sperre(unittest.TestCase):
    def setUp(self):
        self.alt = os.environ.pop(ex.VARIABLE, None)
        self.addCleanup(lambda: os.environ.__setitem__(ex.VARIABLE, self.alt) if self.alt is not None else os.environ.pop(ex.VARIABLE, None))

    def plan(self, freigabe, **k):
        return op.erstelle(testvorlage(), {"H": 25}, test_material(innerRadius=1.0, kFactor=0.4), [kante(**k)], "eigen", freigabe)

    def test_standard_gesperrt(self):
        self.assertEqual(ex.faelle(), frozenset())
        self.assertFalse(op.ist_ausfuehrbar(self.plan(ex.faelle(), flaeche="zylinder")))

    def test_override_gibt_nur_den_exakten_fall_frei(self):
        os.environ[ex.VARIABLE] = "flansch/zylinder/gerade"
        f = ex.faelle()
        self.assertEqual(f, frozenset({("flansch", "zylinder", "gerade")}))
        # Vorlage hat Flansch UND Umschlag → der Umschlag-Fall ist nicht freigegeben → weiterhin gesperrt
        self.assertFalse(op.ist_ausfuehrbar(self.plan(f, flaeche="zylinder")))
        os.environ[ex.VARIABLE] = "flansch/zylinder/gerade; umschlag/zylinder/gerade"
        self.assertTrue(op.ist_ausfuehrbar(self.plan(ex.faelle(), flaeche="zylinder")))
        self.assertFalse(op.ist_ausfuehrbar(self.plan(ex.faelle(), flaeche="kegel")), "Kegel nicht benannt → gesperrt")

    def test_ungueltige_werte_geben_nie_frei(self):
        for roh in ("1", "true", "alles", "flansch/zylinder", "flansch/zylinder/bogen", "flansch/eben/gerade", "x/y/z", "*/*/*", ""):
            self.assertEqual(ex.faelle(roh), frozenset(), roh)
        for frei in (None, False, "flansch/zylinder/gerade", 1, 0.5):
            self.assertFalse(ex.erlaubt(frei, "flansch", "zylinder", "gerade"), repr(frei))

    def test_nicht_unterstuetzte_kombination_bleibt_gesperrt(self):
        os.environ[ex.VARIABLE] = "flansch/eben/bogen;flansch/doppelt_gekruemmt/gerade"
        self.assertEqual(ex.faelle(), frozenset())
        self.assertFalse(op.ist_ausfuehrbar(self.plan(ex.faelle(), kurve="bogen")))

    def test_normale_einstellung_schaltet_nicht_frei(self):
        from spengler_cad.core import models
        self.assertNotIn("prototypenFreigegeben", models.standard_einstellungen()["geometrie"])
        self.assertIn("EXPERIMENTELL – NICHT LIVE GETESTET", ex.warnung({("flansch", "zylinder", "gerade")}))


class EinstellungDatei(DatenTest):
    def test_alte_einstellung_bleibt_wirkungslos(self):
        from spengler_cad.storage.settings_service import Einstellungen
        e = Einstellungen()
        d = e.laden()
        d["geometrie"]["prototypenFreigegeben"] = True                 # alte Datei mit dem früheren Schalter
        e.speichern(d)
        self.assertEqual(ex.faelle(), frozenset(), "die Einstellungsdatei hat keinen Einfluss auf die Freigabe")


if __name__ == "__main__":
    unittest.main()

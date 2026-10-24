"""Ensure Windows packaged GUI smoke validates real startup evidence.

Static regression check; does not replace executing the Windows binary.
Author: Abdelhalim Talbi.
"""
from pathlib import Path
import unittest


class WindowsSmokeEvidenceTests(unittest.TestCase):
    def test_smoke_requires_qt_startup_stages(self):
        app=Path(__file__).resolve().parents[1]
        smoke=(app/'windows'/'smoke-windows.ps1').read_text(encoding='utf-8')
        self.assertIn('startup.jsonl',smoke)
        for stage in ('qt_init','main_window','event_loop'):
            with self.subTest(stage=stage):
                self.assertIn(stage,smoke)
        self.assertIn("$_ .outcome",smoke.replace('$_.outcome','$_ .outcome'))
        self.assertIn("throw 'Packaged GUI recorded a failed startup stage'",smoke)


if __name__=='__main__':
    unittest.main()

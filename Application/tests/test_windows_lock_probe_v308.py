import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOOT=(ROOT/'windows/bootstrap-and-build.ps1').read_text(encoding='utf-8')
PROBE=(ROOT.parent/'02-Compilation/TEST-CONCURRENCE-WINDOWS.ps1').read_text(encoding='utf-8')
class LockProbeTests(unittest.TestCase):
 def test_probe_requires_exclusive_lock(self):
  self.assertLess(BOOT.index('[IO.FileShare]::None'), BOOT.index('LOCK_PROBE_ACQUIRED'))
 def test_probe_bypasses_real_build(self):
  self.assertIn('if ($LockProbeHoldSeconds -gt 0)', BOOT)
  self.assertIn('} else {', BOOT)
 def test_contention_and_recovery(self):
  self.assertIn('Concurrent build unexpectedly acquired lock', PROBE)
  self.assertIn('Lock not released after successful exit', PROBE)
 def test_independent_logs(self):
  self.assertIn('Expected at least two independent build logs', PROBE)

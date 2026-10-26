"""R122 regression tests for the Windows build-environment version report.

Dynamic PowerShell cases run on Windows CI; non-Windows lanes still enforce the
source contract without pretending to execute PowerShell.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Application" / "windows" / "build-environment-report.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


class BuildEnvironmentReportVersionR122Tests(unittest.TestCase):
    def test_report_reads_canonical_version_instead_of_a_literal(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("version = '18.6'", source)
        self.assertIn("Join-Path $repoRoot 'VERSION.txt'", source)
        self.assertIn("version = $productVersion", source)
        self.assertIn(r"$productVersion -notmatch '^\d+\.\d+$'", source)

    @unittest.skipUnless(POWERSHELL, "PowerShell execution is qualified on Windows CI")
    def test_report_uses_the_root_version_file(self):
        completed = self._run_report(version="42.7\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout.lstrip("\ufeff"))
        self.assertEqual(report["version"], "42.7")
        self.assertEqual(report["product"], "OpenRemote Studio")

    @unittest.skipUnless(POWERSHELL, "PowerShell execution is qualified on Windows CI")
    def test_missing_version_file_fails_closed(self):
        completed = self._run_report(version=None)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("VERSION.txt missing", completed.stderr)
        self.assertNotIn('"version"', completed.stdout)

    @unittest.skipUnless(POWERSHELL, "PowerShell execution is qualified on Windows CI")
    def test_noncanonical_version_fails_closed(self):
        completed = self._run_report(version="31.8-beta\n")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("VERSION.txt invalid", completed.stderr)
        self.assertNotIn('"version"', completed.stdout)

    def _run_report(self, version):
        with tempfile.TemporaryDirectory(prefix="ors-r122-version-") as temp_dir:
            root = Path(temp_dir)
            script = root / "Application" / "windows" / "build-environment-report.ps1"
            script.parent.mkdir(parents=True)
            shutil.copyfile(SCRIPT, script)
            if version is not None:
                (root / "VERSION.txt").write_text(version, encoding="utf-8")
            return subprocess.run(
                [
                    POWERSHELL,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
            )


if __name__ == "__main__":
    unittest.main()

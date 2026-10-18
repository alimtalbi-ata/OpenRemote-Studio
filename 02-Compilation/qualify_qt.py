"""Strict Qt test gate: a skipped Qt test is not a qualified Qt integration."""
import os
import sys
import unittest
from pathlib import Path


def main():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    root = Path(__file__).resolve().parents[1] / 'Application'
    sys.path.insert(0, str(root))
    try:
        import PySide6  # noqa: F401
    except ImportError as exc:
        print(f'BLOCK: PySide6 unavailable: {exc}', file=sys.stderr)
        return 3
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'), pattern='test_ssh_qt_bridge_v*.py', top_level_dir=str(root))
    count = suite.countTestCases()
    if count == 0:
        print('BLOCK: no Qt bridge tests discovered', file=sys.stderr)
        return 4
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print(f'BLOCK: {len(result.skipped)} Qt tests skipped', file=sys.stderr)
        return 5
    return 0 if result.wasSuccessful() else 6


if __name__ == '__main__':
    raise SystemExit(main())

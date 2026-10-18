"""Application version resolver for both source and PyInstaller distributions."""
from pathlib import Path


def read_application_version(application_dir):
    """Prefer the bundled VERSION.txt; fail explicitly if release metadata is missing."""
    app = Path(application_dir)
    for path in (app / 'VERSION.txt', app.parent / 'VERSION.txt'):
        if path.is_file():
            value = path.read_text(encoding='utf-8').strip()
            if value and len(value) < 32 and all(c.isdigit() or c == '.' for c in value):
                return value
    raise RuntimeError('VERSION.txt absent ou invalide : livraison incomplète')

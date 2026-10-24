"""Offscreen Qt font raster gate for Windows CI screenshots.

Uses an existing system font by absolute path. No font is bundled or exported.
Author: Abdelhalim Talbi.
"""
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, QImage, QPainter


def _render_glyph(font, glyph):
    image = QImage(96, 70, QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    try:
        painter.setFont(font)
        painter.setPen(Qt.black)
        painter.drawText(12, 50, glyph)
    finally:
        painter.end()
    return image


def configure_readable_offscreen_font(app, candidates=None):
    """Load an OS-installed TTF and prove distinct ASCII glyph rasterization.

    The offscreen Qt platform on Windows may have no usable platform font
    fallback. A successful PNG save alone is not a readability assertion.
    """
    if candidates is None:
        if os.name == 'nt':
            root = Path(os.environ.get('WINDIR', r'C:\\Windows')) / 'Fonts'
            candidates = [root / name for name in
                          ('segoeui.ttf', 'arial.ttf', 'tahoma.ttf', 'verdana.ttf')]
        else:
            candidates = [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]

    for path in candidates:
        if not Path(path).is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            continue
        font = QFont(families[0])
        font.setPointSize(11)
        metrics = QFontMetrics(font)
        if not all(metrics.inFontUcs4(ord(char)) for char in ('A', 'W', 'é')):
            continue
        probe = QFont(font)
        probe.setPixelSize(24)
        if _render_glyph(probe, 'A') == _render_glyph(probe, 'W'):
            continue
        app.setFont(font)
        return families[0]
    raise RuntimeError('Qt offscreen font raster unavailable; screenshot NOT qualified')

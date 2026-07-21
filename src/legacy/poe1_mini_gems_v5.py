"""Mini gem rows with real colour- and kind-correct fallback artwork."""

from __future__ import annotations

from PyQt5.QtGui import QPixmap

from poe1_gem_art_fallback import gem_art_path
from poe1_mini_gems_v4 import MiniGemLinks as BaseMiniGemLinks


class MiniGemLinks(BaseMiniGemLinks):
    def _gem_pixmap(self, gem):
        path = gem_art_path(gem)
        if not path:
            return QPixmap()
        key = f"art:{path.name}"
        if key not in self._pixmaps or self._pixmaps[key].isNull():
            self._pixmaps[key] = QPixmap(str(path))
        return self._pixmaps[key]

"""Use a real same-colour gem artwork when a specific icon is unavailable."""

from __future__ import annotations

from PyQt5.QtGui import QPixmap

from poe1_gem_widgets_v3 import ICON_DIR, ICON_INDEX
from poe1_mini_gems_v2 import MiniGemLinks as BaseMiniGemLinks
from poe1_widgets import infer_gem_color


class MiniGemLinks(BaseMiniGemLinks):
    _fallback_files = None

    @classmethod
    def _fallbacks(cls):
        if cls._fallback_files is None:
            result = {}
            any_file = None
            for name, info in ICON_INDEX.items():
                filename = info.get("file", "")
                path = ICON_DIR / filename
                if not filename or not path.is_file():
                    continue
                any_file = any_file or filename
                result.setdefault(infer_gem_color(name), filename)
            result.setdefault("white", any_file)
            cls._fallback_files = result
        return cls._fallback_files

    def _gem_pixmap(self, gem):
        pixmap = super()._gem_pixmap(gem)
        if not pixmap.isNull():
            return pixmap
        name = (gem.get("name") or "").casefold()
        color = infer_gem_color(gem.get("name", ""))
        filename = self._fallbacks().get(color) or self._fallbacks().get("white")
        fallback = QPixmap(str(ICON_DIR / filename)) if filename else QPixmap()
        self._pixmaps[name] = fallback
        return fallback


"""PoEDB gem rows with real colour- and kind-correct fallback artwork."""

from __future__ import annotations

from PyQt5.QtGui import QPixmap

from poe1_gem_art_fallback import gem_art_path
from poe1_gem_widgets_v8 import PoedbGemChains, PoedbGemIcon


class FallbackPoedbGemIcon(PoedbGemIcon):
    def __init__(self, gem, class_name, parent=None):
        super().__init__(gem, class_name, parent)
        if self.art.isNull():
            path = gem_art_path(gem)
            self.art = QPixmap(str(path)) if path else QPixmap()


class FallbackPoedbGemChains(PoedbGemChains):
    icon_class = FallbackPoedbGemIcon

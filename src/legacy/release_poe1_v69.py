"""Keep the build-tree header icon compact after every style refresh."""

from __future__ import annotations

from PyQt5.QtCore import QSize

import main as legacy
from release_poe1_v35 import build_tree_icon
from release_poe1_v68 import CompactHeaderOverlay as BaseOverlay


class CompactHeaderIconOverlay(BaseOverlay):
    def _style_build_button(self):
        super()._style_build_button()
        if hasattr(self, "build_btn"):
            size = max(14, int(round(18 * legacy.Style.ui_scale())))
            self.build_btn.setIcon(build_tree_icon(size))
            self.build_btn.setIconSize(QSize(size, size))


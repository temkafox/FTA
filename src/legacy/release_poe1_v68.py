"""Larger run timer and a more compact main overlay header."""

from __future__ import annotations

from PyQt5.QtCore import QSize

import main as legacy
from release_poe1_v35 import build_tree_icon
from release_poe1_v67 import KindCorrectGemOverlay as BaseOverlay


COMPACT_BASE = {
    "TIMER_SIZE": 27,
    "HEADER_H": 54,
    "LOGO_HEIGHT": 35,
    "BTN_SIZE": 28,
}


def _install_compact_metrics():
    # Style.set_ui_scale() derives every runtime value from this table. Updating
    # the bases keeps the proportions stable when the user changes UI scale.
    legacy._STYLE_NUMERIC_BASE.update(COMPACT_BASE)


class CompactHeaderOverlay(BaseOverlay):
    def __init__(self, *args, **kwargs):
        _install_compact_metrics()
        super().__init__(*args, **kwargs)

    def _refresh_header(self):
        super()._refresh_header()
        self.header.layout().setSpacing(max(6, int(round(8 * legacy.Style.ui_scale()))))
        if hasattr(self, "build_btn"):
            icon_size = max(14, int(round(18 * legacy.Style.ui_scale())))
            self.build_btn.setIcon(build_tree_icon(icon_size))
            self.build_btn.setIconSize(QSize(icon_size, icon_size))


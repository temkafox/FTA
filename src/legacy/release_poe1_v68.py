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


from actpilot.overlay import CompactHeaderOverlay


"""Keep the build-tree header icon compact after every style refresh."""

from __future__ import annotations

from PyQt5.QtCore import QSize

import main as legacy
from release_poe1_v35 import build_tree_icon
from release_poe1_v68 import CompactHeaderOverlay as BaseOverlay


from actpilot.overlay import CompactHeaderIconOverlay


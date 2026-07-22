"""Keep mini HUDs below editors and add explicit gem stage ranges."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QTimer, Qt

import release_poe1_v41 as editor_release
from poe1_manual_editor_v10 import ManualBuildEditor
from release_poe1_v60 import MiniTreeAndGemsOverlay as BaseOverlay


from actpilot.overlay import StagedGemOverlay


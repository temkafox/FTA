"""Keep mini HUDs below editors and add explicit gem stage ranges."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QTimer, Qt

import release_poe1_v41 as editor_release
from poe1_manual_editor_v10 import ManualBuildEditor
from release_poe1_v60 import MiniTreeAndGemsOverlay as BaseOverlay


class StagedGemOverlay(BaseOverlay):
    def __init__(self):
        self._mini_suspended = False
        super().__init__()
        for panel in (self._mini_panel, self._mini_gem_panel):
            was_visible = panel.isVisible()
            panel.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            if was_visible:
                panel.show()

    def _sync_mini_panel_visibility(self):
        if getattr(self, "_mini_suspended", False):
            if self._mini_panel is not None:
                self._mini_panel.hide()
            if self._mini_gem_panel is not None:
                self._mini_gem_panel.hide()
            return
        super()._sync_mini_panel_visibility()

    def _open_build_progress(self):
        self._mini_suspended = True
        self._sync_mini_panel_visibility()
        try:
            super()._open_build_progress()
        except Exception:
            self._mini_suspended = False
            self._sync_mini_panel_visibility()
            raise
        if self._build_dialog is not None:
            self._build_dialog.installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self._build_dialog and event.type() in (QEvent.Hide, QEvent.Close):
            QTimer.singleShot(0, self._restore_mini_huds)
        return super().eventFilter(watched, event)

    def _restore_mini_huds(self):
        if self._build_dialog is not None and self._build_dialog.isVisible():
            return
        self._mini_suspended = False
        self._sync_mini_panel_visibility()


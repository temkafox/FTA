"""Add a transparent current-level gem preview below the passive mini-map."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QHBoxLayout, QWidget

from actpilot.minipanels import MiniGemLinksV5 as MiniGemLinks
from release_poe1_v59 import MiniTreeOverlay as BaseMiniTreeOverlay


class MiniTreeAndGemsOverlay(BaseMiniTreeOverlay):
    def __init__(self):
        self._mini_gem_panel = None
        self.mini_gems = None
        super().__init__()

        self._mini_gem_panel = QWidget(
            self,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self._mini_gem_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        self._mini_gem_panel.setAttribute(Qt.WA_NoSystemBackground, True)
        self._mini_gem_panel.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._mini_gem_panel.setStyleSheet("background: transparent; border: 0;")
        layout = QHBoxLayout(self._mini_gem_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.mini_gems = MiniGemLinks(self._mini_gem_panel)
        layout.addWidget(self.mini_gems)
        self._refresh_mini_gems()

    def _profile_signature(self):
        base = super()._profile_signature()
        build = self.active_profile().get("build") or {}
        stages = []
        for stage in build.get("gem_sets", []):
            links = tuple(
                tuple((gem.get("name", ""), bool(gem.get("support"))) for gem in link.get("gems", []))
                for link in stage.get("links", [])
            )
            stages.append((int(stage.get("level", 1)), links))
        return base, tuple(stages)

    def _refresh_mini_gems(self):
        if self.mini_gems is None or self._mini_gem_panel is None:
            return
        profile = self.active_profile()
        self.mini_gems.set_build_level(
            profile.get("build") or {}, int(profile.get("level", 1))
        )
        self._mini_gem_panel.setFixedSize(self.mini_gems.size())
        self._mini_gem_panel.setWindowOpacity(1.0)
        self._position_mini_gem_panel()
        self._sync_mini_gem_visibility()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self.mini_gems is not None:
            self._refresh_mini_gems()

    def _position_mini_panel(self):
        super()._position_mini_panel()
        self._position_mini_gem_panel()

    def _position_mini_gem_panel(self):
        if self._mini_gem_panel is None or self._mini_panel is None:
            return
        right_side = self._mini_panel.x() >= self.x()
        x = (
            self._mini_panel.x()
            if right_side
            else self._mini_panel.geometry().right() - self._mini_gem_panel.width() + 1
        )
        y = self._mini_panel.geometry().bottom() + 3
        self._mini_gem_panel.move(QPoint(x, y))

    def _sync_mini_panel_visibility(self):
        super()._sync_mini_panel_visibility()
        self._sync_mini_gem_visibility()

    def _sync_mini_gem_visibility(self):
        if self._mini_gem_panel is None or self.mini_gems is None:
            return
        show = self._mini_panel.isVisible() and bool(self.mini_gems._links)
        self._mini_gem_panel.setVisible(show)
        if show:
            self._position_mini_gem_panel()
            self._mini_gem_panel.raise_()

    def hideEvent(self, event):
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.hide()
        super().hideEvent(event)

    def _update_opacity(self):
        super()._update_opacity()
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.setWindowOpacity(1.0)

    def closeEvent(self, event):
        if self._mini_gem_panel is not None:
            self._mini_gem_panel.close()
        super().closeEvent(event)

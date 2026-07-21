"""Transparent passive mini-route attached to the right of the overlay."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QWidget

import main as legacy
import release_poe1_v51 as mini_release
from poe1_mini_tree_v3 import MiniPassiveRoute
from release_poe1_v53 import MiniTreeOverlay as BaseMiniTreeOverlay


# The base overlay creates this class by resolving the module global at runtime.
mini_release.MiniPassiveRoute = MiniPassiveRoute


class MiniTreeOverlay(BaseMiniTreeOverlay):
    def __init__(self):
        self._mini_hidden_by_user = False
        self._mini_panel = None
        super().__init__()

        body_layout = self.body.layout()
        body_layout.removeWidget(self.mini_tree)

        self._mini_panel = QWidget(
            self,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus,
        )
        self._mini_panel.setAttribute(Qt.WA_TranslucentBackground, True)
        self._mini_panel.setAttribute(Qt.WA_NoSystemBackground, True)
        self._mini_panel.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._mini_panel.setStyleSheet("background: transparent; border: 0;")
        panel_layout = QHBoxLayout(self._mini_panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        self.mini_tree.setParent(self._mini_panel)
        self.mini_tree.setFixedWidth(190)
        panel_layout.addWidget(self.mini_tree)
        self._mini_panel.setFixedSize(190, 56)
        self._mini_panel.setWindowOpacity(self.windowOpacity())

        self.layout_hotkey.triggered.connect(self._toggle_mini_tree)
        self._position_mini_panel()
        self._sync_mini_panel_visibility()

    def _start_hotkey(self):
        super()._start_hotkey()
        if self.game == legacy.GAME_POE1:
            self.layout_hotkey.restart(
                self.settings.get("layout_hotkey", legacy.DEFAULT_SETTINGS["layout_hotkey"])
            )

    def _position_mini_panel(self):
        if self._mini_panel is None:
            return
        gap = 8
        x = self.frameGeometry().right() + gap
        y = self.y() + max(self.header.height(), 54)
        screen = QApplication.screenAt(self.frameGeometry().center())
        geometry = screen.availableGeometry() if screen else QApplication.primaryScreen().availableGeometry()
        if x + self._mini_panel.width() > geometry.right():
            x = self.x() - self._mini_panel.width() - gap
        y = max(geometry.top(), min(y, geometry.bottom() - self._mini_panel.height()))
        self._mini_panel.move(QPoint(x, y))

    def _sync_mini_panel_visibility(self):
        if self._mini_panel is None:
            return
        should_show = (
            self.isVisible()
            and self.game == legacy.GAME_POE1
            and bool(self.mini_tree._visible_nodes)
            and not self._mini_hidden_by_user
        )
        self._mini_panel.setVisible(should_show)
        if should_show:
            self._position_mini_panel()
            self._mini_panel.raise_()

    def _toggle_mini_tree(self):
        if self.game != legacy.GAME_POE1:
            return
        self._mini_hidden_by_user = not self._mini_hidden_by_user
        self._sync_mini_panel_visibility()

    def _refresh_mini_tree(self, force=False):
        super()._refresh_mini_tree(force)
        if self._mini_panel is not None:
            self._sync_mini_panel_visibility()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_mini_panel()
        self._sync_mini_panel_visibility()

    def hideEvent(self, event):
        if self._mini_panel is not None:
            self._mini_panel.hide()
        super().hideEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._position_mini_panel()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_mini_panel()

    def _update_opacity(self):
        super()._update_opacity()
        if self._mini_panel is not None:
            self._mini_panel.setWindowOpacity(self.windowOpacity())

    def closeEvent(self, event):
        if self._mini_panel is not None:
            self._mini_panel.close()
        super().closeEvent(event)


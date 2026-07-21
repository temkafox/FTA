"""Compact ActPilot-styled PoE 1 build window with a level slider."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QSlider

import main as legacy
import release_poe1_v32 as previous
from poe1_builds import clamp_level


class CompactBuildDialog(previous.MasteryAndQuestBuildDialog):
    def __init__(self, overlay):
        self._level_slider_ready = False
        super().__init__(overlay)

        self._level_slider_timer = QTimer(self)
        self._level_slider_timer.setSingleShot(True)
        self._level_slider_timer.setInterval(45)
        self._level_slider_timer.timeout.connect(self._commit_slider_level)
        self._pending_slider_level = None

        level_row = self.layout().itemAt(1).layout()
        self.level_slider = QSlider(Qt.Horizontal)
        self.level_slider.setObjectName("levelSlider")
        self.level_slider.setRange(1, 100)
        self.level_slider.setSingleStep(1)
        self.level_slider.setPageStep(5)
        self.level_slider.setFixedHeight(24)
        self.level_slider.valueChanged.connect(self._slider_level_changed)
        level_row.insertWidget(1, self.level_slider, 1)

        self._remove_tree_chrome()
        self._compact_layout()
        self._apply_actpilot_window_style()
        self._level_slider_ready = True
        self.refresh_level()

    def _remove_tree_chrome(self):
        tree_page = self.tree_canvas.parentWidget()
        for button in tree_page.findChildren(QPushButton):
            button.hide()
            button.setMaximumSize(0, 0)
        for label in tree_page.findChildren(QLabel):
            if label is not self.tree_stage_label:
                label.hide()
                label.setMaximumHeight(0)
        self.status.clear()
        self.status.hide()
        self.status.setMaximumHeight(0)

    def _compact_layout(self):
        style = legacy.Style
        root = self.layout()
        root.setContentsMargins(style.PAD_S, style.PAD_S, style.PAD_S, style.PAD_S)
        root.setSpacing(7)

        profile_row = root.itemAt(0).layout()
        profile_row.setSpacing(6)
        for index in range(profile_row.count()):
            widget = profile_row.itemAt(index).widget()
            if isinstance(widget, QPushButton):
                widget.setFixedHeight(30)
            elif widget is not None:
                widget.setMaximumHeight(30)

        level_row = root.itemAt(1).layout()
        level_row.setSpacing(6)
        for index in range(level_row.count()):
            widget = level_row.itemAt(index).widget()
            if isinstance(widget, QPushButton):
                widget.setFixedSize(30, 30)
        self.level_label.setMinimumWidth(82)
        self.level_label.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        self.character_label.setFont(QFont("Segoe UI", 10, QFont.DemiBold))

        tree_page = self.tree_canvas.parentWidget()
        tree_layout = tree_page.layout()
        tree_layout.setContentsMargins(5, 5, 5, 5)
        tree_layout.setSpacing(3)
        self.tree_stage_label.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.tree_stage_label.setContentsMargins(4, 1, 4, 1)
        self.gem_links.layout.setContentsMargins(8, 7, 6, 7)
        self.gem_links.layout.setSpacing(7)

        self.combined_splitter.setHandleWidth(1)
        self.combined_splitter.setSizes([300, 720])
        self.resize(1040, 640)
        self.setMinimumSize(860, 520)

    def _apply_actpilot_window_style(self):
        style = legacy.Style
        self.setStyleSheet(f"""
            QDialog {{
                background:{style.BG};
                color:{style.TEXT_PRIMARY};
            }}
            QWidget {{
                color:{style.TEXT_PRIMARY};
                selection-background-color:{style.ACCENT_BG};
            }}
            QLabel {{
                color:{style.TEXT_SECONDARY};
                background:transparent;
                border:0;
            }}
            QComboBox {{
                background:{style.BG_SECONDARY};
                color:{style.TEXT_PRIMARY};
                border:1px solid {style.BORDER};
                border-radius:{style.RAD_S}px;
                padding:5px 9px;
                min-height:18px;
            }}
            QComboBox:hover, QComboBox:focus {{ border-color:{style.ACCENT}; }}
            QPushButton {{
                background:{style.BG_SECONDARY};
                color:{style.TEXT_SECONDARY};
                border:1px solid {style.BORDER};
                border-radius:{style.RAD_S}px;
                padding:4px 9px;
            }}
            QPushButton:hover {{
                color:{style.TEXT_PRIMARY};
                background:{style.HOVER};
                border-color:{style.ACCENT};
            }}
            QPushButton:pressed {{
                color:{style.BG};
                background:{style.ACCENT};
            }}
            QScrollArea {{ background:transparent; border:0; }}
            QScrollBar:vertical {{ background:{style.BG}; width:8px; }}
            QScrollBar::handle:vertical {{
                background:{style.TEXT_DISABLED};
                border-radius:4px;
                min-height:22px;
            }}
            QSplitter::handle {{ background:{style.BORDER}; }}
            QSlider#levelSlider::groove:horizontal {{
                background:{style.BG_SECONDARY};
                height:4px;
                border-radius:2px;
            }}
            QSlider#levelSlider::sub-page:horizontal {{
                background:{style.ACCENT};
                border-radius:2px;
            }}
            QSlider#levelSlider::handle:horizontal {{
                background:{style.TEXT_SECONDARY};
                width:14px;
                height:14px;
                margin:-5px 0;
                border-radius:7px;
            }}
            QSlider#levelSlider::handle:horizontal:hover {{
                background:{style.TEXT_PRIMARY};
            }}
        """)
        self.tree_stage_label.setStyleSheet(
            f"color:{style.ACCENT}; background:transparent; font-weight:600;"
        )
        self.gem_links.body.setStyleSheet(f"background:{style.BG};")
        self.tree_canvas.parentWidget().setStyleSheet(f"background:{style.BG};")
        self.gem_links.parentWidget().setStyleSheet(f"background:{style.BG};")

    def _slider_level_changed(self, value):
        if not self._level_slider_ready:
            return
        self._pending_slider_level = clamp_level(value)
        self.level_label.setText(f"Уровень {self._pending_slider_level}")
        self._level_slider_timer.start()

    def _commit_slider_level(self):
        if self._pending_slider_level is None:
            return
        profile = self.overlay.active_profile()
        level = self._pending_slider_level
        self._pending_slider_level = None
        if clamp_level(profile.get("level", 1)) == level:
            return
        profile["level"] = level
        self.overlay.save_profiles()
        self.refresh_level()

    def refresh_level(self):
        super().refresh_level()
        if not hasattr(self, "level_slider"):
            return
        level = clamp_level(self.overlay.active_profile().get("level", 1))
        self.level_slider.blockSignals(True)
        self.level_slider.setValue(level)
        self.level_slider.blockSignals(False)


class CompactBuildOverlay(previous.MasteryAndQuestOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = CompactBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = CompactBuildOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

"""Current PoE 1 release with corrected tree legend."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel

import main as legacy
import release_poe1_v11 as previous


class FinalLevelMappedBuildDialog(previous.LevelMappedBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is self.tree_stage_label:
                continue
            if "Золот" in label.text() or "зелён" in label.text():
                label.setText(
                    "Зелёное — уже взято на выбранном уровне · "
                    "золотое — будущий маршрут · число у узла — уровень его получения"
                )


class FinalLevelMappedOverlay(previous.LevelMappedOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = FinalLevelMappedBuildDialog(self)
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
    window = FinalLevelMappedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

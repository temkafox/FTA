"""PoE 1 build window using the exact ActPilot frame and UI assets."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QWidget

import main as legacy
import release_poe1_v33 as previous


class BuildAssetHeader(QFrame):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self._drag_offset = None
        self.setObjectName("assetHeader")
        self.setFixedHeight(46)
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.owner.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.owner.move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


from actpilot.build_dialog import AssetFramedBuildDialog


from actpilot.overlay import AssetFramedOverlay


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = AssetFramedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

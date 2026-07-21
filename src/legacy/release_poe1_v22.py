"""PoE 1 release with a separate ascendancy progression tab."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QTabWidget, QVBoxLayout, QWidget

import main as legacy
import release_poe1_v21 as previous
from poe1_ascendancy_widget import AscendancyProgressWidget


class AscendancyBuildDialog(previous.SocketedGemBuildDialog):
    def __init__(self, overlay):
        self._ascendancy_ready = False
        super().__init__(overlay)

        gem_page = self.gem_links.parentWidget()
        page_layout = gem_page.layout()
        gem_index = page_layout.indexOf(self.gem_links)
        page_layout.removeWidget(self.gem_links)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(
            "QTabWidget::pane{border:0;background:#08090b;}"
            "QTabBar::tab{background:#17181d;color:#aaa;padding:8px 16px;}"
            "QTabBar::tab:selected{color:#f0d387;border-bottom:2px solid #d8a52e;}"
        )
        gems_tab = QWidget()
        gems_layout = QVBoxLayout(gems_tab)
        gems_layout.setContentsMargins(0, 0, 0, 0)
        gems_layout.addWidget(self.gem_links)
        self.ascendancy_view = AscendancyProgressWidget()
        tabs.addTab(gems_tab, "Камни")
        tabs.addTab(self.ascendancy_view, "Ассенданси")
        page_layout.insertWidget(gem_index, tabs, 1)
        self.left_tabs = tabs
        self._ascendancy_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if self._ascendancy_ready:
            self.ascendancy_view.set_build(build, level)


class AscendancyOverlay(previous.SocketedGemOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = AscendancyBuildDialog(self)
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
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1 CLEAN")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = AscendancyOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

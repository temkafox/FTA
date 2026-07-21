"""PoE 1 release with exact character-level gem scaling."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

import main as legacy
import release_poe1_v9 as previous
from poe1_gem_progression import links_at_level
from poe1_level_plan_v2 import stage_at_level


class ScaledGemBuildDialog(previous.FixedProgressionBuildDialog):
    def __init__(self, overlay):
        self._v10_ready = False
        super().__init__(overlay)
        self._v10_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v10_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stages = build.get("gem_sets", [])
        stage = stage_at_level(stages, level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        title = stage.get("title", "Связки")
        links = links_at_level(stage.get("links", []), level)
        self.gem_links.set_links(title, links)
        future_levels = sorted({
            int(item.get("level", 1)) for item in stages
            if int(item.get("level", 1)) > level
        })
        next_text = f" · следующая смена на {future_levels[0]}" if future_levels else ""
        self.status.setText(
            f"Уровень персонажа {level} · камни пересчитаны для этого уровня · "
            f"набор «{title}»{next_text}"
        )


class ScaledGemOverlay(previous.FixedProgressionOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = ScaledGemBuildDialog(self)
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
    window = ScaledGemOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

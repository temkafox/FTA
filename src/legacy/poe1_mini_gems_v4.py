"""Colour-correct fallback art and full acquisition tooltips for mini gems."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QFont, QPixmap
from PyQt5.QtWidgets import QLabel

from poe1_gem_acquisition import badges_for
from poe1_gem_widgets_v3 import ICON_DIR, ICON_INDEX
from poe1_gem_widgets_v7 import AcquisitionGemTooltip
from poe1_mini_gems_v3 import MiniGemLinks as BaseMiniGemLinks
from poe1_widgets import infer_gem_color


ROOT = Path(__file__).parent / "data" / "poe1"
try:
    GEM_COLOURS = json.loads((ROOT / "gem_colors.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    GEM_COLOURS = {}
try:
    GEM_LEVELS = json.loads((ROOT / "gem_levels.json").read_text(encoding="utf-8"))
except (OSError, ValueError):
    GEM_LEVELS = {}


def gem_colour(name):
    key = (name or "").strip().casefold()
    return GEM_COLOURS.get(key) or infer_gem_color(name)


def required_level(name):
    record = GEM_LEVELS.get((name or "").strip().casefold(), {})
    requirements = record.get("requirements", {})
    try:
        return int(requirements.get("1"))
    except (TypeError, ValueError):
        return None


class MiniGemTooltip(AcquisitionGemTooltip):
    def __init__(self):
        super().__init__()
        self.requirement = QLabel()
        self.requirement.setAlignment(Qt.AlignCenter)
        self.requirement.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.requirement.setStyleSheet(
            "color:#e7c56d; border-top:1px solid #334038; padding-top:7px;"
        )
        layout = self.layout()
        index = layout.indexOf(self.acquisition)
        layout.insertWidget(index, self.requirement)

    def show_mini_gem(self, gem, class_name, global_pos):
        super().show_acquisition(gem, class_name, global_pos)
        name = gem.get("name", "")
        level = required_level(name)
        badges = badges_for(name, class_name)
        ways = " / ".join(badges) if badges else "—"
        level_text = str(level) if level is not None else "неизвестен"
        self.requirement.setText(
            f"Требуемый уровень: {level_text}   ·   Получение: {ways}"
        )
        self.requirement.show()
        self.adjustSize()
        self.show()
        self.raise_()


class MiniGemLinks(BaseMiniGemLinks):
    _fallback_files = None
    tooltip = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character_class = ""
        if MiniGemLinks.tooltip is None:
            MiniGemLinks.tooltip = MiniGemTooltip()

    @classmethod
    def _fallbacks(cls):
        if cls._fallback_files is None:
            result = {}
            any_file = None
            for name, info in ICON_INDEX.items():
                filename = info.get("file", "")
                if not filename or not (ICON_DIR / filename).is_file():
                    continue
                any_file = any_file or filename
                result.setdefault(gem_colour(name), filename)
            result.setdefault("white", any_file)
            cls._fallback_files = result
        return cls._fallback_files

    def set_build_level(self, build, level):
        self.character_class = (build or {}).get("class", "")
        super().set_build_level(build, level)

    def _gem_pixmap(self, gem):
        name = (gem.get("name") or "").casefold()
        info = ICON_INDEX.get(name, {})
        filename = info.get("file", "")
        if filename and (ICON_DIR / filename).is_file():
            if name not in self._pixmaps or self._pixmaps[name].isNull():
                self._pixmaps[name] = QPixmap(str(ICON_DIR / filename))
            return self._pixmaps[name]
        color = gem_colour(gem.get("name", ""))
        fallback_file = self._fallbacks().get(color) or self._fallbacks().get("white")
        cache_key = f"{name}|fallback:{color}"
        if cache_key not in self._pixmaps:
            self._pixmaps[cache_key] = (
                QPixmap(str(ICON_DIR / fallback_file)) if fallback_file else QPixmap()
            )
        return self._pixmaps[cache_key]

    def mouseMoveEvent(self, event):
        gem = self._gem_at(event.pos())
        name = (gem.get("name") or "").strip() if gem else ""
        if name != self._hovered:
            self._hovered = name or None
            if gem and name:
                self.tooltip.show_mini_gem(gem, self.character_class, QCursor.pos())
            else:
                self.tooltip.hide()
        # Skip the base name-only QToolTip; the full card replaces it.
        event.accept()

    def leaveEvent(self, event):
        self._hovered = None
        self.tooltip.hide()
        super(BaseMiniGemLinks, self).leaveEvent(event)

    def mousePressEvent(self, event):
        self.tooltip.hide()
        super().mousePressEvent(event)


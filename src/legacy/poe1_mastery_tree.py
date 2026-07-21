"""Passive tree canvas with complete regular and mastery tooltips."""

import html
import math

from PyQt5.QtWidgets import QToolTip

from poe1_target_widgets import DetailedPassiveTreeCanvas


class CompleteTooltipTreeCanvas(DetailedPassiveTreeCanvas):
    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            return super().mouseMoveEvent(event)
        nearest = None
        nearest_distance = 13.0
        for node_id, point in self.positions.items():
            screen = self._screen(point)
            if abs(screen.x() - event.x()) > nearest_distance or abs(screen.y() - event.y()) > nearest_distance:
                continue
            distance = math.hypot(screen.x() - event.x(), screen.y() - event.y())
            if distance < nearest_distance:
                nearest, nearest_distance = node_id, distance
        if not nearest:
            QToolTip.hideText()
            return
        node = self.nodes.get(nearest, {})
        name = html.escape(node.get("name") or f"Пассив {nearest}")
        stats = list(node.get("stats") or [])
        mastery = node.get("masteryEffects") or []
        if mastery:
            stats = [
                "Вариант: " + " / ".join(str(value) for value in effect.get("stats", []))
                for effect in mastery
            ]
        stat_html = "<br>".join(
            html.escape(str(stat)).replace("\n", "<br>") for stat in stats
        )
        if node.get("isMastery"):
            kind = "Мастерство — выберите один эффект"
        elif node.get("isKeystone"):
            kind = "Ключевое умение"
        elif node.get("isNotable"):
            kind = "Значимое умение"
        else:
            kind = "Пассивное умение"
        selected = "<br><span style='color:#55d96b'>Взято в этом этапе</span>" if nearest in self.selected else ""
        QToolTip.showText(
            event.globalPos(),
            f"<div style='min-width:300px'><b style='color:#e6c477'>{name}</b><br>"
            f"<span style='color:#999'>{kind}</span><p>{stat_html or 'Служебный узел без характеристик'}</p>"
            f"{selected}</div>",
            self,
        )

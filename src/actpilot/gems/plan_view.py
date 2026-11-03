"""Вкладка «План камней»: по актам и квестам — что брать наградой и что покупать."""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from actpilot.gems.widgets import FallbackPoedbGemIcon


TEXT = "#e5dfd1"
MUTED = "#8f96a3"
GOLD = "#f0d387"
LINE = "rgba(154,116,57,.32)"
MISSING_TEXT = {"divine_font": "Divine Font в Лабиринте (из {base}) или трейд", "trade": "только дроп или трейд"}


def _label(text, color=TEXT, size=10, weight=QFont.Normal):
    label = QLabel(text)
    label.setFont(QFont("Segoe UI", size, weight))
    label.setStyleSheet(f"color:{color}; background:transparent;")
    label.setWordWrap(True)
    return label


class GemPlanView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body.setStyleSheet("background:rgba(2,4,4,0.38);")
        self.rows = QVBoxLayout(self.body)
        self.rows.setContentsMargins(10, 8, 10, 10)
        self.rows.setSpacing(2)
        self.setWidget(self.body)
        self._signature = None
        self._current_header = None

    def set_plan(self, plan, current_act):
        signature = (id(plan), current_act)
        if signature == self._signature:
            return
        self._signature = signature
        self._current_header = None
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not plan:
            self.rows.addWidget(_label(
                "Импортируйте билд с указанным классом, чтобы увидеть план камней.", MUTED
            ))
            self.rows.addStretch()
            return

        class_name = plan["class"]
        self.rows.addWidget(_label(
            f"{class_name} · Q — брать наградой за квест, B — купить у торговца. "
            "Наведите на камень, чтобы увидеть детали.", MUTED, 9
        ))

        starts = [
            info for info in plan["gems"].values()
            if any(action["kind"] in ("start", "chest") for action in info["actions"])
        ]
        if starts:
            self._section("Старт")
            for info in starts:
                kind = next(a["kind"] for a in info["actions"] if a["kind"] in ("start", "chest"))
                note = "стартовый камень" if kind == "start" else "сундук на Twilight Strand"
                self._row(info, class_name, note)

        deferred = []
        acts = sorted({step["act"] for step in plan["steps"]})
        for act in acts:
            header = self._section(f"Акт {act}" + (" · сейчас" if act == current_act else ""),
                                   current=act == current_act)
            if act == current_act:
                self._current_header = header
            for step in (s for s in plan["steps"] if s["act"] == act):
                purchases = [entry for entry in step["purchases"] if not entry["deferred"]]
                deferred.extend(entry for entry in step["purchases"] if entry["deferred"])
                if not step["rewards"] and not purchases:
                    continue
                self.rows.addWidget(_label(step["quest"], GOLD if act == current_act else TEXT, 9, QFont.DemiBold))
                for entry in step["rewards"]:
                    self._row(plan["gems"][entry["key"]], class_name, f"награда · {entry['npc']}")
                for entry in purchases:
                    count = f" ×{entry['count']}" if entry["count"] > 1 else ""
                    self._row(plan["gems"][entry["key"]], class_name, f"купить{count} · {entry['npc']}")

        if deferred:
            self._section("Позже, когда понадобятся")
            for entry in sorted(deferred, key=lambda item: item["needed_level"]):
                self._row(
                    plan["gems"][entry["key"]], class_name,
                    f"купить у {entry['npc']} · нужен с ур. {entry['needed_level']}",
                )

        if plan["unavailable"]:
            self._section("Нет у торговцев")
            for item in plan["unavailable"]:
                self._row(plan["gems"][item["key"]], class_name,
                          MISSING_TEXT[item["reason"]].format(base=item["base"]))

        self.rows.addStretch()
        if self._current_header is not None:
            QTimer.singleShot(0, self._scroll_to_current)

    def _scroll_to_current(self):
        if self._current_header is not None:
            self.verticalScrollBar().setValue(max(0, self._current_header.y() - 6))

    def _section(self, title, current=False):
        header = _label(title, GOLD if current else TEXT, 11, QFont.DemiBold)
        accent = GOLD if current else LINE
        header.setStyleSheet(
            f"color:{GOLD if current else TEXT}; background:transparent; "
            f"border-bottom:1px solid {accent}; padding:8px 0 3px 0;"
        )
        self.rows.addWidget(header)
        return header

    def _row(self, info, class_name, note):
        row = QWidget()
        row.setStyleSheet("background:transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(8)
        gem = {"name": info["name"], "support": info["support"], "plan": info}
        layout.addWidget(FallbackPoedbGemIcon(gem, class_name))
        layout.addWidget(_label(info["name"]), 1)
        layout.addWidget(_label(note, MUTED, 9), 0, Qt.AlignRight | Qt.AlignVCenter)
        self.rows.addWidget(row)

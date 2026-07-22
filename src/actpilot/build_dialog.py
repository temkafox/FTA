"""Живая линия билд-диалога PoE1: 46 слоёв MRO от main_poe1.BuildProgressDialog
до release_poe1_v47.FixedInteractionBuildDialog, сведённые в один модуль.

Классы перенесены дословно; базы переписаны на локальные имена. Хелперы
_layout_with_widget и BuildAssetHeader скопированы сюда, чтобы не тянуть
release_poe1_v37/-v34 обратно в цикл импорта."""

from __future__ import annotations

import html

from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

import actpilot.shared as legacy

from actpilot.editor import ManualBuildEditor

from actpilot.build_model import manual_passive_plan
from actpilot.builds import PobImportError, clamp_level, parse_pob, stage_for_level
from actpilot.clientlog import class_matches
from actpilot.data_cache import tree_graph
from actpilot.gems.data import links_at_level
from actpilot.gems.widgets import (
    AcquisitionGemChains, ArtworkGemChains, CleanArtworkGemChains, CompactGemChains,
    CopyableGemChains, FallbackPoedbGemChains as PoedbGemChains, RussianOverlayGemChains,
)
from actpilot.tree import (
    CachedZoomSafeTreeCanvas as ZoomSafeTreeCanvas, CompleteTooltipTreeCanvas,
    DetailedPassiveTreeCanvas,
)
from actpilot.ascendancy_widget import AscendancyProgressWidget
from actpilot.ascendancy_widget import ConnectedAscendancyProgressWidget
from actpilot.clientmonitor import ClientLevelMonitor, find_client_log
from actpilot.gems.widgets import LevelGemChains
from actpilot.level_plans import passive_plan
from actpilot.level_plans_v2 import stage_at_level
from actpilot.level_plans import passive_plan_by_level
from actpilot.level_plans import strict_passive_plan
from actpilot.level_plans import pob_kills_all_bandits, quest_aware_passive_plan
from actpilot.level_plans import book_only_passive_plan
from actpilot.level_plans import visible_book_passive_plan
from actpilot.level_plans import semantic_book_passive_plan
from actpilot.level_plans import corrected_semantic_plan
from actpilot.level_plans import ordinary_nearest_plan as nearest_connected_plan
from actpilot.level_plans import mastery_separated_plan
from actpilot.progression import nodes_at_level
from actpilot.stage_logic import previous_stage
from actpilot.gem_cards import DescribedGemLinksView, leveling_stage, ROOT as _SKILLTREE_ROOT
from actpilot.tree_placeholder import (
    ConstructionTreePlaceholder as CleanPassiveTreeCanvas,
    ConstructionTreePlaceholder as ConnectedPassiveTreeCanvas,
    ConstructionTreePlaceholder as ExplicitProgressionTreeCanvas,
    ConstructionTreePlaceholder as FocusedLevelingTreeCanvas,
    ConstructionTreePlaceholder as ImmediateFocusTreeCanvas,
    ConstructionTreePlaceholder as IntegratedAscendancyTreeCanvas,
    ConstructionTreePlaceholder as LevelMappedTreeCanvas,
    ConstructionTreePlaceholder as LevelingRouteTreeCanvas,
    ConstructionTreePlaceholder as MasteryAwareTreeCanvas,
    ConstructionTreePlaceholder as NativeAscendancyTreeCanvas,
    ConstructionTreePlaceholder as OrbitalPassiveTreeCanvas,
    ConstructionTreePlaceholder as PassiveTreeCanvas,
    ConstructionTreePlaceholder as ProgressionTreeCanvas,
    ConstructionTreePlaceholder as QuestAwareTreeCanvas,
    ConstructionTreePlaceholder as RestoredAscendancyTreeCanvas,
    ConstructionTreePlaceholder as RussianDescriptionTreeCanvas,
    ConstructionTreePlaceholder as SeparateMasteryTreeCanvas,
)
from actpilot.base_widgets import GemLinksView


TREE_GRAPH = tree_graph(_SKILLTREE_ROOT / "skilltree.json")


def _layout_with_widget(layout, target):
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item.widget() is target:
            return layout
        child = item.layout()
        if child is not None:
            found = _layout_with_widget(child, target)
            if found is not None:
                return found
    return None


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



class BuildProgressDialog(QDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.setWindowTitle("Персонаж и прокачка — PoE 1")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.resize(760, 670)
        self.setMinimumSize(620, 500)
        self.setStyleSheet(f"""
            QDialog {{ background:{legacy.Style.BG}; color:{legacy.Style.TEXT_PRIMARY}; }}
            QLabel {{ color:{legacy.Style.TEXT_SECONDARY}; }}
            QComboBox {{ background:{legacy.Style.BG_SECONDARY}; color:white;
                border:1px solid {legacy.Style.BORDER}; padding:7px; min-height:24px; }}
            QTabWidget::pane {{ border:1px solid {legacy.Style.BORDER}; }}
            QTabBar::tab {{ background:{legacy.Style.BG_SECONDARY}; color:{legacy.Style.TEXT_MUTED};
                padding:9px 18px; }}
            QTabBar::tab:selected {{ color:white; border-bottom:2px solid {legacy.Style.ACCENT}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Персонаж:"))
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_combo, 1)
        add_btn = QPushButton("Новый")
        add_btn.setStyleSheet(button_style())
        add_btn.clicked.connect(self._new_profile)
        profile_row.addWidget(add_btn)
        rename_btn = QPushButton("Переименовать")
        rename_btn.setStyleSheet(button_style())
        rename_btn.clicked.connect(self._rename_profile)
        profile_row.addWidget(rename_btn)
        root.addLayout(profile_row)

        level_row = QHBoxLayout()
        self.character_label = QLabel()
        self.character_label.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        level_row.addWidget(self.character_label, 1)
        minus = QPushButton("−")
        plus = QPushButton("+")
        for button in (minus, plus):
            button.setFixedSize(40, 36)
            button.setStyleSheet(button_style())
        minus.clicked.connect(lambda: self._change_level(-1))
        plus.clicked.connect(lambda: self._change_level(1))
        self.level_label = QLabel()
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setMinimumWidth(105)
        self.level_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        level_row.addWidget(minus)
        level_row.addWidget(self.level_label)
        level_row.addWidget(plus)
        root.addLayout(level_row)

        self.tabs = QTabWidget()
        self.gems_view = QLabel()
        self.gems_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.gems_view.setWordWrap(True)
        self.gems_view.setTextFormat(Qt.RichText)
        self.tree_view = QLabel()
        self.tree_view.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.tree_view.setWordWrap(True)
        self.tree_view.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tree_view.setTextFormat(Qt.RichText)
        self.tabs.addTab(self._scroll(self.gems_view), "Камни и связки")
        self.tabs.addTab(self._scroll(self.tree_view), "Дерево")
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color:{legacy.Style.TEXT_MUTED};")
        bottom.addWidget(self.status, 1)
        import_btn = QPushButton("Импортировать PoB")
        import_btn.setStyleSheet(button_style(True))
        import_btn.clicked.connect(self._import_pob)
        bottom.addWidget(import_btn)
        root.addLayout(bottom)
        self.reload()

    def _scroll(self, widget):
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(widget)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(holder)
        return scroll

    def reload(self):
        active_id = self.overlay.active_profile().get("id")
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        selected = 0
        for index, profile in enumerate(self.overlay.profile_data["profiles"]):
            self.profile_combo.addItem(profile.get("name", "Персонаж"), profile.get("id"))
            if profile.get("id") == active_id:
                selected = index
        self.profile_combo.setCurrentIndex(selected)
        self.profile_combo.blockSignals(False)
        self.refresh_level()

    def refresh_level(self):
        profile = self.overlay.active_profile()
        level = clamp_level(profile.get("level", 1))
        build = profile.get("build")
        self.level_label.setText(f"Уровень {level}")
        subtitle = profile.get("name", "Персонаж")
        if build:
            details = " ".join(x for x in (build.get("class"), build.get("ascendancy")) if x)
            subtitle += f" — {details or build.get('name', 'PoB билд')}"
        self.character_label.setText(subtitle)
        self._render_gems(build, level)
        self._render_tree(build, level)

    def _render_gems(self, build, level):
        if not build:
            self.gems_view.setText("Импортируйте PoB, чтобы увидеть связки камней.")
            self.status.setText("У персонажа пока нет импортированного билда.")
            return
        stage = stage_for_level(build.get("gem_sets", []), level)
        if not stage or not stage.get("links"):
            self.gems_view.setText("В импортированном PoB не найдены активные связки камней.")
            return
        blocks = [f"<h3>{html.escape(stage.get('title', 'Связки'))}</h3>"]
        for link in stage["links"]:
            gems = []
            for gem in link.get("gems", []):
                color = "#7dd3fc" if gem.get("support") else legacy.Style.ACCENT
                gems.append(f'<span style="color:{color}">{html.escape(gem.get("name", ""))}</span>')
            blocks.append(
                f'<p><b style="color:white">{html.escape(link.get("label", "Связка"))}</b><br>'
                + " <span style='color:#777'>—</span> ".join(gems) + "</p>"
            )
        self.gems_view.setText("".join(blocks))
        self.status.setText(
            f"Показан ближайший этап камней: уровень {stage.get('level', 1)}. "
            "Уровень меняется независимо от шагов кампании."
        )

    def _render_tree(self, build, level):
        if not build:
            self.tree_view.setText("Импортируйте PoB, чтобы увидеть этапы дерева.")
            return
        stage = stage_for_level(build.get("trees", []), level)
        if not stage:
            self.tree_view.setText("В импортированном PoB не найдено дерево пассивных умений.")
            return
        nodes = stage.get("nodes", [])
        previous_candidates = [
            item for item in build.get("trees", [])
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda x: x.get("level", 1)) if previous_candidates else None
        previous_nodes = set(previous.get("nodes", [])) if previous else set()
        added = [node for node in nodes if node not in previous_nodes]
        chips = " ".join(
            f'<span style="color:{legacy.Style.ACCENT}">{node}</span>' if node in added
            else f'<span style="color:#aaa">{node}</span>' for node in nodes
        )
        self.tree_view.setText(
            f"<h3>{html.escape(stage.get('title', 'Дерево'))}</h3>"
            f"<p>Этап уровня: <b>{stage.get('level', 1)}</b><br>"
            f"Выбрано пассивов: <b>{len(nodes)}</b><br>"
            f"Новых относительно прошлого этапа: <b style='color:{legacy.Style.ACCENT}'>{len(added)}</b></p>"
            "<p style='color:#888'>Сейчас показаны идентификаторы узлов из PoB. "
            "Визуальная подложка дерева будет подключена отдельно из данных дерева PoE 1.</p>"
            f"<p>{chips or 'Узлы отсутствуют'}</p>"
        )

    def _change_level(self, delta):
        profile = self.overlay.active_profile()
        profile["level"] = clamp_level(profile.get("level", 1) + delta)
        self.overlay.save_profiles()
        self.refresh_level()

    def _profile_changed(self, index):
        profile_id = self.profile_combo.itemData(index)
        if profile_id:
            self.overlay.switch_profile(profile_id)
            self.refresh_level()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "Новый персонаж", "Имя персонажа:")
        if ok and name.strip():
            self.overlay.create_profile(name.strip())
            self.reload()

    def _rename_profile(self):
        profile = self.overlay.active_profile()
        name, ok = QInputDialog.getText(
            self, "Переименовать персонажа", "Новое имя:", text=profile.get("name", "")
        )
        if ok and name.strip():
            profile["name"] = name.strip()
            self.overlay.save_profiles()
            self.reload()

    def _import_pob(self):
        dialog = PobImportDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        try:
            build = parse_pob(dialog.source())
        except PobImportError as exc:
            QMessageBox.warning(self, "Не удалось импортировать PoB", str(exc))
            return
        profile = self.overlay.active_profile()
        profile["build"] = build
        if profile.get("level", 1) == 1 and build.get("character_level"):
            profile["level"] = clamp_level(build["character_level"])
        self.overlay.save_profiles()
        self.refresh_level()
        QMessageBox.information(
            self, "PoB импортирован",
            f"Деревьев: {len(build.get('trees', []))}\n"
            f"Наборов камней: {len(build.get('gem_sets', []))}"
        )



class EnhancedBuildProgressDialog(BuildProgressDialog):
    def __init__(self, overlay):
        self._enhanced_ready = False
        super().__init__(overlay)

        self.tabs.clear()
        self.gem_links = GemLinksView()
        self.tabs.addTab(self.gem_links, "Камни и связки")

        tree_page = QWidget()
        tree_layout = QVBoxLayout(tree_page)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_head = QHBoxLayout()
        self.tree_stage_label = QLabel()
        self.tree_stage_label.setStyleSheet("color:#e6c477;")
        tree_head.addWidget(self.tree_stage_label, 1)
        fit_selected = QPushButton("К выбранным")
        fit_selected.setStyleSheet(base.button_style())
        fit_selected.clicked.connect(self._fit_selected)
        fit_all = QPushButton("Всё дерево")
        fit_all.setStyleSheet(base.button_style())
        fit_all.clicked.connect(self._fit_all)
        tree_head.addWidget(fit_selected)
        tree_head.addWidget(fit_all)
        tree_layout.addLayout(tree_head)
        self.tree_canvas = PassiveTreeCanvas()
        tree_layout.addWidget(self.tree_canvas, 1)
        legend = QLabel("Золотые — уже взятые · зелёные — новые на текущем этапе · колесо — масштаб · мышь — перемещение")
        legend.setStyleSheet("color:#777;")
        legend.setWordWrap(True)
        tree_layout.addWidget(legend)
        self.tabs.addTab(tree_page, "Дерево")

        self.step_context = QLabel()
        self.step_context.setWordWrap(True)
        self.step_context.setStyleSheet(
            f"color:{legacy.Style.TEXT_SECONDARY}; background:{legacy.Style.BG_SECONDARY}; "
            f"border:1px solid {legacy.Style.BORDER}; border-radius:7px; padding:8px;"
        )
        self.layout().insertWidget(2, self.step_context)

        self.log_status = QLabel()
        self.log_status.setWordWrap(True)
        self.log_status.setStyleSheet("color:#6f9f77;")
        self.layout().insertWidget(self.layout().count() - 1, self.log_status)

        self.monitor = ClientLevelMonitor(self)
        self.monitor.level_seen.connect(self._on_level_seen)
        self.monitor.status_changed.connect(self.log_status.setText)
        self.overlay.content.active_step_changed.connect(self._refresh_step_context)
        self._enhanced_ready = True
        self.reload()
        self._refresh_step_context()
        self.monitor.start()

    def _render_gems(self, build, level):
        if not self._enhanced_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            self.status.setText("У персонажа пока нет импортированного билда.")
            return
        stage = stage_for_level(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки в PoB не найдены", [])
            return
        self.gem_links.set_links(stage.get("title", "Связки"), stage.get("links", []))
        self.status.setText(
            f"Связки без привязки к экипировке · этап уровня {stage.get('level', 1)}"
        )

    def _render_tree(self, build, level):
        if not self._enhanced_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB для отображения дерева")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = stage_for_level(trees, level)
        if not stage:
            self.tree_stage_label.setText("В PoB дерево не найдено")
            self.tree_canvas.set_stage([])
            return
        previous_candidates = [
            item for item in trees
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda item: item.get("level", 1)) if previous_candidates else None
        nodes = stage.get("nodes", [])
        previous_nodes = previous.get("nodes", []) if previous else []
        self.tree_stage_label.setText(
            f"{stage.get('title', 'Дерево')} · {len(nodes)} пассивов · "
            f"+{len(set(nodes) - set(previous_nodes))} с прошлого этапа"
        )
        self.tree_canvas.set_stage(nodes, previous_nodes)

    def _fit_selected(self):
        self.tree_canvas.fit_selected()
        self.tree_canvas.update()

    def _fit_all(self):
        self.tree_canvas.fit_all()

    def _refresh_step_context(self):
        act, index, text = self.overlay.content.get_active_step_info()
        if index < 0:
            self.step_context.setText("Кампания завершена")
        else:
            self.step_context.setText(
                f"Текущий шаг: {act} · #{index + 1}\n{text}"
            )

    def _on_level_seen(self, character_name, character_class, level):
        profile = self.overlay.active_profile()
        bound_name = profile.get("log_character_name", "").strip()
        profile_name = profile.get("name", "").strip()
        build = profile.get("build") or {}
        allowed_classes = {
            str(build.get("class", "")).casefold(),
            str(build.get("ascendancy", "")).casefold(),
        } - {""}
        name_matches = character_name.casefold() in {
            bound_name.casefold(), profile_name.casefold()
        } - {""}
        class_matches = character_class.casefold() in allowed_classes
        if bound_name and character_name.casefold() != bound_name.casefold():
            return
        if not bound_name and not name_matches and not class_matches:
            return
        profile["log_character_name"] = character_name
        profile["level"] = clamp_level(level)
        self.overlay.save_profiles()
        self.log_status.setText(
            f"Client.txt: {character_name} ({character_class}) · уровень {level}"
        )
        self.refresh_level()

    def _profile_changed(self, index):
        super()._profile_changed(index)
        if self._enhanced_ready:
            self._refresh_step_context()



class TargetBuildProgressDialog(EnhancedBuildProgressDialog):
    def __init__(self, overlay):
        self._target_ready = False
        self._tree_initialized = False
        super().__init__(overlay)

        self.tabs.clear()
        self.gem_links = DescribedGemLinksView()
        self.tabs.addTab(self.gem_links, "Камни и связки")

        tree_page = QWidget()
        tree_layout = QVBoxLayout(tree_page)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        head = QHBoxLayout()
        self.tree_stage_label = QLabel()
        self.tree_stage_label.setStyleSheet("color:#e6c477;")
        head.addWidget(self.tree_stage_label, 1)
        selected_btn = QPushButton("К выбранным")
        selected_btn.setStyleSheet(base.button_style())
        selected_btn.clicked.connect(self._fit_selected)
        all_btn = QPushButton("Всё дерево")
        all_btn.setStyleSheet(base.button_style())
        all_btn.clicked.connect(self._fit_all)
        head.addWidget(selected_btn)
        head.addWidget(all_btn)
        tree_layout.addLayout(head)
        self.tree_canvas = DetailedPassiveTreeCanvas()
        tree_layout.addWidget(self.tree_canvas, 1)
        legend = QLabel(
            "Зелёная рамка — взято · светло-зелёная — добавлено текущим этапом · "
            "наведите на любой пассив для полного описания"
        )
        legend.setStyleSheet("color:#777;")
        legend.setWordWrap(True)
        tree_layout.addWidget(legend)
        self.tabs.addTab(tree_page, "Дерево")

        self._target_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._target_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = leveling_stage(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        self.gem_links.set_links(stage.get("title", "Связки"), stage.get("links", []))
        self.status.setText(
            f"Уровень персонажа {level} · набор камней «{stage.get('title', 'Без названия')}»"
        )

    def _render_tree(self, build, level):
        if not self._target_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous_candidates = [
            item for item in trees
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda item: item.get("level", 1)) if previous_candidates else None
        previous_nodes = previous.get("nodes", []) if previous else []

        old_center = self.tree_canvas.center
        old_scale = self.tree_canvas.scale
        self.tree_canvas.set_stage(stage.get("nodes", []), previous_nodes)
        if self._tree_initialized:
            self.tree_canvas.center = old_center
            self.tree_canvas.scale = old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True

        visible_count = len(self.tree_canvas.selected)
        added_count = len(self.tree_canvas.added)
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{visible_count} пассивов · +{added_count} на этапе"
        )



class PerLevelBuildDialog(TargetBuildProgressDialog):
    def _render_tree(self, build, level):
        if not self._target_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous_candidates = [
            item for item in trees
            if item is not stage and item.get("level", 1) < stage.get("level", 1)
        ]
        previous = max(previous_candidates, key=lambda item: item.get("level", 1)) if previous_candidates else None
        previous_nodes = previous.get("nodes", []) if previous else []
        visible_nodes, newly_added = nodes_at_level(
            stage, previous_nodes, level, TREE_GRAPH
        )
        before_current_level = [node for node in visible_nodes if str(node) not in set(newly_added)]

        old_center = self.tree_canvas.center
        old_scale = self.tree_canvas.scale
        self.tree_canvas.set_stage(visible_nodes, before_current_level)
        if self._tree_initialized:
            self.tree_canvas.center = old_center
            self.tree_canvas.scale = old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        target_count = len([
            node for node in stage.get("nodes", [])
            if str(node) in self.tree_canvas.positions
        ])
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{len(self.tree_canvas.selected)}/{target_count} пассивов · "
            f"+{len(self.tree_canvas.added)} сейчас"
        )



class CorrectedBuildDialog(PerLevelBuildDialog):
    def _render_tree(self, build, level):
        if not self._target_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous = previous_stage(trees, stage)
        previous_nodes = previous.get("nodes", []) if previous else []
        visible_nodes, newly_added = nodes_at_level(
            stage, previous_nodes, level, per_level.TREE_GRAPH
        )
        new_set = set(newly_added)
        before_current_level = [node for node in visible_nodes if str(node) not in new_set]

        old_center = self.tree_canvas.center
        old_scale = self.tree_canvas.scale
        self.tree_canvas.set_stage(visible_nodes, before_current_level)
        if self._tree_initialized:
            self.tree_canvas.center = old_center
            self.tree_canvas.scale = old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        target_count = sum(
            str(node) in self.tree_canvas.positions for node in stage.get("nodes", [])
        )
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{len(self.tree_canvas.selected)}/{target_count} пассивов · "
            f"+{len(self.tree_canvas.added)} сейчас"
        )



class FinalBuildDialog(CorrectedBuildDialog):
    def _render_tree(self, build, level):
        if not self._target_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous = previous_stage(trees, stage)
        previous_nodes = previous.get("nodes", []) if previous else []
        visible_nodes, newly_added = nodes_at_level(
            stage, previous_nodes, level, v3.per_level.TREE_GRAPH
        )
        new_set = set(newly_added)
        before_current_level = [node for node in visible_nodes if str(node) not in new_set]
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_stage(visible_nodes, before_current_level)
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        target_count = sum(
            str(node) in self.tree_canvas.positions for node in stage.get("nodes", [])
        )
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{len(self.tree_canvas.selected)}/{target_count} пассивов · "
            f"+{len(self.tree_canvas.added)} сейчас"
        )



class ReleaseBuildDialog(FinalBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = CompleteTooltipTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self.reload()



class CleanBuildDialog(ReleaseBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = CleanPassiveTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self.reload()



class FullStageBuildDialog(CleanBuildDialog):
    def __init__(self, overlay):
        self._v3_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = ConnectedPassiveTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self._v3_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v3_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_stage([])
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        if not stage:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_stage([])
            return
        previous = previous_stage(trees, stage)
        previous_nodes = previous.get("nodes", []) if previous else []
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_stage(stage.get("nodes", []), previous_nodes)
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self.tree_canvas.fit_all()
            self._tree_initialized = True
        current_count = len(self.tree_canvas.selected)
        added_count = len(self.tree_canvas.added)
        self.tree_stage_label.setText(
            f"Уровень {level} · {stage.get('title', 'Дерево')} · "
            f"{current_count}/{current_count} пассивов · +{added_count} с прошлого этапа"
        )



class MasteryBuildDialog(FullStageBuildDialog):
    def __init__(self, overlay):
        self._v4_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = MasteryAwareTreeCanvas()
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self._v4_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v4_ready:
            return super()._render_tree(build, level)
        super()._render_tree(build, level)
        if build:
            stage = leveling_stage(build.get("trees", []), level)
            self.tree_canvas.set_masteries(stage.get("masteries", "") if stage else "")



class OrbitalBuildDialog(MasteryBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        selected_masteries = dict(old_canvas.selected_masteries)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = OrbitalPassiveTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self.reload()



class RouteBuildDialog(OrbitalBuildDialog):
    def __init__(self, overlay):
        self._v6_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        selected_masteries = dict(old_canvas.selected_masteries)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = LevelingRouteTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        for label in self.tabs.widget(1).findChildren(QLabel):
            if "Зелёная рамка" in label.text() or "Зелёная" in label.text():
                label.setText(
                    "Золотое — уже взято · зелёное — маршрут текущего этапа · "
                    "двойная светлая рамка — следующий доступный узел"
                )
        self._tree_initialized = False
        self._v6_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v6_ready:
            return super()._render_tree(build, level)
        super()._render_tree(build, level)
        if not build:
            return
        trees = build.get("trees", [])
        stage = leveling_stage(trees, level)
        previous_stage_data = previous_stage(trees, stage) if stage else None
        if stage:
            self.tree_canvas.set_stage(
                stage.get("nodes", []),
                previous_stage_data.get("nodes", []) if previous_stage_data else [],
            )
            self.tree_canvas.set_masteries(stage.get("masteries", ""))
            names = sorted({
                self.tree_canvas.nodes.get(node_id, {}).get("name", "Пассив")
                for node_id in self.tree_canvas.next_nodes
            })
            next_text = ", ".join(names[:4]) or "нет"
            self.tree_stage_label.setText(
                f"Уровень {level} · {stage.get('title', 'Дерево')} · "
                f"взято {len(self.tree_canvas.completed_nodes)} · "
                f"маршрут +{len(self.tree_canvas.route_nodes)} · далее: {next_text}"
            )



class CombinedBuildDialog(RouteBuildDialog):
    def __init__(self, overlay):
        self._v7_ready = False
        self._focused_stage_key = None
        super().__init__(overlay)

        root = self.layout()
        tab_index = root.indexOf(self.tabs)
        root.removeWidget(self.tabs)
        self.tabs.hide()

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            "QSplitter::handle{background:#2b2d33;}"
            "QScrollBar{background:#111216;}"
        )

        gem_page = QWidget()
        gem_page.setMinimumWidth(300)
        gem_page.setStyleSheet("background:#08090b;")
        gem_layout = QVBoxLayout(gem_page)
        gem_layout.setContentsMargins(0, 0, 0, 0)
        gem_layout.setSpacing(0)
        self.gem_links = CompactGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.addWidget(self.gem_links, 1)

        tree_page = QWidget()
        tree_page.setMinimumWidth(520)
        tree_page.setStyleSheet("background:#08090b;")
        tree_layout = QVBoxLayout(tree_page)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_layout.setSpacing(7)

        tree_head = QHBoxLayout()
        self.tree_stage_label = QLabel()
        self.tree_stage_label.setStyleSheet("color:#e6c477;")
        self.tree_stage_label.setWordWrap(True)
        tree_head.addWidget(self.tree_stage_label, 1)

        near_btn = QPushButton("К ближайшим")
        near_btn.setStyleSheet(base.button_style())
        near_btn.clicked.connect(self._fit_upcoming)
        selected_btn = QPushButton("К выбранным")
        selected_btn.setStyleSheet(base.button_style())
        selected_btn.clicked.connect(self._fit_selected)
        all_btn = QPushButton("Всё дерево")
        all_btn.setStyleSheet(base.button_style())
        all_btn.clicked.connect(self._fit_all)
        tree_head.addWidget(near_btn)
        tree_head.addWidget(selected_btn)
        tree_head.addWidget(all_btn)
        tree_layout.addLayout(tree_head)

        self.tree_canvas = FocusedLevelingTreeCanvas()
        tree_layout.addWidget(self.tree_canvas, 1)
        legend = QLabel(
            "Золотое — уже взято · зелёное — текущий маршрут · "
            "двойная светлая рамка — следующий доступный узел"
        )
        legend.setStyleSheet("color:#777;")
        legend.setWordWrap(True)
        tree_layout.addWidget(legend)

        splitter.addWidget(gem_page)
        splitter.addWidget(tree_page)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([390, 790])
        root.insertWidget(max(0, tab_index), splitter, 1)
        self.combined_splitter = splitter

        self.resize(1220, 760)
        self._tree_initialized = False
        self._v7_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v7_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = leveling_stage(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        title = stage.get("title", "Связки")
        self.gem_links.set_links(title, stage.get("links", []))
        self.status.setText(f"Уровень персонажа {level} · набор камней «{title}»")

    def _render_tree(self, build, level):
        if not self._v7_ready:
            return super()._render_tree(build, level)

        super()._render_tree(build, level)
        if not build:
            self._focused_stage_key = None
            return
        stage = leveling_stage(build.get("trees", []), level)
        if not stage:
            self._focused_stage_key = None
            return

        stage_key = (
            stage.get("level", 1),
            stage.get("title", ""),
            tuple(stage.get("nodes", [])),
        )
        if stage_key != self._focused_stage_key:
            self._focused_stage_key = stage_key
            QTimer.singleShot(0, self._fit_upcoming)

    def _fit_upcoming(self):
        if self._v7_ready:
            self.tree_canvas.fit_upcoming()



class ProgressionBuildDialog(CombinedBuildDialog):
    def __init__(self, overlay):
        self._v8_ready = False
        super().__init__(overlay)
        old_canvas = self.tree_canvas
        layout = old_canvas.parentWidget().layout()
        index = layout.indexOf(old_canvas)
        selected_masteries = dict(old_canvas.selected_masteries)
        layout.removeWidget(old_canvas)
        old_canvas.deleteLater()
        self.tree_canvas = ProgressionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        self._focused_stage_key = None
        self._tree_initialized = False
        self._v8_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v8_ready:
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
        self.gem_links.set_links(title, stage.get("links", []))
        future_levels = sorted({
            int(item.get("level", 1)) for item in stages
            if int(item.get("level", 1)) > level
        })
        next_text = f" · следующая смена на {future_levels[0]}" if future_levels else ""
        self.status.setText(
            f"Уровень персонажа {level} · набор камней «{title}»{next_text}"
        )

    def _render_tree(self, build, level):
        if not self._v8_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_progression([], [], [])
            self._focused_stage_key = None
            return

        plan = passive_plan(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_progression([], [], [])
            self._focused_stage_key = None
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_progression(
            plan["planned"], plan["completed"], plan["upcoming"]
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        upcoming_names = [
            self.tree_canvas.nodes.get(str(node), {}).get("name", "Пассив")
            for node in plan["upcoming"][:3]
        ]
        next_text = " → ".join(upcoming_names) or "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень {level} · цель: {target.get('title', 'Дерево')} · "
            f"взято {len(self.tree_canvas.completed_nodes)}/{len(self.tree_canvas.selected)} · "
            f"дальше: {next_text}"
        )

        stage_key = (
            level,
            target.get("title", ""),
            tuple(plan["upcoming"][:5]),
        )
        if stage_key != self._focused_stage_key:
            self._focused_stage_key = stage_key
            QTimer.singleShot(0, self._fit_upcoming)



class FixedProgressionBuildDialog(ProgressionBuildDialog):
    def __init__(self, overlay):
        self._v9_ready = False
        super().__init__(overlay)
        self._v9_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v9_ready:
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
        self.gem_links.set_links(title, stage.get("links", []))
        future_levels = sorted({
            int(item.get("level", 1)) for item in stages
            if int(item.get("level", 1)) > level
        })
        next_text = f" · следующая смена на {future_levels[0]}" if future_levels else ""
        self.status.setText(
            f"Уровень персонажа {level} · набор камней «{title}»{next_text}"
        )



class ScaledGemBuildDialog(FixedProgressionBuildDialog):
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



class LevelMappedBuildDialog(ScaledGemBuildDialog):
    def __init__(self, overlay):
        self._v11_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = LevelGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = LevelMappedTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._v11_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v11_ready:
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
        self.gem_links.set_links(f"{title} · уровень {level}", links)
        self.status.setText(
            f"Уровень персонажа {level} · показаны доступные камни и их текущие уровни"
        )

    def _render_tree(self, build, level):
        if not self._v11_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_level_progression([], [], [], {})
            return
        plan = passive_plan_by_level(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_level_progression([], [], [], {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_level_progression(
            plan["planned"], plan["completed"], plan["upcoming"], plan["node_levels"]
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_name = self.tree_canvas.nodes.get(str(first), {}).get("name", "Пассив") if first else "—"
        first_level = plan["node_levels"].get(str(first), "—") if first else "—"
        self.tree_stage_label.setText(
            f"Уровень {level} · зелёное взято {len(self.tree_canvas.completed_nodes)} · "
            f"золотое впереди {len(self.tree_canvas.route_nodes)} · "
            f"следующий: ур. {first_level}, {first_name}"
        )
        focus_key = (level, str(first), first_level)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class FinalLevelMappedBuildDialog(LevelMappedBuildDialog):
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



class ImmediateFocusBuildDialog(FinalLevelMappedBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_tree = self.tree_canvas
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = ImmediateFocusTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        self._tree_initialized = False
        self._focused_stage_key = None
        self.reload()



class StrictProgressionBuildDialog(ImmediateFocusBuildDialog):
    def __init__(self, overlay):
        self._v14_ready = False
        super().__init__(overlay)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v14_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v14_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_level_progression([], [], [], {})
            return

        plan = strict_passive_plan(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_level_progression([], [], [], {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_level_progression(
            plan["planned"], plan["completed"], plan["upcoming"], plan["node_levels"]
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_name = self.tree_canvas.nodes.get(str(first), {}).get("name", "Пассив") if first else "—"
        first_level = plan["node_levels"].get(str(first), "—") if first else "—"
        self.tree_stage_label.setText(
            f"Уровень {level} · зелёное взято {len(self.tree_canvas.completed_nodes)} · "
            f"золотое впереди {len(self.tree_canvas.route_nodes)} · "
            f"следующий: ур. {first_level}, {first_name} · один уровень = одна нода"
        )
        focus_key = (level, str(first), first_level)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class QuestAwareBuildDialog(StrictProgressionBuildDialog):
    def __init__(self, overlay):
        self._v15_ready = False
        super().__init__(overlay)
        old_tree = self.tree_canvas
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = QuestAwareTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — взято · золотое — впереди · 12 — очко уровня · "
                    "12К — квестовая книга · 20Б — награда Эрамира"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v15_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v15_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        kill_all = pob_kills_all_bandits(build)
        plan = quest_aware_passive_plan(
            build.get("trees", []), level, TREE_GRAPH, kill_all
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        bandit_text = "Эрамир +1" if kill_all else "помощь бандиту, без очка"
        self.tree_stage_label.setText(
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · {bandit_text}"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class BookOnlyBuildDialog(QuestAwareBuildDialog):
    def __init__(self, overlay):
        self._v16_ready = False
        super().__init__(overlay)
        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — взято · золотое — впереди · "
                    "12 — очко уровня · 12К — книга за квест"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v16_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v16_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = book_only_passive_plan(build.get("trees", []), level, TREE_GRAPH)
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        self.tree_stage_label.setText(
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · учитываются только книги"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class ContinuousPassiveBuildDialog(BookOnlyBuildDialog):
    def __init__(self, overlay):
        self._v17_ready = False
        super().__init__(overlay)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v17_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v17_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = visible_book_passive_plan(
            build.get("trees", []), level, TREE_GRAPH, self.tree_canvas.positions
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        self.tree_stage_label.setText(
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · "
            "восхождение считается отдельно"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class SemanticPassiveBuildDialog(ContinuousPassiveBuildDialog):
    def __init__(self, overlay):
        self._v18_ready = False
        super().__init__(overlay)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v18_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v18_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = semantic_book_passive_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        self.tree_stage_label.setText(
            f"Уровень {level} · взято {len(self.tree_canvas.completed_nodes)} · "
            f"следующий {marker}: {first_name} ({source}) · локальный порядок ветки"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class CorrectedSemanticBuildDialog(SemanticPassiveBuildDialog):
    def __init__(self, overlay):
        self._v19_ready = False
        super().__init__(overlay)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v19_ready = True
        self.reload()

    def _render_tree(self, build, level):
        if not self._v19_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = corrected_semantic_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "—"
        marker = plan["node_markers"].get(first_key, "—")
        source = plan["node_sources"].get(first_key, "этап завершён")
        self.tree_stage_label.setText(
            f"Уровень {level} · следующий {marker}: {first_name} ({source}) · "
            "кейстоуны берутся при открытии ветки"
        )
        focus_key = (level, first_key, marker)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class CleanArtworkBuildDialog(CorrectedSemanticBuildDialog):
    def __init__(self, overlay):
        self._v20_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = ArtworkGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = CleanPassiveTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        for label in self.tree_canvas.parentWidget().findChildren(QLabel):
            if label is not self.tree_stage_label and ("Зелён" in label.text() or "золот" in label.text()):
                label.setText(
                    "Зелёное — уже взято · золотое — будущий маршрут · "
                    "светлая рамка — следующая нода"
                )
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v20_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v20_ready:
            return super()._render_gems(build, level)
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = stage_at_level(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        self.gem_links.set_links(
            stage.get("title", "Связки"),
            links_at_level(stage.get("links", []), level),
        )
        self.status.setText("Показаны доступные на текущем этапе связки камней")

    def _render_tree(self, build, level):
        if not self._v20_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        plan = corrected_semantic_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            return
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Пассив") if first else "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · следующая нода: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class SocketedGemBuildDialog(CleanArtworkBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = CleanArtworkGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)
        self.reload()



class AscendancyBuildDialog(SocketedGemBuildDialog):
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



class ConnectedAscendancyBuildDialog(AscendancyBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        current_index = self.left_tabs.currentIndex()
        old_view = self.ascendancy_view
        self.left_tabs.removeTab(1)
        old_view.deleteLater()
        self.ascendancy_view = ConnectedAscendancyProgressWidget()
        self.left_tabs.insertTab(1, self.ascendancy_view, "Ассенданси")
        self.left_tabs.setCurrentIndex(current_index)
        self.reload()



class IntegratedTreeBuildDialog(ConnectedAscendancyBuildDialog):
    def __init__(self, overlay):
        self._integrated_ready = False
        super().__init__(overlay)

        # The ascendancy now lives inside the main tree canvas.
        if self.left_tabs.count() > 1:
            hidden_ascendancy = self.left_tabs.widget(1)
            self.left_tabs.removeTab(1)
            hidden_ascendancy.hide()
        self.left_tabs.tabBar().hide()

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = CopyableGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = IntegratedAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._integrated_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if self._integrated_ready:
            self.tree_canvas.set_ascendancy_build(build, level)



class NativeAscendancyBuildDialog(IntegratedTreeBuildDialog):
    def __init__(self, overlay):
        self._native_asc_ready = False
        super().__init__(overlay)

        old_tree = self.tree_canvas
        tree_page = old_tree.parentWidget()
        tree_layout = tree_page.layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = NativeAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)

        header_layout = tree_layout.itemAt(0).layout()
        self.ascendancy_button = QPushButton("К ассенданси")
        self.ascendancy_button.setStyleSheet(base.button_style())
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        header_layout.insertWidget(1, self.ascendancy_button)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._native_asc_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if self._native_asc_ready:
            self.tree_canvas.set_ascendancy_build(build, level)
            self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))



class RestoredAscendancyBuildDialog(NativeAscendancyBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = RestoredAscendancyTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self.reload()



class LocalizedOverlayBuildDialog(RestoredAscendancyBuildDialog):
    def __init__(self, overlay):
        self._v27_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = RussianOverlayGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = RussianDescriptionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)

        self._apply_overlay_style()
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v27_ready = True
        self.reload()

    def _apply_overlay_style(self):
        style = legacy.Style
        self.setStyleSheet(f"""
            QDialog, QWidget {{ background:{style.BG}; color:{style.TEXT_PRIMARY}; }}
            QLabel {{ color:{style.TEXT_PRIMARY}; background:transparent; }}
            QComboBox {{ background:{style.BG_SECONDARY}; color:{style.TEXT_PRIMARY};
                border:1px solid {style.BORDER}; border-radius:{style.RAD_S}px; padding:7px 10px; }}
            QPushButton {{ background:{style.BG_SECONDARY}; color:{style.TEXT_SECONDARY};
                border:1px solid {style.BORDER}; border-radius:{style.RAD_S}px; padding:7px 11px; }}
            QPushButton:hover {{ color:{style.TEXT_PRIMARY}; border-color:{style.ACCENT}; background:{style.HOVER}; }}
            QPushButton:pressed {{ color:{style.BG}; background:{style.ACCENT}; }}
            QPushButton:disabled {{ color:{style.TEXT_DISABLED}; }}
            QScrollArea {{ background:transparent; border:0; }}
            QScrollBar:vertical {{ background:{style.BG}; width:10px; }}
            QScrollBar::handle:vertical {{ background:{style.BG_SECONDARY}; border-radius:5px; min-height:24px; }}
            QSplitter::handle {{ background:{style.BORDER}; }}
            QFrame {{ border-color:{style.BORDER}; }}
        """)
        self.tree_stage_label.setStyleSheet(f"color:{style.ACCENT}; font-weight:600;")
        self.status.setStyleSheet(f"color:{style.TEXT_MUTED};")
        self.gem_links.body.setStyleSheet(f"background:{style.BG};")

    def _render_tree(self, build, level):
        if not self._v27_ready:
            return super()._render_tree(build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_ascendancy_build(None, level)
            return
        plan = nearest_connected_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_ascendancy_build(build, level)
            return
        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            plan["planned"], plan["completed"], plan["upcoming"],
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        self.tree_canvas.set_ascendancy_build(build, level)
        self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True
        first = plan["upcoming"][0] if plan["upcoming"] else None
        first_key = str(first) if first is not None else ""
        first_name = self.tree_canvas.nodes.get(first_key, {}).get("name", "Passive") if first else "этап завершён"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · следующая нода: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            QTimer.singleShot(0, self._fit_upcoming)



class StrictNearestBuildDialog(LocalizedOverlayBuildDialog):
    pass



class MasteryAndQuestBuildDialog(StrictNearestBuildDialog):
    def __init__(self, overlay):
        self._v32_ready = False
        super().__init__(overlay)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        gem_index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = AcquisitionGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gem_layout.insertWidget(gem_index, self.gem_links, 1)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = SeparateMasteryTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)

        self._tree_initialized = False
        self._focused_stage_key = None
        self._apply_overlay_style()
        self._v32_ready = True
        self.reload()

    def _render_gems(self, build, level):
        if not self._v32_ready:
            return super()._render_gems(build, level)
        self.gem_links.set_character_class(build.get("class", "") if build else "")
        if not build:
            self.gem_links.set_links("Импортируйте PoB", [])
            return
        stage = stage_at_level(build.get("gem_sets", []), level)
        if not stage:
            self.gem_links.set_links("Связки не найдены", [])
            return
        self.gem_links.set_links(
            stage.get("title", "Связки"),
            links_at_level(stage.get("links", []), level),
        )
        self.status.setText(
            "Q — награда за квест · B — купить у продавца · наведите на камень для деталей"
        )

    def _render_tree(self, build, level):
        if not self._v32_ready:
            return fallback_renderer.LocalizedOverlayBuildDialog._render_tree(self, build, level)
        if not build:
            self.tree_stage_label.setText("Импортируйте PoB")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_mastery_progression([])
            self.tree_canvas.set_ascendancy_build(None, level)
            return
        plan = mastery_separated_plan(
            build.get("trees", []), level, TREE_GRAPH,
            self.tree_canvas.positions, self.tree_canvas.nodes,
        )
        target = plan.get("target")
        if not target:
            self.tree_stage_label.setText("Дерево в PoB не найдено")
            self.tree_canvas.set_quest_progression([], [], [], {}, {})
            self.tree_canvas.set_mastery_progression([])
            self.tree_canvas.set_ascendancy_build(build, level)
            return

        is_mastery = lambda node: self.tree_canvas.nodes.get(str(node), {}).get("isMastery")
        completed_mastery = [node for node in plan["completed"] if is_mastery(node)]
        completed_regular = [node for node in plan["completed"] if not is_mastery(node)]
        immediate = plan["upcoming"][:1]
        next_mastery = immediate[0] if immediate and is_mastery(immediate[0]) else None
        immediate_regular = [] if next_mastery is not None else immediate
        visible_plan = completed_regular + immediate_regular

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            visible_plan, completed_regular, immediate_regular,
            plan["node_levels"], {},
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        self.tree_canvas.set_mastery_progression(completed_mastery, next_mastery)
        self.tree_canvas.set_ascendancy_build(build, level)
        self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = immediate[0] if immediate else None
        first_key = str(first) if first is not None else ""
        first_name = (
            self.tree_canvas.nodes.get(first_key, {}).get("name", "Passive")
            if first else "этап завершён"
        )
        kind = "следующее мастерство" if next_mastery is not None else "следующая нода"
        self.tree_stage_label.setText(
            f"Уровень персонажа {level} · {kind}: {first_name}"
        )
        focus_key = (level, first_key)
        if focus_key != self._focused_stage_key:
            self._focused_stage_key = focus_key
            if next_mastery is None:
                QTimer.singleShot(0, self._fit_upcoming)



class CompactBuildDialog(MasteryAndQuestBuildDialog):
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



class AssetFramedBuildDialog(CompactBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self._frame_pixmap = legacy.load_background_pixmap()
        self._has_asset_frame = not self._frame_pixmap.isNull()

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setWindowTitle("ActPilot — PoE 1 Build")

        self._install_asset_header()
        self._apply_asset_frame_layout()
        self._apply_asset_style()
        self._resize_handles = legacy.CornerResizeHandles(
            self, 900, 560, parent=self,
        )
        self._resize_handles.raise_()
        self.setWindowOpacity(1.0)

    def _install_asset_header(self):
        self.asset_header = BuildAssetHeader(self)
        row = QHBoxLayout(self.asset_header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(legacy.Style.PAD_S)

        logo = legacy.scaled_ui_pixmap("logo", height=36)
        self.asset_logo = QLabel()
        if not logo.isNull():
            self.asset_logo.setPixmap(logo)
        else:
            self.asset_logo.setText("ActPilot")
            family = legacy.ensure_cormorant_loaded() or "Georgia"
            self.asset_logo.setFont(QFont(family, 22, QFont.DemiBold))
            self.asset_logo.setStyleSheet("color:#c7a45d;")
        self.asset_logo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        row.addWidget(self.asset_logo, 0, Qt.AlignVCenter)
        row.addStretch()

        self.asset_close = legacy.make_icon_button(
            "close", "×", legacy.Style.BTN_SIZE, self.close, self.asset_header,
        )
        self.asset_close.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.asset_close, 0, Qt.AlignVCenter)
        self.layout().insertWidget(0, self.asset_header)

    def _apply_asset_frame_layout(self):
        style = legacy.Style
        self.layout().setContentsMargins(
            style.BG_SLICE_LEFT,
            style.BG_SLICE_TOP - 8,
            style.BG_SLICE_RIGHT,
            style.BG_SLICE_BOTTOM,
        )
        self.layout().setSpacing(6)
        self.combined_splitter.setSizes([300, 730])
        self.resize(1100, 700)
        self.setMinimumSize(900, 560)

    def _apply_asset_style(self):
        style = legacy.Style
        self.setStyleSheet(f"""
            QDialog {{ background:transparent; border:0; }}
            QWidget {{
                background:transparent;
                color:{style.TEXT_PRIMARY};
                selection-background-color:{style.ACCENT_BG};
            }}
            QFrame#assetHeader {{ background:transparent; border:0; }}
            QLabel {{
                background:transparent;
                border:0;
                color:{style.TEXT_SECONDARY};
            }}
            QComboBox {{
                background:rgba(7, 9, 9, 205);
                color:{style.TEXT_PRIMARY};
                border:1px solid rgba(154, 116, 57, 0.38);
                border-radius:{style.RAD_S}px;
                padding:5px 9px;
                min-height:18px;
            }}
            QComboBox:hover, QComboBox:focus {{
                border-color:rgba(205, 165, 92, 0.78);
            }}
            QPushButton {{
                background:rgba(8, 9, 9, 190);
                color:rgba(226, 218, 197, 0.72);
                border:1px solid rgba(154, 116, 57, 0.34);
                border-radius:{style.RAD_S}px;
                padding:4px 9px;
            }}
            QPushButton:hover {{
                color:#f4e8cb;
                background:rgba(118, 82, 27, 0.18);
                border-color:rgba(205, 165, 92, 0.78);
            }}
            QPushButton:pressed {{
                color:#12120f;
                background:#b9924c;
            }}
            QScrollArea {{ background:transparent; border:0; }}
            QScrollBar:vertical {{ background:transparent; width:7px; }}
            QScrollBar::handle:vertical {{
                background:rgba(218, 201, 167, 0.25);
                border-radius:3px;
                min-height:22px;
            }}
            QScrollBar::handle:vertical:hover {{ background:rgba(218, 201, 167, 0.42); }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
            QSplitter::handle {{ background:rgba(154, 116, 57, 0.22); }}
            QSlider#levelSlider::groove:horizontal {{
                background:rgba(104, 83, 43, 0.42);
                height:3px;
                border-radius:1px;
            }}
            QSlider#levelSlider::sub-page:horizontal {{
                background:{style.ACCENT};
                border-radius:1px;
            }}
            QSlider#levelSlider::handle:horizontal {{
                background:#c4a15c;
                border:1px solid #6f5428;
                width:14px;
                height:14px;
                margin:-6px 0;
                border-radius:7px;
            }}
            QSlider#levelSlider::handle:horizontal:hover {{ background:#e0c278; }}
        """)
        self.asset_close.setStyleSheet("""
            QPushButton { background:transparent; border:0; padding:0; }
            QPushButton:hover { background:rgba(122,83,30,0.18); border:0; }
        """)
        self.gem_links.body.setStyleSheet("background:rgba(2,4,4,0.38);")
        self.gem_links.parentWidget().setStyleSheet("background:transparent;")
        self.tree_canvas.parentWidget().setStyleSheet("background:transparent;")
        self.combined_splitter.setStyleSheet(
            "QSplitter::handle{background:rgba(154,116,57,0.22);}"
        )
        family = legacy.ensure_cormorant_loaded() or "Georgia"
        self.level_label.setFont(QFont(family, 14, QFont.DemiBold))
        self.level_label.setStyleSheet("color:#d3b46f; background:transparent;")
        self.character_label.setStyleSheet("color:rgba(255,255,255,0.76);")
        self.tree_stage_label.setStyleSheet(
            f"color:{style.ACCENT}; background:transparent; font-weight:600;"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._has_asset_frame:
            legacy.draw_nine_slice(
                painter,
                self._frame_pixmap,
                self.rect(),
                (
                    legacy.Style.BG_SLICE_LEFT,
                    legacy.Style.BG_SLICE_TOP,
                    legacy.Style.BG_SLICE_RIGHT,
                    legacy.Style.BG_SLICE_BOTTOM,
                ),
            )
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(legacy.Style.BG))
            painter.drawRoundedRect(
                self.rect(), legacy.Style.RAD_L, legacy.Style.RAD_L,
            )
        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_resize_handles"):
            self._resize_handles.reposition()
        self.update()



class PolishedBuildDialog(AssetFramedBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.step_context.clear()
        self.step_context.hide()
        self.step_context.setMaximumHeight(0)

        old_gems = self.gem_links
        gem_layout = old_gems.parentWidget().layout()
        index = gem_layout.indexOf(old_gems)
        gem_layout.removeWidget(old_gems)
        old_gems.deleteLater()
        self.gem_links = PoedbGemChains()
        self.gem_links.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.gem_links.body.setStyleSheet("background:rgba(2,4,4,0.38);")
        gem_layout.insertWidget(index, self.gem_links, 1)
        self._configure_client_monitor()
        self.reload()

    def _configure_client_monitor(self):
        self.monitor._timer.stop()
        configured = str(self.overlay.settings.get("poe1_client_path", "")).strip()
        self.monitor.path = Path(configured) if configured else find_client_log()
        self.monitor._position = 0
        self.monitor.start()



class ExplicitRouteBuildDialog(PolishedBuildDialog):
    def __init__(self, overlay):
        self._v36_ready = False
        self._mastery_focus_key = None
        super().__init__(overlay)

        old_tree = self.tree_canvas
        tree_layout = old_tree.parentWidget().layout()
        tree_index = tree_layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        tree_layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = ExplicitProgressionTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        tree_layout.insertWidget(tree_index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._v36_ready = True
        self.reload()

    def _render_tree(self, build, level):
        super()._render_tree(build, level)
        if not self._v36_ready:
            return
        next_mastery = getattr(self.tree_canvas, "next_mastery", None)
        focus_key = (level, next_mastery)
        if next_mastery and focus_key != self._mastery_focus_key:
            self._mastery_focus_key = focus_key
            QTimer.singleShot(0, self.tree_canvas.fit_upcoming)



class EditableBuildDialog(ExplicitRouteBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.editor_button = QPushButton("Редактор")
        self.editor_button.setCursor(Qt.PointingHandCursor)
        self.editor_button.setToolTip("Вручную выбрать пассивы и этапы связок камней")
        self.editor_button.clicked.connect(self._open_manual_editor)
        self.editor_button.setStyleSheet("""
            QPushButton {background:rgba(91,64,24,.24); color:#d8bd7a;
                border:1px solid rgba(190,145,69,.56); border-radius:5px; padding:5px 11px;}
            QPushButton:hover {background:rgba(122,83,30,.32); color:#f0dfb9; border-color:#d1a85d;}
        """)
        row = _layout_with_widget(self.layout(), self.profile_combo)
        if row is not None:
            row.addWidget(self.editor_button)

    def _open_manual_editor(self):
        editor = ManualBuildEditor(self.overlay, self)
        if editor.exec_():
            self._tree_initialized = False
            self._focused_stage_key = None
            self._mastery_focus_key = None
            self.reload()



class ExactManualBuildDialog(EditableBuildDialog):
    def __init__(self, overlay):
        self._manual_plan_ready = False
        super().__init__(overlay)
        self._manual_plan_ready = True
        self._manual_focus_key = None
        self._tree_initialized = False
        self.reload()

    def _render_tree(self, build, level):
        if not self._manual_plan_ready or not build or build.get("format") != "actpilot-manual-v1":
            return super()._render_tree(build, level)

        plan = manual_passive_plan(build, level)
        target = plan["target"]
        is_mastery = lambda node: self.tree_canvas.nodes.get(str(node), {}).get("isMastery")
        completed_mastery = [node for node in plan["completed"] if is_mastery(node)]
        completed_regular = [node for node in plan["completed"] if not is_mastery(node)]
        immediate = plan["upcoming"][:1]
        next_mastery = immediate[0] if immediate and is_mastery(immediate[0]) else None
        immediate_regular = [] if next_mastery is not None else immediate
        visible_plan = completed_regular + immediate_regular

        old_center, old_scale = self.tree_canvas.center, self.tree_canvas.scale
        self.tree_canvas.set_quest_progression(
            visible_plan, completed_regular, immediate_regular,
            plan["node_levels"], plan["node_markers"],
        )
        self.tree_canvas.set_masteries(target.get("masteries", ""))
        self.tree_canvas.set_mastery_progression(completed_mastery, next_mastery)
        self.tree_canvas.set_ascendancy_build(build, level)
        self.ascendancy_button.setEnabled(bool(self.tree_canvas.ascendancy.get("nodes")))
        if self._tree_initialized:
            self.tree_canvas.center, self.tree_canvas.scale = old_center, old_scale
            self.tree_canvas.update()
        else:
            self._tree_initialized = True

        first = immediate[0] if immediate else None
        first_name = self.tree_canvas.nodes.get(str(first), {}).get("name", "этап завершён") if first else "этап завершён"
        used = len(plan["completed"]) - 1
        total = len(plan["planned"]) - 1
        self.tree_stage_label.setText(
            f"Ручной билд · уровень {level} · {used}/{total} · дальше: {first_name}"
        )
        focus_key = (level, str(first or ""))
        if first and focus_key != self._manual_focus_key:
            self._manual_focus_key = focus_key
            QTimer.singleShot(0, self.tree_canvas.fit_upcoming)



class StableEditorBuildDialog(ExactManualBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        # Replace the preceding editor button so there is always exactly one
        # entry point, bound to the latest editor implementation.
        old = self.editor_button
        row = _layout_with_widget(self.layout(), old)
        if row is not None:
            row.removeWidget(old)
        old.deleteLater()
        self.editor_button = QPushButton("Редактор")
        self.editor_button.setCursor(Qt.PointingHandCursor)
        self.editor_button.setToolTip("Настроить пассивы и наборы камней по уровню")
        self.editor_button.clicked.connect(self._open_manual_editor)
        self.editor_button.setStyleSheet("""
            QPushButton {background:rgba(91,64,24,.24); color:#d8bd7a;
                border:1px solid rgba(190,145,69,.56); border-radius:5px; padding:5px 11px;}
            QPushButton:hover {background:rgba(122,83,30,.32); color:#f0dfb9; border-color:#d1a85d;}
        """)
        if row is not None:
            row.addWidget(self.editor_button)

    def _open_manual_editor(self):
        editor = ManualBuildEditor(self.overlay, self)
        if editor.exec_():
            self._tree_initialized = False
            self._focused_stage_key = None
            self._mastery_focus_key = None
            self._manual_focus_key = None
            self.reload()



class ClearGemEditorBuildDialog(StableEditorBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        old_tree = self.tree_canvas
        layout = old_tree.parentWidget().layout()
        index = layout.indexOf(old_tree)
        selected_masteries = dict(old_tree.selected_masteries)
        layout.removeWidget(old_tree)
        old_tree.deleteLater()
        self.tree_canvas = ZoomSafeTreeCanvas()
        self.tree_canvas.selected_masteries = selected_masteries
        layout.insertWidget(index, self.tree_canvas, 1)
        try:
            self.ascendancy_button.clicked.disconnect()
        except TypeError:
            pass
        self.ascendancy_button.clicked.connect(self.tree_canvas.fit_ascendancy)
        self._tree_initialized = False
        self._focused_stage_key = None
        self._mastery_focus_key = None
        self._manual_focus_key = None
        self.reload()

    def _open_manual_editor(self):
        editor = ManualBuildEditor(self.overlay, self)
        if editor.exec_():
            self._tree_initialized = False
            self._focused_stage_key = None
            self._mastery_focus_key = None
            self._manual_focus_key = None
            self.reload()



class ReliableClientBuildDialog(ClearGemEditorBuildDialog):
    def _on_level_seen(self, character_name, character_class, level):
        profile = self.overlay.active_profile()
        bound_name = str(profile.get("log_character_name", "")).strip()
        if bound_name and character_name.casefold() != bound_name.casefold():
            return

        build = profile.get("build") or {}
        profile_name = str(profile.get("name", "")).strip()
        same_profile_name = profile_name.casefold() == character_name.casefold()
        compatible_class = class_matches(
            str(build.get("class", "")),
            str(build.get("ascendancy", "")),
            character_class,
        )
        if not bound_name and not same_profile_name and not compatible_class:
            return

        profile["log_character_name"] = character_name
        new_level = clamp_level(level)
        if profile.get("level") != new_level:
            profile["level"] = new_level
            self.overlay.save_profiles()
            self.refresh_level()
        else:
            self.overlay.save_profiles()
        self.log_status.setText(
            f"Client.txt: {character_name} ({character_class}) · уровень {new_level}"
        )



class FastBuildDialog(ReliableClientBuildDialog):
    def __init__(self, overlay):
        self._fast_construction_complete = False
        super().__init__(overlay)
        self._fast_construction_complete = True
        # Every inherited constructor attempted to reload. They were deferred,
        # so populate the fully assembled window exactly once now.
        super().reload()

    def reload(self):
        if not self._fast_construction_complete:
            return
        return super().reload()

    def refresh_level(self):
        if not self._fast_construction_complete:
            return
        return super().refresh_level()

    def closeEvent(self, event):
        # Keep the parsed tree and widgets alive. Reopening is then immediate.
        self.hide()
        event.ignore()



class FixedInteractionBuildDialog(FastBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.sync_window_opacity()

    def sync_window_opacity(self):
        self.setWindowOpacity(1.0)

    def reload(self):
        result = super().reload()
        if getattr(self, "_fast_construction_complete", False):
            self.sync_window_opacity()
        return result

    def showEvent(self, event):
        self.sync_window_opacity()
        super().showEvent(event)



import actpilot.profiles as base
from actpilot.profiles import PobImportDialog, button_style
import actpilot.build_dialog as fallback_renderer
import actpilot.tree_graphs as per_level
import actpilot.tree_graphs as v3

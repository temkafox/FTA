"""PoE 1 overlay with a tiny always-visible passive route preview."""

from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QTimer

import main as legacy
import release_poe1_v48 as staged_release
import release_poe1_v50 as previous
from poe1_builds import clamp_level
from poe1_client_log_v2 import class_matches
from poe1_client_monitor_v3 import ClientLevelMonitor
from poe1_mini_tree import MiniPassiveRoute


class MiniTreeOverlay(staged_release.previous.FixedInteractionOverlay):
    def __init__(self):
        super().__init__()
        self.mini_tree = MiniPassiveRoute(self.body)
        body_layout = self.body.layout()
        body_layout.insertWidget(body_layout.indexOf(self.content), self.mini_tree)
        self.mini_tree.activated.connect(self._open_build_progress)

        self._mini_signature = None
        self._mini_refresh_timer = QTimer(self)
        self._mini_refresh_timer.setInterval(1200)
        self._mini_refresh_timer.timeout.connect(self._refresh_mini_tree)
        self._mini_refresh_timer.start()

        self._mini_monitor = None
        self._configure_mini_monitor()
        self._refresh_mini_tree(force=True)
        self._apply_welcome_visibility()

    def _configure_mini_monitor(self):
        if self._mini_monitor is not None:
            self._mini_monitor._timer.stop()
            self._mini_monitor.deleteLater()
        configured = str(self.settings.get("poe1_client_path", "")).strip()
        path = Path(configured) if configured else None
        self._mini_monitor = ClientLevelMonitor(self, path)
        self._mini_monitor.level_seen.connect(self._on_mini_level_seen)
        self._mini_monitor.start()

    def _on_mini_level_seen(self, character_name, character_class, level):
        profile = self.active_profile()
        bound_name = str(profile.get("log_character_name", "")).strip()
        if bound_name and character_name.casefold() != bound_name.casefold():
            return
        build = profile.get("build") or {}
        profile_name = str(profile.get("name", "")).strip()
        same_name = profile_name.casefold() == character_name.casefold()
        compatible = class_matches(
            str(build.get("class", "")),
            str(build.get("ascendancy", "")),
            character_class,
        )
        if not bound_name and not same_name and not compatible:
            return
        profile["log_character_name"] = character_name
        new_level = clamp_level(level)
        changed = int(profile.get("level", 1)) != new_level
        profile["level"] = new_level
        self.save_profiles()
        if changed:
            self._refresh_mini_tree(force=True)
            if self._build_dialog is not None:
                self._build_dialog.refresh_level()

    def _profile_signature(self):
        profile = self.active_profile()
        build = profile.get("build") or {}
        state = build.get("manual_editor") or {}
        stages = state.get("passive_stages") or []
        route = tuple(
            (int(stage.get("level", 1)), tuple(map(str, stage.get("allocation_order", []))))
            for stage in stages
        )
        if not route:
            route = (tuple(map(str, state.get("allocation_order", []))),)
        return profile.get("id"), int(profile.get("level", 1)), route

    def _refresh_mini_tree(self, force=False):
        signature = self._profile_signature()
        if not force and signature == self._mini_signature:
            return
        self._mini_signature = signature
        profile = self.active_profile()
        self.mini_tree.set_build_level(
            profile.get("build") or {}, int(profile.get("level", 1))
        )
        self._apply_welcome_visibility()

    def _apply_welcome_visibility(self):
        super()._apply_welcome_visibility()
        if hasattr(self, "mini_tree"):
            has_route = bool(self.mini_tree._visible_nodes)
            self.mini_tree.setVisible(
                self.game == legacy.GAME_POE1 and self.content.isVisible() and has_route
            )

    def _interactive_widgets(self):
        widgets = super()._interactive_widgets()
        if hasattr(self, "mini_tree"):
            widgets.append(self.mini_tree)
        return widgets

    def create_profile(self, name):
        super().create_profile(name)
        self._refresh_mini_tree(force=True)

    def switch_profile(self, profile_id):
        super().switch_profile(profile_id)
        self._refresh_mini_tree(force=True)

    def _settings(self):
        old_path = str(self.settings.get("poe1_client_path", "")).strip()
        super()._settings()
        new_path = str(self.settings.get("poe1_client_path", "")).strip()
        if old_path != new_path:
            self._configure_mini_monitor()

    def _switch_game(self, game):
        super()._switch_game(game)
        if hasattr(self, "mini_tree"):
            self._refresh_mini_tree(force=True)

    def _open_build_progress(self):
        previous.editor_release.ManualBuildEditor = previous.ManualBuildEditor
        super()._open_build_progress()


def main():
    previous.editor_release.ManualBuildEditor = previous.ManualBuildEditor
    app = legacy.QApplication.instance()
    if app is None:
        return previous.main()
    window = MiniTreeOverlay()
    window.show()
    return window


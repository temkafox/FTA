"""Manual editor with a useful planning budget and separate live character level."""

from __future__ import annotations

from poe1_manual_build_v3 import ascendancy_budget, build_from_state, passive_budget
from poe1_manual_editor_v5 import ManualBuildEditor as PreviousManualBuildEditor


DEFAULT_PLAN_LEVEL = 100


class ManualBuildEditor(PreviousManualBuildEditor):
    def __init__(self, overlay, parent=None):
        super().__init__(overlay, parent)
        self.setWindowOpacity(1.0)

        # A brand-new manual build used to inherit character level 1, giving a
        # 0/0 budget and making the tree appear broken. The editor describes
        # the finished route; the live profile level controls its playback.
        has_route = bool(
            self.state.get("passives")
            or self.state.get("masteries")
            or self.state.get("ascendancy_nodes")
        )
        if not has_route and int(self.state.get("level", 1)) <= 1:
            self.target_level.setValue(DEFAULT_PLAN_LEVEL)
            self.state["level"] = DEFAULT_PLAN_LEVEL
            self._refresh_tree(first=True)
            self.message.setText(
                "Выберите подсвеченную соседнюю ноду. Целевой уровень задаёт бюджет плана, "
                "а текущий уровень персонажа меняется отдельно."
            )

    def _save(self):
        used = len(self.state["passives"]) + len(self.state["masteries"])
        target = self.target_level.value()
        if used > passive_budget(target):
            return self._flash(
                "Выбрано больше пассивов, чем доступно на целевом уровне"
            )
        if len(self.state["ascendancy_nodes"]) > ascendancy_budget(target):
            return self._flash(
                "Выбрано больше очков восхождения, чем доступно на целевом уровне"
            )

        # Do not turn the live character into level 100 merely because the
        # user planned a level-100 tree.
        live_level = self.profile.get("level", 1)
        self.state["level"] = target
        self.profile["build"] = build_from_state(self.state)
        self.profile["level"] = live_level
        self.overlay.save_profiles()
        self.accept()


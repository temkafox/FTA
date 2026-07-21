"""Ascendancy renderer with the free class start treated as completed."""

from poe1_ascendancy_widget import AscendancyProgressWidget


class ConnectedAscendancyProgressWidget(AscendancyProgressWidget):
    def set_build(self, build, level):
        super().set_build(build, level)
        plan = dict(self.canvas.plan)
        nodes = list(plan.get("nodes", []))
        if nodes:
            completed = list(plan.get("completed", []))
            if nodes[0] not in completed:
                completed.insert(0, nodes[0])
            plan["completed"] = completed
            self.canvas.set_plan(plan)

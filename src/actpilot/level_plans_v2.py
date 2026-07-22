"""Corrected milestone selection for overlapping PoB gem ranges."""

from actpilot.builds import clamp_level
from actpilot.level_plans import passive_plan, range_bounds


def stage_at_level(stages, level):
    if not stages:
        return None
    level = clamp_level(level)
    eligible = [
        (clamp_level(stage.get("level", 1)), index, stage)
        for index, stage in enumerate(stages)
        if clamp_level(stage.get("level", 1)) <= level
    ]
    if eligible:
        return max(eligible, key=lambda item: (item[0], item[1]))[2]
    ranged = []
    for index, stage in enumerate(stages):
        bounds = range_bounds(stage)
        if bounds and bounds[0] <= level <= bounds[1]:
            ranged.append((bounds[0], index, stage))
    if ranged:
        return max(ranged, key=lambda item: (item[0], item[1]))[2]
    return min(
        enumerate(stages),
        key=lambda item: (clamp_level(item[1].get("level", 1)), item[0]),
    )[1]

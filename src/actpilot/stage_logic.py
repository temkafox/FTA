"""Stage ordering helpers for range-named Path of Building leveling specs."""

from actpilot.progression import range_bounds


def previous_stage(stages, current):
    bounds = range_bounds(current)
    if bounds:
        start, _ = bounds
        ranged = []
        for stage in stages:
            other = range_bounds(stage)
            if stage is not current and other and other[1] < start:
                ranged.append((other[1], stage))
        if ranged:
            return max(ranged, key=lambda item: item[0])[1]
        return None
    candidates = [
        stage for stage in stages
        if stage is not current and stage.get("level", 1) < current.get("level", 1)
    ]
    return max(candidates, key=lambda stage: stage.get("level", 1)) if candidates else None

"""Final respec-aware per-level interpolation for PoB passive stages."""

from poe1_builds import clamp_level
from poe1_progression import connected_addition_order, range_bounds


def nodes_at_level(stage, previous_nodes, level, graph):
    target = [str(node) for node in stage.get("nodes", [])]
    target_set = set(target)
    previous_common = [str(node) for node in previous_nodes if str(node) in target_set]
    bounds = range_bounds(stage)
    additions = connected_addition_order(previous_common, target, graph)
    if not bounds:
        return target, additions
    start, end = bounds
    level = clamp_level(level)

    def count_for(value):
        if value < start:
            return 0
        if value >= end:
            return len(additions)
        progress = (value - start + 1) / max(1, end - start + 1)
        return max(1, min(len(additions), round(len(additions) * progress)))

    current_count = count_for(level)
    prior_count = count_for(level - 1)
    return (
        previous_common + additions[:current_count],
        additions[prior_count:current_count],
    )

"""Book-only passive progression; bandit rewards are intentionally excluded."""

from poe1_level_plan_v5 import quest_aware_passive_plan


def book_only_passive_plan(stages, level, graph):
    return quest_aware_passive_plan(
        stages, level, graph, kill_all_bandits=False
    )

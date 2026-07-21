"""Official Russian passive text while preserving English node names."""

from __future__ import annotations

import copy

import poe1_ru_text as previous


DATA = previous.DATA


def localized_node(node):
    result = copy.deepcopy(node)
    record = DATA.get("nodes", {}).get(str(node.get("_id", "")), {})
    if record.get("stats"):
        result["stats"] = record["stats"]

    official_masteries = record.get("masteryEffects", {})
    effects = []
    for effect in node.get("masteryEffects", []):
        localized = dict(effect)
        effect_id = str(effect.get("effect", effect.get("id", "")))
        if official_masteries.get(effect_id):
            localized["stats"] = official_masteries[effect_id]
        else:
            localized["stats"] = [
                previous.translate_stat_fallback(line)
                for line in effect.get("stats", [])
            ]
        effects.append(localized)
    result["masteryEffects"] = effects
    return result


gem_description = previous.gem_description

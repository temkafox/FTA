"""Пересборка data/poe1/gem_acquisition.json из данных exile-leveling: награды за квесты и торговцы по классам.

Запуск: .venv/bin/python tools/update_gem_acquisition.py [--ref <commit>] [--source <каталог с json>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "actpilot" / "data" / "poe1" / "gem_acquisition.json"
REPO = "HeartofPhos/exile-leveling"
DEFAULT_REF = "b7b2dd0ed62ae25cf55c74085fa64a1f4d7cf4ba"
FILES = ("quests", "gems", "characters")
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/common/data/json/{name}.json"
START_KINDS = ("start", "chest")


def fetch(ref: str, source: str | None = None) -> dict:
    result = {}
    for name in FILES:
        if source:
            text = (Path(source) / f"{name}.json").read_text(encoding="utf-8")
        else:
            url = RAW_URL.format(repo=REPO, ref=ref, name=name)
            request = urllib.request.Request(url, headers={"User-Agent": "ActPilot gem data updater"})
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8")
        result[name] = json.loads(text)
    return result


def gem_names(gems: dict) -> dict:
    # У одного камня бывает несколько id (Arctic Armour), а id с Royale — отдельный режим, не кампания
    return {
        gem_id: info["name"]
        for gem_id, info in gems.items()
        if info.get("name") and "Royale" not in gem_id
    }


def convert(quests: dict, gems: dict, characters: dict, ref: str) -> dict:
    names = gem_names(gems)
    display = {name.casefold(): name for name in names.values()}
    classes = sorted(characters)

    def expand(raw):
        # Пустой список классов в exile-leveling означает «все классы»
        return sorted(set(raw)) if raw else list(classes)

    quest_list = []
    for quest in quests.values():
        offers = []
        for offer in (quest.get("reward_offers") or {}).values():
            rewards, vendor = {}, {}
            for gem_id, info in (offer.get("quest") or {}).items():
                name = names.get(gem_id)
                if name:
                    key = name.casefold()
                    rewards[key] = sorted(set(rewards.get(key, [])) | set(expand(info.get("classes"))))
            for gem_id, info in (offer.get("vendor") or {}).items():
                name = names.get(gem_id)
                if name:
                    entry = vendor.setdefault(name.casefold(), {"npc": info.get("npc", ""), "classes": []})
                    entry["classes"] = sorted(set(entry["classes"]) | set(expand(info.get("classes"))))
            if rewards or vendor:
                offers.append({"npc": offer.get("quest_npc", ""), "rewards": rewards, "vendor": vendor})
        if offers:
            quest_list.append(
                {"id": quest["id"], "act": int(quest["act"]), "name": quest["name"], "offers": offers}
            )

    start_gems = {}
    for class_name, info in characters.items():
        kinds = {}
        for kind in START_KINDS:
            name = names.get(info.get(f"{kind}_gem_id"))
            if name:
                kinds[kind] = name.casefold()
        start_gems[class_name] = kinds

    index = {}

    def add(key, class_name, kind, entry):
        record = index.setdefault(key, {"name": display.get(key, key), "classes": {}})
        ways = record["classes"].setdefault(class_name, {"quest": [], "vendor": []})
        if entry not in ways[kind]:
            ways[kind].append(entry)

    for quest in quest_list:
        for offer in quest["offers"]:
            for key, reward_classes in offer["rewards"].items():
                for class_name in reward_classes:
                    add(key, class_name, "quest", {"act": quest["act"], "quest": quest["name"]})
            for key, info in offer["vendor"].items():
                for class_name in info["classes"]:
                    add(key, class_name, "vendor",
                        {"act": quest["act"], "quest": quest["name"], "npc": info["npc"]})

    return {
        "format": 2,
        "source": {"repo": f"https://github.com/{REPO}", "ref": ref, "license": "MIT"},
        "classes": classes,
        "start_gems": start_gems,
        "quests": quest_list,
        "gems": index,
    }


def _ways(record: dict) -> set:
    result = set()
    for class_name, ways in (record or {}).get("classes", {}).items():
        for kind, entries in ways.items():
            for entry in entries:
                result.add((class_name, kind, entry.get("act"), entry.get("quest"), entry.get("npc", "")))
    return result


def report(old: dict, new: dict) -> list[str]:
    old_gems, new_gems = old.get("gems", {}), new["gems"]
    added = sorted(set(new_gems) - set(old_gems))
    removed = sorted(set(old_gems) - set(new_gems))
    changed = sorted(
        key for key in set(old_gems) & set(new_gems) if _ways(old_gems[key]) != _ways(new_gems[key])
    )
    return [
        f"квестов: {len(new['quests'])}, камней: {len(new_gems)}",
        f"новые камни ({len(added)}): {', '.join(added)}",
        f"пропали ({len(removed)}): {', '.join(removed)}",
        f"изменились источники ({len(changed)}): {', '.join(changed[:40])}{' …' if len(changed) > 40 else ''}",
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default=DEFAULT_REF, help="коммит или ветка exile-leveling")
    parser.add_argument("--source", help="каталог с quests.json, gems.json, characters.json вместо загрузки")
    parser.add_argument("--dry-run", action="store_true", help="только отчёт, без записи файла")
    args = parser.parse_args(argv)

    raw = fetch(args.ref, args.source)
    data = convert(raw["quests"], raw["gems"], raw["characters"], args.ref)
    old = json.loads(TARGET.read_text(encoding="utf-8")) if TARGET.exists() else {}
    for line in report(old, data):
        print(line)
    if not args.dry_run:
        TARGET.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"записано: {TARGET} ({TARGET.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

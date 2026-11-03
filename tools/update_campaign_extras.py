"""Пересборка data/poe1/campaign_extras.json — необязательное по актам: рецепты верстака, тайники, прочее.

Рецепты берутся из areas.json exile-leveling, русские названия зон — с poedb.tw/ru.
Запуск: .venv/bin/python tools/update_campaign_extras.py [--ref <commit>] [--source <каталог с areas.json>]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "actpilot" / "data" / "poe1" / "campaign_extras.json"
REPO = "HeartofPhos/exile-leveling"
DEFAULT_REF = "b7b2dd0ed62ae25cf55c74085fa64a1f4d7cf4ba"
AREAS_URL = "https://raw.githubusercontent.com/{repo}/{ref}/common/data/json/areas.json"
POEDB_RU = "https://poedb.tw/ru/{slug}"
USER_AGENT = "ActPilot campaign extras updater"

# Лабиринт проходится в актах 4/8/10 маршрута, а не в акте зоны; убер-лабиринт — уже не кампания
LABYRINTH_ACT = {"1_Labyrinth_boss_3": 4, "2_Labyrinth_boss_3": 8, "3_Labyrinth_boss_3": 10}
SKIP_AREAS = {"EndGame_Labyrinth_boss_3"}
EPILOGUE_ACT = 10

RECIPE_FAMILIES = {
    "Accuracy": "Меткость",
    "Ailment, Stun and Curse Mitigation": "Защита от состояний, оглушения и проклятий",
    "All Attributes": "Все характеристики",
    "All Resistances": "Сопротивление всем стихиям",
    "Attack and Cast Speed": "Скорость атаки и чар",
    "Attack, Cast and Warcry Speed": "Скорость атаки, чар и кличей",
    "Attributes": "Характеристики",
    "Chaos Damage": "Урон хаосом",
    "Cold Damage": "Урон от холода",
    "Damage over Time": "Урон со временем",
    "Defences": "Защита",
    "Double Resistances": "Два сопротивления",
    "Elemental Damage with Attacks": "Урон стихиями от атак",
    "Elemental Resistances": "Сопротивление стихиям",
    "Fire Damage": "Урон от огня",
    "Flask Duration": "Длительность флаконов",
    "Life and Mana": "Здоровье и мана",
    "Life and Mana Regeneration": "Регенерация здоровья и маны",
    "Lightning Damage": "Урон от молнии",
    "Mana Regen": "Регенерация маны",
    "Minions": "Приспешники",
    "Movement Speed": "Скорость передвижения",
    "Movement Speed and Exerted Attacks": "Скорость передвижения и усиленные атаки",
    "Movement Speed and Flask Enchantments": "Скорость передвижения и зачарования флаконов",
    "Physical Damage": "Физический урон",
    "Socket Colours": "Цвета гнёзд",
    "Socket Links": "Связи гнёзд",
    "Socket Numbers": "Число гнёзд",
    "Spell Damage": "Урон от чар",
    "Traps and Mines": "Ловушки и мины",
    "Trigger a Socketed Spell when you Use a Skill or Focus": "Срабатывание чар из гнезда при использовании умения (Trigger)",
    "Vaal Skill Damage": "Урон умений Ваал",
}
RECIPE_DETAILS = (
    (re.compile(r"^Rank (\d+)$"), r"ранг \1"),
    (re.compile(r"^(\d+) to (\d+) Linked Sockets$"), r"\1–\2 связанных гнезда"),
    (re.compile(r"^(\d+) to (\d+) Sockets$"), r"\1–\2 гнезда"),
)

MANUAL_EXTRAS = {
    1: [
        {"kind": "optional", "text": "ТЮРЕМНЫЕ ПОМЕЩЕНИЯ: Chemist's Strongbox — значок на миникарте, "
                                     "открывается рычагом рядом; часто ртутный флакон"},
    ],
    7: [
        {"kind": "optional", "text": "РАЗРУШЕННЫЙ МОСТ: серебряный медальон (Silver Locket) у сломанного вп "
                                     "по дороге — сдаем Вейламу после Малигаро, награда — флакон"},
        {"kind": "secret", "text": "ОБИТЕЛЬ ГРЕХОВ — УРОВЕНЬ 2, испытание: рычаг спрятан за табличкой испытания — "
                                   "тайник с камнем с качеством"},
        {"kind": "optional", "text": "ХРАМ РАЗЛОЖЕНИЯ — УРОВЕНЬ 1: в комнате с ямой в центре слева внизу или справа вверху — "
                                     "боковая комната с осквернённым уником"},
    ],
    9: [
        {"kind": "secret", "text": "ТОННЕЛЬ, испытание: скрытый рычаг на полпути к табличке, в углу напротив входа — "
                                   "тайник с трансфигурированным камнем"},
    ],
    10: [
        {"kind": "secret", "text": "КОСТНИЦА, испытание: рычаг перед зигзагообразными стенами, затем на "
                                   "противоположную сторону — тайник с Facetor's Lens"},
    ],
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read().decode("utf-8", errors="replace")
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2)
    return ""


def russian_area_name(english: str) -> str | None:
    slug = re.sub(r"[^A-Za-z0-9_]", "", english.replace(" ", "_"))
    page = fetch_text(POEDB_RU.format(slug=slug))
    time.sleep(0.7)
    match = re.search(r"<title>(.*?)</title>", page, re.S)
    if not match:
        return None
    title = html.unescape(match.group(1)).split(" - PoEDB")[0].strip()
    # Склоняемые названия приходят как «<if:gen>{Каменоломни}<else>{Каменоломня}» — нужен последний вариант
    variants = re.findall(r"\{([^}]*)\}", title)
    name = variants[-1] if variants else title
    return name.strip() or None


def translate_recipe(recipe: str) -> tuple[str, bool]:
    family, _, detail = recipe.partition(" - ")
    family_ru = RECIPE_FAMILIES.get(family)
    if family_ru is None:
        return recipe, False
    if not detail:
        return family_ru, True
    for pattern, replacement in RECIPE_DETAILS:
        if pattern.match(detail):
            return f"{family_ru}, {pattern.sub(replacement, detail)}", True
    return f"{family_ru}, {detail}", False


def _route_order(area_id: str) -> tuple:
    # Номера в id зоны идут по ходу акта; лабиринт в маршруте — после зон акта
    numbers = tuple(int(part) for part in re.findall(r"\d+", area_id))
    return (1 if area_id in LABYRINTH_ACT else 0, numbers)


def area_act(area_id: str, area: dict) -> int | None:
    if area_id in LABYRINTH_ACT:
        return LABYRINTH_ACT[area_id]
    act = int(area.get("act") or 0)
    if act == 11:
        return EPILOGUE_ACT
    return act if 1 <= act <= 10 else None


def build_extras(areas: dict, area_names: dict, ref: str) -> tuple[dict, list[str]]:
    acts = {act: [] for act in range(1, 11)}
    problems = []
    for area_id, area in sorted(areas.items(), key=lambda item: _route_order(item[0])):
        recipes = area.get("crafting_recipes") or []
        if not recipes or area_id in SKIP_AREAS:
            continue
        act = area_act(area_id, area)
        if act is None:
            problems.append(f"акт не определён: {area_id}")
            continue
        if area_id in LABYRINTH_ACT:
            place = "ЛАБИРИНТ (сокровищница Изаро)"
        else:
            place = (area_names.get(area["name"]) or area["name"]).upper()
            if area["name"] not in area_names:
                problems.append(f"нет русского названия: {area['name']}")
        for recipe in recipes:
            text, translated = translate_recipe(recipe)
            if not translated:
                problems.append(f"рецепт не переведён: {recipe}")
            acts[act].append({"kind": "recipe", "text": f"{place}: {text}"})
    for act, items in MANUAL_EXTRAS.items():
        acts[act].extend(items)
    payload = {
        "format": 1,
        "source": {"repo": f"https://github.com/{REPO}", "ref": ref, "license": "MIT"},
        "acts": {f"Act {act}": items for act, items in acts.items() if items},
    }
    return payload, problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ref", default=DEFAULT_REF, help="коммит или ветка exile-leveling")
    parser.add_argument("--source", help="каталог с areas.json вместо загрузки")
    args = parser.parse_args(argv)

    if args.source:
        areas = json.loads((Path(args.source) / "areas.json").read_text(encoding="utf-8"))
    else:
        areas = json.loads(fetch_text(AREAS_URL.format(repo=REPO, ref=args.ref)))
    wanted = sorted({
        area["name"] for area_id, area in areas.items()
        if area.get("crafting_recipes") and area_id not in SKIP_AREAS and area_id not in LABYRINTH_ACT
    })
    area_names = {}
    for name in wanted:
        russian = russian_area_name(name)
        if russian:
            area_names[name] = russian
    payload, problems = build_extras(areas, area_names, args.ref)
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"записано: {TARGET} ({sum(len(v) for v in payload['acts'].values())} пунктов)")
    for line in problems:
        print("!", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

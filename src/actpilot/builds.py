"""PoE 1 character profiles and Path of Building import helpers."""

from __future__ import annotations

import base64
import copy
import re
import uuid
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path


PROFILE_VERSION = 1
LEVEL_MIN = 1
LEVEL_MAX = 100


class PobImportError(ValueError):
    pass


def clamp_level(value) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = LEVEL_MIN
    return max(LEVEL_MIN, min(LEVEL_MAX, value))


def level_from_title(title: str, fallback: int | None = None) -> int | None:
    title = title or ""
    patterns = (
        r"(?:level|lvl|lev|уров(?:ень|ня)?|ур\.?)[\s:_-]*(\d{1,3})",
        r"(?:^|\D)(\d{1,3})(?:\s*(?:points?|pts?|пассив|очк)|\s*$)",
    )
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return clamp_level(match.group(1))
    return clamp_level(fallback) if fallback is not None else None


def decode_pob_xml(source: str) -> str:
    raw = (source or "").strip()
    if not raw:
        raise PobImportError("Вставьте код Path of Building или XML билда.")
    if raw.startswith("<"):
        return raw
    if re.match(r"https?://", raw, re.IGNORECASE):
        raise PobImportError(
            "Ссылки pobb.in требуют загрузки из сети. В Path of Building выберите "
            "Export Build и вставьте полный код экспорта."
        )
    compact = re.sub(r"\s+", "", raw).replace("-", "+").replace("_", "/")
    compact += "=" * (-len(compact) % 4)
    try:
        packed = base64.b64decode(compact)
        try:
            unpacked = zlib.decompress(packed)
        except zlib.error:
            unpacked = zlib.decompress(packed, -zlib.MAX_WBITS)
        return unpacked.decode("utf-8-sig")
    except Exception as exc:
        raise PobImportError("Не удалось распаковать код Path of Building.") from exc


def _node_ids(spec: ET.Element) -> list[int]:
    values = []
    raw = spec.get("nodes", "")
    for value in re.findall(r"\d+", raw):
        node_id = int(value)
        if node_id not in values:
            values.append(node_id)
    return values


def _gem_name(gem: ET.Element) -> str:
    return (
        gem.get("nameSpec")
        or gem.get("name")
        or gem.get("skillId")
        or gem.get("gemId")
        or "Unknown gem"
    )


def _parse_skill_set(skill_set: ET.Element, fallback_level: int) -> dict:
    title = skill_set.get("title") or skill_set.get("label") or "Набор камней"
    links = []
    for index, skill in enumerate(skill_set.findall("Skill"), 1):
        if skill.get("enabled", "true").lower() == "false":
            continue
        gems = []
        for gem in skill.findall("Gem"):
            if gem.get("enabled", "true").lower() == "false":
                continue
            gems.append(
                {
                    "name": _gem_name(gem),
                    "support": gem.get("support", "false").lower() == "true",
                    "level": gem.get("level"),
                    "quality": gem.get("quality"),
                }
            )
        if not gems:
            continue
        label = skill.get("label") or skill.get("slot") or f"Связка {index}"
        links.append({"label": label, "gems": gems})
    return {
        "level": level_from_title(title, fallback_level),
        "title": title,
        "links": links,
    }


def parse_pob(source: str) -> dict:
    xml_text = decode_pob_xml(source)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise PobImportError(f"Некорректный XML Path of Building: {exc}") from exc
    if root.tag != "PathOfBuilding":
        raise PobImportError("Это не экспорт Path of Building.")

    build = root.find("Build")
    build_level = clamp_level(build.get("level", 1) if build is not None else 1)
    class_name = build.get("className", "") if build is not None else ""
    ascendancy = build.get("ascendClassName", "") if build is not None else ""
    build_name = ""
    notes = root.findtext("Notes", default="").strip()
    if notes:
        build_name = notes.splitlines()[0][:80]

    trees = []
    tree = root.find("Tree")
    if tree is not None:
        specs = tree.findall("Spec")
        for index, spec in enumerate(specs, 1):
            title = spec.get("title") or f"Дерево {index}"
            fallback = build_level if len(specs) == 1 else min(100, max(1, index * 10))
            trees.append(
                {
                    "level": level_from_title(title, fallback),
                    "title": title,
                    "tree_version": spec.get("treeVersion", ""),
                    "nodes": _node_ids(spec),
                    "masteries": spec.get("masteryEffects", ""),
                }
            )

    gem_sets = []
    skills = root.find("Skills")
    if skills is not None:
        sets = skills.findall("SkillSet")
        if sets:
            for index, skill_set in enumerate(sets, 1):
                fallback = build_level if len(sets) == 1 else min(100, max(1, index * 10))
                gem_sets.append(_parse_skill_set(skill_set, fallback))
        else:
            synthetic = ET.Element("SkillSet", {"title": "Основные связки"})
            for skill in skills.findall("Skill"):
                synthetic.append(copy.deepcopy(skill))
            gem_sets.append(_parse_skill_set(synthetic, build_level))

    trees.sort(key=lambda item: (item["level"], item["title"]))
    gem_sets.sort(key=lambda item: (item["level"], item["title"]))
    if not trees and not gem_sets:
        raise PobImportError("В билде не найдены дерево или связки камней.")
    return {
        "format": "pob1",
        "name": build_name or f"{class_name} {ascendancy}".strip() or "PoB билд",
        "class": class_name,
        "ascendancy": ascendancy,
        "character_level": build_level,
        "trees": trees,
        "gem_sets": gem_sets,
        "source_code": source.strip(),
    }


def stage_for_level(stages: list[dict], level: int) -> dict | None:
    if not stages:
        return None
    level = clamp_level(level)
    eligible = [item for item in stages if clamp_level(item.get("level", 1)) <= level]
    if eligible:
        return max(eligible, key=lambda item: clamp_level(item.get("level", 1)))
    return min(stages, key=lambda item: clamp_level(item.get("level", 1)))


def new_profile(name: str, legacy_progress: dict | None = None) -> dict:
    return {
        "id": uuid.uuid4().hex,
        "name": (name or "Персонаж").strip() or "Персонаж",
        "game": "poe1",
        "level": 1,
        "campaign": copy.deepcopy(legacy_progress or {}),
        "build": None,
    }


class Poe1ProfileStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self, legacy_progress: dict | None = None) -> dict:
        data = None
        try:
            if self.path.exists():
                import json
                data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
            profile = new_profile("Основной персонаж", legacy_progress)
            data = {
                "version": PROFILE_VERSION,
                "active_profile_id": profile["id"],
                "profiles": [profile],
            }
        if not data["profiles"]:
            profile = new_profile("Основной персонаж")
            data["profiles"] = [profile]
            data["active_profile_id"] = profile["id"]
        if not any(p.get("id") == data.get("active_profile_id") for p in data["profiles"]):
            data["active_profile_id"] = data["profiles"][0]["id"]
        return data

    def save(self, data: dict) -> None:
        import json
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)


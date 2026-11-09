"""Пересборка data/poe1/cluster_jewels.json из Path of Building: шаблоны колец кластеров и смещения прокси-нод.

Запуск: .venv/bin/python tools/update_cluster_jewels.py [--ref <commit>] [--source <ClusterJewels.lua>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "actpilot" / "data" / "poe1" / "cluster_jewels.json"
REPO = "PathOfBuildingCommunity/PathOfBuilding"
DEFAULT_REF = "b32759ab0f31a1c8499a0d420cb0f0633d4fe478"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/src/Data/ClusterJewels.lua"

SIZE_BLOCK = re.compile(
    r'size = "(?P<name>\w+)",\s*sizeIndex = (?P<index>\d+),.*?'
    r"socketIndicies = \{(?P<sockets>[^}]*)\},\s*totalIndicies = (?P<total>\d+)",
    re.S,
)
OFFSET_ENTRY = re.compile(r"\[(\d+)\]\s*=\s*\{([^{}]*)\}")
OFFSET_VALUE = re.compile(r"\[(\d+)\]\s*=\s*(\d+)")


def fetch(ref: str, source: str | None = None) -> str:
    if source:
        return Path(source).read_text(encoding="utf-8")
    url = RAW_URL.format(repo=REPO, ref=ref)
    request = urllib.request.Request(url, headers={"User-Agent": "ActPilot cluster data updater"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def parse(lua: str, ref: str) -> dict:
    sizes = {}
    for match in SIZE_BLOCK.finditer(lua):
        sizes[match.group("index")] = {
            "name": match.group("name"),
            "total": int(match.group("total")),
            "sockets": [int(value) for value in re.findall(r"\d+", match.group("sockets"))],
        }
    # orbitOffsets — последний блок файла: ключи прокси-нод, значения по sizeIndex
    offsets_block = lua[lua.index("orbitOffsets = {"):]
    offsets = {
        proxy: {size: int(value) for size, value in OFFSET_VALUE.findall(body)}
        for proxy, body in OFFSET_ENTRY.findall(offsets_block)
    }
    if set(sizes) != {"0", "1", "2"} or not offsets:
        raise ValueError(f"Неожиданный формат ClusterJewels.lua: размеры {sorted(sizes)}, прокси {len(offsets)}")
    return {
        "source": {"repo": REPO, "ref": ref, "file": "src/Data/ClusterJewels.lua", "license": "MIT"},
        "sizes": sizes,
        "orbit_offsets": dict(sorted(offsets.items(), key=lambda item: int(item[0]))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--source", help="локальный ClusterJewels.lua вместо загрузки")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = parse(fetch(args.ref, args.source), args.ref)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    print(f"Размеров кластеров: {len(data['sizes'])}, прокси-нод со смещениями: {len(data['orbit_offsets'])}")
    if args.dry_run:
        return 0
    TARGET.write_text(text, encoding="utf-8")
    print(f"Записано: {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Runtime-инвентаризация эффективного поведения legacy-башни.

Запуск: .venv/bin/python tools/mro_inventory.py [--out FILE]
Сравнение с базой: .venv/bin/python tools/mro_inventory.py --check
"""

import argparse
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYNPUT_BACKEND_KEYBOARD", "dummy")
os.environ.setdefault("PYNPUT_BACKEND_MOUSE", "dummy")

ROOT = Path(__file__).resolve().parent.parent
for entry in (str(ROOT), str(ROOT / "src"), str(ROOT / "src" / "legacy")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

BASELINE = ROOT / "tools" / "baseline" / "mro_inventory.json"
OWN_MODULE_HINTS = ("main", "poe1", "release_poe1", "actpilot", "settings_dialog", "regex_dialog")


def is_own_module(module_name: str) -> bool:
    return any(module_name == hint or module_name.startswith(hint) for hint in OWN_MODULE_HINTS)


def source_hash(obj) -> str | None:
    try:
        source = inspect.getsource(obj)
    except (OSError, TypeError):
        return None
    normalized = "\n".join(line.strip() for line in source.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def class_inventory(cls) -> dict:
    attributes = {}
    for name in sorted(dir(cls)):
        if name.startswith("__") and name != "__init__":
            continue
        for klass in cls.__mro__:
            if name in vars(klass):
                if not is_own_module(klass.__module__):
                    break
                value = vars(klass)[name]
                attributes[name] = {
                    "defined_in": f"{klass.__module__}.{klass.__name__}",
                    "hash": source_hash(value) if callable(value) else None,
                }
                break
    return {
        "mro": [
            f"{klass.__module__}.{klass.__name__}"
            for klass in cls.__mro__
            if is_own_module(klass.__module__)
        ],
        "attributes": attributes,
    }


def build_report() -> dict:
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])

    import main as legacy

    legacy.ensure_cormorant_loaded()

    import release_poe1_v41 as editor_release
    import release_poe1_v50 as editor_bridge
    import release_poe1_v35 as settings_release
    import release_poe1_v51 as mini_release
    import main_poe1_enhanced as enhanced
    from poe1_manual_editor_v11 import ManualBuildEditor
    from release_poe1_v69 import CompactHeaderIconOverlay
    from actpilot.settings_dialog import ActPilotSettingsDialog

    # Точное повторение проводки app.py:70-73
    editor_bridge.ManualBuildEditor = ManualBuildEditor
    editor_bridge.editor_release.ManualBuildEditor = ManualBuildEditor
    editor_release.ManualBuildEditor = ManualBuildEditor
    settings_release.Poe1SettingsDialog = ActPilotSettingsDialog

    window = CompactHeaderIconOverlay()
    window.show()
    app.processEvents()

    build_dialog_cls = None
    try:
        # Открытие билд-окна выполняет call-time патчи (release_poe1_v51 и далее)
        window._open_build_progress()
        app.processEvents()
        dialog = getattr(window, "_build_dialog", None)
        if dialog is not None:
            build_dialog_cls = type(dialog)
            dialog.hide()
    except Exception as exc:
        print(f"mro_inventory: build dialog failed: {exc}", file=sys.stderr)

    roots = {
        "overlay": type(window),
        "settings_dialog": settings_release.Poe1SettingsDialog,
        "editor": editor_release.ManualBuildEditor,
        "mini_route": mini_release.MiniPassiveRoute,
        "client_monitor": enhanced.ClientLevelMonitor,
    }
    if build_dialog_cls is not None:
        roots["build_dialog"] = build_dialog_cls

    patched = {
        "release_poe1_v41.ManualBuildEditor": f"{editor_release.ManualBuildEditor.__module__}.{editor_release.ManualBuildEditor.__name__}",
        "release_poe1_v50.ManualBuildEditor": f"{editor_bridge.ManualBuildEditor.__module__}.{editor_bridge.ManualBuildEditor.__name__}",
        "release_poe1_v51.MiniPassiveRoute": f"{mini_release.MiniPassiveRoute.__module__}.{mini_release.MiniPassiveRoute.__name__}",
        "main_poe1_enhanced.ClientLevelMonitor": f"{enhanced.ClientLevelMonitor.__module__}.{enhanced.ClientLevelMonitor.__name__}",
    }

    report = {
        "roots": {name: class_inventory(cls) for name, cls in roots.items()},
        "patched_module_attrs": patched,
    }
    window.close()
    return report


def compare(baseline: dict, current: dict) -> list[str]:
    problems = []
    for root, base_data in baseline["roots"].items():
        cur_data = current["roots"].get(root)
        if cur_data is None:
            problems.append(f"{root}: исчез из отчёта")
            continue
        base_attrs, cur_attrs = base_data["attributes"], cur_data["attributes"]
        for name in sorted(set(base_attrs) | set(cur_attrs)):
            if name not in cur_attrs:
                problems.append(f"{root}.{name}: атрибут пропал")
            elif name not in base_attrs:
                problems.append(f"{root}.{name}: новый атрибут")
            elif base_attrs[name]["hash"] != cur_attrs[name]["hash"]:
                problems.append(
                    f"{root}.{name}: исходник изменился "
                    f"({base_attrs[name]['defined_in']} -> {cur_attrs[name]['defined_in']})"
                )
    for key, value in baseline["patched_module_attrs"].items():
        if current["patched_module_attrs"].get(key) != value:
            problems.append(
                f"patch {key}: {value} -> {current['patched_module_attrs'].get(key)}"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=BASELINE)
    parser.add_argument("--check", action="store_true", help="сравнить с базой вместо записи")
    args = parser.parse_args()

    report = build_report()
    if args.check:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        problems = compare(baseline, report)
        if problems:
            print("ИЗМЕНЕНИЯ ПОВЕДЕНИЯ (проверьте намеренность каждого):")
            for problem in problems:
                print(f"  {problem}")
            return 1
        print("OK: эффективное поведение идентично базе")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"baseline: {args.out}")
    for name, data in report["roots"].items():
        print(f"  {name}: {len(data['mro'])} слоёв MRO, {len(data['attributes'])} атрибутов")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ActPilot PoE 1 — canonical source and PyInstaller entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from auto_update import add_update_controls, apply_pending_update, schedule_startup_check


if apply_pending_update(sys.argv):
    raise SystemExit(0)


ROOT = Path(__file__).resolve().parent
LEGACY_SOURCE = ROOT / "src" / "legacy"
if str(LEGACY_SOURCE) not in sys.path:
    sys.path.insert(0, str(LEGACY_SOURCE))

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QFont  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import main as legacy  # noqa: E402
import release_poe1_v41 as editor_release  # noqa: E402
import release_poe1_v50 as editor_bridge  # noqa: E402
import release_poe1_v35 as settings_release  # noqa: E402
from poe1_manual_editor_v11 import ManualBuildEditor  # noqa: E402
from release_poe1_v69 import CompactHeaderIconOverlay  # noqa: E402
from settings_dialog import ActPilotSettingsDialog  # noqa: E402


class UpdateSettingsDialog(ActPilotSettingsDialog):
    def __init__(self, settings, parent=None):
        super().__init__(settings, legacy, parent)
        add_update_controls(self)


def main() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(f"{legacy.APP_NAME} — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet("""
        QScrollBar:vertical {
            background:#111719; width:8px; border:0; border-radius:4px;
        }
        QScrollBar::handle:vertical {
            background:#66543a; border:0; border-radius:4px; min-height:34px;
        }
        QScrollBar::handle:vertical:hover { background:#806b49; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        QScrollBar:horizontal {
            background:#111719; height:8px; border:0; border-radius:4px;
        }
        QScrollBar::handle:horizontal {
            background:#66543a; border:0; border-radius:4px; min-width:34px;
        }
        QScrollBar::handle:horizontal:hover { background:#806b49; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background:transparent; }
    """)

    # The compatibility runtime still has two editor import bridges. Keep both
    # pointed at the one current editor until the internal modules are flattened.
    editor_bridge.ManualBuildEditor = ManualBuildEditor
    editor_bridge.editor_release.ManualBuildEditor = ManualBuildEditor
    editor_release.ManualBuildEditor = ManualBuildEditor
    settings_release.Poe1SettingsDialog = UpdateSettingsDialog

    window = CompactHeaderIconOverlay()
    window.show()
    schedule_startup_check(window)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

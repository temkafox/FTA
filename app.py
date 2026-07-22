"""ActPilot PoE 1 — canonical source and PyInstaller entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from auto_update import apply_pending_update, schedule_startup_check


if apply_pending_update(sys.argv):
    raise SystemExit(0)


ROOT = Path(__file__).resolve().parent
for _source in (ROOT / "src", ROOT / "src" / "legacy"):
    if str(_source) not in sys.path:
        sys.path.insert(0, str(_source))

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QFont  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

import main as legacy  # noqa: E402
import release_poe1_v41 as editor_release  # noqa: E402
import release_poe1_v50 as editor_bridge  # noqa: E402
import release_poe1_v35 as settings_release  # noqa: E402
from poe1_manual_editor_v11 import ManualBuildEditor  # noqa: E402
from release_poe1_v69 import CompactHeaderIconOverlay  # noqa: E402
from actpilot.settings_dialog import UpdateSettingsDialog  # noqa: E402


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

    window = CompactHeaderIconOverlay()
    window.show()
    schedule_startup_check(window)
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

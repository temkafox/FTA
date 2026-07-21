"""PoE 1 build window using the exact ActPilot frame and UI assets."""

from __future__ import annotations

import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QWidget

import main as legacy
import release_poe1_v33 as previous


class BuildAssetHeader(QFrame):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self._drag_offset = None
        self.setObjectName("assetHeader")
        self.setFixedHeight(46)
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.owner.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.owner.move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class AssetFramedBuildDialog(previous.CompactBuildDialog):
    def __init__(self, overlay):
        super().__init__(overlay)
        self._frame_pixmap = legacy.load_background_pixmap()
        self._has_asset_frame = not self._frame_pixmap.isNull()

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setWindowTitle("ActPilot — PoE 1 Build")

        self._install_asset_header()
        self._apply_asset_frame_layout()
        self._apply_asset_style()
        self._resize_handles = legacy.CornerResizeHandles(
            self, 900, 560, parent=self,
        )
        self._resize_handles.raise_()
        opacity = getattr(self.overlay, "settings", {}).get("opacity", 0.95)
        self.setWindowOpacity(max(0.75, min(1.0, float(opacity))))

    def _install_asset_header(self):
        self.asset_header = BuildAssetHeader(self)
        row = QHBoxLayout(self.asset_header)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(legacy.Style.PAD_S)

        logo = legacy.scaled_ui_pixmap("logo", height=36)
        self.asset_logo = QLabel()
        if not logo.isNull():
            self.asset_logo.setPixmap(logo)
        else:
            self.asset_logo.setText("ActPilot")
            family = legacy.ensure_cormorant_loaded() or "Georgia"
            self.asset_logo.setFont(QFont(family, 22, QFont.DemiBold))
            self.asset_logo.setStyleSheet("color:#c7a45d;")
        self.asset_logo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        row.addWidget(self.asset_logo, 0, Qt.AlignVCenter)
        row.addStretch()

        self.asset_close = legacy.make_icon_button(
            "close", "×", legacy.Style.BTN_SIZE, self.close, self.asset_header,
        )
        self.asset_close.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.asset_close, 0, Qt.AlignVCenter)
        self.layout().insertWidget(0, self.asset_header)

    def _apply_asset_frame_layout(self):
        style = legacy.Style
        self.layout().setContentsMargins(
            style.BG_SLICE_LEFT,
            style.BG_SLICE_TOP - 8,
            style.BG_SLICE_RIGHT,
            style.BG_SLICE_BOTTOM,
        )
        self.layout().setSpacing(6)
        self.combined_splitter.setSizes([300, 730])
        self.resize(1100, 700)
        self.setMinimumSize(900, 560)

    def _apply_asset_style(self):
        style = legacy.Style
        self.setStyleSheet(f"""
            QDialog {{ background:transparent; border:0; }}
            QWidget {{
                background:transparent;
                color:{style.TEXT_PRIMARY};
                selection-background-color:{style.ACCENT_BG};
            }}
            QFrame#assetHeader {{ background:transparent; border:0; }}
            QLabel {{
                background:transparent;
                border:0;
                color:{style.TEXT_SECONDARY};
            }}
            QComboBox {{
                background:rgba(7, 9, 9, 205);
                color:{style.TEXT_PRIMARY};
                border:1px solid rgba(154, 116, 57, 0.38);
                border-radius:{style.RAD_S}px;
                padding:5px 9px;
                min-height:18px;
            }}
            QComboBox:hover, QComboBox:focus {{
                border-color:rgba(205, 165, 92, 0.78);
            }}
            QPushButton {{
                background:rgba(8, 9, 9, 190);
                color:rgba(226, 218, 197, 0.72);
                border:1px solid rgba(154, 116, 57, 0.34);
                border-radius:{style.RAD_S}px;
                padding:4px 9px;
            }}
            QPushButton:hover {{
                color:#f4e8cb;
                background:rgba(118, 82, 27, 0.18);
                border-color:rgba(205, 165, 92, 0.78);
            }}
            QPushButton:pressed {{
                color:#12120f;
                background:#b9924c;
            }}
            QScrollArea {{ background:transparent; border:0; }}
            QScrollBar:vertical {{ background:transparent; width:7px; }}
            QScrollBar::handle:vertical {{
                background:rgba(218, 201, 167, 0.25);
                border-radius:3px;
                min-height:22px;
            }}
            QSplitter::handle {{ background:rgba(154, 116, 57, 0.22); }}
            QSlider#levelSlider::groove:horizontal {{
                background:rgba(104, 83, 43, 0.42);
                height:3px;
                border-radius:1px;
            }}
            QSlider#levelSlider::sub-page:horizontal {{
                background:{style.ACCENT};
                border-radius:1px;
            }}
            QSlider#levelSlider::handle:horizontal {{
                background:#c4a15c;
                border:1px solid #6f5428;
                width:14px;
                height:14px;
                margin:-6px 0;
                border-radius:7px;
            }}
            QSlider#levelSlider::handle:horizontal:hover {{ background:#e0c278; }}
        """)
        self.asset_close.setStyleSheet("""
            QPushButton { background:transparent; border:0; padding:0; }
            QPushButton:hover { background:rgba(122,83,30,0.18); border:0; }
        """)
        self.gem_links.body.setStyleSheet("background:rgba(2,4,4,0.38);")
        self.gem_links.parentWidget().setStyleSheet("background:transparent;")
        self.tree_canvas.parentWidget().setStyleSheet("background:transparent;")
        self.combined_splitter.setStyleSheet(
            "QSplitter::handle{background:rgba(154,116,57,0.22);}"
        )
        family = legacy.ensure_cormorant_loaded() or "Georgia"
        self.level_label.setFont(QFont(family, 14, QFont.DemiBold))
        self.level_label.setStyleSheet("color:#d3b46f; background:transparent;")
        self.character_label.setStyleSheet("color:rgba(255,255,255,0.76);")
        self.tree_stage_label.setStyleSheet(
            f"color:{style.ACCENT}; background:transparent; font-weight:600;"
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._has_asset_frame:
            legacy.draw_nine_slice(
                painter,
                self._frame_pixmap,
                self.rect(),
                (
                    legacy.Style.BG_SLICE_LEFT,
                    legacy.Style.BG_SLICE_TOP,
                    legacy.Style.BG_SLICE_RIGHT,
                    legacy.Style.BG_SLICE_BOTTOM,
                ),
            )
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(legacy.Style.BG))
            painter.drawRoundedRect(
                self.rect(), legacy.Style.RAD_L, legacy.Style.RAD_L,
            )
        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_resize_handles"):
            self._resize_handles.reposition()
        self.update()


class AssetFramedOverlay(previous.CompactBuildOverlay):
    def _open_build_progress(self):
        if self.game != legacy.GAME_POE1:
            return
        if self._build_dialog is None:
            self._build_dialog = AssetFramedBuildDialog(self)
            self._build_dialog.finished.connect(
                lambda _: setattr(self, "_build_dialog", None)
            )
        self._build_dialog.reload()
        self._build_dialog.show()
        self._build_dialog.raise_()
        self._build_dialog.activateWindow()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(legacy.APP_NAME)
    app.setApplicationDisplayName(legacy.APP_NAME + " — PoE 1")
    legacy.ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    window = AssetFramedOverlay()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

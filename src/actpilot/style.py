"""Дизайн-токены: Style (мутируется set_ui_scale глобально), палитра PoE."""

# ==================== СТИЛИ ====================
class Style:
    UI_SCALE_MIN = 0.6
    UI_SCALE_MAX = 1.3
    _ui_scale = 1.0

    PAD_XL = 24
    PAD_L = 20
    PAD_M = 16
    PAD_S = 12
    PAD_XS = 8

    RAD_L = 16
    RAD_M = 12
    RAD_S = 8

    BTN_SIZE = 32
    CHECK_SIZE = 20
    CHECK_ICON_SIZE = 32
    LOGO_HEIGHT = 42
    HEADER_H = 64
    PANEL_PAD_X = 32
    PANEL_PAD_TOP = 10
    PANEL_PAD_BOTTOM = 16
    BG_SLICE_LEFT = 36
    BG_SLICE_RIGHT = 36
    BG_SLICE_TOP = 44
    BG_SLICE_BOTTOM = 44
    STEP_MIN_H = 52
    PROGRESS_BAR_H = 9
    GRIP_SIZE = 20
    GRIP_INSET = 22

    FONT_STEP = 11
    FONT_HEADER = 13
    FONT_GROUP_TIME = 11
    FONT_TIMER_BTN = 9
    FONT_STEP_TIME = 9

    @classmethod
    def horizontal_pad(cls, has_background: bool) -> int:
        """Единый отступ слева/справа для хедера, таймера и контента."""
        return cls.BG_SLICE_LEFT if has_background else cls.PAD_XL

    @classmethod
    def panel_margins(cls, has_background: bool):
        if has_background:
            return (cls.BG_SLICE_LEFT, cls.BG_SLICE_TOP, cls.BG_SLICE_RIGHT, cls.BG_SLICE_BOTTOM)
        return (cls.PAD_XL, 0, cls.PAD_XL, cls.PAD_M)

    @classmethod
    def collapsed_height(cls, has_background: bool) -> int:
        _, top, _, bottom = cls.panel_margins(has_background)
        return top + cls.HEADER_H + bottom
    
    BG = "#1a1a1f"
    BG_SECONDARY = "#222228"
    
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "rgba(255, 255, 255, 0.65)"
    TEXT_MUTED = "rgba(255, 255, 255, 0.4)"
    TEXT_DISABLED = "rgba(255, 255, 255, 0.25)"
    
    BORDER = "rgba(255, 255, 255, 0.08)"
    HOVER = "rgba(255, 255, 255, 0.05)"
    
    ACCENT = "#4ade80"
    ACCENT_BG = "rgba(74, 222, 128, 0.12)"
    DANGER = "#f87171"

    # Таймер (макет: Cormorant Garamond + золото)
    TIMER_SIZE = 18
    TIMER_BTN_SIZE = 22
    TIMER_PAD_TOP = 1
    TIMER_PAD_BOTTOM = 6
    TIMER_PAD_RIGHT = 3
    TIMER_COLOR = "#e0b96f"
    TIMER_STROKE = (40, 24, 8)
    TIMER_HIGHLIGHT = (255, 238, 174)
    TIMER_GLOW = (216, 174, 98)

    @classmethod
    def ui_scale(cls) -> float:
        return cls._ui_scale

    @classmethod
    def set_ui_scale(cls, scale: float):
        scale = max(cls.UI_SCALE_MIN, min(cls.UI_SCALE_MAX, float(scale)))
        cls._ui_scale = scale
        for key, base in _STYLE_NUMERIC_BASE.items():
            setattr(cls, key, max(1, int(round(base * scale))))


_STYLE_NUMERIC_BASE = {
    name: getattr(Style, name)
    for name in (
        "PAD_XL", "PAD_L", "PAD_M", "PAD_S", "PAD_XS",
        "RAD_L", "RAD_M", "RAD_S",
        "BTN_SIZE", "CHECK_SIZE", "CHECK_ICON_SIZE",
        "LOGO_HEIGHT", "HEADER_H",
        "PANEL_PAD_X", "PANEL_PAD_TOP", "PANEL_PAD_BOTTOM",
        "BG_SLICE_LEFT", "BG_SLICE_RIGHT", "BG_SLICE_TOP", "BG_SLICE_BOTTOM",
        "STEP_MIN_H", "PROGRESS_BAR_H", "GRIP_SIZE", "GRIP_INSET",
        "TIMER_SIZE", "TIMER_BTN_SIZE", "TIMER_PAD_TOP", "TIMER_PAD_BOTTOM", "TIMER_PAD_RIGHT",
        "FONT_STEP", "FONT_HEADER", "FONT_GROUP_TIME", "FONT_TIMER_BTN", "FONT_STEP_TIME",
    )
}


# Цвета как на poe2wiki (Template:C)
POE_COLORS = {
    "boss": "#d04a4a",       # corrupted — боссы
    "corrupted": "#d04a4a",
    "npc": "#e6c85c",        # жёлтый — НПЦ
    "zone": "#ffffff",       # белый — локации
    "area": "#ffffff",
    "quest": "#4ae63a",      # зелёный — квестовые предметы
    "magic": "#8888ff",      # синий — бонусы/моды
    "unique": "#af6025",     # оранжевый — уникальные предметы
    "item": "#af6025",
}

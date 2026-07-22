import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QSlider, QDialog, QLineEdit,
    QSizePolicy, QSystemTrayIcon, QMenu, QAction, QCheckBox, QButtonGroup,
    QMessageBox,
)
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty, QObject,
    QTimer, QRect, QRectF, QSize, QPoint, QPointF,
)
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPen, QBrush,
    QIcon, QPixmap, QImage, QPainterPath, QTransform, QCursor, QLinearGradient,
)
import time

from actpilot.hotkeys import HotkeyListener, display_hotkey, normalize_hotkey
from actpilot.paths import (
    APP_DIR, APP_NAME, DATA_DIR, LEGACY_PROGRESS_FILE, SETTINGS_FILE,
    get_app_dir, get_data_dir, get_resource_dir,
)
from actpilot.persistence import load_json, save_json
from actpilot.style import POE_COLORS, Style, _STYLE_NUMERIC_BASE
from actpilot.winapi import set_window_click_through
from actpilot.regex_dialog import DEFAULT_REGEXES, RegexDialog


# ==================== СТИЛИ ====================
# Style/_STYLE_NUMERIC_BASE/POE_COLORS живут в actpilot.style


# ==================== ПУТИ ====================
# APP_DIR/DATA_DIR/SETTINGS_FILE и миграция в %APPDATA% живут в actpilot.paths

GAME_POE1 = "poe1"
GAME_POE2 = "poe2"


def get_steps_file(game: str) -> Path:
    name = "steps_poe2.json" if game == GAME_POE2 else "steps.json"
    external = APP_DIR / name
    if external.exists():
        return external
    bundled = get_resource_dir() / name
    if bundled.exists():
        return bundled
    return external


def get_progress_file(game: str) -> Path:
    if game == GAME_POE2:
        return DATA_DIR / "progress_poe2.json"
    return DATA_DIR / "progress_poe1.json"


def get_data_file(name: str) -> Path:
    external = DATA_DIR / name
    if external.exists():
        return external
    bundled = get_resource_dir() / "data" / name
    if bundled.exists():
        return bundled
    return external


POE2_LAYOUTS_FILE = "poe2_layouts.json"
POE2_LAYOUT_STEPS_FILE = "poe2_layout_steps.json"
MANOR_FLOOR_IDS = ("ogham_manor_1", "ogham_manor_2", "ogham_manor_3")


def layout_asset_path(rel_path: str) -> Path:
    rel = rel_path.replace("\\", "/")
    for base in (APP_DIR, get_resource_dir()):
        p = base / rel
        if p.is_file():
            return p
    return APP_DIR / rel


def load_poe2_layout_catalog() -> dict:
    data = load_json(get_data_file(POE2_LAYOUTS_FILE), {})
    return data.get("layouts", {})


_layout_steps_cache = None


def load_poe2_layout_steps_all() -> dict:
    global _layout_steps_cache
    if _layout_steps_cache is None:
        _layout_steps_cache = load_json(get_data_file(POE2_LAYOUT_STEPS_FILE), {})
    return _layout_steps_cache


def load_poe2_layout_steps(act: str) -> dict:
    return load_poe2_layout_steps_all().get(act, {})


def resolve_layout_id(act: str, step_index: int, step_text: str) -> str | None:
    steps_map = load_poe2_layout_steps(act)
    if not steps_map:
        return None
    raw = steps_map.get(str(step_index))
    if raw is None:
        return None
    if raw == "ogham_manor":
        if "Граф Жеонор" in step_text and "Свечная масса" not in step_text:
            return "ogham_manor_3"
        return "ogham_manor_1"
    return raw


def is_manor_floor_step(layout_id: str | None) -> bool:
    return layout_id in MANOR_FLOOR_IDS or layout_id == "ogham_manor"


_font_cache = {}
_cormorant_family = None
FONT_CANDIDATES = (
    "CormorantGaramond-Medium.otf",
    "CormorantGaramond-Medium.ttf",
    "CormorantGaramond-Regular.otf",
    "CormorantGaramond-Variable.ttf",
)
MIN_FONT_FILE_SIZE = 1024


def _fonts_dir() -> Path:
    for base in (get_resource_dir(), APP_DIR):
        d = base / "assets" / "fonts"
        if d.is_dir():
            return d
    return APP_DIR / "assets" / "fonts"


def register_ui_font(filename: str):
    path = _fonts_dir() / filename
    if not path.is_file() or path.stat().st_size < MIN_FONT_FILE_SIZE:
        return None
    key = str(path.resolve())
    if key in _font_cache:
        return _font_cache[key]
    fid = QFontDatabase.addApplicationFont(str(path))
    if fid < 0:
        return None
    families = QFontDatabase.applicationFontFamilies(fid)
    if not families:
        return None
    _font_cache[key] = families[0]
    return families[0]


def ensure_cormorant_loaded():
    global _cormorant_family
    if _cormorant_family is not None:
        return _cormorant_family or None
    for filename in FONT_CANDIDATES:
        family = register_ui_font(filename)
        if family:
            _cormorant_family = family
            return family
    _cormorant_family = ""
    return None


def timer_display_font() -> QFont:
    family = ensure_cormorant_loaded()
    if family:
        font = QFont(family, Style.TIMER_SIZE)
    else:
        font = QFont("Georgia", Style.TIMER_SIZE, QFont.Medium)
    font.setStyleHint(QFont.Serif)
    font.setLetterSpacing(QFont.AbsoluteSpacing, Style.TIMER_SIZE * 0.015)
    return font


def timer_row_height() -> int:
    fm = QFontMetrics(timer_display_font())
    return max(fm.height() + 6, Style.TIMER_BTN_SIZE)


def _ui_asset_paths(name: str):
    stem = name if name.endswith(".png") else f"{name}.png"
    return (
        APP_DIR / stem,
        APP_DIR / "assets" / stem,
        get_resource_dir() / stem,
        get_resource_dir() / "assets" / stem,
    )


def load_ui_pixmap(name: str) -> QPixmap:
    for path in _ui_asset_paths(name):
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap
    return QPixmap()


def _prepare_bg_pixmap(pixmap: QPixmap) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    if pixmap.hasAlphaChannel():
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
        return QPixmap.fromImage(image)
    return pixmap


def load_background_pixmap() -> QPixmap:
    return _prepare_bg_pixmap(load_ui_pixmap("bg"))


def draw_nine_slice(painter, pixmap: QPixmap, target: QRect, borders: tuple):
    """Рисует фон с фиксированными углами и рамками сверху/снизу."""
    l, t, r, b = borders
    sw, sh = pixmap.width(), pixmap.height()
    if sw < 2 or sh < 2:
        return

    l = min(l, sw // 2)
    r = min(r, sw // 2)
    t = min(t, sh // 2)
    b = min(b, sh // 2)

    cw_s = max(1, sw - l - r)
    ch_s = max(1, sh - t - b)
    x, y, tw, th = target.x(), target.y(), target.width(), target.height()
    cw_d = max(1, tw - l - r)
    ch_d = max(1, th - t - b)

    def blit(dst: QRect, src: QRect):
        painter.drawPixmap(dst, pixmap, src)

    blit(QRect(x, y, l, t), QRect(0, 0, l, t))
    blit(QRect(x + l, y, cw_d, t), QRect(l, 0, cw_s, t))
    blit(QRect(x + tw - r, y, r, t), QRect(sw - r, 0, r, t))

    blit(QRect(x, y + t, l, ch_d), QRect(0, t, l, ch_s))
    blit(QRect(x + l, y + t, cw_d, ch_d), QRect(l, t, cw_s, ch_s))
    blit(QRect(x + tw - r, y + t, r, ch_d), QRect(sw - r, t, r, ch_s))

    blit(QRect(x, y + th - b, l, b), QRect(0, sh - b, l, b))
    blit(QRect(x + l, y + th - b, cw_d, b), QRect(l, sh - b, cw_s, b))
    blit(QRect(x + tw - r, y + th - b, r, b), QRect(sw - r, sh - b, r, b))


def set_widget_transparent(widget):
    if widget is None:
        return
    widget.setAutoFillBackground(False)
    widget.setAttribute(Qt.WA_StyledBackground, True)


def scaled_ui_pixmap(name: str, width: int = None, height: int = None) -> QPixmap:
    pixmap = load_ui_pixmap(name)
    if pixmap.isNull():
        return pixmap
    if width is None and height is None:
        return pixmap
    if width is None:
        return pixmap.scaledToHeight(height, Qt.SmoothTransformation)
    if height is None:
        return pixmap.scaledToWidth(width, Qt.SmoothTransformation)
    return pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def make_icon_button(
    asset_name: str,
    fallback_text: str,
    size: int,
    action,
    parent=None,
) -> QPushButton:
    btn = QPushButton(parent)
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet("""
        QPushButton {
            background: transparent;
            border: none;
        }
        QPushButton:hover {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 16px;
        }
    """)
    if asset_name == "collapse":
        icon = QPixmap()
        btn.setIcon(QIcon())
        btn.setFont(QFont("Segoe UI", 13, QFont.Normal))
        btn.setText("−")
        btn.setStyleSheet(btn.styleSheet() + "QPushButton { color:#c9a35a; padding:0; }")
    else:
        icon = scaled_ui_pixmap(asset_name, size, size)
    if asset_name == "collapse":
        pass
    elif not icon.isNull():
        btn.setIcon(QIcon(icon))
        btn.setIconSize(icon.size())
    else:
        btn.setFont(QFont("Segoe UI", 14))
        btn.setText(fallback_text)
        btn.setStyleSheet(btn.styleSheet() + f" color: {Style.TEXT_MUTED};")
    btn.clicked.connect(action)
    return btn


# ==================== ДАННЫЕ ====================
DEFAULT_STEPS = {
    "Act 1": [
        "Убиваем хиллока",
        "Идем в побережье, активируем вп, прибрежный остров игнорим",
        "Идем в ИЛИСТЫЕ НИЗИНЫ, собираем 3 предмета из гнезд роа",
        "Идем в СЫРОЙ ПРОХОД, активируем вп, летим через него на ПОБЕРЕЖЬЕ",
        "Идем в ПРИБРЕЖНЫЙ ОСТРОВ, убиваем босса",
        "Идем в город, берем ртутный флакон",
        "Тп в СЫРОЙ ПРОХОД",
        "🕮 Идем в залитый провал и убиваем краба (первая половина области до моста)",
        "Идем обратно, бежим дальше в локу УТЕС",
        "Пробегаем, доходим до СКЛОНА, пробегаем",
        "Идем в ТЮРЕМНЫЕ ПОДЗЕМЕЛЬЯ, активируем вп в начале области",
        "Испытание восхождения",
        "Идем дальше до ТЮРЕМНЫХ ПОМЕЩЕНИЙ",
        "Ищем комнату с боссом Изувер и убиваем",
        "Тп в город, сдаем квесты",
        "Идем во ВРАТА ЗАКЛЮЧЕННЫХ (по дороге не бежим, находим небольшой спуск в сторону и проход через горы)",
        "Идем в КЛАДБИЩЕ КОРАБЛЕЙ, активируем вп",
        "🕮 Квест Обманутый моряк - ищем вход в Грот, находим квестовый предмет, возвращаемся обратно на кладбище",
        "Недалеко ищем вход в ПЕЩЕРЫ ГНЕВА, ищем вп, делаем тп обратно на кладбище и сдаем квест капитану, если не сделали это ранее",
        "Тп в город, сдаем квесты",
        "Тп в ПЕЩЕРУ ГНЕВА, пробегаем",
        "Идем до ПЕЩЕРЫ ЗЛОБЫ, убиваем Мервейл"
    ],
    "Act 2": [
      "Через ЮЖНЫЙ ЛЕС доходим до города",
      "Из города справа выходим в СТАРЫЕ ПОЛЯ",
      "🕮 Находим БЕРЛОГУ, убиваем медведя",
      "Идем обратно в СТАРЫЕ ПОЛЯ, пробегаем по дороге",
      "Идем в ПЕРЕКРЕСТОК, бежим по дороге до портала, бежим влево вверх по дороге",
      "Идем в ОБИТЕЛЬ ГРЕХОВ",
      "В цетре этой области есть портал (с какой стороны от центра портал, там и выход)",
      "Идем на второй уровень",
      "2 Испытание восхождения",
      "Убиваем Фиделиса",
      "ТП в город",
      "ТП в ПЕРЕКРЕСТОК",
      "Идем вниз вправо до РУИНЫ ОСКВЕРНЕННОЙ СВЯТЫНИ",
      "Бежим по дороге до склепа",
      "Идем в СКЛЕП",
      "3 Испытание восхождения (побочное задание не выполняем)",
      "Тп в город",
      "Тп в ПЕРЕКРЕСТОК",
      "Бежим вправо вверх до РАЗРУШЕННОГО МОСТА",
      "Бежим по дороге и находим одного из трех бандитов, убиваем",
      "Тп в город",
      "Выходим слева в ПОЙМУ РЕКИ",
      "Бежим по дороге до вп",
      "Сходим с дороги и идем вверх влево до локи ТОПЬ",
      "Убиваем Дуба, ищем вп (скорее всего в левой части области)",
      "Тп в ПОЙМУ РЕКИ",
      "Идем по дороге влево до ЗАПАДНОГО ЛЕСА",
      "По дороге идем до вп, находим Алиру, оставляем (+15 к резистам) или убиваем (+1 очко умений)",
      "🕮 Идем по дороге вниз до упора и убиваем кучку мобов с главарем (награда в 1 акте)",
      "Находим пещеру ткачихи, идем внутрь и убиваем",
      "Тп в город, в 1 акт и забираем награду",
      "Тп в ТОПЬ, переходим в РУИНЫ ВААЛ",
      "Идем в СЕВЕРНЫЙ ЛЕС, пробегаем",
      "Идем в ПЕЩЕРЫ, берем вп",
      "Идем в ДРЕВНЮЮ ПИРАМИДУ",
      "Пробегаем все уровни ДРЕВНЕЙ ПИРАМИДЫ (выход каждого уровня в противоположной стороны области)",
      "Убиваем босса 2 акта"
    ],
    "Act 3": [
      "Идем в ГОРОД САРН",
      "Перед входом в лагерь спасаем Кларису и говорим с ней",
      "Из лагеря идем в ТРУЩОБЫ",
      "Идем в КРЕМАТОРИЙ",
      "Активируем ВП",
      "Проходим Испытание восхождения",
      "Находим Веру и сражаемся, берем квестовый предмет",
      "Тп в город - Клариса - забираем ключи от канализации",
      "Тп в ТРУЩОБЫ",
      "Идем в КАНАЛИЗАЦИЮ",
      "Собираем 3 бюста (1 до вп, 2 после)",
      "Идем на РЫНОК",
      "Ищем проход с арками, за ним вп, недалеко от него справа вход в КАТАКОМБЫ",
      "Испытание восхождения",
      "Тп в город, сдаем квесты",
      "Тп на рынок",
      "Ищем проход до ПЕРЕДОВОЙ",
      "В левой части находим вп, слева от него подбираем квестовый предмет",
      "Идем вверх до ДОКОВ (можно покачаться)",
      "Находим Волшебную соль",
      "Возвращаемся в ПЕРЕДОВУЮ",
      "Идем вправо вверх до ХРАМА СОЛЯРИС",
      "Бежим по красной дорожке до 2 уровня",
      "Бежим до НПЦ, получаем квестовый предмет",
      "Идем в КАНАЛИЗАЦИЮ",
      "Открываем проход в ЛАГЕРЬ ЭБЕНОВОГО ЛЕГИОНА",
      "Бежим влево вверх до ХРАМА ЛУНАРИС (по пути можно убить Гравиция)",
      "В ХРАМЕ ЛУНАРИС двигаемся по красной дорожке до 2 уровня",
      "Проходим 2 уровень",
      "Убиваем босса ВЕРУ",
      "Тп в город, сдаем квесты",
      "Тп в ЛАГЕРЬ ЭБЕНОВОГО ЛЕГИОНА",
      "Правее сверху от портала идем в ИМПЕРСКИЕ САДЫ",
      "Испытание восхождения (справа сверху скорее всего)",
      "Идем в БИБЛИОТЕКУ, выполняем квест, ищем обрывки (камни умений)",
      "Идем в ПЕРСТЬ ГОСПОДЕН (внизу справа скорее всего)",
      "Проходим до босса 3 акта и убиваем"
    ],
    "Act 4": [
      "Пробегаем АКВЕДУК и доходим до города",
      "Идем в лабиринт восохождения",
      "Выходим в ВЫСОХШЕЕ ОЗЕРО",
      "Убиваем уник моба ВОЛА и забираем квестовый предмет",
      "Тп в город",
      "Заходим в ШАХТЫ",
      "Пробегаем 1 уровень",
      "На втором уровне  выполняем квест - находим дух Дешред",
      "Переходим в КРИСТАЛЬНУЮ ЖИЛУ, ищем вп",
      "Рядом с ВП будет два портала",
      "Проходим первый портал",
      "Проходим второй портал",
      "Тп в КРИСТАЛЬНУЮ ЖИЛУ, открываем проход",
      "Пролетаем два уровня локации БРЮХО ЗВЕРЯ",
      "Убиваем Веру",
      "Идем в ЖАТВУ",
      "Убиваем трех минибоссов",
      "Идем к последнему боссу Малахаю и убиваем его"
    ],
    "Act 5": [
      "Через ПОДЪЕМ добираемся до УЗИЛИЩА",
      "Берем вп",
      "Бежим вправо по часовой стрелке до минибосса и убиваем его",
      "Заходим в город Башня надзирателя",
      "Выходим в ИЗОЛЯТОР",
      "Двигаемся по кругу, игнорируя центр зоны, берем квестовый предмет",
      "Идем вверх, убиваем босса",
      "Идем в ПЛОЩАДЬ ОРИАТА",
      "Бежим вправо вправо вверх до моста, дальше вправо вниз до входа в СУДЫ ЖРЕЦОВ",
      "Пробегаем по часовой стрелке до ОБИТЕЛЬ НЕВИННОСТИ",
      "Пробегаем против часовой стрелки",
      "Находим босса и убиваем",
      "Идем в ПОДОЖЕННЫЕ СУДЫ",
      "Пробегаем до РАЗРУШЕННАЯ ПЛОЩАДЬ",
      "Берем ВП, заходим в КОСТНИЦУ, берем квестовый предмет",
      "Тп на РАЗРУШЕННУЮ ПЛОЩАДЬ",
      "Бежим вниз через мост до большой открытой территории, открываем свитком портал",
      "Ищем снизу в РЕЛИКВАРИЙ",
      "Активируем ВП",
      "Собираем три квестовых предмета по краям локи",
      "Возвращаемся к вп, тп в город, сдаем квесты и заходим в открытый свитком портал",
      "Слева бежим до входа КРЫША ХРАМА",
      "Пробегаем и убиваем Китаву",
      "Через ПРИСТАНЬ добираемся до корабля и отправляемся в город"
    ],
    "Act 6": [
      "Слева заходим в локу и зачищаем полностью локу",
      "Идем в город, выходим вверх до ПОБЕРЕЖЬЯ",
      "Пробегаем до ИЛИСТЫХ НИЗИН",
      "В ИЛИСТЫХ НИЗИНАХ в правой части локи убиваем мини босса, поднимаем квестовый предмет",
      "Слева этим предметом открываем проход в КРЕПОСТЬ КАРУИ",
      "Бежим, в центре локи убиваем Тукохаму",
      "Идем дальше в ХРЕБЕТ",
      "Пробегаем до входа в ТЮРЕМНОЕ ПОДЗЕМЕЛЬЕ",
      "Испытание восхождения",
      "Идем в БАШНЮ ШЕВРОН, пробегаем",
      "Убиваем босса",
      "Тп в город, сдаем квесты",
      "Тп во ВРАТА ЗАКЛЮЧЕННЫХ",
      "Сходим с дороги и ищем узкий проход, убиваем Аберата",
      "Возвращаемся к дороге, бежим до ЗАПАДНОГО ЛЕСА",
      "Пробегаем до ПОЙМЫ РЕКИ",
      "Бежим по дороге до вп, от него идем вверх до локи ТОПЬ",
      "В левой верхней части зоны ищем проход к боссу",
      "Тп в город",
      "Тп в пойму реки",
      "Идем по дороге вправо до ЮЖНОГО ЛЕСА",
      "Идем по мостикам через острова, входим в ПЕЩЕРУ ЗЛОБЫ",
      "Подбираем квестовый предмет черный флаг",
      "Идем в локу МАЯК",
      "Бежим вдоль берега, активируем маяки, идем в локу РИФ МОРСКОГО ЦАРЯ",
      "Убиваем босса"
    ],
    "Act 7": [
      "Выходим в РАЗРУШЕННЫЙ МОСТ",
      "Выходим на дорогу и идем до ПЕРЕКРЕСТКА",
      "Бежим по дороге до вп",
      "Идем вниз до локи РУИНЫ ОСКВЕРНЕННОЙ СВЯТЫНИ",
      "Идем по дороге до СКЛЕПА",
      "Испытание восхождения на первом уровне",
      "На втором уровне находим квестовый предмет",
      "Возвращаемся на ПЕРЕКРЕСТОК",
      "По дороге идем вверх до ОБИТЕЛЯ ГРЕХОВ",
      "Идем к центру локи, находим вп и запускаем машину картоходца, заходим",
      "Находим босса, убиваем, подбираем квестовый предмет",
      "Возвращаемся в ОБИТЕЛЬ ГРЕХОВ",
      "Говорим с НПЦ и берем ключи",
      "Вп указывает, в какой стороне выход",
      "Идем дальше на второй уровень",
      "Испытание восхождения",
      "Идем в БЕРЛОГУ, выходим в ПЕПЕЛЬНЫЕ ПОЛЯ",
      "По дороге до босса Груста, убиваем, идем в СЕВЕРНЫЙ ЛЕС",
      "В СЕВЕРНОМ ЛЕСУ ищем вход в ЧАЩОБУ",
      "Собираем светлячков и находим локу с минибоссом, убиваем",
      "Тп в СЕВЕРНЫЙ ЛЕС",
      "Идем вверх до локи ПЕРЕШЕЕК",
      "Пробегаем до ВХОДА ВААЛ, подбираем квестовый предмет, заходим внутрь",
      "Идем вверх посередине и отдаем светлячков НПЦ, заходим в ХРАМ РАЗЛОЖЕНИЯ",
      "Первый этажи (выход в противоположном от начала месте)",
      "Убиваем босса акта"
    ],
    "Act 8": [
      "Через локу БАСТИОН САРНА добираемся до города",
      "Проходим второй лабиринт",
      "Идем из города в ОТРАВЛЕННЫЕ КАНАЛЫ",
      "Добегаем до СТОЧНОЙ ЯМЫ ДЕРИИ",
      "Находим босса и убиваем",
      "Проходим дальше до вп, двигаемся на ПРИСТАНЬ",
      "На ПРИСТАНЕ бежим до узкого мостика и подбираем квестовый предмет",
      "Возвращаемся немного назад, бежим бежать дальше, находим переход в область, убиваем ТОЛМАНА, выходим и бежим дальше",
      "Бежим вправо вверх до ЗЕРНОВЫХ ВОРОТ",
      "Убиваем ЛЕГИОНЕРОВ на небольшой площади",
      "Бежим до ИМПЕРСКИХ ПОЛЕЙ, пробегаем влево вверх",
      "Входим в ХРАМ СОЛЯРИС",
      "Бежим по красной дорожке до вп, двигаемся вверх до второго уровня",
      "Бежим до босса и подбираем квестовый предмет",
      "Тп в город, сдаем квесты",
      "Тп на первый уровень ХРАМА СОЛЯРИС",
      "Спускаемся немного вниз и бежим до входа ПЛОЩАДЬ СОЛЯРИС",
      "Бежим влево вниз, берем вп, идем в ПОРТОВЫЙ МОСТ",
      "Пробегаем ПОРТОВЫЙ МОСТ вниз влево до конца, комнату с боссами не трогаем",
      "Доходим до ПЛОЩАДИ ЛУНАРИС, берем ВП",
      "Идем вверх влево до ХРАМА ЛУНАРИС",
      "Бежим до второго уровня",
      "Убиваем босса, подбираем квестовый предмет",
      "Тп в город",
      "Тп на ПЛОЩАДЬ ЛУНАРИС",
      "Бежим влево до локации КУПАЛЬНЯ",
      "Испытание восхождения",
      "Идем в ВИСЯЩИЕ САДЫ",
      "Убиваем босса",
      "Тп в город, сдаем квесты",
      "Тп в ПОРТОВЫЙ МОСТ",
      "Бежим до середины локи и убиваем финальных боссов"
    ],
    "Act 9": [
      "Кровавый акведук, можно покачаться, бежим до города",
      "Заходим в город",
      "Заходи в локацию СПУСК, пробегаем",
      "Идем в ПУСТЫНЮ ВАСТИРИ",
      "Находим ВП!",
      "Находим клинок бури и отдаем его НПЦ",
      "Тп в город, берем закупоренную бурю у нпц",
      "Тп в ПУСТЫНЮ ВАСТИРИ, бежим в правую верхнюю часть территории",
      "Открываем проход в ОАЗИС",
      "Находим минибосса, убиваем Шакари",
      "Тп в ПУСТЫНЮ, ищем проход в ПРЕДГОРЬЕ",
      "Ищем вп, выше от него бежим в КИПЯЩЕЕ ОЗЕРО",
      "Вверху убиваем Василиска",
      "Тп в ПРЕДГОРЬЕ, бежим в левую сторону до ТОННЕЛЯ",
      "Испытание восхождения",
      "Идем в КАМЕНОЛОМНЮ",
      "В центре локи стоит Грех, отдаем предметы",
      "В одной из сторон локи будет ФАБРИКА, там находим квестовы предмет",
      "В другой стороне будет лока с минибоссом, убиваем",
      "Возвращаемся в КАМЕНОЛОМНЮ к НПЦ, открываем проход",
      "Заходим в БРЮХО ЗВЕРЯ, пробегаем",
      "Заходим в ГНИЮЩЕЕ НУТРО",
      "Пробегаем 3 портала до конца",
      "Возвращаемся к НПЦ, открываем портал до босса",
      "Убиваем босса"
    ],
    "Act 10": [
      "Выходим из города на КРЫШУ СОБОРА",
      "Заходим в следующую зону, перебиваем культистов китавы, говорим с нпц Бенноном",
      "Возвращаемся на КРЫШУ СОБОРА",
      "Бежим вправо до РАЗОРЕННОЙ ПЛОЩАДИ",
      "Недалеко от старта этой локи открываем свитком портал",
      "Бежим по площади через мост до вп",
      "Тп в город",
      "Прыгаем в портал через свиток",
      "Бежим вниз до ИЗОЛЯТОРА",
      "Убиваем минибосса ВЕЛЕНТУ",
      "Тп в город",
      "Тп в разоренную площадь",
      "Бежим вправо вниз до локи ПОДОЖЕННЫЕ СУДЫ, заходим",
      "Бежим до ОСКВЕРНЕННОЙ ОБИТЕЛИ, заходим",
      "Бежим до босса Араварии, убиваем, подбираем квестовый предмет",
      "Тп в город, сдаем квесты",
      "Тп в РАЗОРЕННУЮ ПЛОЩАДЬ, идем в КОСТНИЦУ",
      "Испытание ВОСХОЖДЕНИЯ",
      "Тп в город, сдаем квесты",
      "Тп в РАЗОРЕННУЮ ПЛОЩАДЬ, говорим с нпц",
      "Пролетаем все локи до Китавы",
      "Убиваем босса 10 акта",
      "Не забываем в Ориате у нпц Ланы забираем книгу умений",
      "Проходим 3 лабиринт"
    ]
}


DEFAULT_STEPS_POE2 = {
    "Act 1": [
        "Добавьте шаги гайда PoE2 в steps_poe2.json"
    ]
}


DEFAULT_SETTINGS = {
    "hotkey": "F3",
    "previous_hotkey": "Ctrl+F3",
    "opacity": 0.95,
    "layout_hotkey": "F4",
    "regex_hotkey": "F6",
    "layout_opacity": 0.92,
    "layout_size": {"width": 420, "height": 520},
    "layout_position": {"x": -1, "y": -1},
    "position": {"x": 10, "y": 10},
    "size": {"width": 391, "height": 598},
    "game": GAME_POE1,
    "click_through": False,
    "ui_scale": 1.0,
    "show_hotkey_hints": True,
    "regexes": [entry.copy() for entry in DEFAULT_REGEXES],
    "show_welcome": True,
}


def migrate_settings(settings: dict) -> bool:
    """Дополняет настройки новыми ключами, не трогая пользовательские значения."""
    changed = False
    if int(settings.get("regex_defaults_version", 0)) < 2:
        settings.setdefault("regexes", [entry.copy() for entry in DEFAULT_REGEXES])
        settings["regex_defaults_version"] = 2
        changed = True
    if int(settings.get("hotkey_defaults_version", 0)) < 2:
        settings.setdefault("previous_hotkey", normalize_hotkey("Ctrl+F3"))
        settings.setdefault("regex_hotkey", normalize_hotkey("F6"))
        settings["hotkey_defaults_version"] = 2
        changed = True
    return changed


# ==================== УТИЛИТЫ ====================
def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def migrate_legacy_progress():
    if LEGACY_PROGRESS_FILE.exists() and not get_progress_file(GAME_POE1).exists():
        try:
            with open(LEGACY_PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            save_json(get_progress_file(GAME_POE1), data)
        except Exception:
            pass

def format_time(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def parse_step_markup(text: str, base_color: str, done: bool = False) -> str:
    import html
    import re

    effective_base = Style.TEXT_DISABLED if done else base_color
    strike = "text-decoration:line-through;" if done else ""
    parts = []
    last = 0

    for match in re.finditer(r"\{(\w+)\|([^}]+)\}", text):
        if match.start() > last:
            plain = html.escape(text[last:match.start()])
            parts.append(
                f'<span style="color:{effective_base};{strike}">{plain}</span>'
            )

        kind = match.group(1).lower()
        inner = html.escape(match.group(2))
        color = effective_base if done else POE_COLORS.get(kind, effective_base)
        parts.append(f'<span style="color:{color};{strike}">{inner}</span>')
        last = match.end()

    if last < len(text):
        plain = html.escape(text[last:])
        parts.append(f'<span style="color:{effective_base};{strike}">{plain}</span>')

    if not parts:
        escaped = html.escape(text)
        return f'<span style="color:{effective_base};{strike}">{escaped}</span>'

    return "".join(parts)


# ==================== ГОРЯЧИЕ КЛАВИШИ ====================
# normalize_hotkey/display_hotkey/HotkeyListener живут в actpilot.hotkeys


class HotkeyFooter(QLabel):
    """Compact hint that never dictates the overlay's minimum width."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setMinimumWidth(0)
        self.setFixedHeight(22)
        self.setToolTip("")

    def set_full_text(self, text: str):
        self._full_text = text
        self.setToolTip("")
        self.setText(text)

    def _update_elided_text(self):
        # Rich-text labels are clipped naturally, while Ignored size policy
        # keeps this decorative footer from constraining the overlay width.
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided_text()


# ==================== ТАЙМЕР ====================
class TimerLabel(QLabel):
    """Золотой таймер: обводка + многослойная тень (как в CSS-макете)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._glow = True
        self.setFont(timer_display_font())
        fm = QFontMetrics(self.font())
        self.setMinimumHeight(fm.height() + 6)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

    def set_glow(self, active: bool):
        self._glow = active
        self.update()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        return fm.size(Qt.TextSingleLine, self.text() or "00:00")

    def paintEvent(self, event):
        text = self.text()
        if not text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        font = self.font()
        fm = QFontMetrics(font)
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        path = QPainterPath()
        path.addText(0.0, float(y), font, text)

        strength = 1.0 if self._glow else 0.72

        glow = QColor(*Style.TIMER_GLOW, int(61 * strength))
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)):
            painter.fillPath(QTransform().translate(dx, dy).map(path), glow)

        painter.fillPath(
            QTransform().translate(0, 2).map(path),
            QColor(0, 0, 0, int(217 * strength)),
        )
        painter.fillPath(
            QTransform().translate(0, 1).map(path),
            QColor(*Style.TIMER_HIGHLIGHT, int(107 * strength)),
        )

        stroke = QPen(QColor(*Style.TIMER_STROKE, int(217 * strength)))
        stroke.setWidthF(0.7)
        stroke.setJoinStyle(Qt.RoundJoin)
        painter.setPen(stroke)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        fill = QColor(Style.TIMER_COLOR)
        fill.setAlpha(int(255 * strength))
        painter.fillPath(path, fill)


# ==================== ПРОГРЕСС ====================
class FantasyProgressBar(QWidget):
    def __init__(self, value: float = 0, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._display_value = 0.0
        self._anim = QPropertyAnimation(self, b"displayValue")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.refresh_scale()
        self.setMinimumWidth(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setValue(value)

    def get_display_value(self) -> float:
        return self._display_value

    def set_display_value(self, value: float):
        self._display_value = float(value)
        self.update()

    displayValue = pyqtProperty(float, get_display_value, set_display_value)

    def value(self) -> float:
        return self._value

    def setValue(self, value: float):
        value = max(0.0, min(100.0, float(value)))
        self._value = value
        self._anim.stop()
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(value)
        self._anim.start()

    def refresh_scale(self):
        self.setFixedHeight(Style.PROGRESS_BAR_H)

    def sizeHint(self):
        return QSize(240, Style.PROGRESS_BAR_H)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        bar_h = 8.0
        y = (self.height() - bar_h) / 2.0
        track = QRectF(0.5, y, max(1.0, self.width() - 1.0), bar_h)
        radius = bar_h / 2.0

        glow_rect = track.adjusted(-1.5, -1.5, 1.5, 1.5)
        glow_path = QPainterPath()
        glow_path.addRoundedRect(glow_rect, radius + 1.5, radius + 1.5)
        painter.fillPath(glow_path, QColor(95, 255, 100, 18))

        track_path = QPainterPath()
        track_path.addRoundedRect(track, radius, radius)
        painter.fillPath(track_path, QColor(8, 9, 10, 220))

        border_pen = QPen(QColor(150, 112, 55, 120))
        border_pen.setWidthF(1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(track, radius, radius)

        inner = track.adjusted(1.0, 1.0, -1.0, -1.0)
        inner_pen = QPen(QColor(0, 0, 0, 90))
        inner_pen.setWidthF(0.5)
        painter.setPen(inner_pen)
        painter.drawLine(
            QPointF(inner.left() + radius * 0.4, inner.top() + 0.6),
            QPointF(inner.right() - radius * 0.4, inner.top() + 0.6),
        )
        hi_pen = QPen(QColor(255, 220, 140, 30))
        hi_pen.setWidthF(0.5)
        painter.setPen(hi_pen)
        painter.drawLine(
            QPointF(inner.left() + radius * 0.6, inner.bottom() - 0.5),
            QPointF(inner.right() - radius * 0.6, inner.bottom() - 0.5),
        )

        progress = self._display_value
        if progress <= 0:
            return

        fill_w = track.width() * (progress / 100.0)
        fill_w = min(track.width(), max(bar_h * 0.55, fill_w))
        fill = QRectF(track.left(), track.top(), fill_w, track.height())
        fill_radius = min(radius, fill_w / 2.0)

        clip = QPainterPath()
        clip.addRoundedRect(track, radius, radius)
        painter.setClipPath(clip)

        glow_fill = fill.adjusted(-2, -2, 2, 2)
        glow_fill_path = QPainterPath()
        glow_fill_path.addRoundedRect(glow_fill, fill_radius + 2, fill_radius + 2)
        painter.fillPath(glow_fill_path, QColor(95, 255, 100, 90))

        grad = QLinearGradient(fill.left(), fill.top(), fill.right(), fill.top())
        grad.setColorAt(0.0, QColor(47, 188, 77, 255))
        grad.setColorAt(0.5, QColor(150, 245, 92, 255))
        grad.setColorAt(1.0, QColor(68, 204, 78, 255))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(fill, fill_radius, fill_radius)

        top_hi = fill.adjusted(1.2, 1.0, -1.2, -fill.height() * 0.55)
        if top_hi.width() > 1:
            hi_grad = QLinearGradient(top_hi.topLeft(), top_hi.topRight())
            hi_grad.setColorAt(0.0, QColor(235, 255, 160, 0))
            hi_grad.setColorAt(0.35, QColor(235, 255, 160, 130))
            hi_grad.setColorAt(1.0, QColor(235, 255, 160, 0))
            painter.setBrush(QBrush(hi_grad))
            painter.drawRoundedRect(top_hi, fill_radius * 0.6, fill_radius * 0.6)

        painter.setPen(QPen(QColor(20, 90, 30, 110), 0.6))
        painter.drawLine(
            QPointF(fill.left() + fill_radius * 0.5, fill.bottom() - 0.8),
            QPointF(fill.right() - fill_radius * 0.3, fill.bottom() - 0.8),
        )


class Timer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_time = None
        self._elapsed = 0
        self._running = False
        
        pad_top = Style.TIMER_PAD_TOP
        pad_bottom = Style.TIMER_PAD_BOTTOM
        pad_right = Style.TIMER_PAD_RIGHT
        row_h = timer_row_height()
        self.setFixedHeight(pad_top + row_h + pad_bottom)
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, pad_top, pad_right, pad_bottom)
        layout.setSpacing(Style.PAD_S)
        
        self.time_label = TimerLabel("00:00")
        self.time_label.set_glow(False)
        layout.addWidget(self.time_label)
        
        layout.addStretch()
        
        self._init_control_button()
        layout.addWidget(self.btn)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)

    def _init_control_button(self):
        size = Style.TIMER_BTN_SIZE
        self.btn = QPushButton(self)
        self.btn.setFixedSize(size, size)
        self.btn.setCursor(Qt.PointingHandCursor)
        self._pix_play = scaled_ui_pixmap("play", size, size)
        self._pix_pause = scaled_ui_pixmap("pause", size, size)
        self._use_btn_icons = not self._pix_play.isNull() and not self._pix_pause.isNull()
        self._btn_filled_bg = True
        if self._use_btn_icons:
            self.btn.setIconSize(QSize(size, size))
        else:
            self.btn.setFont(QFont("Segoe UI", Style.FONT_TIMER_BTN))
        self._refresh_control_button()
        self.btn.clicked.connect(self.toggle)

    def refresh_scale(self):
        pad_top = Style.TIMER_PAD_TOP
        pad_bottom = Style.TIMER_PAD_BOTTOM
        pad_right = Style.TIMER_PAD_RIGHT
        row_h = timer_row_height()
        self.setFixedHeight(pad_top + row_h + pad_bottom)
        self.layout().setContentsMargins(0, pad_top, pad_right, pad_bottom)
        self.time_label.setFont(timer_display_font())
        fm = QFontMetrics(self.time_label.font())
        self.time_label.setMinimumHeight(fm.height() + 6)
        size = Style.TIMER_BTN_SIZE
        self.btn.setFixedSize(size, size)
        self.btn.setFont(QFont("Segoe UI", Style.FONT_TIMER_BTN))
        self._pix_play = scaled_ui_pixmap("play", size, size)
        self._pix_pause = scaled_ui_pixmap("pause", size, size)
        self._use_btn_icons = not self._pix_play.isNull() and not self._pix_pause.isNull()
        if self._use_btn_icons:
            self.btn.setIconSize(QSize(size, size))
            self._refresh_control_button()
        self._apply_control_button_style()

    def _apply_control_button_style(self):
        btn_r = Style.TIMER_BTN_SIZE // 2
        if self._btn_filled_bg:
            bg, hover = Style.HOVER, "rgba(255, 255, 255, 0.08)"
        else:
            bg, hover = "transparent", Style.HOVER
        extra = "" if self._use_btn_icons else f"color: {Style.TEXT_MUTED};"
        self.btn.setStyleSheet(f"""
            QPushButton {{
                {extra}
                background: {bg};
                border: none;
                border-radius: {btn_r}px;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
        """)

    def set_control_button_theme(self, filled: bool):
        self._btn_filled_bg = filled
        self._apply_control_button_style()

    def _refresh_control_button(self):
        if self._use_btn_icons:
            self.btn.setText("")
            self.btn.setIcon(QIcon(self._pix_pause if self._running else self._pix_play))
        else:
            self.btn.setIcon(QIcon())
            self.btn.setText("⏸" if self._running else "▶")
        self._apply_control_button_style()
    
    def toggle(self):
        if self._running:
            self.pause()
        else:
            self.start()
    
    def start(self):
        if not self._running:
            self._start_time = time.time() - self._elapsed
            self._running = True
            self._timer.start(500)
            self._refresh_control_button()
            self.time_label.set_glow(True)
    
    def pause(self):
        if self._running:
            self._elapsed = time.time() - self._start_time
            self._running = False
            self._timer.stop()
            self._refresh_control_button()
            self.time_label.set_glow(False)
    
    def reset(self):
        self._running = False
        self._timer.stop()
        self._elapsed = 0
        self._start_time = None
        self._refresh_control_button()
        self.time_label.setText("00:00")
        self.time_label.set_glow(False)
    
    def _update(self):
        if self._start_time:
            elapsed = time.time() - self._start_time
            self.time_label.setText(format_time(elapsed))
    
    def get_elapsed(self) -> float:
        if self._running and self._start_time:
            return time.time() - self._start_time
        return self._elapsed
    
    def get_state(self):
        return {
            "elapsed": self._elapsed if not self._running else time.time() - self._start_time,
            "running": self._running
        }
    
    def set_state(self, state):
        self._elapsed = state.get("elapsed", 0)
        if state.get("running"):
            self._start_time = time.time() - self._elapsed
            self._running = True
            self._timer.start(500)
            self.time_label.set_glow(True)
        else:
            self._running = False
            self._timer.stop()
            self.time_label.setText(format_time(self._elapsed))
            self.time_label.set_glow(False)
        self._refresh_control_button()


# ==================== ЧЕКБОКС ====================
class Checkbox(QLabel):
    _pix_checked = None
    _pix_unchecked = None
    _use_images = None

    @classmethod
    def _load_assets(cls):
        if cls._use_images is not None:
            return
        cls._pix_checked = load_ui_pixmap("checked")
        cls._pix_unchecked = load_ui_pixmap("no_checked")
        cls._use_images = not cls._pix_checked.isNull() and not cls._pix_unchecked.isNull()

    @classmethod
    def reload_assets(cls):
        cls._use_images = None
        cls._pix_checked = None
        cls._pix_unchecked = None
        cls._load_assets()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_assets()
        self._checked = False
        self._active = False
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: transparent;")
        set_widget_transparent(self)

        icon_size = Style.CHECK_ICON_SIZE if self._use_images else Style.CHECK_SIZE
        self.setFixedSize(icon_size, icon_size)

        self._apply_icon()

    def _apply_icon(self):
        if self._use_images:
            source = self._pix_checked if self._checked else self._pix_unchecked
            scaled = source.scaled(
                Style.CHECK_ICON_SIZE,
                Style.CHECK_ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)
            return

        self.setPixmap(QPixmap())
        self.update()

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, val):
        self._checked = val
        self._apply_icon()
        if not self._use_images:
            self.update()

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, val):
        self._active = val
        if not self._use_images:
            self.update()

    def refresh_scale(self):
        Checkbox.reload_assets()
        icon_size = Style.CHECK_ICON_SIZE if self._use_images else Style.CHECK_SIZE
        self.setFixedSize(icon_size, icon_size)
        self._apply_icon()

    def paintEvent(self, event):
        if self._use_images:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        if self._checked:
            painter.setBrush(QBrush(QColor(Style.ACCENT)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 5, 5)

            painter.setPen(QPen(QColor("#1a1a1f"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            cx, cy = self.width() / 2, self.height() / 2
            painter.drawLine(int(cx - 4), int(cy), int(cx - 1), int(cy + 3))
            painter.drawLine(int(cx - 1), int(cy + 3), int(cx + 4), int(cy - 3))
        else:
            border_alpha = 100 if self._active else 50
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.5))
            painter.drawRoundedRect(rect, 5, 5)


# ==================== ШАГ ====================
class StepItem(QFrame):
    clicked = pyqtSignal(object)
    
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text
        self._done = False
        self._active = False
        
        self.setMinimumHeight(Style.STEP_MIN_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, Style.PAD_S, 0, Style.PAD_S)
        layout.setSpacing(Style.PAD_M)
        
        self.check = Checkbox()
        layout.addWidget(self.check, 0, Qt.AlignVCenter)
        
        self.label = QLabel()
        self.label.setFont(QFont("Segoe UI", Style.FONT_STEP))
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        layout.addWidget(self.label, 1)
        
        self._apply_style()
    
    def _base_text_color(self):
        if self._done:
            return Style.TEXT_DISABLED
        if self._active:
            return Style.TEXT_PRIMARY
        return Style.TEXT_SECONDARY
    
    def _apply_style(self):
        self.check.checked = self._done
        self.check.active = self._active
        
        base = self._base_text_color()
        self.label.setText(parse_step_markup(self.text, base, self._done))
        
        if self._done:
            self.setStyleSheet("background: transparent;")
        elif self._active:
            self.setStyleSheet(f"""
                StepItem {{
                    background: {Style.ACCENT_BG};
                    border-radius: {Style.RAD_S}px;
                    margin: 0;
                }}
            """)
        else:
            self.setStyleSheet("background: transparent;")
    
    @property
    def done(self):
        return self._done
    
    @done.setter
    def done(self, val):
        self._done = val
        self._apply_style()
    
    @property
    def active(self):
        return self._active
    
    @active.setter
    def active(self, val):
        self._active = val
        self._apply_style()
    
    def refresh_scale(self):
        self.setMinimumHeight(Style.STEP_MIN_H)
        self.layout().setContentsMargins(0, Style.PAD_S, 0, Style.PAD_S)
        self.label.setFont(QFont("Segoe UI", Style.FONT_STEP))
        self.check.refresh_scale()
        self._apply_style()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self)


# ==================== ГРУППА ====================
class GroupWidget(QFrame):
    step_clicked = pyqtSignal(object)
    
    def __init__(self, title: str, steps: list, parent=None):
        super().__init__(parent)
        self.title = title
        self._collapsed = False
        self._completion_time = None
        self.steps = []
        
        self.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, Style.PAD_S)
        layout.setSpacing(Style.PAD_XS)
        
        header_widget = QFrame()
        header_widget.setCursor(Qt.PointingHandCursor)
        header_widget.setStyleSheet("background: transparent;")
        header_widget.mousePressEvent = lambda e: self.toggle()
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, Style.PAD_M, 0, Style.PAD_S)
        header_layout.setSpacing(Style.PAD_S)
        
        self.header = QLabel(title)
        self.header.setFont(QFont("Segoe UI", Style.FONT_HEADER, QFont.DemiBold))
        self.header.setStyleSheet(f"color: {Style.TEXT_PRIMARY};")
        header_layout.addWidget(self.header)
        
        header_layout.addStretch()
        
        self.time_label = QLabel("")
        self.time_label.setFont(QFont("Segoe UI", Style.FONT_GROUP_TIME))
        self.time_label.setStyleSheet(f"color: {Style.ACCENT};")
        self.time_label.hide()
        header_layout.addWidget(self.time_label)
        
        layout.addWidget(header_widget)
        
        self.container = QFrame()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)
        
        for step_text in steps:
            item = StepItem(step_text)
            item.clicked.connect(self.step_clicked.emit)
            self.steps.append(item)
            self.container_layout.addWidget(item)
        
        layout.addWidget(self.container)
    
    def toggle(self):
        self._collapsed = not self._collapsed
        self.container.setVisible(not self._collapsed)
        color = Style.TEXT_MUTED if self._collapsed else Style.TEXT_PRIMARY
        self.header.setStyleSheet(f"color: {color};")
    
    def expand(self):
        if self._collapsed:
            self.toggle()
    
    def collapse(self):
        if not self._collapsed:
            self.toggle()
    
    def set_completion_time(self, time_str: str):
        self._completion_time = time_str
        self.time_label.setText(time_str)
        self.time_label.show()
    
    def clear_completion_time(self):
        self._completion_time = None
        self.time_label.hide()

    def refresh_scale(self):
        self.layout().setContentsMargins(0, 0, 0, Style.PAD_S)
        self.layout().setSpacing(Style.PAD_XS)
        header_layout = self.header.parentWidget().layout()
        header_layout.setContentsMargins(0, Style.PAD_M, 0, Style.PAD_S)
        header_layout.setSpacing(Style.PAD_S)
        self.header.setFont(QFont("Segoe UI", Style.FONT_HEADER, QFont.DemiBold))
        self.time_label.setFont(QFont("Segoe UI", Style.FONT_GROUP_TIME))
        for step in self.steps:
            step.refresh_scale()
    
    def is_completed(self) -> bool:
        return all(s.done for s in self.steps)
    
    def reset(self):
        for s in self.steps:
            s.done = False
        self.clear_completion_time()
        if self._collapsed:
            self.toggle()
    
    def get_state(self):
        return {
            "steps": [s.done for s in self.steps],
            "time": self._completion_time
        }
    
    def set_state(self, state):
        if isinstance(state, list):
            for i, done in enumerate(state):
                if i < len(self.steps):
                    self.steps[i].done = done
        else:
            for i, done in enumerate(state.get("steps", [])):
                if i < len(self.steps):
                    self.steps[i].done = done
            if state.get("time"):
                self.set_completion_time(state["time"])


# ==================== КОНТЕНТ ====================
class ContentArea(QScrollArea):
    progress_changed = pyqtSignal()
    first_step_started = pyqtSignal()
    active_step_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups = []
        self.all_steps = []
        self.current_index = 0
        self._first_step_done = False
        self._timer_ref = None
        self._group_start_times = {}
        
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(f"""
            QScrollArea {{ 
                background: transparent; 
                border: none; 
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: {Style.PAD_M}px 0;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.25);
            }}
            QScrollBar::add-line:vertical, 
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)
        
        self.steps_widget = QWidget()
        self.steps_widget.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.steps_widget)
        self.layout.setContentsMargins(0, 0, 0, Style.PAD_M)
        self.layout.setSpacing(0)
        self.setWidget(self.steps_widget)
        set_widget_transparent(self)
        set_widget_transparent(self.viewport())
    
    def set_timer(self, timer: Timer):
        self._timer_ref = timer
    
    def load(self, data: dict):
        for g in self.groups:
            g.deleteLater()
        self.groups.clear()
        self.all_steps.clear()
        self._group_start_times.clear()
        
        while self.layout.count():
            self.layout.takeAt(0)
        
        for name, steps in data.items():
            group = GroupWidget(name, steps)
            group.step_clicked.connect(self._on_click)
            self.groups.append(group)
            self.layout.addWidget(group)
            self.all_steps.extend(group.steps)
        
        self.layout.addStretch()
        
        if self.all_steps:
            self.all_steps[0].active = True
            self.current_index = 0
    
    def _get_current_group(self, step):
        for group in self.groups:
            if step in group.steps:
                return group
        return None
    
    def _on_click(self, step):
        was_first = not self._first_step_done
        
        step_index = self.all_steps.index(step)
        
        if not step.done:
            # Отметить этот и все предыдущие шаги как выполненные
            for i in range(step_index + 1):
                self.all_steps[i].done = True
            
            if was_first:
                self._first_step_done = True
                self.first_step_started.emit()
        else:
            # Снять отметку с этого и всех последующих шагов
            for i in range(step_index, len(self.all_steps)):
                self.all_steps[i].done = False
        
        self._check_all_groups()
        self._update_active()
        self.progress_changed.emit()
    
    def complete_current(self):
        if self.current_index < len(self.all_steps):
            step = self.all_steps[self.current_index]
            if not step.done:
                was_first = not self._first_step_done
                step.done = True
                
                if was_first:
                    self._first_step_done = True
                    self.first_step_started.emit()
                
                self._check_all_groups()
                self._update_active()
                self.progress_changed.emit()

    def previous_current(self):
        """Move progress back by one step and make that step active again."""
        completed = [index for index, step in enumerate(self.all_steps) if step.done]
        if not completed:
            return
        index = completed[-1]
        self.all_steps[index].done = False
        self._check_all_groups()
        self._update_active()
        self.progress_changed.emit()
    
    def _check_all_groups(self):
        for group in self.groups:
            group_idx = self.groups.index(group)
            
            # Инициализировать время старта группы
            if group_idx == 0:
                if group.title not in self._group_start_times:
                    self._group_start_times[group.title] = 0
            else:
                prev = self.groups[group_idx - 1]
                if prev.is_completed() and group.title not in self._group_start_times:
                    if prev._completion_time:
                        parts = prev._completion_time.split(":")
                        prev_elapsed = int(parts[0]) * 60 + int(parts[1])
                        prev_start = self._group_start_times.get(prev.title, 0)
                        self._group_start_times[group.title] = prev_start + prev_elapsed
                    elif self._timer_ref:
                        self._group_start_times[group.title] = self._timer_ref.get_elapsed()
            
            # Проверить завершение группы
            if group.is_completed():
                if not group._completion_time and self._timer_ref:
                    elapsed = self._timer_ref.get_elapsed()
                    start = self._group_start_times.get(group.title, 0)
                    group.set_completion_time(format_time(elapsed - start))
                    QTimer.singleShot(300, group.collapse)
            else:
                if group._completion_time:
                    group.clear_completion_time()
                    group.expand()
                # Убрать время старта если группа не завершена
                if group.title in self._group_start_times and group_idx > 0:
                    prev = self.groups[group_idx - 1]
                    if not prev.is_completed():
                        del self._group_start_times[group.title]
    
    def _update_active(self):
        for s in self.all_steps:
            s.active = False
        
        for i, s in enumerate(self.all_steps):
            if not s.done:
                s.active = True
                self.current_index = i
                
                for g in self.groups:
                    if s in g.steps:
                        g.expand()
                        break
                
                # Скролл после сворачивания акта (400мс > 300мс collapse)
                QTimer.singleShot(400, lambda step=s: self._scroll_to(step))
                self.active_step_changed.emit()
                return
        
        self.current_index = len(self.all_steps)
        self.active_step_changed.emit()

    def get_active_step_info(self):
        if not self.all_steps or self.current_index >= len(self.all_steps):
            return "", -1, ""
        step = self.all_steps[self.current_index]
        for group in self.groups:
            if step in group.steps:
                return group.title, group.steps.index(step), step.text
        return "", self.current_index, step.text
    
    def _scroll_to(self, step):
        try:
            if step is None or not step.isVisible():
                return
            y = step.mapTo(self.steps_widget, step.rect().topLeft()).y()
            h = self.viewport().height()
            target = y - h // 2 + step.height() // 2
            
            bar = self.verticalScrollBar()
            anim = QPropertyAnimation(bar, b"value", self)
            anim.setDuration(200)
            anim.setEndValue(max(0, target))
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
        except RuntimeError:
            pass
    
    def reset(self):
        self._first_step_done = False
        self._group_start_times.clear()
        for g in self.groups:
            g.reset()
        self._update_active()
        self.progress_changed.emit()
    
    def get_state(self):
        return {g.title: g.get_state() for g in self.groups}

    def progress_percent(self) -> float:
        total = len(self.all_steps)
        if total == 0:
            return 0.0
        completed = sum(1 for s in self.all_steps if s.done)
        return completed / total * 100.0
    
    def set_state(self, state):
        for g in self.groups:
            if g.title in state:
                g.set_state(state[g.title])
                if any(s.done for s in g.steps):
                    self._first_step_done = True
        self._update_active()


# ==================== РУЧКИ ИЗМЕНЕНИЯ РАЗМЕРА ====================
class _ResizeHandle(QLabel):
    def __init__(self, owner: "CornerResizeHandles", edge: str, symbol: str, cursor):
        super().__init__(symbol, owner)
        self._owner = owner
        self._edge = edge
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(cursor)
        self.setStyleSheet(f"""
            QLabel {{
                color: {Style.TEXT_MUTED};
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid {Style.BORDER};
                border-radius: 3px;
                font-size: {max(9, int(10 * Style.ui_scale()))}px;
            }}
            QLabel:hover {{
                color: {Style.TEXT_PRIMARY};
                background: rgba(255, 255, 255, 0.12);
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._owner._begin_resize(self._edge, event.globalPos())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._owner._active_edge == self._edge:
            self._owner._drag_resize(event.globalPos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._owner._active_edge == self._edge:
            self._owner._end_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class CornerResizeHandles(QWidget):
    """Ручка ◢ справа снизу — изменение размера по диагонали."""

    def __init__(
        self,
        target: QWidget,
        min_width: int,
        min_height: int,
        on_resize_end=None,
        collapsed_width_only: bool = False,
        parent=None,
    ):
        super().__init__(parent or target)
        self._target = target
        self._min_w = min_width
        self._min_h = min_height
        self._on_resize_end = on_resize_end
        self._collapsed_width_only = collapsed_width_only
        self._active_edge = None
        self._resize_start = None
        self._resize_geom = None
        self._handle_size = max(14, int(16 * Style.ui_scale()))

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self._corner = _ResizeHandle(self, "bottom-right", "◢", Qt.SizeFDiagCursor)
        self._corner.setFixedSize(self._handle_size, self._handle_size)

        self.reposition()

    def handles(self):
        return (self, self._corner)

    def set_collapsed_mode(self, collapsed: bool):
        self._collapsed_width_only = collapsed
        self.reposition()

    def reposition(self):
        if not self._target:
            return
        hs = self._handle_size
        inset = max(4, int(6 * Style.ui_scale()))
        box_w = hs + inset * 2
        box_h = hs + inset * 2
        self._corner.move(inset, inset)
        x = max(0, self._target.width() - box_w)
        y = max(0, self._target.height() - box_h)
        self.setFixedSize(box_w, box_h)
        self.move(x, y)
        self.raise_()

    def _begin_resize(self, edge: str, global_pos: QPoint):
        self._active_edge = edge
        self._resize_start = global_pos
        self._resize_geom = self._target.geometry()
        self.grabMouse()

    def _drag_resize(self, global_pos: QPoint):
        if not self._active_edge or self._resize_start is None or self._resize_geom is None:
            return
        diff = global_pos - self._resize_start
        g = self._resize_geom
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        edge = self._active_edge

        if self._collapsed_width_only:
            w = max(self._min_w, g.width() + diff.x())
            h = g.height()
        else:
            w = max(self._min_w, g.width() + diff.x())
            h = max(self._min_h, g.height() + diff.y())

        self._target.setGeometry(x, y, w, h)
        self.reposition()

    def mouseMoveEvent(self, event):
        if self._active_edge:
            self._drag_resize(event.globalPos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _end_resize(self):
        if self._active_edge:
            if self._on_resize_end:
                self._on_resize_end(self._target.size())
        self._active_edge = None
        self._resize_start = None
        self._resize_geom = None
        if self.mouseGrabber() == self:
            self.releaseMouse()

    def mouseReleaseEvent(self, event):
        self._end_resize()
        super().mouseReleaseEvent(event)


# ==================== ЛЕЙАУТЫ POE2 ====================
class LayoutHintDialog(QDialog):
    IMAGE_MIN_W = 200
    IMAGE_MAX_W = 520

    def __init__(self, parent=None):
        super().__init__(parent)
        self._overlay = parent
        self._catalog = load_poe2_layout_catalog()
        self._meta = load_json(get_data_file(POE2_LAYOUTS_FILE), {})
        self._manor_floor = 0
        self._manor_mode = False
        self._drag_pos = None
        self._source_pixmap = QPixmap()

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        min_w = max(320, int(360 * Style.ui_scale()))
        min_h = max(180, int(220 * Style.ui_scale()))
        self.setMinimumSize(min_w, min_h)

        self.setStyleSheet(f"""
            QDialog {{
                background: {Style.BG};
                border-radius: {Style.RAD_L}px;
                border: 1px solid {Style.BORDER};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(Style.PAD_L, Style.PAD_L, Style.PAD_L, Style.PAD_L)
        outer.setSpacing(Style.PAD_S)

        self._header = QWidget()
        self._header.setFixedHeight(36)
        self._header.setStyleSheet("background: transparent;")
        header_row = QHBoxLayout(self._header)
        header_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Лейаут зоны")
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        self.title_label.setStyleSheet(f"color: {Style.TEXT_PRIMARY};")
        header_row.addWidget(self.title_label, 1)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Style.TEXT_SECONDARY};
                font-size: 20px;
            }}
            QPushButton:hover {{ color: {Style.TEXT_PRIMARY}; }}
        """)
        self.close_btn.clicked.connect(self.close)
        header_row.addWidget(self.close_btn)
        outer.addWidget(self._header)

        self.floor_bar = QHBoxLayout()
        self.floor_bar.setSpacing(Style.PAD_XS)
        self._floor_buttons = []
        self._floor_group = QButtonGroup(self)
        self._floor_group.setExclusive(True)
        for i, label in enumerate(("Этаж 1", "Этаж 2", "Этаж 3"), start=0):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Style.BG_SECONDARY};
                    border: 1px solid {Style.BORDER};
                    border-radius: {Style.RAD_S}px;
                    color: {Style.TEXT_SECONDARY};
                    padding: 4px 10px;
                }}
                QPushButton:checked {{
                    background: {Style.ACCENT};
                    color: {Style.BG};
                    border-color: {Style.ACCENT};
                }}
            """)
            btn.clicked.connect(lambda _c=False, idx=i: self._on_manor_floor(idx))
            self._floor_group.addButton(btn, i)
            self._floor_buttons.append(btn)
            self.floor_bar.addWidget(btn)
        self._floor_widget = QWidget()
        self._floor_widget.setLayout(self.floor_bar)
        self._floor_widget.hide()
        outer.addWidget(self._floor_widget)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_body = QWidget()
        self.scroll_body.setStyleSheet("background: transparent;")
        self.body_layout = QVBoxLayout(self.scroll_body)
        self.body_layout.setContentsMargins(0, 0, 4, 0)
        self.body_layout.setSpacing(Style.PAD_S)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")
        self.body_layout.addWidget(self.image_label)

        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.RichText)
        self.content_label.setFont(QFont("Segoe UI", 11))
        self.content_label.setStyleSheet(f"color: {Style.TEXT_SECONDARY};")
        self.body_layout.addWidget(self.content_label)

        self.scroll.setWidget(self.scroll_body)
        outer.addWidget(self.scroll, 1)

        foot = QLabel()
        foot.setWordWrap(True)
        foot.setFont(QFont("Segoe UI", 9))
        foot.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        attr = self._meta.get("attribution", "")
        disc = self._meta.get("disclaimer", "")
        foot.setText(f"{disc}<br><span style='color:{Style.TEXT_MUTED}'>{attr}</span>")
        outer.addWidget(foot)

        self._click_through_timer = QTimer(self)
        self._click_through_timer.setInterval(40)
        self._click_through_timer.timeout.connect(self._sync_click_through_state)

        self._resize_handles = CornerResizeHandles(
            self, min_w, min_h, on_resize_end=self._on_resize_end
        )
        self.resize(self._load_saved_size(min_w, min_h))

    def _load_saved_size(self, min_w: int, min_h: int) -> QSize:
        ls = {}
        if self._overlay is not None:
            ls = self._overlay.settings.get(
                "layout_size", DEFAULT_SETTINGS.get("layout_size", {})
            )
        else:
            ls = DEFAULT_SETTINGS.get("layout_size", {})
        w = max(min_w, int(ls.get("width", 420)))
        h = max(min_h, int(ls.get("height", 520)))
        return QSize(w, h)

    def _save_layout_size(self):
        if self._overlay is None:
            return
        self._overlay.settings["layout_size"] = {
            "width": self.width(),
            "height": self.height(),
        }
        save_json(SETTINGS_FILE, self._overlay.settings)

    def _saved_position(self):
        if self._overlay is None:
            return None
        lp = self._overlay.settings.get(
            "layout_position", DEFAULT_SETTINGS.get("layout_position", {})
        )
        x, y = int(lp.get("x", -1)), int(lp.get("y", -1))
        if x < 0 or y < 0:
            return None
        return QPoint(x, y)

    def _clamp_position(self, pos: QPoint) -> QPoint:
        screen = QApplication.primaryScreen().availableGeometry()
        x = max(screen.left(), min(pos.x(), screen.right() - self.width() + 1))
        y = max(screen.top(), min(pos.y(), screen.bottom() - self.height() + 1))
        return QPoint(x, y)

    def apply_saved_position(self):
        saved = self._saved_position()
        if saved is not None:
            self.move(self._clamp_position(saved))

    def _save_layout_position(self):
        if self._overlay is None:
            return
        self._overlay.settings["layout_position"] = {
            "x": self.x(),
            "y": self.y(),
        }
        save_json(SETTINGS_FILE, self._overlay.settings)

    def _on_resize_end(self, size: QSize):
        if self._overlay is None:
            return
        self._overlay.settings["layout_size"] = {
            "width": size.width(),
            "height": size.height(),
        }
        save_json(SETTINGS_FILE, self._overlay.settings)
        self._refresh_layout_image()

    def scroll_to_top(self):
        bar = self.scroll.verticalScrollBar()
        if bar is not None:
            bar.setValue(bar.minimum())

    def _layout_image_width(self) -> int:
        """Ширина картинки: как раньше (200–520), растёт если окно шире."""
        margin = Style.PAD_L * 4
        vp = self.scroll.viewport()
        if vp is not None and vp.width() > 120:
            avail = vp.width() - 8
        else:
            avail = self.width() - margin
        base = max(self.IMAGE_MIN_W, avail)
        if avail <= self.IMAGE_MAX_W:
            return min(self.IMAGE_MAX_W, base)
        return base

    def _refresh_layout_image(self):
        if self._source_pixmap.isNull() or not self.image_label.isVisible():
            return
        img_w = self._layout_image_width()
        scaled = self._source_pixmap.scaledToWidth(
            img_w, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")
        self.image_label.adjustSize()
        self.scroll_body.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_layout_image()
        if hasattr(self, "_resize_handles"):
            self._resize_handles.reposition()

    def _click_through_enabled(self) -> bool:
        parent = self.parent()
        if parent is None:
            return False
        return bool(parent.settings.get("click_through", False))

    def _widget_hit(self, widget, global_pos: QPoint, pad: int = 6) -> bool:
        if widget is None or not widget.isVisible():
            return False
        top_left = widget.mapToGlobal(QPoint(0, 0))
        hit = QRect(
            top_left.x() - pad,
            top_left.y() - pad,
            widget.width() + pad * 2,
            widget.height() + pad * 2,
        )
        return hit.contains(global_pos)

    def _in_header(self, pos: QPoint) -> bool:
        return self._header.geometry().contains(pos)

    def _hit_test_interactive(self, global_pos: QPoint) -> bool:
        if self._widget_hit(self._header, global_pos):
            return True
        if hasattr(self, "_resize_handles"):
            for w in self._resize_handles.handles():
                if self._widget_hit(w, global_pos):
                    return True
        if self._floor_widget.isVisible():
            for btn in self._floor_buttons:
                if self._widget_hit(btn, global_pos):
                    return True
        if self.scroll.isVisible() and self._widget_hit(self.scroll, global_pos):
            return True
        return False

    def _sync_click_through_state(self):
        if not self._click_through_enabled():
            set_window_click_through(self, False)
            return
        passthrough = not self._hit_test_interactive(QCursor.pos())
        set_window_click_through(self, passthrough)

    def _apply_click_through_mode(self):
        if self._click_through_enabled() and sys.platform == "win32":
            self._click_through_timer.start()
            self._sync_click_through_state()
        else:
            self._click_through_timer.stop()
            set_window_click_through(self, False)

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_click_through_mode()
        QTimer.singleShot(0, self._refresh_layout_image)

    def hideEvent(self, event):
        self._click_through_timer.stop()
        set_window_click_through(self, False)
        super().hideEvent(event)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.LeftButton
            and self._in_header(event.pos())
            and not self._widget_hit(self.close_btn, event.globalPos(), pad=2)
        ):
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(self._clamp_position(event.globalPos() - self._drag_pos))
        elif (
            self._in_header(event.pos())
            and not self._widget_hit(self.close_btn, event.globalPos(), pad=2)
        ):
            self.setCursor(Qt.SizeAllCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_pos is not None and event.button() == Qt.LeftButton:
            self._save_layout_position()
        self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        self._click_through_timer.stop()
        set_window_click_through(self, False)
        self._save_layout_size()
        self._save_layout_position()
        super().closeEvent(event)

    def set_opacity(self, value: float):
        # The zone/tree helper is a separate utility window and must remain
        # fully readable regardless of the main overlay opacity.
        self.setWindowOpacity(1.0)

    def _on_manor_floor(self, index: int):
        self._manor_floor = index
        self._floor_buttons[index].setChecked(True)
        self._show_layout_id(MANOR_FLOOR_IDS[index])

    def show_no_layout(self):
        self._manor_mode = False
        self._source_pixmap = QPixmap()
        self._floor_widget.hide()
        self.image_label.hide()
        self.title_label.setText("Лейаут")
        self.content_label.setText(
            f"<p style='color:{Style.TEXT_SECONDARY}'>"
            "Для этого шага нет карты лейаута.</p>"
        )
        self.scroll_to_top()

    def show_for_step(self, act: str, step_index: int, step_text: str):
        layout_id = resolve_layout_id(act, step_index, step_text)
        if not layout_id:
            self.show_no_layout()
            return

        if layout_id == "ogham_manor" or layout_id in MANOR_FLOOR_IDS:
            self._manor_mode = True
            self._floor_widget.show()
            floor = 0
            if layout_id in MANOR_FLOOR_IDS:
                floor = MANOR_FLOOR_IDS.index(layout_id)
            elif "Граф Жеонор" in step_text:
                floor = 2
            self._manor_floor = floor
            self._floor_buttons[floor].setChecked(True)
            self._show_layout_id(MANOR_FLOOR_IDS[floor])
            return

        self._manor_mode = False
        self._floor_widget.hide()
        self._show_layout_id(layout_id)

    def _show_layout_id(self, layout_id: str):
        entry = self._catalog.get(layout_id)
        if not entry:
            self.show_no_layout()
            return

        self.title_label.setText(entry.get("title", layout_id))
        self.image_label.show()

        img_path = layout_asset_path(entry.get("image", ""))
        pixmap = QPixmap(str(img_path)) if img_path.is_file() else QPixmap()
        self._source_pixmap = pixmap
        if pixmap.isNull():
            self.image_label.setPixmap(QPixmap())
            self.image_label.setFixedSize(0, 0)
            self.image_label.setText("Изображение не найдено")
        else:
            self._refresh_layout_image()

        parts = []
        conf = entry.get("confidence_ru")
        if conf:
            parts.append(
                f"<p><b style='color:{Style.TEXT_PRIMARY}'>Уверенность:</b> "
                f"<span style='color:{Style.ACCENT}'>{conf}</span></p>"
            )
        route = entry.get("route") or []
        if route:
            items = "".join(
                f"<li>{line}</li>" for line in route
            )
            parts.append(
                f"<p><b style='color:{Style.TEXT_PRIMARY}'>Маршрут</b></p><ol>{items}</ol>"
            )
        clues = entry.get("clues") or []
        if clues:
            items = "".join(f"<li>{line}</li>" for line in clues)
            parts.append(
                f"<p><b style='color:{Style.TEXT_PRIMARY}'>Подсказки</b></p><ul>{items}</ul>"
            )
        speedrun = entry.get("speedrun")
        if speedrun:
            parts.append(
                f"<p><b style='color:{Style.ACCENT}'>Speedrun:</b> {speedrun}</p>"
            )

        self.content_label.setText("".join(parts))
        QTimer.singleShot(0, self._refresh_layout_image)
        self.scroll_to_top()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


# ==================== ПРИВЕТСТВИЕ ====================
class WelcomePanel(QFrame):
    dismissed = pyqtSignal(bool)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(Style.PAD_S)

        title = QLabel("Добро пожаловать в ActPilot")
        title.setFont(QFont("Segoe UI", 16, QFont.DemiBold))
        title.setStyleSheet(f"color: {Style.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        outer.addWidget(title)

        sub = QLabel("Краткий обзор")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        sub.setAlignment(Qt.AlignCenter)
        outer.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px; min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        """)

        scroll_body = QWidget()
        scroll_body.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_body)
        scroll_layout.setContentsMargins(0, 0, 4, 0)

        step_hk = display_hotkey(settings.get("hotkey", DEFAULT_SETTINGS["hotkey"]))
        layout_hk = display_hotkey(settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"]))

        body = QLabel(
            f"<p style='line-height:155%; color:{Style.TEXT_SECONDARY};'>"
            f"<b style='color:{Style.TEXT_PRIMARY};'>Горячие клавиши</b><br>"
            f"• <b>{step_hk}</b> — следующий шаг<br>"
            f"• <b>{layout_hk}</b> — мини-панель билда (PoE1) / лейаут зоны (PoE2)<br>"
            f"Переназначить можно в настройках (⚙).</p>"
            f"<p style='line-height:155%; color:{Style.TEXT_SECONDARY};'>"
            f"<b style='color:{Style.TEXT_PRIMARY};'>Настройки</b><br>"
            f"• Масштаб интерфейса можно изменить, можно включить клики сквозь оверлей<br>"
            f"• Оверлей и окно подсказок за шапку можно перетаскивать<br>"
            f"• Кнопка <b>◢</b> справа снизу — тянуть для изменения размера<br>"
            "</p>"
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setFont(QFont("Segoe UI", 11))
        scroll_layout.addWidget(body)
        scroll.setWidget(scroll_body)
        outer.addWidget(scroll, 1)

        self.dont_show_checkbox = QCheckBox("Больше не показывать")
        self.dont_show_checkbox.setFont(QFont("Segoe UI", 10))
        self.dont_show_checkbox.setCursor(Qt.PointingHandCursor)
        self.dont_show_checkbox.setStyleSheet(f"""
            QCheckBox {{ color: {Style.TEXT_SECONDARY}; spacing: {Style.PAD_S}px; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px; border-radius: 4px;
                border: 1.5px solid rgba(255, 255, 255, 0.25);
                background: {Style.BG_SECONDARY};
            }}
            QCheckBox::indicator:checked {{
                background: {Style.ACCENT}; border-color: {Style.ACCENT};
            }}
        """)
        outer.addWidget(self.dont_show_checkbox)

        ok_btn = QPushButton("Понятно")
        ok_btn.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        ok_btn.setFixedHeight(40)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Style.ACCENT};
                border: none;
                border-radius: {Style.RAD_S}px;
                color: {Style.BG};
            }}
            QPushButton:hover {{ background: #22c55e; }}
        """)
        ok_btn.clicked.connect(self._on_ok)
        outer.addWidget(ok_btn)

    def _on_ok(self):
        self.dismissed.emit(self.dont_show_checkbox.isChecked())


# ==================== НАСТРОЙКИ ====================
class SettingsDialog(QDialog):
    DIALOG_W = 340
    DIALOG_H = 520

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self._should_reset = False

        screen = QApplication.primaryScreen()
        max_h = int(screen.availableGeometry().height() * 0.85) if screen else 700
        dialog_h = min(self.DIALOG_H, max_h)

        self.setFixedSize(self.DIALOG_W, dialog_h)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)

        self.setStyleSheet(f"""
            QDialog {{
                background: {Style.BG};
                border-radius: {Style.RAD_L}px;
                border: 1px solid {Style.BORDER};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(Style.PAD_M)
        layout.setContentsMargins(Style.PAD_XL, Style.PAD_XL, Style.PAD_XL, Style.PAD_XL)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Light))
        title.setStyleSheet(f"color: {Style.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.25);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content = QVBoxLayout(scroll_content)
        content.setSpacing(Style.PAD_M)
        content.setContentsMargins(0, 0, 4, 0)

        # Game
        self.poe2_checkbox = QCheckBox("Path of Exile 2")
        self.poe2_checkbox.setFont(QFont("Segoe UI", 11))
        self.poe2_checkbox.setChecked(settings.get("game", GAME_POE2) == GAME_POE2)
        self.poe2_checkbox.setCursor(Qt.PointingHandCursor)
        self.poe2_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {Style.TEXT_SECONDARY};
                spacing: {Style.PAD_S}px;
            }}
            QCheckBox:hover {{
                color: {Style.TEXT_PRIMARY};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1.5px solid rgba(255, 255, 255, 0.25);
                background: {Style.BG_SECONDARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: rgba(255, 255, 255, 0.4);
            }}
            QCheckBox::indicator:checked {{
                background: {Style.ACCENT};
                border-color: {Style.ACCENT};
            }}
        """)
        content.addWidget(self.poe2_checkbox)

        self.click_through_checkbox = QCheckBox("Клики сквозь оверлей")
        self.click_through_checkbox.setFont(QFont("Segoe UI", 11))
        self.click_through_checkbox.setChecked(settings.get("click_through", False))
        self.click_through_checkbox.setCursor(Qt.PointingHandCursor)
        self.click_through_checkbox.setStyleSheet(self.poe2_checkbox.styleSheet())
        content.addWidget(self.click_through_checkbox)

        content.addSpacing(Style.PAD_XS)

        hk_label = QLabel("Hotkey")
        hk_label.setFont(QFont("Segoe UI", 10))
        hk_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(hk_label)
        
        self.hotkey_input = QLineEdit(display_hotkey(settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])))
        self.hotkey_input.setFont(QFont("Segoe UI", 12))
        self.hotkey_input.setFixedHeight(44)
        self.hotkey_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Style.BG_SECONDARY};
                border: 1px solid {Style.BORDER};
                border-radius: {Style.RAD_S}px;
                padding: 0 {Style.PAD_M}px;
                color: {Style.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Style.ACCENT};
            }}
        """)
        content.addWidget(self.hotkey_input)

        op_label = QLabel("Opacity")
        op_label.setFont(QFont("Segoe UI", 10))
        op_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(op_label)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setFixedHeight(28)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(settings.get("opacity", 0.95) * 100))
        self.opacity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {Style.BG_SECONDARY};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {Style.TEXT_SECONDARY};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Style.TEXT_PRIMARY};
            }}
            QSlider::sub-page:horizontal {{
                background: {Style.ACCENT};
                border-radius: 2px;
            }}
        """)
        content.addWidget(self.opacity_slider)

        layout_hk_label = QLabel("Хоткей лейаута (PoE2)")
        layout_hk_label.setFont(QFont("Segoe UI", 10))
        layout_hk_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(layout_hk_label)

        self.layout_hotkey_input = QLineEdit(
            display_hotkey(settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"]))
        )
        self.layout_hotkey_input.setFont(QFont("Segoe UI", 12))
        self.layout_hotkey_input.setFixedHeight(44)
        self.layout_hotkey_input.setStyleSheet(self.hotkey_input.styleSheet())
        content.addWidget(self.layout_hotkey_input)

        layout_op_label = QLabel("Прозрачность подсказки")
        layout_op_label.setFont(QFont("Segoe UI", 10))
        layout_op_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(layout_op_label)

        self.layout_opacity_slider = QSlider(Qt.Horizontal)
        self.layout_opacity_slider.setFixedHeight(28)
        self.layout_opacity_slider.setRange(50, 100)
        self.layout_opacity_slider.setValue(
            int(settings.get("layout_opacity", DEFAULT_SETTINGS["layout_opacity"]) * 100)
        )
        self.layout_opacity_slider.setStyleSheet(self.opacity_slider.styleSheet())
        content.addWidget(self.layout_opacity_slider)

        scale_label = QLabel("Масштаб интерфейса")
        scale_label.setFont(QFont("Segoe UI", 10))
        scale_label.setStyleSheet(f"color: {Style.TEXT_MUTED};")
        content.addWidget(scale_label)

        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setFixedHeight(28)
        self.scale_slider.setRange(int(Style.UI_SCALE_MIN * 100), int(Style.UI_SCALE_MAX * 100))
        self.scale_slider.setValue(int(settings.get("ui_scale", 1.0) * 100))
        self.scale_slider.setStyleSheet(self.opacity_slider.styleSheet())
        content.addWidget(self.scale_slider)

        self.scale_value_label = QLabel(f"{self.scale_slider.value()}%")
        self.scale_value_label.setFont(QFont("Segoe UI", 10))
        self.scale_value_label.setStyleSheet(f"color: {Style.TEXT_SECONDARY};")
        self.scale_value_label.setAlignment(Qt.AlignRight)
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_value_label.setText(f"{v}%")
        )
        content.addWidget(self.scale_value_label)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        reset_btn = QPushButton("Reset progress")
        reset_btn.setFont(QFont("Segoe UI", 11))
        reset_btn.setFixedHeight(40)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {Style.DANGER};
            }}
            QPushButton:hover {{
                color: #fca5a5;
            }}
        """)
        reset_btn.clicked.connect(self._reset)
        layout.addWidget(reset_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Style.PAD_M)
        
        cancel = QPushButton("Cancel")
        cancel.setFont(QFont("Segoe UI", 11))
        cancel.setFixedHeight(44)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: {Style.BG_SECONDARY};
                border: 1px solid {Style.BORDER};
                border-radius: {Style.RAD_S}px;
                color: {Style.TEXT_SECONDARY};
            }}
            QPushButton:hover {{
                background: {Style.HOVER};
            }}
        """)
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        
        save = QPushButton("Save")
        save.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        save.setFixedHeight(44)
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(f"""
            QPushButton {{
                background: {Style.ACCENT};
                border: none;
                border-radius: {Style.RAD_S}px;
                color: {Style.BG};
            }}
            QPushButton:hover {{
                background: #22c55e;
            }}
        """)
        save.clicked.connect(self.accept)
        btn_layout.addWidget(save)
        
        layout.addLayout(btn_layout)
    
    def _reset(self):
        self._should_reset = True
        self.accept()
    
    def get_settings(self):
        self.settings["hotkey"] = normalize_hotkey(self.hotkey_input.text())
        self.settings["opacity"] = self.opacity_slider.value() / 100
        self.settings["layout_hotkey"] = normalize_hotkey(self.layout_hotkey_input.text())
        self.settings["layout_opacity"] = self.layout_opacity_slider.value() / 100
        self.settings["game"] = GAME_POE2 if self.poe2_checkbox.isChecked() else GAME_POE1
        self.settings["click_through"] = self.click_through_checkbox.isChecked()
        self.settings["ui_scale"] = self.scale_slider.value() / 100.0
        return self.settings
    
    @property
    def should_reset(self):
        return self._should_reset


# ==================== ГЛАВНОЕ ОКНО ====================
class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        
        ensure_dirs()
        migrate_legacy_progress()
        self.settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        if migrate_settings(self.settings):
            save_json(SETTINGS_FILE, self.settings)
        self.settings["hotkey"] = normalize_hotkey(
            self.settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])
        )
        self.settings["layout_hotkey"] = normalize_hotkey(
            self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
        )
        self._ui_scale = float(self.settings.get("ui_scale", DEFAULT_SETTINGS["ui_scale"]))
        Style.set_ui_scale(self._ui_scale)
        self.game = self.settings.get("game", DEFAULT_SETTINGS["game"])
        self._load_steps_data()
        
        self._collapsed = False
        self._welcome_dismissed_session = False
        size = self.settings.get("size", DEFAULT_SETTINGS["size"])
        self._expanded_size = QSize(size["width"], size["height"])
        self._resizing = False
        self._resize_edge = None
        self._drag_pos = None
        self._bg_pixmap = load_background_pixmap()
        self._has_bg = not self._bg_pixmap.isNull()
        
        self.hotkey = HotkeyListener(self.settings["hotkey"])
        self.previous_hotkey = HotkeyListener(
            self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])
        )
        self.layout_hotkey = HotkeyListener(
            self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
        )
        self.regex_hotkey = HotkeyListener(
            self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])
        )
        self._layout_dialog = None
        self._regex_dialog = None
        self._regex_restore_state = None
        
        self._setup_ui()
        self._setup_hotkey()
        self._load_progress()
    
    def _load_steps_data(self):
        steps_file = get_steps_file(self.game)
        default = DEFAULT_STEPS_POE2 if self.game == GAME_POE2 else DEFAULT_STEPS
        self.steps_data = load_json(steps_file, default)
        if not steps_file.exists():
            try:
                save_json(steps_file, default)
            except OSError:
                pass
    
    def _switch_game(self, game: str):
        self.game = game
        self._load_steps_data()
        self.content.load(self.steps_data)
        self.timer.reset()
        self._load_progress()
        self._start_hotkey()
        
    def _setup_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setMouseTracking(True)
        self.setMinimumSize(max(150, int(280 * Style.ui_scale())), max(100, int(180 * Style.ui_scale())))
        
        size = self.settings.get("size", DEFAULT_SETTINGS["size"])
        self._expanded_size = QSize(size["width"], size["height"])
        self.resize(self._expanded_size)
        
        screen = QApplication.primaryScreen().geometry()
        pos = self.settings.get("position", DEFAULT_SETTINGS["position"])
        x = pos["x"] if pos["x"] >= 0 else screen.width() - self.width() - 40
        self.move(x, pos["y"])
        
        if self._has_bg:
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WA_NoSystemBackground, True)
            self.setStyleSheet("""
                QWidget#main {
                    background: transparent;
                    border: none;
                }
                QWidget {
                    background: transparent;
                }
            """)
        else:
            self.setStyleSheet(f"""
                QWidget#main {{
                    background: {Style.BG};
                    border-radius: {Style.RAD_L}px;
                    border: 1px solid {Style.BORDER};
                }}
            """)
        self.setObjectName("main")
        set_widget_transparent(self)
        
        self._panel_margins = Style.panel_margins(self._has_bg)
        pad_x, panel_top, pad_right, panel_bottom = self._panel_margins

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(pad_x, panel_top, pad_right, panel_bottom)
        self._main_layout.setSpacing(0)
        layout = self._main_layout
        
        # Header
        self.header = QFrame()
        self.header.setFixedHeight(Style.HEADER_H)
        self.header.setStyleSheet("background: transparent;")
        self.header.setMouseTracking(True)
        
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(Style.PAD_S)
        
        self.logo_label = None
        logo = scaled_ui_pixmap("logo", height=Style.LOGO_HEIGHT)
        if not logo.isNull():
            self.logo_label = QLabel()
            self.logo_label.setPixmap(logo)
            self.logo_label.setStyleSheet("background: transparent;")
            set_widget_transparent(self.logo_label)
            h_layout.addWidget(self.logo_label, 0, Qt.AlignVCenter)
        
        h_layout.addStretch()
        
        self.collapse_btn = make_icon_button(
            "collapse", "−", Style.BTN_SIZE, self._toggle, self.header
        )
        align = Qt.AlignVCenter
        h_layout.addWidget(self.collapse_btn, 0, align)
        self.settings_btn = make_icon_button(
            "settings", "⚙", Style.BTN_SIZE, self._settings, self.header
        )
        self.close_btn = make_icon_button(
            "close", "×", Style.BTN_SIZE, self.close, self.header
        )
        h_layout.addWidget(self.settings_btn, 0, align)
        h_layout.addWidget(self.close_btn, 0, align)
        
        layout.addWidget(self.header)
        
        # Body
        self.body = QFrame()
        self.body.setStyleSheet("background: transparent;")
        self.body.setMouseTracking(True)
        
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        
        self.timer = Timer()
        body_layout.addWidget(self.timer)
        body_layout.addSpacing(Style.PAD_XS)

        self.progress_bar = FantasyProgressBar()
        body_layout.addWidget(self.progress_bar)
        body_layout.addSpacing(Style.PAD_S)

        self.welcome_panel = WelcomePanel(self.settings)
        self.welcome_panel.dismissed.connect(self._on_welcome_dismissed)
        body_layout.addWidget(self.welcome_panel, 1)
        
        self.content = ContentArea()
        self.content.set_timer(self.timer)
        self.content.load(self.steps_data)
        self.content.progress_changed.connect(self._update_progress_bar)
        self.content.progress_changed.connect(self._save_progress)
        self.content.first_step_started.connect(self._on_first_step)
        self.content.active_step_changed.connect(self._on_active_step_changed)
        body_layout.addWidget(self.content, 1)

        self.hotkey_footer = HotkeyFooter()
        self.hotkey_footer.setObjectName("hotkeyFooter")
        self.hotkey_footer.setStyleSheet(
            "color:#a9a08e; background:transparent; border:0; font-size:8px; padding:3px 1px 0 1px;"
        )
        body_layout.addWidget(self.hotkey_footer)
        self._refresh_hotkey_footer()

        self._apply_welcome_visibility()
        
        layout.addWidget(self.body, 1)
        
        min_w = max(150, int(280 * Style.ui_scale()))
        min_h = max(100, int(180 * Style.ui_scale()))
        self._resize_handles = CornerResizeHandles(
            self,
            min_w,
            min_h,
            on_resize_end=self._on_corner_resize_end,
            collapsed_width_only=self._collapsed,
        )
        
        self._apply_transparent_layers()
        self._update_opacity()
        self._update_progress_bar()

        self._click_through_enabled = False
        self._click_through_timer = QTimer(self)
        self._click_through_timer.setInterval(40)
        self._click_through_timer.timeout.connect(self._sync_click_through_state)
    
    def _apply_transparent_layers(self):
        for widget in (
            self.header,
            self.body,
            self.timer,
            self.progress_bar,
            self.content,
            self.content.viewport(),
            self.content.steps_widget,
            self.welcome_panel,
        ):
            set_widget_transparent(widget)
        for w in self.welcome_panel.findChildren(QWidget):
            set_widget_transparent(w)
        if hasattr(self, "_resize_handles"):
            for w in self._resize_handles.handles():
                set_widget_transparent(w)
        for label in self.timer.findChildren(QLabel):
            set_widget_transparent(label)
        self.timer.set_control_button_theme(filled=not self._has_bg)
    
    def _update_progress_bar(self):
        if self.content.isVisible():
            self.progress_bar.setValue(self.content.progress_percent())

    def _apply_welcome_visibility(self):
        show = (
            bool(self.settings.get("show_welcome", True))
            and not self._collapsed
            and not self._welcome_dismissed_session
        )
        self.welcome_panel.setVisible(show)
        self.timer.setVisible(not show)
        self.progress_bar.setVisible(not show)
        self.content.setVisible(not show)

    def _on_welcome_dismissed(self, dont_show_again: bool):
        self._welcome_dismissed_session = True
        if dont_show_again:
            self.settings["show_welcome"] = False
            save_json(SETTINGS_FILE, self.settings)
        self._apply_welcome_visibility()
        self._update_progress_bar()
    
    def _apply_panel_margins(self):
        self._panel_margins = Style.panel_margins(self._has_bg)
        pad_x, panel_top, pad_right, panel_bottom = self._panel_margins
        self._main_layout.setContentsMargins(pad_x, panel_top, pad_right, panel_bottom)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._has_bg:
            borders = (
                Style.BG_SLICE_LEFT,
                Style.BG_SLICE_TOP,
                Style.BG_SLICE_RIGHT,
                Style.BG_SLICE_BOTTOM,
            )
            draw_nine_slice(painter, self._bg_pixmap, self.rect(), borders)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(Style.BG))
            painter.drawRoundedRect(self.rect(), Style.RAD_L, Style.RAD_L)
        painter.end()
        super().paintEvent(event)
    
    def _update_opacity(self):
        opacity = self.settings.get("opacity", 0.95)
        self.setWindowOpacity(opacity)

    def _on_corner_resize_end(self, size: QSize):
        if not self._collapsed:
            self._expanded_size = size

    def _reposition_resize_handles(self):
        if hasattr(self, "_resize_handles"):
            self._resize_handles.reposition()

    def _refresh_icon_button(self, btn: QPushButton, asset: str, fallback: str):
        size = Style.BTN_SIZE
        btn.setFixedSize(size, size)
        if asset == "collapse":
            btn.setIcon(QIcon())
            btn.setText("+" if self._collapsed else "−")
            btn.setFont(QFont("Segoe UI", max(10, int(round(13 * Style.ui_scale())))))
            btn.setStyleSheet("""
                QPushButton { background:transparent; color:#c9a35a; border:0; padding:0; }
                QPushButton:hover { background:rgba(122,83,30,.18); border-radius:6px; }
                QPushButton:pressed { background:rgba(172,124,47,.24); }
            """)
            return
        icon = scaled_ui_pixmap(asset, size, size)
        if not icon.isNull():
            btn.setIcon(QIcon(icon))
            btn.setIconSize(icon.size())
            btn.setText("")
        else:
            btn.setIcon(QIcon())
            btn.setText(fallback)

    def _refresh_header(self):
        if self.logo_label is not None:
            logo = scaled_ui_pixmap("logo", height=Style.LOGO_HEIGHT)
            if not logo.isNull():
                self.logo_label.setPixmap(logo)
        self._refresh_icon_button(self.collapse_btn, "collapse", "−")
        self._refresh_icon_button(self.settings_btn, "settings", "⚙")
        self._refresh_icon_button(self.close_btn, "close", "×")
        self.header.layout().setSpacing(Style.PAD_S)

    def _apply_ui_scale(self, old_scale: float, new_scale: float):
        if abs(old_scale - new_scale) < 0.001:
            return
        Style.set_ui_scale(new_scale)
        ratio = new_scale / old_scale if old_scale > 0 else new_scale

        self._apply_panel_margins()

        if self._collapsed:
            w = max(150, int(self.width() * ratio))
            self.setFixedSize(w, Style.collapsed_height(self._has_bg))
        else:
            w = max(150, int(self._expanded_size.width() * ratio))
            h = max(100, int(self._expanded_size.height() * ratio))
            self._expanded_size = QSize(w, h)
            self.resize(self._expanded_size)

        self.setMinimumSize(max(150, int(280 * new_scale)), max(100, int(180 * new_scale)))
        self.header.setFixedHeight(Style.HEADER_H)
        self._refresh_header()
        self.timer.refresh_scale()
        self.progress_bar.refresh_scale()
        for group in self.content.groups:
            group.refresh_scale()
        self._reposition_resize_handles()
        self.update()

    def _interactive_widgets(self):
        widgets = [
            self.collapse_btn,
            self.settings_btn,
            self.close_btn,
            self.timer.btn,
        ]
        if hasattr(self, "_resize_handles"):
            widgets.extend(self._resize_handles.handles())
        return widgets

    def _hit_test_interactive(self, global_pos: QPoint) -> bool:
        # Click-through must never swallow the title bar: it is the permanent
        # grab handle for moving the overlay, including in passthrough mode.
        if self.header is not None and self.header.isVisible():
            header_top_left = self.header.mapToGlobal(QPoint(0, 0))
            if QRect(header_top_left, self.header.size()).contains(global_pos):
                return True
        if self.welcome_panel.isVisible():
            top_left = self.welcome_panel.mapToGlobal(QPoint(0, 0))
            if QRect(top_left, self.welcome_panel.size()).contains(global_pos):
                return True
        pad = 6
        for widget in self._interactive_widgets():
            if widget is None or not widget.isVisible() or not widget.isEnabled():
                continue
            top_left = widget.mapToGlobal(QPoint(0, 0))
            hit = QRect(
                top_left.x() - pad,
                top_left.y() - pad,
                widget.width() + pad * 2,
                widget.height() + pad * 2,
            )
            if hit.contains(global_pos):
                return True
        return False

    def _sync_click_through_state(self):
        if not self._click_through_enabled:
            set_window_click_through(self, False)
            return
        pos = QCursor.pos()
        over_overlay = self.frameGeometry().contains(pos)
        passthrough = not over_overlay or not self._hit_test_interactive(pos)
        set_window_click_through(self, passthrough)

    def _apply_click_through_mode(self):
        self._click_through_enabled = bool(self.settings.get("click_through", False))
        if self._click_through_enabled and sys.platform == "win32":
            self._click_through_timer.start()
            self._sync_click_through_state()
        else:
            self._click_through_timer.stop()
            set_window_click_through(self, False)
        if self._layout_dialog is not None and self._layout_dialog.isVisible():
            self._layout_dialog._apply_click_through_mode()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_click_through_mode()
        if not getattr(self, "_hotkey_started", False):
            self._hotkey_started = True
            QTimer.singleShot(0, self._start_hotkey)

    def _setup_hotkey(self):
        self._previous_combo_active = False
        self.hotkey.triggered.connect(self._on_next_hotkey)
        self.previous_hotkey.triggered.connect(self._on_previous_hotkey)
        self.layout_hotkey.triggered.connect(self._toggle_layout_hint)
        self.regex_hotkey.triggered.connect(self._toggle_regex_dialog)
        for listener, key in (
            (self.hotkey, "hotkey"),
            (self.previous_hotkey, "previous_hotkey"),
            (self.layout_hotkey, "layout_hotkey"),
            (self.regex_hotkey, "regex_hotkey"),
        ):
            listener.failed.connect(
                lambda error, key=key: self._notify_hotkey_error(
                    self.settings.get(key, DEFAULT_SETTINGS.get(key, "")), error
                )
            )

    def _notify_hotkey_error(self, hotkey: str, error: str):
        box = getattr(self, "_hotkey_error_box", None)
        if box is None:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Горячие клавиши")
            box.setWindowModality(Qt.NonModal)
            self._hotkey_error_box = box
        elif box.isVisible():
            return
        box.setText(
            f"Не удалось включить горячую клавишу {display_hotkey(hotkey)}.\n"
            f"{error}\nИзменить её можно в настройках (⚙)."
        )
        box.show()

    def _on_previous_hotkey(self):
        self._previous_combo_active = True
        self.content.previous_current()
        QTimer.singleShot(120, lambda: setattr(self, "_previous_combo_active", False))

    def _on_next_hotkey(self):
        # Ctrl+F3 can also be observed by the plain F3 listener. Delay the
        # plain action briefly so the more specific shortcut can suppress it.
        QTimer.singleShot(
            45,
            lambda: None if self._previous_combo_active else self.content.complete_current(),
        )

    def _start_hotkey(self):
        self.hotkey.restart(self.settings["hotkey"])
        self.previous_hotkey.restart(
            self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])
        )
        self.regex_hotkey.restart(
            self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])
        )
        if self.game == GAME_POE2:
            self.layout_hotkey.restart(
                self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])
            )
        else:
            self.layout_hotkey.stop()
        self._refresh_hotkey_footer()

    def _save_regexes(self, entries):
        self.settings["regexes"] = entries
        save_json(SETTINGS_FILE, self.settings)

    def _toggle_regex_dialog(self):
        if self._regex_dialog is not None and self._regex_dialog.isVisible():
            self._regex_dialog.hide()
            return
        if self._regex_dialog is None:
            self._regex_dialog = RegexDialog(
                self.settings.get("regexes", DEFAULT_REGEXES), self._save_regexes, None
            )
            self._regex_dialog.hidden.connect(self._restore_after_regex)
        self._regex_restore_state = {
            "overlay": self.isVisible(),
            "layout": bool(self._layout_dialog is not None and self._layout_dialog.isVisible()),
            "build": bool(
                getattr(self, "_build_dialog", None) is not None
                and self._build_dialog.isVisible()
            ),
        }
        if self._regex_restore_state["layout"]:
            self._layout_dialog.hide()
        if self._regex_restore_state["build"]:
            self._build_dialog.hide()
        if self._regex_restore_state["overlay"]:
            self.hide()
        screen = QApplication.primaryScreen().availableGeometry()
        self._regex_dialog.move(
            screen.center().x() - self._regex_dialog.width() // 2,
            screen.center().y() - self._regex_dialog.height() // 2,
        )
        self._regex_dialog.show()
        self._regex_dialog.raise_()
        self._regex_dialog.activateWindow()

    def _restore_after_regex(self):
        state = self._regex_restore_state
        self._regex_restore_state = None
        if not state:
            return
        if state["overlay"]:
            self.show()
            self.raise_()
        if state["layout"] and self._layout_dialog is not None:
            self._layout_dialog.show()
            self._layout_dialog.raise_()
        if state["build"] and getattr(self, "_build_dialog", None) is not None:
            self._build_dialog.show()
            self._build_dialog.raise_()

    def _refresh_hotkey_footer(self):
        if not hasattr(self, "hotkey_footer"):
            return
        show = display_hotkey
        def item(key, label):
            return f"<span style='color:#629d6c;font-weight:600'>{key}</span>&nbsp; {label}"
        self.hotkey_footer.set_full_text("&nbsp; · &nbsp;".join((
            item(show(self.settings.get("hotkey", DEFAULT_SETTINGS["hotkey"])), "След. шаг"),
            item(show(self.settings.get("previous_hotkey", DEFAULT_SETTINGS["previous_hotkey"])), "Пред. шаг"),
            item(show(self.settings.get("layout_hotkey", DEFAULT_SETTINGS["layout_hotkey"])), "Мини-панель"),
            item(show(self.settings.get("regex_hotkey", DEFAULT_SETTINGS["regex_hotkey"])), "Регэкспы"),
        )))
        self.hotkey_footer.setVisible(bool(self.settings.get("show_hotkey_hints", True)))

    def _close_layout_dialog(self):
        if self._layout_dialog is not None:
            self._layout_dialog._save_layout_size()
            self._layout_dialog._save_layout_position()
            self._layout_dialog._click_through_timer.stop()
            set_window_click_through(self._layout_dialog, False)
            self._layout_dialog.close()
            self._layout_dialog = None

    def _position_layout_dialog(self):
        if self._layout_dialog is None:
            return
        dlg = self._layout_dialog
        if dlg._saved_position() is not None:
            dlg.apply_saved_position()
            return
        screen = QApplication.primaryScreen().availableGeometry()
        x = self.x() + self.width() + 16
        y = self.y()
        if x + dlg.width() > screen.right():
            x = max(screen.left(), self.x() - dlg.width() - 16)
        if y + dlg.height() > screen.bottom():
            y = max(screen.top(), screen.bottom() - dlg.height() - 8)
        dlg.move(dlg._clamp_position(QPoint(x, y)))

    def _refresh_layout_hint(self):
        if self.game != GAME_POE2:
            return
        first_open = self._layout_dialog is None
        if first_open:
            self._layout_dialog = LayoutHintDialog(self)
        was_visible = self._layout_dialog.isVisible()
        act, step_index, step_text = self.content.get_active_step_info()
        self._layout_dialog.set_opacity(1.0)
        self._layout_dialog.show_for_step(act, step_index, step_text)
        if first_open or not was_visible:
            self._position_layout_dialog()

    def _toggle_layout_hint(self):
        if self.game != GAME_POE2:
            return
        if self._layout_dialog is not None and self._layout_dialog.isVisible():
            self._close_layout_dialog()
            return
        self._refresh_layout_hint()
        if self._layout_dialog is not None:
            self._layout_dialog.show()
            self._position_layout_dialog()
            self._layout_dialog._apply_click_through_mode()

    def _on_active_step_changed(self):
        if (
            self.game == GAME_POE2
            and self._layout_dialog is not None
            and self._layout_dialog.isVisible()
        ):
            self._refresh_layout_hint()
            self._layout_dialog.scroll_to_top()
    
    def _on_first_step(self):
        if not self.timer._running:
            self.timer.start()
    
    def _collapsed_height(self) -> int:
        return Style.collapsed_height(self._has_bg)

    def _drag_zone_height(self) -> int:
        if self._collapsed:
            return self._collapsed_height()
        _, top, _, _ = self._panel_margins
        return top + Style.HEADER_H

    def _toggle(self):
        self._collapsed = not self._collapsed
        self.body.setVisible(not self._collapsed)
        if hasattr(self, "_resize_handles"):
            self._resize_handles.set_collapsed_mode(self._collapsed)
            self._resize_handles.setVisible(True)
        if self._collapsed:
            self.welcome_panel.setVisible(False)
            self._expanded_size = self.size()
            self.setFixedSize(self.width(), self._collapsed_height())
            if self.collapse_btn.text():
                self.collapse_btn.setText("+")
        else:
            self.setMinimumSize(
                max(150, int(280 * Style.ui_scale())),
                max(100, int(180 * Style.ui_scale())),
            )
            self.setMaximumSize(16777215, 16777215)
            self.resize(self._expanded_size)
            self.header.setFixedHeight(Style.HEADER_H)
            if self.collapse_btn.text():
                self.collapse_btn.setText("−")
            self._apply_welcome_visibility()
        self._refresh_icon_button(self.collapse_btn, "collapse", "−")
        self.update()
    
    def _settings(self):
        dialog = SettingsDialog(self.settings, self)
        dialog.move(self.x() + (self.width() - dialog.width()) // 2, self.y() + 60)
        
        if dialog.exec_() == QDialog.Accepted:
            old_game = self.game
            self.settings = dialog.get_settings()
            save_json(SETTINGS_FILE, self.settings)
            self.hotkey.restart(self.settings["hotkey"])
            self._start_hotkey()
            self._update_opacity()
            self._apply_click_through_mode()
            new_scale = float(self.settings.get("ui_scale", DEFAULT_SETTINGS["ui_scale"]))
            self._apply_ui_scale(self._ui_scale, new_scale)
            self._ui_scale = new_scale
            
            new_game = self.settings.get("game", GAME_POE2)
            if new_game != old_game:
                self._close_layout_dialog()
                self._save_progress()
                self._switch_game(new_game)
            
            if dialog.should_reset:
                self.content.reset()
                self.timer.reset()
                self._save_progress()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_resize_handles()
        if self._has_bg:
            self.update()
    
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self._get_edge(e.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start = e.globalPos()
                self._resize_geom = self.geometry()
            elif e.pos().y() < self._drag_zone_height():
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, e):
        if self._resizing:
            self._do_resize(e.globalPos())
        elif self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)
        else:
            edge = self._get_edge(e.pos())
            if edge:
                cursors = {
                    "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
                    "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
                    "top-left": Qt.SizeFDiagCursor, "bottom-right": Qt.SizeFDiagCursor,
                    "top-right": Qt.SizeBDiagCursor, "bottom-left": Qt.SizeBDiagCursor,
                }
                self.setCursor(cursors.get(edge, Qt.ArrowCursor))
            else:
                self.setCursor(Qt.ArrowCursor)
    
    def mouseReleaseEvent(self, e):
        self._resizing = False
        self._resize_edge = None
        self._drag_pos = None
        self.setCursor(Qt.ArrowCursor)
    
    def _get_edge(self, pos):
        m = 8
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        l, r, t, b = x < m, x > w - m, y < m, y > h - m

        if self._collapsed:
            if l:
                return "left"
            if r:
                return "right"
            return None
        
        if b and r: return "bottom-right"
        if b and l: return "bottom-left"
        if t and r: return "top-right"
        if t and l: return "top-left"
        if l: return "left"
        if r: return "right"
        if t: return "top"
        if b: return "bottom"
        return None
    
    def _do_resize(self, pos):
        diff = pos - self._resize_start
        g = self._resize_geom
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        min_w = max(150, int(280 * Style.ui_scale()))
        min_h = max(100, int(180 * Style.ui_scale()))

        if self._collapsed:
            min_w = max(120, int(220 * Style.ui_scale()))
            if "right" in self._resize_edge:
                w = max(min_w, g.width() + diff.x())
            if "left" in self._resize_edge:
                d = min(diff.x(), g.width() - min_w)
                x, w = g.x() + d, g.width() - d
            self.setFixedSize(w, Style.collapsed_height(self._has_bg))
            self.setGeometry(x, y, w, h)
            return
        
        if "right" in self._resize_edge:
            w = max(min_w, g.width() + diff.x())
        if "left" in self._resize_edge:
            d = min(diff.x(), g.width() - min_w)
            x, w = g.x() + d, g.width() - d
        if "bottom" in self._resize_edge:
            h = max(min_h, g.height() + diff.y())
        if "top" in self._resize_edge:
            d = min(diff.y(), g.height() - min_h)
            y, h = g.y() + d, g.height() - d
        
        self.setGeometry(x, y, w, h)
    
    def _save_progress(self):
        save_json(get_progress_file(self.game), {
            "steps": self.content.get_state(),
            "timer": self.timer.get_state()
        })
    
    def _load_progress(self):
        data = load_json(get_progress_file(self.game), {})
        if "steps" in data:
            self.content.set_state(data["steps"])
        if "timer" in data:
            self.timer.set_state(data["timer"])
        self._update_progress_bar()

    def closeEvent(self, e):
        self._click_through_timer.stop()
        set_window_click_through(self, False)
        self._save_progress()
        self.settings["position"] = {"x": self.x(), "y": self.y()}
        if not self._collapsed:
            self._expanded_size = self.size()
        self.settings["size"] = {
            "width": self._expanded_size.width(),
            "height": self._expanded_size.height(),
        }
        save_json(SETTINGS_FILE, self.settings)
        self.hotkey.stop()
        self.previous_hotkey.stop()
        self.layout_hotkey.stop()
        self.regex_hotkey.stop()
        if self._regex_dialog is not None:
            self._regex_restore_state = None
            self._regex_dialog.close()
        self._close_layout_dialog()
        if hasattr(self, "tray"):
            self.tray.hide()
        e.accept()
        QApplication.quit()

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    ensure_cormorant_loaded()
    app.setFont(QFont("Segoe UI", 10))
    
    window = Overlay()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

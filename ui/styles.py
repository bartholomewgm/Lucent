"""
Глобальные стили приложения в стиле Liquid Glass (iOS) и темы оформления.

Цвета берутся из текущей палитры `T` в момент построения стиля или рисования,
поэтому при смене темы (set_theme) достаточно перестроить стили виджетов.
"""

from PyQt6.QtGui import QColor


class Palette:
    """Цвета темы: атрибут — CSS-строка для стилей, color(имя) — QColor для рисования"""

    def __init__(self, name, *, flat, blobs, glow, edge, colors):
        self.name = name
        self.flat = flat      # True — однотонный фон, цвета видео только вокруг окна видео
        self.blobs = blobs    # цвета пятен фона по умолчанию (для «Градиента»)
        self.glow = glow      # прозрачность трёх пятен фона
        self.edge = edge      # прозрачность свечения края стекла: сверху, снизу
        self._colors = colors

    def __getattr__(self, key):
        try:
            r, g, b, a = self.__dict__["_colors"][key]
        except KeyError:
            raise AttributeError(key) from None
        return f"rgba({r}, {g}, {b}, {a / 255:.3f})"

    def color(self, key) -> QColor:
        return QColor(*self._colors[key])


_DARK_COMMON = dict(
    text=(255, 255, 255, 255), text_sub=(235, 235, 245, 158), text_muted=(235, 235, 245, 82),
    fill=(255, 255, 255, 18), fill_hover=(255, 255, 255, 36), fill_pressed=(255, 255, 255, 51),
    stroke=(255, 255, 255, 41), accent=(10, 132, 255, 255), accent_soft=(10, 132, 255, 71),
    card=(255, 255, 255, 13), segmented=(255, 255, 255, 18), segment_checked=(255, 255, 255, 56),
    groove=(255, 255, 255, 41), scroll=(255, 255, 255, 56), scroll_hover=(255, 255, 255, 97),
    play_top=(255, 255, 255, 255), play_bottom=(228, 230, 238, 255), play_fg=(10, 12, 20, 255),
    play_pressed=(214, 216, 224, 255), toggle_off=(255, 255, 255, 40), danger=(255, 105, 97, 255),
    outline=(255, 255, 255, 44), placeholder=(0, 0, 0, 140), sheen=(255, 255, 255, 255),
    edge_line=(255, 255, 255, 255),
    # Объёмные стеклянные кнопки (ui/glass_button.py)
    glass_top=(255, 255, 255, 46), glass_bottom=(255, 255, 255, 12),
    glass_highlight=(255, 255, 255, 130), glass_shade=(0, 0, 0, 70), glass_shadow=(0, 0, 0, 130),
)

THEMES = {
    # Тёмные «обои» с цветными пятнами — исходный вид плеера
    "gradient": Palette(
        "gradient", flat=False,
        blobs=((47, 107, 255), (155, 77, 255), (20, 200, 180)),  # синий, фиолетовый, бирюзовый
        glow=(120, 95, 80), edge=(16, 6),
        colors=dict(_DARK_COMMON, base=(10, 12, 20, 255), panel=(12, 14, 24, 120),
                    menu=(36, 38, 50, 245), tooltip=(36, 38, 50, 255), dialog=(28, 30, 40, 255)),
    ),
    # Нейтральная тёмная, как тёмная тема iOS
    "dark": Palette(
        "dark", flat=True, blobs=None, glow=(130, 105, 90), edge=(14, 5),
        colors=dict(_DARK_COMMON, base=(22, 22, 24, 255), panel=(44, 44, 48, 190),
                    menu=(44, 44, 48, 248), tooltip=(44, 44, 48, 255), dialog=(32, 32, 36, 255)),
    ),
    # Светлая: светло-серый фон, белое стекло, тёмный текст
    "light": Palette(
        "light", flat=True, blobs=None, glow=(150, 125, 105), edge=(10, 16),
        colors=dict(
            text=(28, 28, 30, 255), text_sub=(60, 60, 67, 153), text_muted=(60, 60, 67, 77),
            fill=(0, 0, 0, 13), fill_hover=(0, 0, 0, 23), fill_pressed=(0, 0, 0, 36),
            stroke=(0, 0, 0, 31), accent=(0, 122, 255, 255), accent_soft=(0, 122, 255, 46),
            card=(0, 0, 0, 10), segmented=(0, 0, 0, 15), segment_checked=(255, 255, 255, 255),
            groove=(0, 0, 0, 31), scroll=(0, 0, 0, 56), scroll_hover=(0, 0, 0, 97),
            play_top=(44, 44, 46, 255), play_bottom=(20, 20, 22, 255), play_fg=(255, 255, 255, 255),
            play_pressed=(70, 70, 74, 255), toggle_off=(0, 0, 0, 31), danger=(255, 59, 48, 255),
            outline=(0, 0, 0, 38), placeholder=(0, 0, 0, 20), sheen=(255, 255, 255, 255),
            edge_line=(0, 0, 0, 255),
            glass_top=(255, 255, 255, 250), glass_bottom=(234, 234, 240, 240),
            glass_highlight=(255, 255, 255, 255), glass_shade=(0, 0, 0, 30), glass_shadow=(0, 0, 0, 60),
            base=(242, 242, 247, 255), panel=(255, 255, 255, 175),
            menu=(255, 255, 255, 250), tooltip=(255, 255, 255, 255), dialog=(242, 242, 247, 255),
        ),
    ),
}

THEME_NAMES = (("Градиент", "gradient"), ("Тёмная", "dark"), ("Светлая", "light"))

# Текущая палитра. Один и тот же объект на всё приложение — set_theme меняет его содержимое
T = Palette("gradient", flat=False, blobs=None, glow=(0, 0, 0), edge=(0, 0), colors={})
T.__dict__.update(THEMES["gradient"].__dict__)

# Панель поверх видео в полноэкранном режиме всегда тёмная, в любой теме
OVERLAY = THEMES["gradient"]


def set_theme(name: str):
    T.__dict__.update(THEMES.get(name, THEMES["gradient"]).__dict__)

GLASS_RADIUS = 24
GLASS_GAP = 12

FONT_FAMILY = "'Segoe UI Variable Text', 'Segoe UI', sans-serif"

# Системный шрифт иконок Windows 11 (Windows 10 — MDL2 с теми же кодами)
ICON_FONT = "'Segoe Fluent Icons', 'Segoe MDL2 Assets'"


class Icons:
    PLAY = "\uF5B0"
    PAUSE = "\uF8AE"
    PREVIOUS = "\uF8AC"
    NEXT = "\uF8AD"
    VOLUME = "\uE767"
    MUTE = "\uE74F"
    FULLSCREEN = "\uE740"
    EXIT_FULLSCREEN = "\uE73F"
    ADD = "\uE710"
    VIDEO = "\uE714"
    SETTINGS = "\uE713"
    CIRCLE_ARROW = "\uE72C"  # круговая стрелка по часовой


def app_style(p=None) -> str:
    """Общий стиль окна: меню, подсказки, полосы прокрутки, системные диалоги"""
    p = p or T
    return f"""
QWidget {{
    background-color: transparent;
    color: {p.text};
    font-family: {FONT_FAMILY};
}}

QMenu {{
    background-color: {p.menu};
    color: {p.text};
    border: none;
    border-radius: 14px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 28px 8px 16px;
    border-radius: 9px;
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: {p.accent};
    color: white;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 6px 2px;
}}

QScrollBar::handle:vertical {{
    background: {p.scroll};
    border-radius: 2px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background: {p.scroll_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {p.scroll};
    border-radius: 2px;
    min-width: 40px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0px;
}}

QToolTip {{
    background-color: {p.tooltip};
    color: {p.text};
    border: 1px solid {p.stroke};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}

QMessageBox, QFileDialog {{
    background-color: {p.dialog};
}}
"""

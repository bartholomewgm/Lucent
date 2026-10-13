"""
Глобальные стили приложения в стиле Liquid Glass (iOS)
"""

# Фон «обоев» под стеклом
GLASS_BASE = "#0a0c14"
GLASS_BLOB_1 = "#2f6bff"   # синий, слева сверху
GLASS_BLOB_2 = "#9b4dff"   # фиолетовый, справа
GLASS_BLOB_3 = "#14c8b4"   # бирюзовый, снизу

# Стекло
GLASS_FILL = "rgba(255, 255, 255, 0.07)"
GLASS_FILL_HOVER = "rgba(255, 255, 255, 0.14)"
GLASS_FILL_PRESSED = "rgba(255, 255, 255, 0.20)"
GLASS_STROKE = "rgba(255, 255, 255, 0.16)"
GLASS_MENU = "rgba(36, 38, 50, 0.96)"

# Акцент и текст (системные цвета iOS, тёмная тема)
GLASS_ACCENT = "#0a84ff"
GLASS_ACCENT_SOFT = "rgba(10, 132, 255, 0.28)"
GLASS_TEXT = "#ffffff"
GLASS_TEXT_SUB = "rgba(235, 235, 245, 0.62)"
GLASS_TEXT_MUTED = "rgba(235, 235, 245, 0.32)"

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
    CIRCLE_ARROW = "\uE72C"  # круговая стрелка по часовой


STYLE = f"""
QWidget {{
    background-color: transparent;
    color: {GLASS_TEXT};
    font-family: {FONT_FAMILY};
}}

QMenu {{
    background-color: {GLASS_MENU};
    color: {GLASS_TEXT};
    border: 1px solid {GLASS_STROKE};
    border-radius: 14px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 28px 8px 16px;
    border-radius: 9px;
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: {GLASS_ACCENT};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 6px 2px;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.22);
    border-radius: 2px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.38);
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
    background: rgba(255, 255, 255, 0.22);
    border-radius: 2px;
    min-width: 40px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0px;
}}

QToolTip {{
    background-color: rgb(36, 38, 50);
    color: {GLASS_TEXT};
    border: 1px solid {GLASS_STROKE};
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
}}

QMessageBox, QFileDialog {{
    background-color: rgb(28, 30, 40);
}}
"""

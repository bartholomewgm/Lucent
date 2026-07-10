"""
Глобальные стили приложения в стиле Spotify
"""

# Spotify palette
SPOTIFY_BLACK = "#000000"
SPOTIFY_DARK = "#121212"
SPOTIFY_ELEVATED = "#181818"
SPOTIFY_CARD = "#282828"
SPOTIFY_HOVER = "#2a2a2a"
SPOTIFY_GREEN = "#1db954"
SPOTIFY_GREEN_HOVER = "#1ed760"
SPOTIFY_TEXT = "#ffffff"
SPOTIFY_TEXT_SUB = "#b3b3b3"
SPOTIFY_TEXT_MUTED = "#6a6a6a"
SPOTIFY_BORDER = "#282828"

STYLE = f"""
QMainWindow {{
    background-color: {SPOTIFY_BLACK};
}}

QWidget {{
    background-color: transparent;
    color: {SPOTIFY_TEXT};
    font-family: 'Segoe UI', 'Circular', 'Inter', sans-serif;
}}

QMenu {{
    background-color: {SPOTIFY_CARD};
    color: {SPOTIFY_TEXT};
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 2px;
    font-size: 13px;
}}

QMenu::item:selected {{
    background-color: {SPOTIFY_HOVER};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}

QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.25);
    border-radius: 5px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.4);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.25);
    border-radius: 5px;
    min-width: 40px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
    width: 0px;
}}

QToolTip {{
    background-color: {SPOTIFY_CARD};
    color: {SPOTIFY_TEXT};
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 6px 10px;
    font-size: 12px;
}}
"""

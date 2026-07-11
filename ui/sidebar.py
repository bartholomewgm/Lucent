"""
Боковая панель в стиле Spotify
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles import (
    SPOTIFY_BLACK, SPOTIFY_TEXT,
    SPOTIFY_TEXT_MUTED, SPOTIFY_HOVER
)
from ui.playlist import PlaylistWidget


class SidebarWidget(QWidget):
    """Левая панель: кнопка открытия, плейлист"""

    open_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self.setStyleSheet(f"background-color: {SPOTIFY_BLACK};")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(18)

        # ===== КНОПКА ОТКРЫТИЯ (ВМЕСТО ЛОГОТИПА) =====
        self.open_button = QPushButton("+  Открыть видео")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setFixedHeight(48)
        self.open_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_HOVER};
                color: {SPOTIFY_TEXT};
                border: none;
                border-radius: 24px;
                font-size: 15px;
                font-weight: 600;
                text-align: left;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                background-color: #3e3e3e;
            }}
            QPushButton:pressed {{
                background-color: #333333;
            }}
        """)
        self.open_button.clicked.connect(self.open_clicked.emit)
        layout.addWidget(self.open_button)

        # ===== ЗАГОЛОВОК СЕКЦИИ =====
        section_header = QLabel("ОЧЕРЕДЬ")
        section_header.setStyleSheet(f"""
            color: {SPOTIFY_TEXT_MUTED};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding-left: 4px;
        """)
        layout.addWidget(section_header)

        # ===== ПЛЕЙЛИСТ =====
        self.playlist = PlaylistWidget()
        layout.addWidget(self.playlist, stretch=1)

        # ===== ПОДСКАЗКА =====
        hint = QLabel("Двойной клик — воспроизвести")
        hint.setStyleSheet(f"color: {SPOTIFY_TEXT_MUTED}; font-size: 11px; padding-left: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)
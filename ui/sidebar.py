"""
Боковая панель в стиле Spotify
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ui.styles import (
    SPOTIFY_BLACK, SPOTIFY_TEXT, SPOTIFY_TEXT_SUB,
    SPOTIFY_TEXT_MUTED, SPOTIFY_GREEN, SPOTIFY_HOVER
)
from ui.playlist import PlaylistWidget


class SidebarWidget(QWidget):
    """Левая панель: логотип, навигация, плейлист"""

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

        # Логотип
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)

        logo_icon = QLabel("▶")
        logo_icon.setFixedSize(32, 32)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet(f"""
            background-color: {SPOTIFY_GREEN};
            color: black;
            border-radius: 16px;
            font-size: 14px;
            font-weight: bold;
        """)

        logo_text = QLabel("VideoPlayer")
        logo_font = QFont()
        logo_font.setPointSize(18)
        logo_font.setBold(True)
        logo_text.setFont(logo_font)
        logo_text.setStyleSheet(f"color: {SPOTIFY_TEXT};")

        logo_row.addWidget(logo_icon)
        logo_row.addWidget(logo_text)
        logo_row.addStretch()
        layout.addLayout(logo_row)

        # Кнопка открытия
        self.open_button = QPushButton("  +  Открыть видео")
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setFixedHeight(40)
        self.open_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SPOTIFY_HOVER};
                color: {SPOTIFY_TEXT};
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                text-align: left;
                padding-left: 16px;
            }}
            QPushButton:hover {{
                background-color: #3e3e3e;
                transform: scale(1.02);
            }}
        """)
        self.open_button.clicked.connect(self.open_clicked.emit)
        layout.addWidget(self.open_button)

        # Заголовок секции
        section_header = QLabel("ОЧЕРЕДЬ")
        section_header.setStyleSheet(f"""
            color: {SPOTIFY_TEXT_MUTED};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            padding-left: 4px;
        """)
        layout.addWidget(section_header)

        self.playlist = PlaylistWidget()
        layout.addWidget(self.playlist, stretch=1)

        hint = QLabel("Двойной клик — воспроизвести")
        hint.setStyleSheet(f"color: {SPOTIFY_TEXT_MUTED}; font-size: 11px; padding-left: 4px;")
        layout.addWidget(hint)

        self.setLayout(layout)

"""
Миниатюра / обложка в стиле Spotify (нижняя панель)
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

from ui.styles import SPOTIFY_CARD, SPOTIFY_TEXT_MUTED


class CoverArtWidget(QLabel):
    """Квадратная обложка 56×56 как в Spotify player bar"""

    def __init__(self, size: int = 56):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {SPOTIFY_CARD};
            border-radius: 4px;
            color: {SPOTIFY_TEXT_MUTED};
        """)
        self.set_placeholder()

    def set_placeholder(self):
        font = QFont()
        font.setPointSize(18)
        self.setFont(font)
        self.setText("🎬")
        self.setPixmap(QPixmap())

    def set_pixmap_scaled(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.set_placeholder()
            return
        scaled = pixmap.scaled(
            self._size, self._size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)

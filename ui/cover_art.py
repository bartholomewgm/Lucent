"""
Миниатюра / обложка (нижняя панель)
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from ui.styles import GLASS_FILL, GLASS_TEXT_SUB, ICON_FONT, Icons


class CoverArtWidget(QLabel):
    """Квадратная стеклянная обложка 56×56"""

    def __init__(self, size: int = 56):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {GLASS_FILL};
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 14px;
            color: {GLASS_TEXT_SUB};
            font-family: {ICON_FONT};
            font-size: 20px;
        """)
        self.set_placeholder()

    def set_placeholder(self):
        self.setPixmap(QPixmap())
        self.setText(Icons.VIDEO)

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

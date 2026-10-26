"""
Миниатюра / обложка (нижняя панель)
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtCore import QRectF, Qt

from ui.styles import GLASS_FILL, GLASS_TEXT_SUB, ICON_FONT, Icons


class CoverArtWidget(QLabel):
    """Квадратная стеклянная обложка 56×56: кадр из видео или значок"""

    RADIUS = 14

    def __init__(self, size: int = 56):
        super().__init__()
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {GLASS_FILL};
            border: none;
            border-radius: {self.RADIUS}px;
            color: {GLASS_TEXT_SUB};
            font-family: {ICON_FONT};
            font-size: 20px;
        """)
        self.set_placeholder()

    def set_placeholder(self):
        self.setPixmap(QPixmap())
        self.setText(Icons.VIDEO)

    def set_image(self, image: QImage):
        """Кадр: квадрат из середины, скруглённые углы, чёткий на HiDPI"""
        if image.isNull():
            self.set_placeholder()
            return
        dpr = self.devicePixelRatioF()
        side = round(self._size * dpr)
        scaled = image.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                              Qt.TransformationMode.SmoothTransformation)
        x = (scaled.width() - side) // 2
        y = (scaled.height() - side) // 2
        square = scaled.copy(x, y, side, side)

        pixmap = QPixmap(side, side)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, side, side), self.RADIUS * dpr, self.RADIUS * dpr)
        painter.setClipPath(clip)
        painter.drawImage(0, 0, square)
        painter.end()
        pixmap.setDevicePixelRatio(dpr)
        self.setText("")
        self.setPixmap(pixmap)

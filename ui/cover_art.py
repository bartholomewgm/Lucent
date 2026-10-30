"""
Миниатюра / обложка (нижняя панель)
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QImage, QPainter, QPainterPath, QPixmap
from PyQt6.QtCore import QRectF, Qt

from ui.icons import Icons, draw_icon
from ui.styles import T


class CoverArtWidget(QLabel):
    """Квадратная стеклянная обложка 56×56: кадр из видео или значок"""

    RADIUS = 14

    def __init__(self, size: int = 56):
        super().__init__()
        self._size = size
        self._placeholder = True
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.apply_theme()
        self.set_placeholder()

    def apply_theme(self):
        self.setStyleSheet(f"""
            background-color: {T.fill};
            border: none;
            border-radius: {self.RADIUS}px;
        """)

    def set_placeholder(self):
        self._placeholder = True
        self.setPixmap(QPixmap())

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._placeholder:
            side = 22
            rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
            draw_icon(QPainter(self), Icons.VIDEO, rect, T.color("text_sub"), 1.6)

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
        self._placeholder = False
        self.setPixmap(pixmap)

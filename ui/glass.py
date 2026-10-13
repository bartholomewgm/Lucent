"""
Стеклянные поверхности в стиле Liquid Glass:
фон-«обои» с цветными пятнами и полупрозрачные панели с бликом по краю
"""

from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPainterPath, QPen
)

from ui.styles import GLASS_BASE, GLASS_BLOB_1, GLASS_BLOB_2, GLASS_BLOB_3, GLASS_RADIUS


class GlassBackground(QWidget):
    """Тёмные «обои» с размытыми цветными пятнами, на которых лежит стекло"""

    BLOBS = (
        # цвет, центр (доля ширины, доля высоты), радиус (доля диагонали), прозрачность
        (GLASS_BLOB_1, (0.08, 0.05), 0.55, 120),
        (GLASS_BLOB_2, (0.95, 0.35), 0.50, 95),
        (GLASS_BLOB_3, (0.35, 1.05), 0.45, 80),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.plain = False  # в полноэкранном режиме — просто чёрный фон

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        if self.plain:
            p.fillRect(rect, QColor("black"))
            return

        p.fillRect(rect, QColor(GLASS_BASE))
        diagonal = (rect.width() ** 2 + rect.height() ** 2) ** 0.5
        for color, (fx, fy), fr, alpha in self.BLOBS:
            center = QPointF(rect.width() * fx, rect.height() * fy)
            grad = QRadialGradient(center, diagonal * fr)
            inner = QColor(color)
            inner.setAlpha(alpha)
            outer = QColor(color)
            outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            p.fillRect(rect, grad)


class GlassPanel(QWidget):
    """Полупрозрачная панель: матовая заливка, светлый кант сверху, мягкая тень"""

    def __init__(self, parent=None, radius: int = GLASS_RADIUS):
        super().__init__(parent)
        self.radius = radius

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        # Заливка: сверху светлее — эффект преломления света
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0.0, QColor(255, 255, 255, 30))
        fill.setColorAt(0.5, QColor(255, 255, 255, 16))
        fill.setColorAt(1.0, QColor(255, 255, 255, 10))
        p.fillPath(path, QColor(12, 14, 24, 120))
        p.fillPath(path, fill)

        # Кант: яркий блик сверху, затухающий книзу
        stroke = QLinearGradient(rect.topLeft(), rect.bottomRight())
        stroke.setColorAt(0.0, QColor(255, 255, 255, 110))
        stroke.setColorAt(0.45, QColor(255, 255, 255, 28))
        stroke.setColorAt(1.0, QColor(255, 255, 255, 60))
        p.setPen(QPen(stroke, 1.0))
        p.drawPath(path)


def make_glass_menu(parent=None) -> QMenu:
    """QMenu со скруглёнными углами без чёрных уголков"""
    menu = QMenu(parent)
    menu.setWindowFlags(
        menu.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu

"""
Стеклянные поверхности в стиле Liquid Glass:
фон-«обои» с цветными пятнами и полупрозрачные панели с бликом по краю
"""

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QMenu, QWidget

from ui.styles import GLASS_BASE, GLASS_BLOB_1, GLASS_BLOB_2, GLASS_BLOB_3, GLASS_RADIUS


class GlassBackground(QWidget):
    """Тёмные «обои» с размытыми цветными пятнами, на которых лежит стекло"""

    DEFAULT_COLORS = (GLASS_BLOB_1, GLASS_BLOB_2, GLASS_BLOB_3)
    BLOBS = (
        # центр (доля ширины, доля высоты), радиус (доля диагонали), прозрачность
        ((0.08, 0.05), 0.55, 120),
        ((0.95, 0.35), 0.50, 95),
        ((0.35, 1.05), 0.45, 80),
    )
    TRANSITION_MS = 1200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.plain = False  # в полноэкранном режиме — просто чёрный фон
        self._colors = [QColor(c) for c in self.DEFAULT_COLORS]
        self._from = list(self._colors)
        self._to = list(self._colors)
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self.TRANSITION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.valueChanged.connect(self._blend)

    def set_colors(self, colors):
        """Плавно перекрасить пятна (например, под цвета видео)"""
        self._from = list(self._colors)
        self._to = [QColor(c) for c in colors]
        self._anim.stop()
        self._anim.start()

    def reset_colors(self):
        self.set_colors(self.DEFAULT_COLORS)

    def _blend(self, t):
        self._colors = [
            QColor(round(a.red() + (b.red() - a.red()) * t),
                   round(a.green() + (b.green() - a.green()) * t),
                   round(a.blue() + (b.blue() - a.blue()) * t))
            for a, b in zip(self._from, self._to)
        ]
        if not self.plain:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        if self.plain:
            p.fillRect(rect, QColor("black"))
            return

        p.fillRect(rect, QColor(GLASS_BASE))
        diagonal = (rect.width() ** 2 + rect.height() ** 2) ** 0.5
        for color, ((fx, fy), fr, alpha) in zip(self._colors, self.BLOBS):
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
    """Полупрозрачная панель: матовая заливка и мягкое свечение по краю"""

    FEATHER = 8  # ширина плавного перехода по краю, px

    def __init__(self, parent=None, radius: int = GLASS_RADIUS, tint_alpha: int = 120):
        super().__init__(parent)
        self.radius = radius
        self.tint_alpha = tint_alpha  # насколько стекло затемняет то, что под ним

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
        p.fillPath(path, QColor(12, 14, 24, self.tint_alpha))
        p.fillPath(path, fill)

        # Край без резкой линии: свечение, которое плавно гаснет внутрь панели
        # (сверху чуть ярче — свет падает сверху)
        for i in range(self.FEATHER):
            k = (1 - i / self.FEATHER) ** 2
            edge = rect.adjusted(i, i, -i, -i)
            glow = QLinearGradient(edge.topLeft(), edge.bottomLeft())
            glow.setColorAt(0.0, QColor(255, 255, 255, round(16 * k)))
            glow.setColorAt(1.0, QColor(255, 255, 255, round(6 * k)))
            p.setPen(QPen(glow, 1.0))
            radius = max(self.radius - i, 0)
            p.drawRoundedRect(edge, radius, radius)


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

"""
Стеклянные поверхности в стиле Liquid Glass:
фон-«обои» и полупрозрачные панели с бликом по краю. Цвета — из текущей темы (ui/styles.py).
"""

from PyQt6.QtCore import QEasingCurve, QEvent, QPointF, QRectF, Qt, QVariantAnimation
from PyQt6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QMenu, QWidget

from ui.styles import GLASS_RADIUS, T


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t),
                  round(a.alpha() + (b.alpha() - a.alpha()) * t))


class GlassBackground(QWidget):
    """
    Фон окна, на котором лежит стекло.
    «Градиент» — тёмные «обои» с цветными пятнами по всему окну.
    «Тёмная»/«Светлая» — однотонный фон; цвета видео ложатся свечением
    только вокруг окна воспроизведения (focus_widget).
    """

    # Пятна «Градиента»: центр (доля ширины, доля высоты), радиус (доля диагонали)
    BLOBS = (((0.08, 0.05), 0.55), ((0.95, 0.35), 0.50), ((0.35, 1.05), 0.45))
    # Свечение вокруг видео: центр (доли прямоугольника видео), радиус (доля его диагонали)
    FOCUS_BLOBS = (((0.05, 0.05), 0.50), ((1.0, 0.5), 0.45), ((0.5, 1.0), 0.45))
    TRANSITION_MS = 1200
    # Контур окна как у Windows 11: линия 1 px по краю, углы 8 px.
    # Системную рамку Windows не рисует — у окна свой заголовок (ui/window_frame.py)
    WINDOW_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.plain = False   # в полноэкранном режиме — просто чёрный фон
        self.outline = True  # в развёрнутом окне контура нет, как у системных окон
        self.focus_widget = None  # окно видео: вокруг него свечение в однотонных темах
        self._ambient = False     # сейчас показаны цвета видео, а не цвета темы
        self._colors = self._default_colors()
        self._from = list(self._colors)
        self._to = list(self._colors)
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self.TRANSITION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.valueChanged.connect(self._blend)

    @staticmethod
    def _default_colors():
        if T.blobs:
            return [QColor(*c) for c in T.blobs]
        # Однотонные темы: без видео свечения нет — цвета фона, полностью прозрачные
        base = T.color("base")
        return [QColor(base.red(), base.green(), base.blue(), 0) for _ in range(3)]

    def set_focus_widget(self, widget):
        """Окно видео: свечение следует за ним (скрытие плейлиста, изменение размера)"""
        self.focus_widget = widget
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.focus_widget and event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
            if T.flat and self._ambient:
                self.update()
        return super().eventFilter(obj, event)

    def set_colors(self, colors):
        """Плавно перекрасить пятна под цвета видео"""
        self._ambient = True
        self._animate_to([QColor(c) for c in colors])

    def reset_colors(self):
        """Плавно вернуть цвета темы (в однотонных темах — погасить свечение)"""
        self._ambient = False
        self._animate_to(self._default_colors())

    def apply_theme(self):
        """Тема сменилась: цвета видео оставляем, остальное — по новой теме"""
        self._anim.stop()
        if not self._ambient:
            self._colors = self._default_colors()
        self.update()

    def _animate_to(self, colors):
        self._from = list(self._colors)
        self._to = colors
        self._anim.stop()
        self._anim.start()

    def _blend(self, t):
        self._colors = [_lerp(a, b, t) for a, b in zip(self._from, self._to)]
        if not self.plain:
            self.update()

    def _blob_layout(self, rect: QRectF):
        """Где рисовать пятна: по всему окну («Градиент») или вокруг видео"""
        if not T.flat:
            diagonal = (rect.width() ** 2 + rect.height() ** 2) ** 0.5
            return [(QPointF(rect.width() * fx, rect.height() * fy), diagonal * fr)
                    for (fx, fy), fr in self.BLOBS]
        if self.focus_widget is None or not self.focus_widget.isVisible():
            return []
        area = QRectF(self.focus_widget.geometry())
        area.moveTopLeft(QPointF(self.focus_widget.mapTo(self, self.focus_widget.rect().topLeft())))
        diagonal = (area.width() ** 2 + area.height() ** 2) ** 0.5
        return [(QPointF(area.x() + area.width() * fx, area.y() + area.height() * fy), diagonal * fr)
                for (fx, fy), fr in self.FOCUS_BLOBS]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        if self.plain:
            p.fillRect(rect, QColor("black"))
            return

        p.fillRect(rect, T.color("base"))
        for color, (center, radius), strength in zip(self._colors, self._blob_layout(rect), T.glow):
            if color.alpha() == 0 or radius <= 0:
                continue
            grad = QRadialGradient(center, radius)
            inner = QColor(color)
            inner.setAlpha(round(strength * color.alphaF()))
            outer = QColor(color)
            outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            p.fillRect(rect, grad)

        if self.outline:
            p.setPen(QPen(T.color("outline"), 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), self.WINDOW_RADIUS, self.WINDOW_RADIUS)


class GlassPanel(QWidget):
    """Полупрозрачная панель: матовая заливка и мягкое свечение по краю"""

    FEATHER = 8  # ширина плавного перехода по краю, px

    def __init__(self, parent=None, radius: int = GLASS_RADIUS, tint_alpha=None, palette=None):
        super().__init__(parent)
        self.radius = radius
        self.tint_alpha = tint_alpha  # насколько стекло закрывает то, что под ним (None — как в теме)
        self.palette_override = palette  # None — текущая тема (полноэкранная панель всегда тёмная)

    def paintEvent(self, event):
        pal = self.palette_override or T
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        # Заливка: сверху светлее — эффект преломления света
        base = pal.color("panel")
        if self.tint_alpha is not None:
            base.setAlpha(self.tint_alpha)
        sheen = pal.color("sheen")
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        for stop, alpha in ((0.0, 30), (0.5, 16), (1.0, 10)):
            fill.setColorAt(stop, QColor(sheen.red(), sheen.green(), sheen.blue(), alpha))
        p.fillPath(path, base)
        p.fillPath(path, fill)

        # Край без резкой линии: свечение, которое плавно гаснет внутрь панели
        line = pal.color("edge_line")
        top, bottom = pal.edge
        for i in range(self.FEATHER):
            k = (1 - i / self.FEATHER) ** 2
            edge = rect.adjusted(i, i, -i, -i)
            glow = QLinearGradient(edge.topLeft(), edge.bottomLeft())
            glow.setColorAt(0.0, QColor(line.red(), line.green(), line.blue(), round(top * k)))
            glow.setColorAt(1.0, QColor(line.red(), line.green(), line.blue(), round(bottom * k)))
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

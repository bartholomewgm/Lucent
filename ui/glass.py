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
    «Тёмная»/«Светлая» — однотонный фон; от цветов видео остаётся только
    небольшой ореол вокруг самой картинки (focus_widget).
    """

    # Пятна «Градиента»: центр (доля ширины, доля высоты), радиус (доля диагонали)
    BLOBS = (((0.08, 0.05), 0.55), ((0.95, 0.35), 0.50), ((0.35, 1.05), 0.45))
    # Ореол вокруг картинки: ширина и число колец, из которых он складывается
    HALO_WIDTH = 42
    HALO_RINGS = 21
    TRANSITION_MS = 900
    AMBIENT_BOOST = 1.45  # пятна «Градиента» под цвета видео ярче обычных
    # Контур окна как у Windows 11: линия 1 px по краю, углы 8 px.
    # Системную рамку Windows не рисует — у окна свой заголовок (ui/window_frame.py)
    WINDOW_RADIUS = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.plain = False   # в полноэкранном режиме — просто чёрный фон
        self.outline = True  # в развёрнутом окне контура нет, как у системных окон
        self.focus_widget = None  # окно видео (VideoFrame): вокруг картинки ореол в однотонных темах
        self._ambient = False     # сейчас показаны цвета видео, а не цвета темы
        self._colors = self._default_colors()
        self._from = list(self._colors)
        self._to = list(self._colors)
        self._boost = self._boost_from = 1.0
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
        """Окно видео: ореол следует за картинкой (скрытие плейлиста, изменение размера)"""
        self.focus_widget = widget
        widget.installEventFilter(self)
        widget.picture_changed.connect(self._on_picture_changed)

    def _on_picture_changed(self):
        if T.flat and self._ambient:
            self.update()

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
            self._boost = 1.0
        self.update()

    def _animate_to(self, colors):
        self._from = list(self._colors)
        self._to = colors
        self._boost_from = self._boost
        self._anim.stop()
        self._anim.start()

    def _blend(self, t):
        self._colors = [_lerp(a, b, t) for a, b in zip(self._from, self._to)]
        target = self.AMBIENT_BOOST if self._ambient else 1.0
        self._boost = self._boost_from + (target - self._boost_from) * t
        if not self.plain:
            self.update()

    def _paint_blobs(self, p: QPainter, rect: QRectF):
        """«Градиент»: цветные пятна по всему окну"""
        diagonal = (rect.width() ** 2 + rect.height() ** 2) ** 0.5
        for color, ((fx, fy), fr), strength in zip(self._colors, self.BLOBS, T.glow):
            grad = QRadialGradient(QPointF(rect.width() * fx, rect.height() * fy), diagonal * fr)
            inner = QColor(color)
            inner.setAlpha(min(255, round(strength * self._boost * color.alphaF())))
            outer = QColor(color)
            outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            p.fillRect(rect, grad)

    def _paint_halo(self, p: QPainter):
        """Однотонные темы: узкий ореол цветов кадра вокруг видимой картинки"""
        widget = self.focus_widget
        if widget is None or not widget.isVisible():
            return
        picture = widget.picture_rect().translated(QPointF(widget.mapTo(self, widget.rect().topLeft())))
        if picture.width() <= 0:
            return
        brush = QLinearGradient(picture.topLeft(), picture.topRight())
        brush.setColorAt(0.0, self._colors[0])
        brush.setColorAt(0.5, self._colors[2])
        brush.setColorAt(1.0, self._colors[1])
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(brush)
        strength, rings = T.glow[0] / 255, self.HALO_RINGS
        step = 2 * strength / (rings * (rings + 1))  # у картинки плотнее, наружу сходит на нет
        for i in range(rings):
            spread = self.HALO_WIDTH * (1 - i / rings)
            radius = GLASS_RADIUS + spread
            p.setOpacity(step * (i + 1))
            p.drawRoundedRect(picture.adjusted(-spread, -spread, spread, spread), radius, radius)
        p.restore()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())

        if self.plain:
            p.fillRect(rect, QColor("black"))
            return

        p.fillRect(rect, T.color("base"))
        if T.flat:
            self._paint_halo(p)
        else:
            self._paint_blobs(p, rect)

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

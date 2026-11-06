"""
Стеклянные поверхности в стиле Liquid Glass:
фон-«обои» и полупрозрачные панели с бликом по краю. Цвета — из текущей темы (ui/styles.py).
"""

import math

from PyQt6.QtCore import QEasingCurve, QEvent, QPointF, QRectF, Qt, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import QMenu, QWidget

from ui.styles import GLASS_RADIUS, T


def _lerp(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(round(a.red() + (b.red() - a.red()) * t),
                  round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t),
                  round(a.alpha() + (b.alpha() - a.alpha()) * t))


def _halo_brush(picture: QRectF, colors) -> QLinearGradient:
    brush = QLinearGradient(picture.topLeft(), picture.topRight())
    brush.setColorAt(0.0, colors[0])
    brush.setColorAt(0.5, colors[2])
    brush.setColorAt(1.0, colors[1])
    return brush


def _paint_halo_rings(p: QPainter, picture: QRectF, brush, strength: float, width: float, corner: float):
    """Ореол как он есть: два десятка скруглённых слоёв, у картинки плотнее"""
    rings = 21
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(brush)
    step = 2 * strength / (rings * (rings + 1))  # у картинки плотнее, наружу сходит на нет
    for i in range(rings):
        spread = width * (1 - i / rings)
        radius = corner + spread
        p.setOpacity(step * (i + 1))
        p.drawRoundedRect(picture.adjusted(-spread, -spread, spread, spread), radius, radius)
    p.restore()


_halo_masks = {}


def _halo_mask(strength: float, width: float, corner: float) -> QImage:
    """Образец ореола (белый) вокруг маленького прямоугольника: углы и полоски краёв"""
    key = (strength, width, corner)
    mask = _halo_masks.get(key)
    if mask is None:
        edge = math.ceil(width + corner)
        size = 2 * edge + 2
        mask = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inner = QRectF(width, width, size - 2 * width, size - 2 * width)
        _paint_halo_rings(painter, inner, QColor("white"), strength, width, corner)
        painter.end()
        _halo_masks[key] = mask
    return mask


def paint_halo(p: QPainter, picture: QRectF, colors, strength: float, width: float, corner: float):
    """
    Мягкий ореол цветов вокруг прямоугольника: слева colors[0], по центру [2], справа [1].

    Слоёв два десятка, и рисовать их заново на каждом кадре дорого (несколько мс
    на картинку во всё окно). Поэтому ореол собирается из образца: углы как есть,
    края — растянутые полоски, и всё это окрашивается цветами видео.
    Середину (под самой картинкой) не рисуем — её закрывает видео.
    """
    mask = _halo_mask(strength, width, corner)
    size = mask.width()
    edge = (size - 2) // 2
    outer = picture.adjusted(-width, -width, width, width).toAlignedRect()
    if outer.width() < size or outer.height() < size:
        _paint_halo_rings(p, picture, _halo_brush(picture, colors), strength, width, corner)
        return
    brush = _halo_brush(picture, colors)
    x0, y0, x1, y1 = outer.left(), outer.top(), outer.left() + outer.width(), outer.top() + outer.height()
    long_w, long_h = outer.width() - 2 * edge, outer.height() - 2 * edge
    pieces = (  # (куда: x, y, ширина, высота), (откуда в образце)
        ((x0, y0, edge, edge), (0, 0, edge, edge)),
        ((x1 - edge, y0, edge, edge), (size - edge, 0, edge, edge)),
        ((x0, y1 - edge, edge, edge), (0, size - edge, edge, edge)),
        ((x1 - edge, y1 - edge, edge, edge), (size - edge, size - edge, edge, edge)),
        ((x0 + edge, y0, long_w, edge), (edge, 0, 2, edge)),
        ((x0 + edge, y1 - edge, long_w, edge), (edge, size - edge, 2, edge)),
        ((x0, y0 + edge, edge, long_h), (0, edge, edge, 2)),
        ((x1 - edge, y0 + edge, edge, long_h), (size - edge, edge, edge, 2)),
    )
    for (x, y, w, h), source in pieces:
        piece = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        piece.fill(Qt.GlobalColor.transparent)
        painter = QPainter(piece)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF(0, 0, w, h), mask, QRectF(*source))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.translate(-x, -y)  # цвета — по всей ширине картинки, как у целого ореола
        painter.fillRect(QRectF(x, y, w, h), brush)
        painter.end()
        p.drawImage(x, y, piece)


class GlassBackground(QWidget):
    """
    Фон окна, на котором лежит стекло.
    «Градиент» — тёмные «обои» с цветными пятнами по всему окну.
    «Тёмная»/«Светлая» — однотонный фон; от цветов видео остаётся только
    небольшой ореол вокруг самой картинки (focus_widget).
    """

    # Пятна «Градиента»: центр (доля ширины, доля высоты), радиус (доля диагонали)
    BLOBS = (((0.08, 0.05), 0.55), ((0.95, 0.35), 0.50), ((0.35, 1.05), 0.45))
    HALO_WIDTH = 24  # ореол вокруг картинки в однотонных темах
    HALO_SOFTNESS = 0.7
    TRANSITION_MS = 900
    AMBIENT_BOOST = 1.45  # пятна «Градиента» под цвета видео ярче обычных
    colors_changed = pyqtSignal()
    # Контур окна как у Windows 11: линия 1 px по краю, углы 8 px.
    # Системную рамку Windows не рисует — у окна свой заголовок (ui/window_frame.py)
    WINDOW_RADIUS = 8
    # Пятна размытые — их хватает нарисовать вчетверо меньше и растянуть: иначе
    # три градиента на всё окно — самая дорогая часть кадра при растягивании окна
    BLOB_SCALE = 4

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
        self._blob_key = None
        self._blob_image = None

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

    def video_colors(self):
        """Текущие цвета видео; None — сейчас показаны цвета темы"""
        return self._colors if self._ambient else None

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
        self.colors_changed.emit()
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

    def _blob_layer(self, width: int, height: int) -> QImage:
        key = (width, height, tuple(c.rgba() for c in self._colors), self._boost, tuple(T.glow))
        if key != self._blob_key:
            scale = self.BLOB_SCALE
            image = QImage(max(1, math.ceil(width / scale)), max(1, math.ceil(height / scale)),
                           QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            self._paint_blobs(painter, QRectF(0, 0, width / scale, height / scale))
            painter.end()
            self._blob_key, self._blob_image = key, image
        return self._blob_image

    def _paint_halo(self, p: QPainter):
        """Однотонные темы: узкий ореол цветов кадра вокруг видимой картинки"""
        widget = self.focus_widget
        if widget is None or not widget.isVisible():
            return
        picture = widget.picture_rect().translated(QPointF(widget.mapTo(self, widget.rect().topLeft())))
        if picture.width() <= 0:
            return
        paint_halo(p, picture, self._colors, T.glow[0] / 255 * self.HALO_SOFTNESS, self.HALO_WIDTH, GLASS_RADIUS)

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
            scale = self.BLOB_SCALE
            p.save()
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(rect, self._blob_layer(self.width(), self.height()),
                        QRectF(0, 0, rect.width() / scale, rect.height() / scale))
            p.restore()

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
        self._sample_key = None
        self._sample = None

    def paintEvent(self, event):
        """
        По горизонтали панель везде одинакова, кроме скруглённых краёв. Поэтому
        рисуется узкий образец (два края и полоска между ними), а середина
        растягивается из полоски. Рисовать всю панель заново на каждом шаге
        растягивания окна и при каждом обновлении кнопок и времени — дорого.
        """
        pal = self.palette_override or T
        w, h = self.width(), self.height()
        cap = self.radius + self.FEATHER + 2  # край целиком, с запасом
        p = QPainter(self)
        if w < 2 * cap + 4:
            self._paint_panel(p, pal, w, h)
            return
        dpr = self.devicePixelRatioF()
        sample_w = 2 * cap + 2
        key = (h, dpr, self.radius, self.tint_alpha, pal.color("panel").rgba(), pal.color("sheen").rgba(),
               pal.color("edge_line").rgba(), tuple(pal.edge))
        if key != self._sample_key:
            sample = QPixmap(math.ceil(sample_w * dpr), math.ceil(h * dpr))
            sample.setDevicePixelRatio(dpr)
            sample.fill(Qt.GlobalColor.transparent)
            painter = QPainter(sample)
            self._paint_panel(painter, pal, sample_w, h)
            painter.end()
            self._sample_key, self._sample = key, sample
        sample = self._sample
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawPixmap(QRectF(0, 0, cap, h), sample, QRectF(0, 0, cap * dpr, h * dpr))
        p.drawPixmap(QRectF(cap, 0, w - 2 * cap, h), sample, QRectF(cap * dpr, 0, 2 * dpr, h * dpr))
        p.drawPixmap(QRectF(w - cap, 0, cap, h), sample, QRectF((sample_w - cap) * dpr, 0, cap * dpr, h * dpr))

    def _paint_panel(self, p: QPainter, pal, w: int, h: int):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, w, h).adjusted(0.5, 0.5, -0.5, -0.5)
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

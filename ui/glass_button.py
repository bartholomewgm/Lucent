"""
Объёмные кнопки в стиле Liquid Glass.

GlassLook рисует под кнопкой выпуклое стекло (градиент сверху вниз, блик по
верхнему краю, тень по нижнему) и даёт мягкий переход в фон — размытую тень
вокруг. Надпись или значок кнопка рисует сама, поверх, по своему стилю
(фон в стиле кнопки должен быть прозрачным).
"""

import weakref

from PyQt6.QtCore import QEvent, QObject, QRectF, Qt
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from ui.styles import T


def _mix(color: QColor, toward: QColor, amount: float) -> QColor:
    return QColor(round(color.red() + (toward.red() - color.red()) * amount),
                  round(color.green() + (toward.green() - color.green()) * amount),
                  round(color.blue() + (toward.blue() - color.blue()) * amount),
                  color.alpha())


def _with_alpha(color: QColor, alpha: int) -> QColor:
    c = QColor(color)
    c.setAlpha(max(0, min(255, alpha)))
    return c


class GlassLook(QObject):
    """Стеклянный объём для QPushButton. kind: "glass" — обычная, "play" — кнопка Play"""

    _all = weakref.WeakSet()

    def __init__(self, button, kind: str = "glass", radius=None, palette=None):
        super().__init__(button)
        self.button = button
        self.kind = kind
        self.radius = radius        # None — капсула (половина высоты)
        self.palette = palette      # None — текущая тема (полноэкранная панель — всегда тёмная)
        button.setAttribute(Qt.WidgetAttribute.WA_Hover)
        button.installEventFilter(self)
        # Мягкий переход в фон: размытая тень вокруг кнопки
        self.shadow = QGraphicsDropShadowEffect(button)
        self.shadow.setBlurRadius(18 if kind == "play" else 14)
        self.shadow.setOffset(0, 2 if kind == "play" else 1.5)
        button.setGraphicsEffect(self.shadow)
        self.retheme()
        GlassLook._all.add(self)

    def retheme(self):
        self.shadow.setColor((self.palette or T).color("glass_shadow"))
        self.button.update()

    @classmethod
    def retheme_all(cls):
        """Сменилась тема — перекрасить тени всех стеклянных кнопок"""
        for look in list(cls._all):
            look.retheme()

    def eventFilter(self, obj, event):
        if obj is self.button and event.type() == QEvent.Type.Paint:
            self._paint()
        return False  # дальше кнопка рисует надпись/значок как обычно

    def _paint(self):
        b = self.button
        p = QPainter(b)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not b.isEnabled():
            p.setOpacity(0.55)
        rect = QRectF(b.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2 if self.radius is None else self.radius
        paint_glass(p, rect, radius, self.palette or T, self.kind,
                    hovered=b.underMouse() and b.isEnabled(), down=b.isDown())
        p.end()


def paint_glass_shadow(p: QPainter, rect: QRectF, radius: float, palette=None):
    """Мягкая тень под стеклом без QGraphicsEffect — дёшево, можно рисовать каждый кадр"""
    base = (palette or T).color("glass_shadow")
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    for spread, alpha in ((2.5, 0.10), (1.5, 0.16), (0.6, 0.24)):
        p.setBrush(_with_alpha(base, round(base.alpha() * alpha)))
        r = rect.adjusted(-spread, -spread + 1, spread, spread + 1)
        p.drawRoundedRect(r, radius + spread, radius + spread)
    p.restore()


def paint_glass(p: QPainter, rect: QRectF, radius: float, pal=None, kind: str = "glass",
                hovered: bool = False, down: bool = False):
    """
    Выпуклое стекло: градиент сверху вниз, глянец, свет у нижнего края, кант.
    kind: "glass" — обычная кнопка, "play" — кнопка Play, "segment" — подложка переключателя
    """
    pal = pal or T
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    # Тело: градиент сверху вниз — выпуклое стекло
    if kind == "play":
        top, bottom = pal.color("play_top"), pal.color("play_bottom")
    elif kind == "segment":
        base = pal.color("segment_checked")
        top, bottom = _with_alpha(base, base.alpha() + 28), _with_alpha(base, base.alpha() - 14)
    else:
        top, bottom = pal.color("glass_top"), pal.color("glass_bottom")
    white, black = QColor(255, 255, 255), QColor(0, 0, 0)
    if down:
        top, bottom = _mix(top, black, 0.12), _mix(bottom, black, 0.12)
    elif hovered:
        if kind == "play":
            top, bottom = _mix(top, white, 0.1), _mix(bottom, white, 0.1)
        else:
            top = _with_alpha(top, top.alpha() + 26)
            bottom = _with_alpha(bottom, bottom.alpha() + 16)
    # Тёмное стекло (Play в светлой теме): белый блик и глянец на нём читаются как
    # светлая «шапка» над кнопкой — для него они намного слабее
    dark_body = top.lightness() < 110
    body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    body.setColorAt(0.0, top)
    body.setColorAt(1.0, bottom)
    p.fillPath(path, body)

    p.save()
    p.setClipPath(path)
    # Свет, прошедший сквозь стекло, мягко скапливается у нижнего края
    low = QRectF(rect.left(), rect.bottom() - rect.height() * 0.35, rect.width(), rect.height() * 0.35)
    caustic = QLinearGradient(low.topLeft(), low.bottomLeft())
    caustic.setColorAt(0.0, QColor(255, 255, 255, 0))
    caustic.setColorAt(1.0, QColor(255, 255, 255, 0 if kind == "play" else 22))
    p.fillRect(low, caustic)
    # Глянец: мягкое светлое пятно в верхней половине
    high = QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.6)
    gloss = QLinearGradient(high.topLeft(), high.bottomLeft())
    gloss.setColorAt(0.0, QColor(255, 255, 255, (12 if dark_body else 46) if not down else 8))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(high, gloss)
    p.restore()

    # Кант: блик по верхнему краю гаснет к середине, снизу — лёгкая тень
    highlight, shade = pal.color("glass_highlight"), pal.color("glass_shade")
    if dark_body:
        highlight = QColor(255, 255, 255, 34)
    rim = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    rim.setColorAt(0.0, highlight)
    rim.setColorAt(0.45, _with_alpha(highlight, 0))
    rim.setColorAt(0.6, _with_alpha(shade, 0))
    rim.setColorAt(1.0, shade)
    p.save()
    p.setPen(QPen(rim, 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    inner = rect.adjusted(0.5, 0.5, -0.5, -0.5)
    p.drawRoundedRect(inner, max(radius - 0.5, 0), max(radius - 0.5, 0))
    p.restore()

"""
Значки интерфейса — векторные фигуры, нарисованные в самом приложении.

Шрифтами значков пользоваться нельзя: Segoe Fluent Icons есть не на всех Windows,
а вшивать его лицензия не разрешает. Без него Windows подставляет случайные символы
(например, иероглифы). Здесь значки не зависят от системы и одинаковы везде.
Все фигуры заданы в квадрате 24×24.
"""

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform
from PyQt6.QtWidgets import QPushButton

from ui.styles import T


class Icons:
    PLAY = "play"
    PAUSE = "pause"
    PREVIOUS = "previous"
    NEXT = "next"
    VOLUME = "volume"
    MUTE = "mute"
    FULLSCREEN = "fullscreen"
    EXIT_FULLSCREEN = "exit_fullscreen"
    ADD = "add"
    VIDEO = "video"
    SETTINGS = "settings"
    CIRCLE_ARROW = "circle_arrow"  # круговая стрелка по часовой
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    CLOSE = "close"


def _polygon(*points) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(*point)
    path.closeSubpath()
    return path


def _lines(*segments) -> QPainterPath:
    """Ломаные линии: каждая — список точек"""
    path = QPainterPath()
    for points in segments:
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
    return path


def _speaker() -> QPainterPath:
    return _polygon((3.5, 9.2), (7.2, 9.2), (12, 5), (12, 19), (7.2, 14.8), (3.5, 14.8))


def _gear() -> QPainterPath:
    teeth, outer, inner = 8, 10.4, 7.9
    step = 2 * math.pi / teeth
    points = []
    for i in range(teeth):
        a = i * step
        for angle, radius in ((a - step * 0.30, inner), (a - step * 0.16, outer),
                              (a + step * 0.16, outer), (a + step * 0.30, inner)):
            points.append((12 + radius * math.cos(angle), 12 + radius * math.sin(angle)))
    path = _polygon(*points)
    path.addEllipse(QPointF(12, 12), 3.2, 3.2)
    return path


def _circle_arrow() -> QPainterPath:
    box = QRectF(3, 3, 18, 18)
    path = QPainterPath()
    path.arcMoveTo(box, 45)
    path.arcTo(box, 45, -315)  # по часовой, от правого верхнего края до верха
    path.moveTo(10.2, 0.2)
    path.lineTo(13.4, 3)
    path.lineTo(10.2, 5.8)
    return path


def _video() -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(2.5, 5.5, 13.5, 13), 3, 3)
    path.addPath(_polygon((16, 10.5), (21.5, 7.2), (21.5, 16.8), (16, 13.5)))
    return path


def _restore() -> QPainterPath:
    path = QPainterPath()
    path.addRect(QRectF(3, 7, 14, 14))
    path.addPath(_lines([(7, 7), (7, 3), (21, 3), (21, 17), (17, 17)]))
    return path


def _rect_path(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    path.addRect(rect)
    return path


def _pause() -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(6, 4, 4.4, 16), 1.4, 1.4)
    path.addRoundedRect(QRectF(13.6, 4, 4.4, 16), 1.4, 1.4)
    return path


def _prev_next(flip: bool) -> QPainterPath:
    path = _polygon((6, 5.5), (17, 12), (6, 18.5))
    path.addRoundedRect(QRectF(17.2, 4.5, 2.6, 15), 1.2, 1.2)
    return QTransform(-1, 0, 0, 1, 24, 0).map(path) if flip else path


# Залитые фигуры: сглаженные углы даёт обводка того же цвета
_FILLED = {
    Icons.PLAY: lambda: _polygon((7.5, 4.8), (19.5, 12), (7.5, 19.2)),
    Icons.PAUSE: _pause,
    Icons.PREVIOUS: lambda: _prev_next(True),
    Icons.NEXT: lambda: _prev_next(False),
}
# Контурные фигуры
_OUTLINED = {
    Icons.FULLSCREEN: lambda: _lines([(4, 9), (4, 4), (9, 4)], [(15, 4), (20, 4), (20, 9)],
                                     [(20, 15), (20, 20), (15, 20)], [(9, 20), (4, 20), (4, 15)]),
    Icons.EXIT_FULLSCREEN: lambda: _lines([(9, 4), (9, 9), (4, 9)], [(20, 9), (15, 9), (15, 4)],
                                          [(15, 20), (15, 15), (20, 15)], [(4, 15), (9, 15), (9, 20)]),
    Icons.ADD: lambda: _lines([(12, 4), (12, 20)], [(4, 12), (20, 12)]),
    Icons.VIDEO: _video,
    Icons.SETTINGS: _gear,
    Icons.CIRCLE_ARROW: _circle_arrow,
    Icons.MINIMIZE: lambda: _lines([(3, 12), (21, 12)]),
    Icons.MAXIMIZE: lambda: _rect_path(QRectF(3, 3, 18, 18)),
    Icons.RESTORE: _restore,
    Icons.CLOSE: lambda: _lines([(3, 3), (21, 21)], [(21, 3), (3, 21)]),
}


def _volume_waves(p: QPainter):
    for radius, span in ((4.6, 70), (8.0, 80)):
        box = QRectF(12 - radius + 1.5, 12 - radius, radius * 2, radius * 2)
        path = QPainterPath()
        path.arcMoveTo(box, span / 2)
        path.arcTo(box, span / 2, -span)
        p.drawPath(path)


def draw_icon(p: QPainter, name: str, rect: QRectF, color: QColor, stroke: float = 1.8):
    """Нарисовать значок в квадрате rect. stroke — толщина линий в единицах сетки 24×24"""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(rect.topLeft())
    p.scale(rect.width() / 24, rect.height() / 24)
    pen = QPen(color, stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if name in _FILLED:
        p.setBrush(color)
        p.drawPath(_FILLED[name]())
    elif name in (Icons.VOLUME, Icons.MUTE):
        p.setBrush(color)
        p.drawPath(_speaker())
        p.setBrush(Qt.BrushStyle.NoBrush)
        if name == Icons.VOLUME:
            _volume_waves(p)
        else:
            p.drawPath(_lines([(15.5, 9), (21, 15)], [(21, 9), (15.5, 15)]))
    else:
        p.drawPath(_OUTLINED[name]())
    p.restore()


class IconButton(QPushButton):
    """Кнопка со значком. Фон и объём — как у обычной кнопки (стили, GlassLook)"""

    def __init__(self, icon: str, icon_size: int = 16, palette=None,
                 color: str = "text", hover_color=None, stroke: float = 1.8):
        super().__init__()
        self.icon_name = icon
        self.icon_size_px = icon_size
        self._palette = palette      # None — текущая тема
        self._color = color          # ключ цвета палитры
        self._hover_color = hover_color  # ключ палитры или QColor
        self._stroke = stroke

    def set_icon(self, icon: str):
        self.icon_name = icon
        self.update()

    def _current_color(self) -> QColor:
        pal = self._palette or T
        wanted = self._hover_color if self._hover_color is not None and self.underMouse() else self._color
        return QColor(wanted) if isinstance(wanted, QColor) else pal.color(wanted)

    def paintEvent(self, event):
        super().paintEvent(event)
        size = self.icon_size_px
        rect = QRectF((self.width() - size) / 2, (self.height() - size) / 2, size, size)
        p = QPainter(self)
        draw_icon(p, self.icon_name, rect, self._current_color(), self._stroke)

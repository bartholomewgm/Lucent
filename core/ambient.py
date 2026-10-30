"""
Цвета фона под видео («эмбиент»): дважды в секунду берём кадр и в трёх зонах ищем
его заметный цвет. Простое среднее почти любого кадра — буро-серое, поэтому
насыщенные и светлые пиксели весят намного больше, а итог усиливается для фона.
"""

from PyQt6.QtCore import QElapsedTimer, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor

# Зоны кадра (доли x0, y0, x1, y1) под пятнами фона: левый верх, правый край, низ
ZONES = ((0.0, 0.0, 0.5, 0.5), (0.5, 0.15, 1.0, 0.85), (0.15, 0.5, 0.85, 1.0))


def _vivid(image, zone) -> QColor:
    """Средний цвет зоны с весом по насыщенности и яркости пикселя"""
    w, h = image.width(), image.height()
    x0, y0, x1, y1 = (round(zone[0] * w), round(zone[1] * h), round(zone[2] * w), round(zone[3] * h))
    r = g = b = total = 0.0
    for y in range(y0, max(y1, y0 + 1)):
        for x in range(x0, max(x1, x0 + 1)):
            c = image.pixelColor(min(x, w - 1), min(y, h - 1))
            weight = 0.01 + c.saturationF() ** 2 * c.valueF()
            r, g, b, total = r + c.red() * weight, g + c.green() * weight, b + c.blue() * weight, total + weight
    return QColor(round(r / total), round(g / total), round(b / total))


def _for_background(color: QColor) -> QColor:
    """Цвет кадра — в «светящееся» пятно: насыщенное и не тёмное"""
    h, s, v, _ = color.getHsvF()
    if s < 0.1:  # чёрно-белая картинка: оставляем нейтральным, но видимым
        return QColor.fromHsvF(max(h, 0.0), s, min(max(v, 0.4), 0.65))
    return QColor.fromHsvF(max(h, 0.0), min(max(s * 1.5, 0.6), 0.95), min(max(v * 1.4, 0.65), 0.95))


def _distance(a: QColor, b: QColor) -> int:
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())


class AmbientColors(QObject):
    palette_changed = pyqtSignal(list)  # три QColor — для трёх пятен фона

    INTERVAL_MS = 500
    MIN_CHANGE = 24  # меньшие изменения не стоят перерисовки фона

    def __init__(self, sink, parent=None):
        super().__init__(parent)
        self.enabled = True
        self._last = None
        self._clock = QElapsedTimer()
        self._sink = sink
        sink.videoFrameChanged.connect(self._on_frame)

    def set_sink(self, sink):
        """Видео стало выводиться в другое окно (мини-плеер)"""
        self._sink.videoFrameChanged.disconnect(self._on_frame)
        self._sink = sink
        sink.videoFrameChanged.connect(self._on_frame)

    def reset(self):
        self._last = None
        self._clock.invalidate()

    def _on_frame(self, frame):
        if not self.enabled or not frame.isValid():
            return
        if self._clock.isValid() and self._clock.elapsed() < self.INTERVAL_MS:
            return
        self._clock.start()
        # Кадр сразу в маленькую картинку — сам кадр не держим
        image = frame.toImage().scaled(32, 18, Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        if image.isNull():
            return
        colors = [_for_background(_vivid(image, zone)) for zone in ZONES]
        if self._last and all(_distance(a, b) < self.MIN_CHANGE for a, b in zip(colors, self._last)):
            return
        self._last = colors
        self.palette_changed.emit(colors)

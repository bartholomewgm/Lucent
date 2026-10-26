"""
Цвета фона под видео («эмбиент»): раз в секунду берём кадр, считаем средний цвет
в зонах, где на фоне лежат цветные пятна, и делаем цвета пригодными для фона —
достаточно насыщенными и не слишком яркими/тёмными.
"""

from PyQt6.QtCore import QElapsedTimer, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor

# Зоны кадра (доли x0, y0, x1, y1) под пятнами фона: левый верх, правый край, низ
ZONES = ((0.0, 0.0, 0.5, 0.5), (0.5, 0.15, 1.0, 0.85), (0.15, 0.5, 0.85, 1.0))


def _average(image, zone) -> QColor:
    w, h = image.width(), image.height()
    x0, y0, x1, y1 = (round(zone[0] * w), round(zone[1] * h), round(zone[2] * w), round(zone[3] * h))
    r = g = b = n = 0
    for y in range(y0, max(y1, y0 + 1)):
        for x in range(x0, max(x1, x0 + 1)):
            c = image.pixelColor(min(x, w - 1), min(y, h - 1))
            r, g, b, n = r + c.red(), g + c.green(), b + c.blue(), n + 1
    return QColor(r // n, g // n, b // n)


def _for_background(color: QColor) -> QColor:
    """Средний цвет кадра часто серый и тёмный — делаем его «светящимся» пятном"""
    h, s, v, _ = color.getHsvF()
    if s < 0.08:  # почти серое: оставляем нейтральным, но видимым
        return QColor.fromHsvF(max(h, 0.0), s, min(max(v, 0.35), 0.6))
    return QColor.fromHsvF(max(h, 0.0), min(max(s * 1.4, 0.45), 0.85), min(max(v * 1.3, 0.45), 0.8))


def _distance(a: QColor, b: QColor) -> int:
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue())


class AmbientColors(QObject):
    palette_changed = pyqtSignal(list)  # три QColor — для трёх пятен фона

    INTERVAL_MS = 1000
    MIN_CHANGE = 36  # меньшие изменения не стоят перерисовки фона

    def __init__(self, sink, parent=None):
        super().__init__(parent)
        self.enabled = True
        self._last = None
        self._clock = QElapsedTimer()
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
        colors = [_for_background(_average(image, zone)) for zone in ZONES]
        if self._last and all(_distance(a, b) < self.MIN_CHANGE for a, b in zip(colors, self._last)):
            return
        self._last = colors
        self.palette_changed.emit(colors)

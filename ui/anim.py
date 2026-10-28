"""
Плавная анимация с частотой кадров монитора.

Встроенные анимации Qt (QPropertyAnimation) обновляются не чаще 60 раз в секунду —
на мониторе 144/240 Гц это заметно дёргается. SmoothAnimation тикает так часто,
как обновляется экран, и отдаёт прогресс 0…1 уже по кривой сглаживания.
"""

from PyQt6.QtCore import QEasingCurve, QElapsedTimer, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication


class SmoothAnimation(QObject):
    step = pyqtSignal(float)  # прогресс 0…1 после кривой; последний шаг — ровно 1

    def __init__(self, duration_ms: int, parent=None, curve=QEasingCurve.Type.OutCubic):
        super().__init__(parent)
        self.duration = duration_ms
        self._curve = QEasingCurve(curve)
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)

    def start(self):
        widget = self.parent()
        screen = widget.screen() if hasattr(widget, "screen") else QGuiApplication.primaryScreen()
        hz = screen.refreshRate() if screen else 60.0
        self._timer.setInterval(max(1, int(1000 / max(hz, 60.0))))
        self._clock.start()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    def _tick(self):
        t = min(1.0, self._clock.nsecsElapsed() / 1e6 / self.duration)
        if t >= 1.0:
            self._timer.stop()
        self.step.emit(self._curve.valueForProgress(t))

"""
Превью видео для обложки: отдельный скрытый плеер без звука встаёт на паузу
на ~10% длительности и отдаёт кадр. Основной плеер при этом не трогается.
"""

from PyQt6.QtCore import QObject, QTimer, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink


def _is_dark(image: QImage) -> bool:
    """Почти чёрный кадр (затемнение, титры на чёрном) — не годится в превью"""
    total = n = 0
    for y in range(0, image.height(), max(image.height() // 8, 1)):
        for x in range(0, image.width(), max(image.width() // 8, 1)):
            c = image.pixelColor(x, y)
            total += (c.red() + c.green() + c.blue()) / 3
            n += 1
    return total / max(n, 1) < 18


class Thumbnailer(QObject):
    ready = pyqtSignal(str, QImage)  # путь, кадр

    POSITIONS = (0.10, 0.25, 0.50)  # доли длительности: если кадр тёмный — берём дальше
    THUMB_SIZE = 256
    TIMEOUT_MS = 6000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = {}
        self._path = None
        self._attempt = 0
        self._target = -1

        self._player = QMediaPlayer(self)  # без QAudioOutput — звука нет
        self._sink = QVideoSink(self)
        self._player.setVideoSink(self._sink)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(self.TIMEOUT_MS)
        self._timeout.timeout.connect(self._give_up)

    def request(self, path: str):
        if path in self._cache:
            image = self._cache[path]
            QTimer.singleShot(0, lambda: self.ready.emit(path, image))
            return
        self._reset()
        self._path = path
        self._attempt = 0
        self._timeout.start()
        self._player.setSource(QUrl.fromLocalFile(path))

    def _on_status(self, status):
        if self._path and self._target < 0 and status == QMediaPlayer.MediaStatus.LoadedMedia:
            self._seek()

    def _seek(self):
        self._target = int(self._player.duration() * self.POSITIONS[self._attempt])
        self._player.setPosition(self._target)
        self._player.pause()  # на паузе ffmpeg отдаёт один кадр после перехода

    def _on_frame(self, frame):
        if not self._path or self._target < 0 or not frame.isValid():
            return
        if frame.startTime() // 1000 < self._target - 2000:
            return  # кадр ещё с прежнего места
        image = frame.toImage().scaled(
            self.THUMB_SIZE, self.THUMB_SIZE,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        if _is_dark(image) and self._attempt < len(self.POSITIONS) - 1:
            self._attempt += 1
            self._seek()
            return
        path = self._path
        self._cache[path] = image
        self._reset()
        self.ready.emit(path, image)

    def _give_up(self):
        self._reset()  # нет видеодорожки или файл не открылся — остаётся значок

    def _reset(self):
        self._timeout.stop()
        self._path = None
        self._target = -1
        self._player.stop()
        self._player.setSource(QUrl())

"""
Сведения о видеофайле для окна «Свойства»: метаданные, параметры дорожек
и число звуковых каналов. Собирает скрытый плеер без вывода и аудиодекодер,
поэтому работает для любого файла, а не только для играющего.
"""

from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioDecoder, QMediaMetaData, QMediaPlayer

K = QMediaMetaData.Key
# metaData().keys() в PyQt6 роняет процесс — читаем только нужные ключи по одному
_KEYS = {
    "title": K.Title,
    "subtitle": K.Description,
    "comment": K.Comment,
    "artists": K.ContributingArtist,
    "author": K.Author,
    "genre": K.Genre,
    "date": K.Date,
    "duration": K.Duration,
    "resolution": K.Resolution,
    "frame_rate": K.VideoFrameRate,
    "video_codec": K.VideoCodec,
    "audio_codec": K.AudioCodec,
    "video_bitrate": K.VideoBitRate,
    "audio_bitrate": K.AudioBitRate,
    "container": K.FileFormat,
}


class MediaInfoProbe(QObject):
    finished = pyqtSignal(dict)

    TIMEOUT_MS = 6000

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.info = {"path": path}
        try:
            self.info["size"] = Path(path).stat().st_size
        except OSError:
            self.info["size"] = None
        self._meta_done = False
        self._channels_done = False

        self._player = QMediaPlayer(self)  # без выводов: ничего не показывает и не звучит
        self._player.mediaStatusChanged.connect(self._on_status)
        self._decoder = QAudioDecoder(self)
        self._decoder.bufferReady.connect(self._on_buffer)
        self._decoder.error.connect(lambda *_: self._channels(None))
        self._decoder.finished.connect(lambda: self._channels(None))
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._finish)

    def start(self):
        url = QUrl.fromLocalFile(self.info["path"])
        self._timeout.start(self.TIMEOUT_MS)
        self._player.setSource(url)
        self._decoder.setSource(url)
        self._decoder.start()

    def _on_status(self, status):
        if self._meta_done:
            return
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            meta = self._player.metaData()
            for name, key in _KEYS.items():
                self.info[name] = meta.value(key)
            self._meta_done = True
            self._player.setSource(QUrl())
            self._maybe_finish()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._meta_done = True
            self._maybe_finish()

    def _on_buffer(self):
        buffer = self._decoder.read()
        self._channels(buffer.format().channelCount())

    def _channels(self, count):
        if self._channels_done:
            return
        self._channels_done = True
        self.info["channels"] = count
        self._decoder.stop()
        self._maybe_finish()

    def _maybe_finish(self):
        if self._meta_done and self._channels_done:
            self._finish()

    def _finish(self):
        if self._timeout.isActive():
            self._timeout.stop()
        if "finished" in self.info:
            return
        self.info["finished"] = True
        self._decoder.stop()
        self.finished.emit(self.info)

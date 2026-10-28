"""
Модуль видеоплеера (движок)
Обёртка над QMediaPlayer
"""

from pathlib import Path

from PyQt6.QtCore import QUrl, pyqtSignal, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from core.i18n import tr


class VideoPlayer(QObject):
    """Обёртка над QMediaPlayer"""

    # Сигналы для связи с UI
    media_state_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    finished = pyqtSignal()  # видео доиграло до конца

    def __init__(self, parent=None):
        super().__init__(parent)

        # ========== ПЛЕЕР ==========
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self.audio.setVolume(0.5)
        
        # ========== ПОДКЛЮЧЕНИЕ СИГНАЛОВ ==========
        # ВАЖНО: подключаем сигналы QMediaPlayer к нашим слотам-обработчикам
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_error)
        
        # НЕ ПОДКЛЮЧАЕМ НАПРЯМУЮ! Используем промежуточные методы
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def set_video_output(self, output: QObject):
        """Куда выводить картинку (VideoOutput из ui/video.qml)"""
        self.player.setVideoOutput(output)

    def video_sink(self):
        return self.player.videoSink()

    # ========== ЗАГРУЗКА ==========

    def load_video(self, file_path: str) -> bool:
        """Загружает видео файл"""
        try:
            if not Path(file_path).is_file():
                self.error_occurred.emit(tr("Файл не найден: {}").format(file_path))
                return False
            self.player.setSource(QUrl.fromLocalFile(file_path))
            return True
        except Exception as e:
            self.error_occurred.emit(tr("Ошибка загрузки: {}").format(e))
            return False

    # ========== УПРАВЛЕНИЕ ==========

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def is_playing(self) -> bool:
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ========== ПОЗИЦИЯ ==========

    def set_position(self, position: int):
        self.player.setPosition(position)

    def get_position(self) -> int:
        return self.player.position()
    
    def position(self) -> int:
        return self.player.position()

    def duration(self) -> int:
        return self.player.duration()

    # ========== ГРОМКОСТЬ ==========

    def set_volume(self, value: int):
        self.audio.setVolume(max(0.0, min(1.0, value / 100)))

    # ========== СКОРОСТЬ ==========

    def set_speed(self, speed: float):
        self.player.setPlaybackRate(speed)

    # ========== ПЕРЕМОТКА ==========

    def forward(self, milliseconds: int = 5000):
        new_pos = self.player.position() + milliseconds
        self.player.setPosition(min(new_pos, self.player.duration()))

    def backward(self, milliseconds: int = 5000):
        new_pos = self.player.position() - milliseconds
        self.player.setPosition(max(0, new_pos))

    # ========== ВНУТРЕННИЕ ОБРАБОТЧИКИ ==========

    def _on_playback_state_changed(self, state):
        """Обработчик изменения состояния воспроизведения"""
        is_playing = (state == QMediaPlayer.PlaybackState.PlayingState)
        self.media_state_changed.emit(is_playing)
    
    def _on_error(self, error, error_string):
        """Обработчик ошибок QMediaPlayer"""
        self.error_occurred.emit(tr("Ошибка: {}").format(error_string))
    
    def _on_position_changed(self, position):
        """Прокси-обработчик для позиции"""
        self.position_changed.emit(position)
    
    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.finished.emit()

    def _on_duration_changed(self, duration):
        """Прокси-обработчик для длительности"""
        self.duration_changed.emit(duration)
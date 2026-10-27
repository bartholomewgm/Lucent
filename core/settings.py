"""
Настройки плеера: хранятся в INI-файле профиля пользователя
(%APPDATA%\\Lucent\\Lucent.ini) и переживают перезапуск
"""

from PyQt6.QtCore import QObject, QSettings, pyqtSignal


class Settings(QObject):
    """Типизированная обёртка над QSettings с сигналом об изменении"""

    changed = pyqtSignal(str, object)  # ключ, новое значение

    # Значения по умолчанию: тип значения задаёт тип при чтении
    DEFAULTS = {
        "resume": "always",          # always | ask | never
        "skip_seconds": 10,          # шаг кнопок ↺/↻
        "on_end": "stop",            # stop | next | repeat
        "remember_volume": True,
        "volume": 50,
        "fullscreen_hide_seconds": 3,  # 0 — не прятать
        "theme": "gradient",         # gradient | dark | light (см. ui/styles.py)
        "ambient_background": True,  # фон под цвета видео
        "aspect_mode": "auto",       # формат картинки (см. ui/video_frame.py)
        "playlist_folder": "",       # пусто — очередь собирается вручную
        "watch_folder": True,        # подхватывать новые видео из папки-плейлиста
        "folder_sort": "name",       # name | date
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._store = QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Lucent", "Lucent"
        )

    def get(self, key: str):
        default = self.DEFAULTS[key]
        return self._store.value(key, default, type=type(default))

    def set(self, key: str, value):
        if self.get(key) == value:
            return
        self._store.setValue(key, value)
        self.changed.emit(key, value)

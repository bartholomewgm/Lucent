"""
Папка-плейлист: все видео из выбранной папки и слежение за ней.
Новый файл попадает в очередь только когда «дописан» — его размер перестал
меняться (иначе в очередь попадёт видео, которое ещё скачивается или копируется).
"""

import os
import re
from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal


def _natural_key(path: str):
    """«Серия 2» раньше «Серия 10»"""
    name = Path(path).name.casefold()
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


class FolderPlaylist(QObject):
    added = pyqtSignal(str)
    removed = pyqtSignal(str)

    SCAN_DELAY_MS = 400      # пачку событий от системы обрабатываем одним сканом
    CHECK_INTERVAL_MS = 1000
    STABLE_CHECKS = 2        # столько проверок подряд размер не должен меняться

    def __init__(self, extensions, parent=None):
        super().__init__(parent)
        self._extensions = {ext.lower() for ext in extensions}
        self._folder = None
        self._known = set()
        self._pending = {}  # путь -> (последний размер, сколько раз подряд не менялся)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(self._schedule_scan)
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.setInterval(self.SCAN_DELAY_MS)
        self._scan_timer.timeout.connect(self._scan)
        self._stable_timer = QTimer(self)
        self._stable_timer.setInterval(self.CHECK_INTERVAL_MS)
        self._stable_timer.timeout.connect(self._check_pending)

    # ----- Управление -----

    def start(self, folder: str, watch: bool, sort: str) -> list:
        """Начать работу с папкой; вернуть её видео в нужном порядке"""
        self.stop()
        self._folder = str(Path(folder).resolve())
        files = self._video_files()
        self._known = set(files)
        if watch:
            self._watcher.addPath(self._folder)
        return self.sorted(files, sort)

    def stop(self):
        if self._watcher.directories():
            self._watcher.removePaths(self._watcher.directories())
        self._scan_timer.stop()
        self._stable_timer.stop()
        self._folder = None
        self._known.clear()
        self._pending.clear()

    @staticmethod
    def sorted(files, sort: str) -> list:
        if sort == "date":
            return sorted(files, key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
        return sorted(files, key=_natural_key)

    # ----- Слежение -----

    def _video_files(self) -> set:
        try:
            with os.scandir(self._folder) as entries:
                return {
                    str(Path(e.path).resolve()) for e in entries
                    if e.is_file() and Path(e.name).suffix.lower() in self._extensions
                }
        except OSError:
            return set()

    def _schedule_scan(self, _path=None):
        self._scan_timer.start()

    def _scan(self):
        if not self._folder:
            return
        current = self._video_files()
        for path in self._known - current:
            self._known.discard(path)
            self.removed.emit(path)
        for path in list(self._pending):
            if path not in current:
                del self._pending[path]
        for path in current - self._known - self._pending.keys():
            self._pending[path] = (-1, 0)
        if self._pending and not self._stable_timer.isActive():
            self._stable_timer.start()

    def _check_pending(self):
        for path, (last_size, stable) in list(self._pending.items()):
            try:
                size = os.path.getsize(path)
            except OSError:
                del self._pending[path]
                continue
            stable = stable + 1 if size > 0 and size == last_size else 0
            if stable >= self.STABLE_CHECKS:
                del self._pending[path]
                self._known.add(path)
                self.added.emit(path)
            else:
                self._pending[path] = (size, stable)
        if not self._pending:
            self._stable_timer.stop()

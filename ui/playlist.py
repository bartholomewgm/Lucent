"""
Виджет плейлиста в стиле Spotify
"""

from pathlib import Path

from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt

from ui.styles import SPOTIFY_TEXT_SUB, SPOTIFY_TEXT, SPOTIFY_GREEN


class PlaylistWidget(QListWidget):
    """Виджет плейлиста"""

    def __init__(self):
        super().__init__()
        self.video_files = []
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {SPOTIFY_TEXT_SUB};
                font-size: 14px;
                outline: none;
                padding: 0px;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 4px;
                margin: 1px 0px;
            }}
            QListWidget::item:hover {{
                color: {SPOTIFY_TEXT};
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.12);
                color: {SPOTIFY_GREEN};
                font-weight: 600;
            }}
        """)

    def add_video(self, file_path: str) -> int:
        """Добавляет видео в плейлист. Возвращает индекс."""
        file_path = str(Path(file_path).resolve())
        if file_path in self.video_files:
            return self.video_files.index(file_path)

        self.video_files.append(file_path)
        video_name = Path(file_path).stem
        if len(video_name) > 32:
            video_name = video_name[:29] + "..."

        item = QListWidgetItem(f"  {video_name}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setToolTip(file_path)
        self.addItem(item)
        return len(self.video_files) - 1

    def select_video(self, file_path: str):
        """Выделяет текущее видео в списке."""
        file_path = str(Path(file_path).resolve())
        if file_path not in self.video_files:
            return
        row = self.video_files.index(file_path)
        self.setCurrentRow(row)

    def get_video_path(self, row: int):
        if 0 <= row < self.count():
            item = self.item(row)
            if item:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path:
                    return str(path)
        return None

    def current_video(self):
        return self.get_video_path(self.currentRow())

    def next_video(self):
        row = self.currentRow() + 1
        if row < self.count():
            self.setCurrentRow(row)
            return self.get_video_path(row)
        return None

    def previous_video(self):
        row = self.currentRow() - 1
        if row >= 0:
            self.setCurrentRow(row)
            return self.get_video_path(row)
        return None

    def clear_playlist(self):
        self.clear()
        self.video_files.clear()

    def has_videos(self) -> bool:
        return len(self.video_files) > 0

    def get_count(self) -> int:
        return len(self.video_files)

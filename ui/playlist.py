"""
Виджет плейлиста в стиле Spotify
"""

from pathlib import Path

from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from ui.styles import SPOTIFY_TEXT_SUB, SPOTIFY_TEXT, SPOTIFY_GREEN, SPOTIFY_DARK


class PlaylistWidget(QListWidget):
    """Виджет плейлиста"""

    count_changed = pyqtSignal(int)

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
                padding: 4px 0px;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px 0px;
            }}
            QListWidget::item:hover {{
                color: {SPOTIFY_TEXT};
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {SPOTIFY_GREEN};
                font-weight: 600;
            }}
        """)

    def add_video(self, file_path: str) -> int:
        file_path = str(Path(file_path).resolve())
        if file_path in self.video_files:
            return self.video_files.index(file_path)

        self.video_files.append(file_path)
        video_name = Path(file_path).stem
        if len(video_name) > 32:
            video_name = video_name[:29] + "..."

        item = QListWidgetItem(f"🎬  {video_name}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        item.setToolTip(file_path)
        self.addItem(item)
        self.count_changed.emit(len(self.video_files))
        return len(self.video_files) - 1

    def select_video(self, file_path: str):
        file_path = str(Path(file_path).resolve())
        if file_path not in self.video_files:
            return
        row = self.video_files.index(file_path)
        self.setCurrentRow(row)
        self.scrollToItem(self.item(row), QListWidget.ScrollHint.PositionAtCenter)

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
        self.count_changed.emit(0)

    def has_videos(self) -> bool:
        return len(self.video_files) > 0

    def get_count(self) -> int:
        return len(self.video_files)

    def remove_video(self, row: int) -> bool:
        if 0 <= row < self.count():
            self.takeItem(row)
            if row < len(self.video_files):
                del self.video_files[row]
            self.count_changed.emit(len(self.video_files))
            return True
        return False


class PlaylistHeaderWidget(QWidget):
    """Заголовок плейлиста с количеством видео"""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {SPOTIFY_DARK};
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        self.title_label = QLabel("Плейлист")
        self.title_label.setStyleSheet(f"""
            color: {SPOTIFY_TEXT};
            font-size: 14px;
            font-weight: 700;
        """)
        
        self.count_label = QLabel("0 видео")
        self.count_label.setStyleSheet(f"""
            color: {SPOTIFY_TEXT_SUB};
            font-size: 11px;
        """)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.count_label)
        self.setLayout(layout)
    
    def update_count(self, count: int):
        if count == 0:
            self.count_label.setText("Нет видео")
        elif count == 1:
            self.count_label.setText("1 видео")
        else:
            self.count_label.setText(f"{count} видео")
from pathlib import Path

from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal

from ui.glass import make_glass_menu
from ui.styles import GLASS_TEXT_SUB, GLASS_TEXT, GLASS_ACCENT_SOFT


class PlaylistWidget(QListWidget):
    """Виджет плейлиста"""

    count_changed = pyqtSignal(int)
    remove_requested = pyqtSignal(str)  # путь видео, которое просят убрать из очереди

    def __init__(self):
        super().__init__()
        self.video_files = []
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {GLASS_TEXT_SUB};
                font-size: 13px;
                outline: none;
                padding: 2px 0px;
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 12px;
                margin: 2px 0px;
            }}
            QListWidget::item:hover {{
                color: {GLASS_TEXT};
                background-color: rgba(255, 255, 255, 0.07);
            }}
            QListWidget::item:selected {{
                background-color: {GLASS_ACCENT_SOFT};
                color: {GLASS_TEXT};
                font-weight: 600;
            }}
        """)

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = make_glass_menu(self)
        remove = menu.addAction("Удалить из очереди")
        if menu.exec(self.viewport().mapToGlobal(pos)) == remove:
            self.remove_requested.emit(str(path))

    def request_remove_current(self):
        """Удалить выделенное видео (клавиша Delete)"""
        path = self.current_video()
        if path:
            self.remove_requested.emit(path)

    def add_video(self, file_path: str) -> int:
        file_path = str(Path(file_path).resolve())
        if file_path in self.video_files:
            return self.video_files.index(file_path)

        self.video_files.append(file_path)
        video_name = Path(file_path).stem
        if len(video_name) > 32:
            video_name = video_name[:29] + "..."

        item = QListWidgetItem(video_name)
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

    def remove_path(self, file_path: str) -> bool:
        file_path = str(Path(file_path).resolve())
        if file_path not in self.video_files:
            return False
        return self.remove_video(self.video_files.index(file_path))

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
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        self.title_label = QLabel("Плейлист")
        self.title_label.setStyleSheet(f"""
            color: {GLASS_TEXT};
            font-size: 14px;
            font-weight: 700;
        """)
        
        self.count_label = QLabel("0 видео")
        self.count_label.setStyleSheet(f"""
            color: {GLASS_TEXT_SUB};
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
"""
Главное окно приложения — layout в стиле Spotify
"""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QShortcut, QKeySequence, QDragEnterEvent, QDropEvent

from ui.sidebar import SidebarWidget
from ui.controls import ControlsWidget
from ui.styles import STYLE, SPOTIFY_DARK

from core.player import VideoPlayer
from core.history import HistoryManager


class MainWindow(QMainWindow):
    """Главное окно видеоплеера"""

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

    def __init__(self):
        super().__init__()

        self.setWindowTitle("VideoPlayer")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self.last_folder = str(Path.home())
        self.current_file_path = None
        self._pending_position = 0

        self.player = VideoPlayer()
        self.history = HistoryManager()
        self.sidebar = SidebarWidget()
        self.controls = ControlsWidget()
        self.playlist = self.sidebar.playlist

        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()

        self.setStyleSheet(STYLE)

        self.cursor_timer = None
        self.controls_hide_timer = None
        self._fullscreen_hide_delay = 2000
        self._controls_zone_height = 120
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave_position)
        self.autosave_timer.start(15000)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_ui(self):
        # Область видео
        self.video_container = QWidget()
        self.video_container.setStyleSheet(f"background-color: {SPOTIFY_DARK};")
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self.player.video_widget)
        self.video_container.setLayout(video_layout)

        # Разделитель: сайдбар | видео
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.video_container)
        self.splitter.setSizes([280, self.width() - 280])
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #282828;
            }
        """)

        root = QWidget()
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.splitter, stretch=1)
        root_layout.addWidget(self.controls)
        root.setLayout(root_layout)

        self.setCentralWidget(root)

        self.player.video_widget.setMouseTracking(True)
        self.video_container.setMouseTracking(True)
        self.player.video_widget.installEventFilter(self)
        self.video_container.installEventFilter(self)
        self.controls.installEventFilter(self)
        self.player.video_widget.mouseDoubleClickEvent = self._on_video_double_click

    def setup_connections(self):
        # Сайдбар
        self.sidebar.open_clicked.connect(self.open_file)

        # Кнопки управления
        self.controls.prev_button.clicked.connect(self.prev_video)
        self.controls.play_button.clicked.connect(self.play_pause)
        self.controls.next_button.clicked.connect(self.next_video)

        # Ползунки
        self.controls.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.controls.position_slider.sliderMoved.connect(self.player.set_position)

        # Скорость
        self.controls.speed_changed.connect(self.change_speed)

        # Плейлист
        self.playlist.itemDoubleClicked.connect(self.play_selected_video)

        # Сигналы плеера
        self.player.position_changed.connect(self.update_position)
        self.player.duration_changed.connect(self.update_duration)
        self.player.media_state_changed.connect(self.on_media_state_changed)
        self.player.error_occurred.connect(self.handle_player_error)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.open_file)
        QShortcut(QKeySequence("F"), self).activated.connect(self.toggle_fullscreen)
        QShortcut(QKeySequence("F11"), self).activated.connect(self.toggle_fullscreen)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.exit_fullscreen)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.play_pause)
        QShortcut(QKeySequence("K"), self).activated.connect(self.play_pause)
        QShortcut(QKeySequence("Right"), self).activated.connect(lambda: self.player.forward(5000))
        QShortcut(QKeySequence("Left"), self).activated.connect(lambda: self.player.backward(5000))
        QShortcut(QKeySequence("L"), self).activated.connect(lambda: self.player.forward(5000))
        QShortcut(QKeySequence("J"), self).activated.connect(lambda: self.player.backward(5000))
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(lambda: self.player.forward(30000))
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(lambda: self.player.backward(30000))
        QShortcut(QKeySequence("Up"), self).activated.connect(self._volume_up)
        QShortcut(QKeySequence("Down"), self).activated.connect(self._volume_down)
        QShortcut(QKeySequence("M"), self).activated.connect(self.controls.toggle_mute)
        QShortcut(QKeySequence("N"), self).activated.connect(self.next_video)
        QShortcut(QKeySequence("P"), self).activated.connect(self.prev_video)
        QShortcut(QKeySequence("["), self).activated.connect(lambda: self.controls.cycle_speed(-1))
        QShortcut(QKeySequence("]"), self).activated.connect(lambda: self.controls.cycle_speed(1))
        QShortcut(QKeySequence("Backspace"), self).activated.connect(self.controls.reset_speed)
        QShortcut(QKeySequence("Home"), self).activated.connect(lambda: self.player.set_position(0))
        QShortcut(QKeySequence("End"), self).activated.connect(
            lambda: self.player.set_position(self.player.duration())
        )
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.reload_video)

    # --- Drag & Drop ---

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if Path(path).suffix.lower() in self.VIDEO_EXTENSIONS:
                    self.load_video(path)
                    break

    # --- Громкость ---

    def _on_volume_changed(self, value: int):
        self.player.set_volume(value)
        if value > 0:
            self.controls._muted = False
            self.controls.mute_button.setText("🔊")

    def _volume_up(self):
        v = min(100, self.controls.volume_slider.value() + 5)
        self.controls.volume_slider.setValue(v)

    def _volume_down(self):
        v = max(0, self.controls.volume_slider.value() - 5)
        self.controls.volume_slider.setValue(v)

    # --- Event Filter для полноэкранного режима ---

    def eventFilter(self, obj, event):
        if not self.isFullScreen():
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.MouseMove:
            if obj in (self.player.video_widget, self.video_container):
                window_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                self._handle_fullscreen_mouse(window_pos)
            elif obj == self.controls:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.start_cursor_timer()
                self.show_controls_in_fullscreen()
                if self.controls_hide_timer:
                    self.controls_hide_timer.stop()

        elif event.type() == QEvent.Type.Leave and obj == self.controls:
            self.start_controls_hide_timer()

        return super().eventFilter(obj, event)

    def _handle_fullscreen_mouse(self, window_pos):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.start_cursor_timer()

        if window_pos.y() >= self.height() - self._controls_zone_height:
            self.show_controls_in_fullscreen()
        elif self.controls.isVisible():
            self.start_controls_hide_timer()

    def _on_video_double_click(self, event):
        self.toggle_fullscreen()

    # --- Полноэкранный режим ---

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.sidebar.setVisible(True)
            self.controls.setVisible(True)
            self.controls.set_fullscreen_mode(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._stop_fullscreen_timers()
            self.splitter.setSizes([280, self.width() - 280])
        else:
            self.showFullScreen()
            self.sidebar.setVisible(False)
            self.controls.setVisible(True)
            self.controls.set_fullscreen_mode(True)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.start_cursor_timer()
            self.start_controls_hide_timer()

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.toggle_fullscreen()

    def _stop_fullscreen_timers(self):
        if self.cursor_timer:
            self.cursor_timer.stop()
            self.cursor_timer = None
        if self.controls_hide_timer:
            self.controls_hide_timer.stop()
            self.controls_hide_timer = None

    def start_cursor_timer(self):
        if self.cursor_timer:
            self.cursor_timer.stop()
        self.cursor_timer = QTimer()
        self.cursor_timer.setSingleShot(True)
        self.cursor_timer.timeout.connect(self.hide_cursor)
        self.cursor_timer.start(self._fullscreen_hide_delay)

    def hide_cursor(self):
        if self.isFullScreen():
            self.setCursor(Qt.CursorShape.BlankCursor)

    def start_controls_hide_timer(self):
        if self.controls_hide_timer:
            self.controls_hide_timer.stop()
        self.controls_hide_timer = QTimer()
        self.controls_hide_timer.setSingleShot(True)
        self.controls_hide_timer.timeout.connect(self.hide_controls_in_fullscreen)
        self.controls_hide_timer.start(self._fullscreen_hide_delay)

    def hide_controls_in_fullscreen(self):
        if self.isFullScreen():
            self.controls.setVisible(False)

    def show_controls_in_fullscreen(self):
        if self.isFullScreen():
            self.controls.setVisible(True)
            self.start_controls_hide_timer()

    def mouseMoveEvent(self, event):
        if self.isFullScreen():
            self._handle_fullscreen_mouse(event.pos())
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_F11, Qt.Key.Key_F):
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    # --- Видео ---

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть видео", self.last_folder,
            "Видео (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v)"
        )
        if file_name:
            self.last_folder = str(Path(file_name).parent)
            self.load_video(file_name)

    def load_video(self, file_path: str):
        file_path = str(Path(file_path).resolve())

        if self.current_file_path:
            self.history.save_video(self.current_file_path, self.player.get_position())

        if self.player.load_video(file_path):
            self._pending_position = self.history.get_position(file_path)
            self.current_file_path = file_path

            self.controls.update_track_info(file_path, 0)
            self.playlist.add_video(file_path)
            self.playlist.select_video(file_path)

            self.player.play()
            self.controls.set_play_button_state(True)
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить видео:\n{file_path}")

    def reload_video(self):
        if self.current_file_path:
            pos = self.player.get_position()
            if self.player.load_video(self.current_file_path):
                self.player.set_position(pos)
                self.player.play()

    def play_selected_video(self, item):
        file_path = self.playlist.get_video_path(self.playlist.row(item))
        if file_path:
            self.load_video(file_path)

    def play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.controls.set_play_button_state(False)
        else:
            self.player.play()
            self.controls.set_play_button_state(True)

    def next_video(self):
        file_path = self.playlist.next_video()
        if file_path:
            self.load_video(file_path)

    def prev_video(self):
        file_path = self.playlist.previous_video()
        if file_path:
            self.load_video(file_path)

    def change_speed(self, text: str):
        try:
            speed = float(text.replace("x", ""))
            self.player.set_speed(speed)
        except ValueError:
            pass

    def update_position(self, position: int):
        self.controls.position_slider.blockSignals(True)
        self.controls.position_slider.setValue(position)
        self.controls.position_slider.blockSignals(False)
        self.controls.update_time_display(position, self.player.duration())

    def update_duration(self, duration: int):
        self.controls.position_slider.setRange(0, max(duration, 0))
        if self.current_file_path and duration > 0:
            self.controls.update_track_info(self.current_file_path, duration)
            if self._pending_position > 0:
                self.player.set_position(self._pending_position)
                self._pending_position = 0

    def on_media_state_changed(self, is_playing: bool):
        self.controls.set_play_button_state(is_playing)

    def handle_player_error(self, error_message: str):
        QMessageBox.critical(self, "Ошибка плеера", error_message)

    def _autosave_position(self):
        if self.current_file_path and self.player.duration() > 0:
            self.history.save_video(self.current_file_path, self.player.get_position())

    def closeEvent(self, event):
        self.autosave_timer.stop()
        self._stop_fullscreen_timers()

        if self.current_file_path:
            self.history.save_video(self.current_file_path, self.player.get_position())

        self.history.close()
        event.accept()
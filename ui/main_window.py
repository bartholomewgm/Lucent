from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer
from PyQt6.QtGui import QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QCursor

from ui.sidebar import SidebarWidget, SidebarDrawer
from ui.controls import ControlsWidget
from ui.fullscreen_controls import FullscreenControls
from ui.glass import GlassBackground
from ui.styles import STYLE, GLASS_GAP, GLASS_RADIUS

from core.player import VideoPlayer
from core.history import HistoryManager


class MainWindow(QMainWindow):
    """Главное окно видеоплеера"""

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
    FULLSCREEN_IDLE_MS = 3000  # через сколько бездействия прятать курсор и панель

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
        self.drawer = SidebarDrawer(self.sidebar, GLASS_GAP)
        self.controls = ControlsWidget()
        self.fs_controls = FullscreenControls(self, ControlsWidget.SKIP_SECONDS)
        self.playlist = self.sidebar.playlist

        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()

        self.setStyleSheet(STYLE)

        # Полноэкранный режим: опрашиваем позицию курсора, а не события мыши —
        # так смена раскладки и всплывающая панель не дают ложных «движений»
        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(100)
        self._idle_timer.timeout.connect(self._check_fullscreen_idle)
        self._idle_clock = QElapsedTimer()
        self._last_cursor_pos = None
        self._cursor_hidden = False

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave_position)
        self.autosave_timer.start(15000)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_ui(self):
        # Область видео
        self.video_container = QWidget()
        self.video_container.setObjectName("video_card")
        self.video_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._set_video_card_style(rounded=True)
        video_layout = QVBoxLayout()
        video_layout.setContentsMargins(8, 8, 8, 8)
        video_layout.addWidget(self.player.video_widget)
        self.video_container.setLayout(video_layout)

        # Выдвижной плейлист | видео (отступ между ними входит в ширину drawer)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.drawer)
        content_layout.addWidget(self.video_container, stretch=1)

        root = GlassBackground()
        self.root = root
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(GLASS_GAP, GLASS_GAP, GLASS_GAP, GLASS_GAP)
        root_layout.setSpacing(GLASS_GAP)
        root_layout.addWidget(content, stretch=1)
        root_layout.addWidget(self.controls)
        root.setLayout(root_layout)

        self.setCentralWidget(root)

        self.player.video_widget.mouseDoubleClickEvent = self._on_video_double_click

    def _set_video_card_style(self, rounded: bool):
        if rounded:
            self.video_container.setStyleSheet(f"""
                QWidget#video_card {{
                    background-color: rgba(0, 0, 0, 0.55);
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: {GLASS_RADIUS}px;
                }}
            """)
        else:
            self.video_container.setStyleSheet(
                "QWidget#video_card { background-color: black; border: none; }"
            )

    def _set_glass_layout(self, glass: bool):
        """Стеклянная раскладка с отступами или «голое» видео на весь экран"""
        gap = GLASS_GAP if glass else 0
        self.root.layout().setContentsMargins(gap, gap, gap, gap)
        self.root.layout().setSpacing(gap)
        self.root.plain = not glass
        self.root.update()
        self.video_container.layout().setContentsMargins(*([8] * 4 if glass else [0] * 4))
        self._set_video_card_style(rounded=glass)

    def setup_connections(self):
        # Сайдбар
        self.sidebar.open_clicked.connect(self.open_file)

        # Кнопки управления
        self.controls.prev_button.clicked.connect(self.prev_video)
        self.controls.play_button.clicked.connect(self.play_pause)
        self.controls.next_button.clicked.connect(self.next_video)
        skip_ms = self.controls.SKIP_SECONDS * 1000
        self.controls.rewind_button.clicked.connect(lambda: self.player.backward(skip_ms))
        self.controls.skip_button.clicked.connect(lambda: self.player.forward(skip_ms))
        self.controls.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.controls.playlist_button.clicked.connect(self.drawer.toggle)

        # Полноэкранная панель
        fs = self.fs_controls
        fs.prev_button.clicked.connect(self.prev_video)
        fs.rewind_button.clicked.connect(lambda: self.player.backward(skip_ms))
        fs.play_button.clicked.connect(self.play_pause)
        fs.skip_button.clicked.connect(lambda: self.player.forward(skip_ms))
        fs.next_button.clicked.connect(self.next_video)
        fs.mute_button.clicked.connect(self.controls.toggle_mute)
        fs.exit_button.clicked.connect(self.exit_fullscreen)
        fs.position_slider.sliderMoved.connect(self.player.set_position)
        self.controls.muted_changed.connect(fs.set_muted)
        fs.volume_slider.valueChanged.connect(self.controls.volume_slider.setValue)
        self.controls.volume_slider.valueChanged.connect(fs.set_volume)

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
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.drawer.toggle)

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
            self.controls.set_muted(False)

    def _volume_up(self):
        v = min(100, self.controls.volume_slider.value() + 5)
        self.controls.volume_slider.setValue(v)

    def _volume_down(self):
        v = max(0, self.controls.volume_slider.value() - 5)
        self.controls.volume_slider.setValue(v)

    def _on_video_double_click(self, event):
        self.toggle_fullscreen()

    # --- Полноэкранный режим ---

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self._idle_timer.stop()
            self.fs_controls.hide_now()
            self._show_cursor()
            self.showNormal()
            self._set_glass_layout(True)
            self.drawer.setVisible(True)
            self.controls.setVisible(True)
        else:
            self.showFullScreen()
            self._set_glass_layout(False)
            self.drawer.setVisible(False)
            self.controls.setVisible(False)
            self._last_cursor_pos = QCursor.pos()
            self._idle_clock.start()
            self.fs_controls.show_animated()
            self._idle_timer.start()

    def exit_fullscreen(self):
        if self.isFullScreen():
            self.toggle_fullscreen()

    def _check_fullscreen_idle(self):
        pos = QCursor.pos()
        if pos != self._last_cursor_pos:
            self._last_cursor_pos = pos
            self._idle_clock.restart()
            self._show_cursor()
            self.fs_controls.show_animated()
            return

        # Пока курсор над панелью — не прячем её
        if self.fs_controls.isVisible() and self.fs_controls.geometry().contains(pos):
            self._idle_clock.restart()
            return

        if self._idle_clock.elapsed() >= self.FULLSCREEN_IDLE_MS:
            self._hide_cursor()
            self.fs_controls.hide_animated()

    def _hide_cursor(self):
        if not self._cursor_hidden:
            QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
            self._cursor_hidden = True

    def _show_cursor(self):
        if self._cursor_hidden:
            QApplication.restoreOverrideCursor()
            self._cursor_hidden = False

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
            self._set_play_state(True)
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
            self._set_play_state(False)
        else:
            self.player.play()
            self._set_play_state(True)

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
        self.fs_controls.set_position(position)

    def update_duration(self, duration: int):
        self.controls.position_slider.setRange(0, max(duration, 0))
        self.fs_controls.set_duration(duration)
        if self.current_file_path and duration > 0:
            self.controls.update_track_info(self.current_file_path, duration)
            if self._pending_position > 0:
                self.player.set_position(self._pending_position)
                self._pending_position = 0

    def on_media_state_changed(self, is_playing: bool):
        self._set_play_state(is_playing)

    def _set_play_state(self, is_playing: bool):
        self.controls.set_play_button_state(is_playing)
        self.fs_controls.set_play_button_state(is_playing)

    def handle_player_error(self, error_message: str):
        QMessageBox.critical(self, "Ошибка плеера", error_message)

    def _autosave_position(self):
        if self.current_file_path and self.player.duration() > 0:
            self.history.save_video(self.current_file_path, self.player.get_position())

    def closeEvent(self, event):
        self.autosave_timer.stop()
        self._idle_timer.stop()
        self.fs_controls.hide_now()
        self._show_cursor()

        if self.current_file_path:
            self.history.save_video(self.current_file_path, self.player.get_position())

        self.history.close()
        event.accept()
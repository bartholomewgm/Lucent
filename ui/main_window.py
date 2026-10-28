import ctypes
import sys
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
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer, QLibraryInfo, QTranslator
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtGui import QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QCursor

from ui.sidebar import SidebarWidget, SidebarDrawer
from ui.controls import ControlsWidget, format_time
from ui.fullscreen_controls import FullscreenControls
from ui.glass import GlassBackground
from ui.glass_button import GlassLook
from ui.video_frame import VideoFrame, ASPECT_MODES
from ui.window_frame import TitleBar, handle_native_event, restore_native_frame, IS_WINDOWS
from ui.settings_dialog import SettingsDialog
from ui.properties_dialog import PropertiesDialog
from ui.styles import T, app_style, set_theme, GLASS_GAP, GLASS_RADIUS

from core.player import VideoPlayer
from core.history import HistoryManager
from core.settings import Settings
from core.i18n import tr, set_language, retranslate
from core.folder_playlist import FolderPlaylist
from core.thumbnailer import Thumbnailer
from core.ambient import AmbientColors


# Windows 11 рисует вокруг окна рамку в 1 px — даже в полноэкранном режиме
_DWMWA_BORDER_COLOR = 34
_DWM_COLOR_NONE = 0xFFFFFFFE
_DWM_COLOR_DEFAULT = 0xFFFFFFFF


def set_window_border(widget, visible: bool):
    """Показать или убрать системную рамку окна (только Windows 11, иначе ничего)"""
    if sys.platform != "win32":
        return
    color = ctypes.c_uint(_DWM_COLOR_DEFAULT if visible else _DWM_COLOR_NONE)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())), _DWMWA_BORDER_COLOR,
            ctypes.byref(color), ctypes.sizeof(color),
        )
    except (AttributeError, OSError):
        pass  # старая Windows без этого атрибута — рамки там и нет


class MainWindow(QMainWindow):
    """Главное окно видеоплеера"""

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"}
    RESUME_MIN_MS = 5000  # меньше — не спрашиваем и не продолжаем, начинаем сначала

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Lucent")
        # Свой заголовок на стеклянном фоне; рамку Windows вернём после показа окна
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self._native_frame_ready = False
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self.last_folder = str(Path.home())
        self.current_file_path = None
        self._pending_position = 0

        self.settings = Settings(self)
        # Тема — до создания виджетов: они берут цвета из палитры при построении
        set_theme(self.settings.get("theme"))
        # Язык — тоже до создания виджетов; переводы самого Qt (кнопки «Да/Нет» и т.п.)
        self._qt_translator = QTranslator(self)
        self._set_language(self.settings.get("language"))
        self.player = VideoPlayer()
        self.history = HistoryManager()
        self.sidebar = SidebarWidget()
        self.drawer = SidebarDrawer(self.sidebar, GLASS_GAP)
        self.controls = ControlsWidget()
        self.fs_controls = FullscreenControls(self, self.settings.get("skip_seconds"))
        self.playlist = self.sidebar.playlist
        self.title_bar = TitleBar(self)
        self.folder_playlist = FolderPlaylist(self.VIDEO_EXTENSIONS, self)
        self.thumbnailer = Thumbnailer(self)
        self._folder_items = set()  # видео, пришедшие из папки-плейлиста

        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()

        self.setStyleSheet(app_style())
        self._apply_settings()

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
        # Область видео: картинка по своим пропорциям, со скруглёнными углами
        self.video_container = VideoFrame(GLASS_RADIUS)
        self.player.set_video_output(self.video_container.video_output)
        self.ambient = AmbientColors(self.player.video_sink(), self)
        self.video_container.double_clicked.connect(self.toggle_fullscreen)

        # Выдвижной плейлист | видео (отступ между ними входит в ширину drawer)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.drawer)
        content_layout.addWidget(self.video_container, stretch=1)

        root = GlassBackground()
        self.root = root
        # Заголовок — на всю ширину окна (кнопки окна вплотную к углу, как у Windows),
        # остальное — с общими стеклянными отступами
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(GLASS_GAP, GLASS_GAP, GLASS_GAP, GLASS_GAP)
        self.body_layout.setSpacing(GLASS_GAP)
        self.body_layout.addWidget(content, stretch=1)
        self.body_layout.addWidget(self.controls)

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.title_bar)
        root_layout.addWidget(body, stretch=1)
        root.setLayout(root_layout)

        self.setCentralWidget(root)
        root.set_focus_widget(self.video_container)  # свечение цветов видео — вокруг него
        self.video_container.set_placeholder_color(T.color("placeholder"))

    def _set_glass_layout(self, glass: bool):
        """Стеклянная раскладка с отступами или «голое» видео на весь экран"""
        gap = GLASS_GAP if glass else 0
        self.body_layout.setContentsMargins(gap, gap, gap, gap)
        self.body_layout.setSpacing(gap)
        self.title_bar.setVisible(glass)
        self.root.plain = not glass
        self.root.update()
        self.video_container.set_rounded(glass)

    def setup_connections(self):
        # Сайдбар
        self.sidebar.open_clicked.connect(self.open_file)

        # Кнопки управления
        self.controls.prev_button.clicked.connect(self.prev_video)
        self.controls.play_button.clicked.connect(self.play_pause)
        self.controls.next_button.clicked.connect(self.next_video)
        self.controls.rewind_button.clicked.connect(lambda: self.player.backward(self._skip_ms()))
        self.controls.skip_button.clicked.connect(lambda: self.player.forward(self._skip_ms()))
        self.title_bar.settings_button.clicked.connect(self.open_settings)
        self.controls.fullscreen_button.clicked.connect(self.toggle_fullscreen)

        # Плейлист: кнопка в нижней панели крутится в такт выезду панели
        self.controls.playlist_button.clicked.connect(self.drawer.toggle)
        self.drawer.openness_changed.connect(self.controls.playlist_button.set_progress)
        self.drawer.toggled.connect(self._update_playlist_tooltip)

        # Полноэкранная панель
        fs = self.fs_controls
        fs.prev_button.clicked.connect(self.prev_video)
        fs.rewind_button.clicked.connect(lambda: self.player.backward(self._skip_ms()))
        fs.play_button.clicked.connect(self.play_pause)
        fs.skip_button.clicked.connect(lambda: self.player.forward(self._skip_ms()))
        fs.next_button.clicked.connect(self.next_video)
        fs.mute_button.clicked.connect(self.controls.toggle_mute)
        fs.exit_button.clicked.connect(self.exit_fullscreen)
        fs.position_slider.seek_requested.connect(self.player.set_position)
        self.controls.muted_changed.connect(fs.set_muted)
        fs.volume_slider.valueChanged.connect(self.controls.volume_slider.setValue)
        self.controls.volume_slider.valueChanged.connect(fs.set_volume)

        # Ползунки
        self.controls.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.controls.position_slider.seek_requested.connect(self.player.set_position)
        self.controls.position_slider.valueChanged.connect(
            lambda value: self.controls.update_time_display(value, self.player.duration())
        )

        # Скорость
        self.controls.speed_changed.connect(self.change_speed)
        self.controls.aspect_changed.connect(lambda mode: self.settings.set("aspect_mode", mode))

        # Плейлист
        self.playlist.itemDoubleClicked.connect(self.play_selected_video)
        self.playlist.remove_requested.connect(self.remove_from_queue)
        self.playlist.properties_requested.connect(self.open_properties)
        self.controls.properties_clicked.connect(self.open_properties)

        # Сигналы плеера
        self.player.position_changed.connect(self.update_position)
        self.player.duration_changed.connect(self.update_duration)
        self.player.media_state_changed.connect(self.on_media_state_changed)
        self.player.error_occurred.connect(self.handle_player_error)
        self.player.finished.connect(self._on_video_finished)
        self.thumbnailer.ready.connect(self._on_thumbnail_ready)
        self.ambient.palette_changed.connect(self._on_ambient_palette)
        # Продолжение с места остановки — только когда файл загружен
        self.player.player.mediaStatusChanged.connect(lambda _status: self._apply_pending_position())

        self.settings.changed.connect(self._on_setting_changed)
        self.folder_playlist.added.connect(self._on_folder_video_added)
        self.folder_playlist.removed.connect(self._on_folder_video_removed)

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
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self.open_settings)
        QShortcut(QKeySequence("A"), self).activated.connect(self.cycle_aspect_mode)
        QShortcut(QKeySequence("Ctrl+I"), self).activated.connect(self.open_properties)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.playlist.request_remove_current)

    # --- Настройки ---

    def _apply_settings(self):
        """Применить сохранённые настройки при запуске"""
        if self.settings.get("remember_volume"):
            self.controls.volume_slider.setValue(self.settings.get("volume"))
        self._set_skip_seconds(self.settings.get("skip_seconds"))
        self.ambient.enabled = self.settings.get("ambient_background")
        self._set_aspect_mode(self.settings.get("aspect_mode"))
        self._load_folder_playlist()

    def _on_setting_changed(self, key: str, value):
        if key == "skip_seconds":
            self._set_skip_seconds(value)
        elif key in ("playlist_folder", "watch_folder", "folder_sort"):
            self._load_folder_playlist()
        elif key == "aspect_mode":
            self._set_aspect_mode(value)
        elif key == "theme":
            self.apply_theme(value)
        elif key == "language":
            self.apply_language(value)
        elif key == "ambient_background":
            self.ambient.enabled = value
            self.ambient.reset()
            if not value:
                self.root.reset_colors()

    # --- Папка-плейлист ---

    def _load_folder_playlist(self):
        """(Пере)загрузить видео из папки-плейлиста; добавленные вручную не трогаем"""
        for path in self._folder_items:
            if path != self.current_file_path:
                self.playlist.remove_path(path)
        self._folder_items.clear()
        self.folder_playlist.stop()

        folder = self.settings.get("playlist_folder")
        if not folder or not Path(folder).is_dir():
            return
        files = self.folder_playlist.start(
            folder, self.settings.get("watch_folder"), self.settings.get("folder_sort")
        )
        for path in files:
            self._on_folder_video_added(path)
        if self.current_file_path:
            self.playlist.select_video(self.current_file_path)

    def _on_folder_video_added(self, path: str):
        self._folder_items.add(path)
        self.playlist.add_video(path)

    def _on_folder_video_removed(self, path: str):
        # Играющее сейчас не выдёргиваем: уберём, когда переключатся на другое
        if path != self.current_file_path:
            self._folder_items.discard(path)
            self.playlist.remove_path(path)

    def _drop_deleted_folder_items(self):
        for path in list(self._folder_items):
            if path != self.current_file_path and not Path(path).exists():
                self._folder_items.discard(path)
                self.playlist.remove_path(path)

    def _set_language(self, code: str):
        set_language(code)
        app = QApplication.instance()
        app.removeTranslator(self._qt_translator)
        path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if self._qt_translator.load(f"qtbase_{code}", path):
            app.installTranslator(self._qt_translator)

    def apply_language(self, code: str):
        """Сменить язык на лету: постоянные надписи (bind) и те, что зависят от состояния"""
        self._set_language(code)
        retranslate()
        self.title_bar.update_state()
        self._update_playlist_tooltip(self.drawer.is_open())
        self._set_skip_seconds(self.settings.get("skip_seconds"))
        self.controls.set_aspect_text(self.settings.get("aspect_mode"))
        self.controls.update_track_info(self.current_file_path, self.player.duration())

    def _update_playlist_tooltip(self, is_open: bool):
        self.controls.playlist_button.setToolTip(
            tr("Скрыть плейлист (Ctrl+L)" if is_open else "Показать плейлист (Ctrl+L)"))

    def apply_theme(self, name: str):
        """Сменить тему на лету: палитра, затем стили всех частей окна"""
        set_theme(name)
        self.setStyleSheet(app_style())
        for part in (self.title_bar, self.sidebar, self.controls, self.root):
            part.apply_theme()
        GlassLook.retheme_all()
        self.video_container.set_placeholder_color(T.color("placeholder"))
        for widget in self.findChildren(QWidget):
            widget.update()

    def _set_aspect_mode(self, mode: str):
        if mode not in [value for _, value, _ in ASPECT_MODES]:
            # Формат из старой версии, которого больше нет (например, «Заполнить»)
            self.settings.set("aspect_mode", "auto")
            return
        self.video_container.set_aspect_mode(mode)
        self.controls.set_aspect_text(mode)

    def cycle_aspect_mode(self):
        """Клавиша A: следующий формат по кругу"""
        values = [value for _, value, _ in ASPECT_MODES]
        current = self.settings.get("aspect_mode")
        index = values.index(current) if current in values else 0
        self.settings.set("aspect_mode", values[(index + 1) % len(values)])

    def _set_skip_seconds(self, seconds: int):
        for btn in (self.controls.rewind_button, self.controls.skip_button,
                    self.fs_controls.rewind_button, self.fs_controls.skip_button):
            btn.set_seconds(seconds)

    def _skip_ms(self) -> int:
        return self.settings.get("skip_seconds") * 1000

    def open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        dialog.history_cleared.connect(self.history.clear_history)
        dialog.exec()

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

    # --- Полноэкранный режим ---

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self._idle_timer.stop()
            self.fs_controls.hide_now()
            self._show_cursor()
            set_window_border(self, True)
            self.showNormal()
            restore_native_frame(self)  # Qt при выходе из полного экрана сбрасывает стиль рамки
            self._set_glass_layout(True)
            self.drawer.setVisible(True)
            self.controls.setVisible(True)
        else:
            self.showFullScreen()
            set_window_border(self, False)
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

        hide_seconds = self.settings.get("fullscreen_hide_seconds")
        if hide_seconds and self._idle_clock.elapsed() >= hide_seconds * 1000:
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

    # --- Окно: свой заголовок поверх настоящей рамки Windows ---

    def showEvent(self, event):
        super().showEvent(event)
        if not self._native_frame_ready:
            self._native_frame_ready = True
            restore_native_frame(self)

    def nativeEvent(self, event_type, message):
        if IS_WINDOWS and event_type == b"windows_generic_MSG" and self._native_frame_ready:
            result = handle_native_event(self, self.title_bar, message)
            if result is not None:
                return result
        # Не super(): базовый nativeEvent ничего не делает, а его ответ (False, None)
        # в PyQt6 под Python 3.14 роняет приложение. (False, 0) — то же «не обработано».
        return False, 0

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            self.title_bar.update_state()
            # Контур окна — только у обычного окна, как у системных
            self.root.outline = not (self.isMaximized() or self.isFullScreen())
            self.root.update()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_F11, Qt.Key.Key_F):
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    # --- Видео ---

    def open_file(self):
        # «+» открывает папку-плейлист, а без неё — последнюю использованную
        folder = self.settings.get("playlist_folder")
        if not folder or not Path(folder).is_dir():
            folder = self.last_folder
        file_name, _ = QFileDialog.getOpenFileName(
            self, tr("Добавить видео"), folder,
            tr("Видео (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v)")
        )
        if file_name:
            self.last_folder = str(Path(file_name).parent)
            self.load_video(file_name)

    def load_video(self, file_path: str):
        file_path = str(Path(file_path).resolve())

        self._save_progress()
        if not Path(file_path).is_file():
            QMessageBox.warning(self, tr("Ошибка"), tr("Не удалось загрузить видео:\n{}").format(file_path))
            return

        # Место продолжения и текущий файл — ДО открытия: ffmpeg может сообщить
        # длительность прямо во время setSource, и update_duration должен их видеть
        self._pending_position = self._resume_position(file_path)
        self.current_file_path = file_path
        self.player.load_video(file_path)
        self._drop_deleted_folder_items()

        self.controls.update_track_info(file_path, 0)
        self.controls.cover.set_placeholder()
        self.thumbnailer.request(file_path)
        self.playlist.add_video(file_path)
        self.playlist.select_video(file_path)

        # Тот же файл ещё раз (или длительность уже пришла): сигнала durationChanged
        # не будет — обновляем полосу и время сами
        if self.player.duration() > 0:
            self.update_duration(self.player.duration())

        self.player.play()
        self._set_play_state(True)

    def _on_ambient_palette(self, colors):
        # Последний кадр может прийти уже после остановки — фон тогда не трогаем
        if self.current_file_path:
            self.root.set_colors(colors)

    def _on_thumbnail_ready(self, path: str, image):
        if path == self.current_file_path:  # пока снимали кадр, могли открыть другое видео
            self.controls.cover.set_image(image)

    def _resume_position(self, file_path: str) -> int:
        """С какого места начать видео — по настройке «Продолжать с места остановки»"""
        mode = self.settings.get("resume")
        position = self.history.get_position(file_path)
        if mode == "never" or position < self.RESUME_MIN_MS:
            return 0
        if mode == "ask":
            answer = QMessageBox.question(
                self, "Lucent", tr("Продолжить с {}?\n\n{}").format(format_time(position), Path(file_path).stem)
            )
            if answer != QMessageBox.StandardButton.Yes:
                return 0
        return position

    def _on_video_finished(self):
        self._save_progress()  # досмотренное — в следующий раз с начала
        action = self.settings.get("on_end")
        if action == "repeat":
            self.player.set_position(0)
            self.player.play()
        elif action == "next" and self.playlist.currentRow() < self.playlist.count() - 1:
            self.next_video()
        else:
            self._set_play_state(False)

    def reload_video(self):
        if self.current_file_path:
            pos = self.player.get_position()
            if self.player.load_video(self.current_file_path):
                self.player.set_position(pos)
                self.player.play()

    def open_properties(self, path: str = ""):
        """Окно «Свойства»: заданное видео, иначе играющее, иначе выделенное в очереди"""
        path = path or self.current_file_path or self.playlist.current_video()
        if path and Path(path).is_file():
            PropertiesDialog(path, self).exec()

    def remove_from_queue(self, path: str):
        """Убрать видео из очереди (файл на диске не трогаем)"""
        path = str(Path(path).resolve())
        if path == self.current_file_path:
            self._save_progress()  # место просмотра не теряется
            self.player.stop()
            self.current_file_path = None
            self.ambient.reset()
            self.root.reset_colors()
            self._set_play_state(False)
            self.controls.update_track_info(None)
            self.controls.position_slider.setRange(0, 0)
            self.controls.update_time_display(0, 0)
            self.fs_controls.set_duration(0)
            self.fs_controls.set_position(0)
        self._folder_items.discard(path)
        self.playlist.remove_path(path)

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
        slider = self.controls.position_slider
        slider.sync(position)
        # Время — по ручке: пока её тянут, видно, куда будет перемотка
        self.controls.update_time_display(slider.value(), self.player.duration())
        self.fs_controls.set_position(position)

    def update_duration(self, duration: int):
        self.controls.position_slider.setRange(0, max(duration, 0))
        self.fs_controls.set_duration(duration)
        if self.current_file_path and duration > 0:
            self.controls.update_track_info(self.current_file_path, duration)
            self._apply_pending_position()

    def _apply_pending_position(self):
        """Перейти к месту остановки. Длительность приходит, пока файл ещё
        загружается (LoadingMedia), — тогда setPosition молча игнорируется."""
        status = self.player.player.mediaStatus()
        loaded = status in (QMediaPlayer.MediaStatus.LoadedMedia,
                            QMediaPlayer.MediaStatus.BufferingMedia,
                            QMediaPlayer.MediaStatus.BufferedMedia)
        if self._pending_position > 0 and self.current_file_path and loaded:
            self.player.set_position(self._pending_position)
            self._pending_position = 0

    def on_media_state_changed(self, is_playing: bool):
        self._set_play_state(is_playing)

    def _set_play_state(self, is_playing: bool):
        self.controls.set_play_button_state(is_playing)
        self.fs_controls.set_play_button_state(is_playing)

    def handle_player_error(self, error_message: str):
        QMessageBox.critical(self, tr("Ошибка плеера"), error_message)

    def _save_progress(self):
        """Запомнить место остановки; досмотренное видео — с начала"""
        if not self.current_file_path or self.player.duration() <= 0:
            return
        finished = self.player.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia
        position = 0 if finished else self.player.get_position()
        self.history.save_video(self.current_file_path, position)

    def _autosave_position(self):
        self._save_progress()

    def closeEvent(self, event):
        self.autosave_timer.stop()
        self._idle_timer.stop()
        self.fs_controls.hide_now()
        self._show_cursor()

        self._save_progress()

        # Без звука сохраняем громкость «до выключения», а не ноль
        controls = self.controls
        volume = controls._volume_before_mute if controls._muted else controls.volume_slider.value()
        self.settings.set("volume", volume)

        self.history.close()
        event.accept()
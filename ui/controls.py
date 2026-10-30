import math
from pathlib import Path

from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QSlider,
    QHBoxLayout,
    QVBoxLayout,
    QProgressBar,
    QStyle,
    QStyleOptionSlider,
)
from core.i18n import bind, tr
from PyQt6.QtCore import Qt, QPointF, QRectF, QElapsedTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen

from ui.cover_art import CoverArtWidget
from ui.video_frame import ASPECT_MODES
from ui.glass import GlassPanel, make_glass_menu
from ui.glass_button import GlassLook
from ui.icons import IconButton, Icons, draw_icon
from ui.styles import T


def _round_btn(btn: QPushButton, size: int) -> QPushButton:
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return btn


def make_icon_btn(icon: str, size: int, palette=None) -> QPushButton:
    """Круглая стеклянная кнопка со значком (объём и тень — GlassLook)"""
    btn = _round_btn(IconButton(icon, 16, palette), size)
    btn.setObjectName("icon_btn")
    GlassLook(btn, palette=palette)
    return btn


def make_control_btn(icon: str, size: int, palette=None) -> QPushButton:
    btn = make_icon_btn(icon, size, palette)
    btn.icon_size_px = 18
    btn.setObjectName("control_btn")
    return btn


def make_play_btn(palette=None) -> QPushButton:
    btn = _round_btn(IconButton(Icons.PLAY, 22, palette, color="play_fg"), 48)
    btn.setObjectName("play_btn")
    bind(btn, "setToolTip", "Воспроизвести (Пробел)")
    GlassLook(btn, kind="play", palette=palette)  # объёмная, с мягкой тенью
    return btn


def format_time(ms: int) -> str:
    if ms <= 0:
        return "0:00"
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def control_styles(p=None) -> str:
    """Общие стили кнопок и ползунков для нижней и полноэкранной панелей"""
    p = p or T
    return f"""
        QLabel#time_label {{
            color: {p.text};
            font-size: 13px;
        }}
        /* Объём, блик, тень и подсветку при наведении у всех кнопок рисует GlassLook
           (ui/glass_button.py), поэтому фон в стилях всегда прозрачный */
        QPushButton#icon_btn, QPushButton#control_btn,
        QPushButton#icon_btn:hover, QPushButton#control_btn:hover,
        QPushButton#icon_btn:pressed, QPushButton#control_btn:pressed {{
            background: transparent;
            border: none;
        }}
        QPushButton#play_btn, QPushButton#play_btn:hover, QPushButton#play_btn:pressed {{
            background: transparent;
            border: none;
        }}
        QPushButton#pill_btn, QPushButton#pill_btn:hover, QPushButton#pill_btn:pressed {{
            background: transparent;
            color: {p.text};
            border: none;
            font-size: 12px;
            font-weight: 600;
        }}
        QProgressBar {{
            background-color: transparent;
            border: none;
            max-height: 2px;
        }}
        QProgressBar::chunk {{
            background-color: {p.accent};
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {p.groove};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {p.text};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {p.text};
            width: 14px;
            height: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }}
        QSlider::handle:horizontal:hover {{
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
    """


class SeekSlider(QSlider):
    """
    Полоса перемотки видео.
    Клик в любое место сразу ставит туда ручку (её можно тут же тянуть дальше),
    а перемотка выполняется один раз — когда кнопку мыши отпустили.
    Пока ручку держат, позиция от плеера её не трогает.
    """

    seek_requested = pyqtSignal(int)
    # Сколько ждать, пока плеер «догонит» новую позицию после перемотки:
    # до этого старые значения позиции не возвращают ручку назад
    SETTLE_MS = 800
    SETTLE_TOLERANCE_MS = 1500

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # стрелки — горячие клавиши окна
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._seek_target = None
        self._seek_clock = QElapsedTimer()

    def _value_at(self, x: float) -> int:
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        handle = style.subControlRect(
            QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)
        span = max(groove.width() - handle.width(), 1)
        pos = round(x - groove.x() - handle.width() / 2)
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), max(0, min(pos, span)), span)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.maximum() <= self.minimum():
            return super().mousePressEvent(event)
        self.setSliderDown(True)
        self.setValue(self._value_at(event.position().x()))
        event.accept()

    def mouseMoveEvent(self, event):
        if self.isSliderDown():
            self.setValue(self._value_at(event.position().x()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            self._seek_target = self.value()
            self._seek_clock.start()
            self.seek_requested.emit(self.value())
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        event.ignore()  # колесо по полосе не должно сдвигать её на миллисекунды

    def sync(self, position_ms: int):
        """Показать позицию, пришедшую от плеера"""
        if self.isSliderDown():
            return
        if self._seek_target is not None:
            caught_up = abs(position_ms - self._seek_target) < self.SETTLE_TOLERANCE_MS
            if not caught_up and self._seek_clock.elapsed() < self.SETTLE_MS:
                return
            self._seek_target = None
        self.blockSignals(True)
        self.setValue(position_ms)
        self.blockSignals(False)


class SkipButton(QPushButton):
    """Кнопка перемотки в стиле iOS: круговая стрелка с числом секунд внутри"""

    def __init__(self, seconds: int, forward: bool, palette=None):
        super().__init__()
        self._palette = palette  # None — текущая тема
        self.seconds = seconds
        self.forward = forward
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("control_btn")
        GlassLook(self, palette=palette)
        self.set_seconds(seconds)

    def set_seconds(self, seconds: int):
        self.seconds = seconds
        text = "Вперёд на {} сек" if self.forward else "Назад на {} сек"
        self.setToolTip(tr(text).format(seconds))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)  # фон и подсветка из стилей
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        color = (self._palette or T).color("text")
        p.setPen(color)
        rect = QRectF(self.rect())

        # Стрелка: для «назад» отражаем по горизонтали
        p.save()
        if not self.forward:
            p.translate(rect.width(), 0)
            p.scale(-1, 1)
        draw_icon(p, Icons.CIRCLE_ARROW, QRectF(6, 6, 28, 28), color, 1.5)
        p.restore()

        number_font = QFont(self.font())
        number_font.setPixelSize(9)
        number_font.setWeight(QFont.Weight.Bold)
        p.setFont(number_font)
        p.drawText(rect.adjusted(0, 1, 0, 1), Qt.AlignmentFlag.AlignCenter, str(self.seconds))


class PlaylistToggleButton(QPushButton):
    """
    Кнопка «☰» плейлиста. Пока панель выезжает или прячется, полоски делают
    пол-оборота (при открытии — по часовой, при закрытии — обратно), на середине
    сжимаются к центру «вихрем» и снова раскрываются. Открытый плейлист
    отмечен мягкой синей подсветкой за иконкой.
    progress: 0 — плейлист скрыт, 1 — открыт.
    """

    SIZE = 36

    def __init__(self):
        super().__init__()
        self._progress = 1.0
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("icon_btn")
        GlassLook(self)

    def set_progress(self, value: float):
        self._progress = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        t = self._progress
        squeeze = math.sin(math.pi * t)  # 0 в начале и в конце, 1 — на середине
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Подсветка «открыто»: синий кружок проявляется вместе с панелью
        if t > 0:
            glow = T.color("accent")
            glow.setAlphaF(0.45 * t)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))

        pen = QPen(T.color("text"), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(180 * t)
        p.scale(1 - 0.15 * squeeze, 1 - 0.15 * squeeze)

        gap = 5.5 * (1 - 0.55 * squeeze)    # полоски сходятся к центру
        outer = 8.0 * (1 - 0.25 * squeeze)  # крайние чуть короче
        middle = 8.0 * (1 - 0.9 * squeeze)  # средняя почти в точку
        for y, half in ((-gap, outer), (0.0, middle), (gap, outer)):
            p.drawLine(QPointF(-half, y), QPointF(half, y))


class ControlsWidget(GlassPanel):
    """Нижняя плавающая стеклянная панель плеера"""

    speed_changed = pyqtSignal(str)
    aspect_changed = pyqtSignal(str)
    properties_clicked = pyqtSignal()  # клик по обложке или названию
    muted_changed = pyqtSignal(bool)
    SKIP_SECONDS = 10
    SPEEDS = ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]

    def __init__(self):
        super().__init__()
        self._current_speed_index = 2
        self._muted = False
        self._volume_before_mute = 50

        self.setup_ui()
        self.setup_speed_menu()
        # Обложка и название открывают «Свойства» видео
        for widget in (self.cover, self.title_label, self.subtitle_label):
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
            bind(widget, "setToolTip", "Свойства (Ctrl+I)")
            widget.installEventFilter(self)
        self.setup_aspect_menu()
        self.apply_theme()
        self.setFixedHeight(112)

    def setup_ui(self):
        """Создаёт все элементы управления"""

        # ----- 1. ПРОГРЕСС СВЕРХУ -----
        self.position_slider = SeekSlider()
        self.position_slider.setRange(0, 0)
        self.position_slider.setFixedHeight(16)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(2)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setVisible(False)

        # ----- 2. ЛЕВАЯ ЧАСТЬ: обложка + информация о видео -----
        self.playlist_button = PlaylistToggleButton()
        bind(self.playlist_button, "setToolTip", "Скрыть плейлист (Ctrl+L)")

        self.cover = CoverArtWidget(56)

        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title_label.setFont(title_font)

        self.subtitle_label = QLabel()

        # Вертикальное расположение: название + подзаголовок
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.subtitle_label)

        # Горизонтальное расположение: обложка + информация
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)
        left_layout.addWidget(self.playlist_button)
        left_layout.addWidget(self.cover)
        left_layout.addLayout(info_layout)
        left_layout.addStretch()

        # ----- 3. ЦЕНТР: кнопки управления -----
        self.prev_button = make_control_btn(Icons.PREVIOUS, 40)
        bind(self.prev_button, "setToolTip", "Предыдущее (P)")
        self.play_button = make_play_btn()
        self.next_button = make_control_btn(Icons.NEXT, 40)
        bind(self.next_button, "setToolTip", "Следующее (N)")
        self.rewind_button = SkipButton(self.SKIP_SECONDS, forward=False)
        self.skip_button = SkipButton(self.SKIP_SECONDS, forward=True)

        center_layout = QHBoxLayout()
        center_layout.setSpacing(12)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.prev_button)
        center_layout.addWidget(self.rewind_button)
        center_layout.addWidget(self.play_button)
        center_layout.addWidget(self.skip_button)
        center_layout.addWidget(self.next_button)

        # ----- 4. ПРАВАЯ ЧАСТЬ: время, скорость, громкость -----
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setMinimumWidth(120)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.speed_button = QPushButton("1.0x")
        self.speed_button.setObjectName("pill_btn")
        self.speed_button.setFixedSize(56, 32)
        self.speed_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speed_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bind(self.speed_button, "setToolTip", "Скорость ([ / ])")
        GlassLook(self.speed_button)

        self.aspect_button = QPushButton(tr("Авто"))
        self.aspect_button.setObjectName("pill_btn")
        self.aspect_button.setMinimumWidth(56)
        self.aspect_button.setFixedHeight(32)
        self.aspect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aspect_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bind(self.aspect_button, "setToolTip", "Формат картинки (A)")
        self.aspect_button.setStyleSheet("padding: 0 14px;")
        GlassLook(self.aspect_button)

        self.mute_button = make_icon_btn(Icons.VOLUME, 36)
        bind(self.mute_button, "setToolTip", "Без звука (M)")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        bind(self.volume_slider, "setToolTip", "Громкость (↑/↓)")

        self.mini_button = make_icon_btn(Icons.MINI_PLAYER, 36)
        bind(self.mini_button, "setToolTip", "Мини-плеер (Ctrl+M)")

        self.fullscreen_button = make_icon_btn(Icons.FULLSCREEN, 36)
        bind(self.fullscreen_button, "setToolTip", "Полный экран (F)")

        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)
        right_layout.addWidget(self.time_label)
        right_layout.addWidget(self.aspect_button)
        right_layout.addWidget(self.speed_button)
        right_layout.addWidget(self.mute_button)
        right_layout.addWidget(self.volume_slider)
        right_layout.addWidget(self.mini_button)
        right_layout.addWidget(self.fullscreen_button)

        # ----- 5. НИЖНИЙ РЯД -----
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(18, 2, 18, 14)
        bottom_row.addLayout(left_layout, stretch=3)
        bottom_row.addLayout(center_layout, stretch=2)
        bottom_row.addLayout(right_layout, stretch=3)

        # ----- 6. ГЛАВНЫЙ ВЕРТИКАЛЬНЫЙ ЛЕЙАУТ -----
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 12, 20, 0)
        main_layout.setSpacing(4)
        main_layout.addWidget(self.loading_bar)
        main_layout.addWidget(self.position_slider)
        main_layout.addLayout(bottom_row)

        self.setLayout(main_layout)

    def setup_speed_menu(self):
        self.speed_menu = make_glass_menu(self)
        for speed in self.SPEEDS:
            action = self.speed_menu.addAction(speed)
            action.setData(speed)
            action.triggered.connect(self._on_speed_selected)
        self.speed_button.clicked.connect(self._show_speed_menu)
        self.mute_button.clicked.connect(self.toggle_mute)

    def eventFilter(self, obj, event):
        if (event.type() == event.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and obj in (self.cover, self.title_label, self.subtitle_label)):
            self.properties_clicked.emit()
            return True
        return super().eventFilter(obj, event)

    def apply_theme(self):
        """Перестроить стили под текущую тему"""
        self.setStyleSheet(control_styles())
        self.title_label.setStyleSheet(f"color: {T.text};")
        self.subtitle_label.setStyleSheet(f"color: {T.text_sub}; font-size: 11px;")
        self.cover.apply_theme()
        self.update()

    def setup_aspect_menu(self):
        self.aspect_menu = make_glass_menu(self)
        for label, value, _ in ASPECT_MODES:
            action = self.aspect_menu.addAction("")
            bind(action, "setText", label)
            action.triggered.connect(lambda _=False, v=value: self.aspect_changed.emit(v))
        self.aspect_button.clicked.connect(self._show_aspect_menu)

    def _show_aspect_menu(self):
        pos = self.aspect_button.mapToGlobal(self.aspect_button.rect().bottomLeft())
        self.aspect_menu.exec(pos)

    def set_aspect_text(self, mode: str):
        label = tr(next((lbl for lbl, value, _ in ASPECT_MODES if value == mode), "Авто"))
        self.aspect_button.setText(label)

    def _show_speed_menu(self):
        pos = self.speed_button.mapToGlobal(self.speed_button.rect().bottomLeft())
        self.speed_menu.exec(pos)

    def _on_speed_selected(self):
        action = self.sender()
        if action:
            speed_text = action.data()
            if speed_text:
                self.speed_button.setText(speed_text)
                self.speed_changed.emit(speed_text)
                if speed_text in self.SPEEDS:
                    self._current_speed_index = self.SPEEDS.index(speed_text)

    def set_speed_text(self, text: str):
        self.speed_button.setText(text)
        if text in self.SPEEDS:
            self._current_speed_index = self.SPEEDS.index(text)

    def cycle_speed(self, direction: int):
        self._current_speed_index = max(
            0, min(len(self.SPEEDS) - 1, self._current_speed_index + direction)
        )
        speed = self.SPEEDS[self._current_speed_index]
        self.set_speed_text(speed)
        self.speed_changed.emit(speed)

    def reset_speed(self):
        self.set_speed_text("1.0x")
        self.speed_changed.emit("1.0x")

    def toggle_mute(self):
        if self._muted:
            self.volume_slider.setValue(self._volume_before_mute)
            self.set_muted(False)
        else:
            self._volume_before_mute = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.set_muted(True)

    def set_muted(self, muted: bool):
        self._muted = muted
        self.mute_button.set_icon(Icons.MUTE if muted else Icons.VOLUME)
        self.muted_changed.emit(muted)

    def set_play_button_state(self, is_playing: bool):
        self.play_button.set_icon(Icons.PAUSE if is_playing else Icons.PLAY)

    def update_track_info(self, file_path: str | None, duration_ms: int = 0):
        if not file_path:
            self.title_label.setText(tr("Ничего не воспроизводится"))
            self.subtitle_label.setText(tr("Откройте видео, чтобы начать"))
            self.cover.set_placeholder()
            return

        path = Path(file_path)
        name = path.stem
        if len(name) > 40:
            name = name[:37] + "..."
        self.title_label.setText(name)

        size_bytes = path.stat().st_size
        if size_bytes >= 1024 ** 3:
            size_text = f"{size_bytes / (1024 ** 3):.2f} GB"
        elif size_bytes >= 1024 ** 2:
            size_text = f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            size_text = f"{size_bytes / 1024:.0f} KB"

        duration_text = format_time(duration_ms) if duration_ms > 0 else "--:--"
        self.subtitle_label.setText(f"{duration_text}  ·  {size_text}")

    def update_time_display(self, current_ms: int, total_ms: int):
        self.time_label.setText(
            f"{format_time(current_ms)} / {format_time(total_ms)}"
        )

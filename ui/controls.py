from PyQt6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QSlider,
    QHBoxLayout,
    QVBoxLayout,
    QProgressBar,
    QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path

from ui.cover_art import CoverArtWidget
from ui.styles import (
    SPOTIFY_ELEVATED,
    SPOTIFY_BORDER,
    SPOTIFY_TEXT,
    SPOTIFY_TEXT_SUB,
    SPOTIFY_GREEN,
    SPOTIFY_GREEN_HOVER
)


class ControlsWidget(QWidget):
    """Нижняя панель плеера в стиле Spotify"""

    speed_changed = pyqtSignal(str)
    SPEEDS = ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]

    def __init__(self):
        super().__init__()
        self.setObjectName("player_bar")
        self._current_speed_index = 2
        self._muted = False
        self._volume_before_mute = 50

        self.setup_ui()
        self.setup_speed_menu()
        self.setStyleSheet(self._get_styles())
        self.setFixedHeight(100)

        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_controls)
        self.is_controls_visible = True

    def setup_ui(self):
        """Создаёт все элементы управления"""

        # ----- 1. ПРОГРЕСС СВЕРХУ -----
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 100)
        self.position_slider.setFixedHeight(12)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(2)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setVisible(False)

        # ----- 2. ЛЕВАЯ ЧАСТЬ: обложка + информация о видео -----
        self.cover = CoverArtWidget(56)

        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {SPOTIFY_TEXT};")

        self.subtitle_label = QLabel()
        self.subtitle_label.setStyleSheet(f"color: {SPOTIFY_TEXT_SUB}; font-size: 11px;")

        # Вертикальное расположение: название + подзаголовок
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.subtitle_label)

        # Горизонтальное расположение: обложка + информация
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)
        left_layout.addWidget(self.cover)
        left_layout.addLayout(info_layout)
        left_layout.addStretch()

        # ----- 3. ЦЕНТР: кнопки управления -----
        self.prev_button = self._make_control_btn("⏮", 32)
        self.play_button = self._make_play_btn()
        self.next_button = self._make_control_btn("⏭", 32)

        center_layout = QHBoxLayout()
        center_layout.setSpacing(16)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.prev_button)
        center_layout.addWidget(self.play_button)
        center_layout.addWidget(self.next_button)

        # ----- 4. ПРАВАЯ ЧАСТЬ: время, скорость, громкость -----
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(f"color: {SPOTIFY_TEXT_SUB}; font-size: 11px;")
        self.time_label.setMinimumWidth(90)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.speed_button = QPushButton("1.0x")
        self.speed_button.setFixedSize(48, 28)
        self.speed_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speed_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_button.setToolTip("Скорость ([ / ])")

        self.mute_button = QPushButton("🔊")
        self.mute_button.setFixedSize(32, 32)
        self.mute_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.mute_button.setToolTip("Без звука (M)")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setToolTip("Громкость (↑/↓)")

        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)
        right_layout.addWidget(self.time_label)
        right_layout.addWidget(self.speed_button)
        right_layout.addWidget(self.mute_button)
        right_layout.addWidget(self.volume_slider)

        # ----- 5. НИЖНИЙ РЯД -----
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(16, 0, 16, 12)
        bottom_row.addLayout(left_layout, stretch=3)
        bottom_row.addLayout(center_layout, stretch=2)
        bottom_row.addLayout(right_layout, stretch=3)

        # ----- 6. ГЛАВНЫЙ ВЕРТИКАЛЬНЫЙ ЛЕЙАУТ -----
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.loading_bar)
        main_layout.addWidget(self.position_slider)
        main_layout.addLayout(bottom_row)

        self.setLayout(main_layout)

    def _make_control_btn(self, text: str, size: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setObjectName("control_btn")
        return btn

    def _make_play_btn(self) -> QPushButton:
        btn = QPushButton("▶")
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setObjectName("play_btn")
        btn.setToolTip("Воспроизвести (Пробел)")
        return btn

    def setup_speed_menu(self):
        self.speed_menu = QMenu(self)
        for speed in self.SPEEDS:
            action = self.speed_menu.addAction(speed)
            action.setData(speed)
            action.triggered.connect(self._on_speed_selected)
        self.speed_button.clicked.connect(self._show_speed_menu)
        self.mute_button.clicked.connect(self.toggle_mute)

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
            self._muted = False
            self.mute_button.setText("🔊")
        else:
            self._volume_before_mute = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self._muted = True
            self.mute_button.setText("🔇")

    def set_play_button_state(self, is_playing: bool):
        self.play_button.setText("⏸" if is_playing else "▶")

    def update_track_info(self, file_path: str | None, duration_ms: int = 0):
        if not file_path:
            self.title_label.setText("Ничего не воспроизводится")
            self.subtitle_label.setText("Откройте видео, чтобы начать")
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

        duration_text = self._format_time(duration_ms) if duration_ms > 0 else "--:--"
        self.subtitle_label.setText(f"{duration_text}  ·  {size_text}")

    def update_time_display(self, current_ms: int, total_ms: int):
        self.time_label.setText(
            f"{self._format_time(current_ms)} / {self._format_time(total_ms)}"
        )

    def _format_time(self, ms: int) -> str:
        if ms <= 0:
            return "0:00"
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _get_styles(self):
        return f"""
            QWidget#player_bar {{
                background-color: {SPOTIFY_ELEVATED};
                border-top: 1px solid {SPOTIFY_BORDER};
            }}
            QPushButton#control_btn {{
                background-color: transparent;
                color: {SPOTIFY_TEXT_SUB};
                border: none;
                border-radius: 16px;
                font-size: 16px;
            }}
            QPushButton#control_btn:hover {{
                color: {SPOTIFY_TEXT};
            }}
            QPushButton#play_btn {{
                background-color: {SPOTIFY_TEXT};
                color: black;
                border: none;
                border-radius: 18px;
                font-size: 14px;
            }}
            QPushButton#play_btn:hover {{
                background-color: #f0f0f0;
            }}
            QPushButton {{
                background-color: transparent;
                color: {SPOTIFY_TEXT_SUB};
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {SPOTIFY_TEXT};
                background-color: rgba(255, 255, 255, 0.08);
            }}
            QProgressBar {{
                background-color: transparent;
                border: none;
                max-height: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {SPOTIFY_GREEN};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {SPOTIFY_TEXT};
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {SPOTIFY_GREEN_HOVER};
            }}
            QSlider::sub-page:horizontal {{
                background: {SPOTIFY_TEXT};
                border-radius: 2px;
            }}
        """

    # ----- АВТОСКРЫТИЕ В ПОЛНОЭКРАННОМ РЕЖИМЕ -----

    def show_controls(self):
        self.setVisible(True)
        self.is_controls_visible = True

    def hide_controls(self):
        if not self.underMouse():
            self.setVisible(False)
            self.is_controls_visible = False

    def start_hide_timer(self):
        self.auto_hide_timer.start(2000)

    def reset_hide_timer(self):
        if not self.isVisible():
            self.show_controls()
        self.auto_hide_timer.start(2000)

    def stop_hide_timer(self):
        self.auto_hide_timer.stop()

    def set_fullscreen_mode(self, is_fullscreen: bool):
        if is_fullscreen:
            self.show_controls()
            self.start_hide_timer()
        else:
            self.stop_hide_timer()
            self.show_controls()
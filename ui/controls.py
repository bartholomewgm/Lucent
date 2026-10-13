from PyQt6.QtWidgets import (
    QPushButton,
    QLabel,
    QSlider,
    QHBoxLayout,
    QVBoxLayout,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path

from ui.cover_art import CoverArtWidget
from ui.glass import GlassPanel, make_glass_menu
from ui.styles import (
    GLASS_FILL,
    GLASS_FILL_HOVER,
    GLASS_FILL_PRESSED,
    GLASS_TEXT,
    GLASS_TEXT_SUB,
    GLASS_ACCENT,
    ICON_FONT,
    Icons
)


class ControlsWidget(GlassPanel):
    """Нижняя плавающая стеклянная панель плеера"""

    speed_changed = pyqtSignal(str)
    SPEEDS = ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"]

    def __init__(self):
        super().__init__()
        self._current_speed_index = 2
        self._muted = False
        self._volume_before_mute = 50

        self.setup_ui()
        self.setup_speed_menu()
        self.setStyleSheet(self._get_styles())
        self.setFixedHeight(112)

        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_controls)
        self.is_controls_visible = True

    def setup_ui(self):
        """Создаёт все элементы управления"""

        # ----- 1. ПРОГРЕСС СВЕРХУ -----
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 100)
        self.position_slider.setFixedHeight(16)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)
        self.loading_bar.setFixedHeight(2)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setVisible(False)

        # ----- 2. ЛЕВАЯ ЧАСТЬ: обложка + информация о видео -----
        self.cover = CoverArtWidget(56)

        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {GLASS_TEXT};")

        self.subtitle_label = QLabel()
        self.subtitle_label.setStyleSheet(f"color: {GLASS_TEXT_SUB}; font-size: 11px;")

        # Вертикальное расположение: название + подзаголовок
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
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
        self.prev_button = self._make_control_btn(Icons.PREVIOUS, 40)
        self.prev_button.setToolTip("Предыдущее (P)")
        self.play_button = self._make_play_btn()
        self.next_button = self._make_control_btn(Icons.NEXT, 40)
        self.next_button.setToolTip("Следующее (N)")

        center_layout = QHBoxLayout()
        center_layout.setSpacing(14)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.prev_button)
        center_layout.addWidget(self.play_button)
        center_layout.addWidget(self.next_button)

        # ----- 4. ПРАВАЯ ЧАСТЬ: время, скорость, громкость -----
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setObjectName("time_label")
        self.time_label.setMinimumWidth(90)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.speed_button = QPushButton("1.0x")
        self.speed_button.setObjectName("pill_btn")
        self.speed_button.setFixedSize(52, 30)
        self.speed_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.speed_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.speed_button.setToolTip("Скорость ([ / ])")

        self.mute_button = self._make_icon_btn(Icons.VOLUME, 34)
        self.mute_button.setToolTip("Без звука (M)")

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setToolTip("Громкость (↑/↓)")

        self.fullscreen_button = self._make_icon_btn(Icons.FULLSCREEN, 34)
        self.fullscreen_button.setToolTip("Полный экран (F)")

        right_layout = QHBoxLayout()
        right_layout.setSpacing(8)
        right_layout.addWidget(self.time_label)
        right_layout.addWidget(self.speed_button)
        right_layout.addWidget(self.mute_button)
        right_layout.addWidget(self.volume_slider)
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

    def _make_icon_btn(self, glyph: str, size: int) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(size, size)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setObjectName("icon_btn")
        return btn

    def _make_control_btn(self, glyph: str, size: int) -> QPushButton:
        btn = self._make_icon_btn(glyph, size)
        btn.setObjectName("control_btn")
        return btn

    def _make_play_btn(self) -> QPushButton:
        btn = self._make_icon_btn(Icons.PLAY, 48)
        btn.setObjectName("play_btn")
        btn.setToolTip("Воспроизвести (Пробел)")
        return btn

    def setup_speed_menu(self):
        self.speed_menu = make_glass_menu(self)
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
            self.set_muted(False)
        else:
            self._volume_before_mute = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.set_muted(True)

    def set_muted(self, muted: bool):
        self._muted = muted
        self.mute_button.setText(Icons.MUTE if muted else Icons.VOLUME)

    def set_play_button_state(self, is_playing: bool):
        self.play_button.setText(Icons.PAUSE if is_playing else Icons.PLAY)

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
            QLabel#time_label {{
                color: {GLASS_TEXT_SUB};
                font-size: 11px;
            }}
            QPushButton#icon_btn, QPushButton#control_btn {{
                background-color: transparent;
                color: {GLASS_TEXT_SUB};
                border: none;
                border-radius: 17px;
                font-family: {ICON_FONT};
                font-size: 15px;
            }}
            QPushButton#control_btn {{
                color: {GLASS_TEXT};
                border-radius: 20px;
                font-size: 17px;
            }}
            QPushButton#icon_btn:hover, QPushButton#control_btn:hover {{
                color: {GLASS_TEXT};
                background-color: {GLASS_FILL_HOVER};
            }}
            QPushButton#icon_btn:pressed, QPushButton#control_btn:pressed {{
                background-color: {GLASS_FILL_PRESSED};
            }}
            QPushButton#play_btn {{
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #e4e6ee);
                color: #0a0c14;
                border: 1px solid rgba(255, 255, 255, 0.9);
                border-radius: 24px;
                font-family: {ICON_FONT};
                font-size: 18px;
            }}
            QPushButton#play_btn:hover {{
                background-color: #ffffff;
            }}
            QPushButton#play_btn:pressed {{
                background-color: #d6d8e0;
            }}
            QPushButton#pill_btn {{
                background-color: {GLASS_FILL};
                color: {GLASS_TEXT};
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 15px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#pill_btn:hover {{
                background-color: {GLASS_FILL_HOVER};
            }}
            QProgressBar {{
                background-color: transparent;
                border: none;
                max-height: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {GLASS_ACCENT};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {GLASS_TEXT};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {GLASS_TEXT};
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
        self.fullscreen_button.setText(
            Icons.EXIT_FULLSCREEN if is_fullscreen else Icons.FULLSCREEN
        )
        self.fullscreen_button.setToolTip(
            "Выйти из полного экрана (Esc)" if is_fullscreen else "Полный экран (F)"
        )
        if is_fullscreen:
            self.show_controls()
            self.start_hide_timer()
        else:
            self.stop_hide_timer()
            self.show_controls()
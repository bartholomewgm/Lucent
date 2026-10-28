"""
Стеклянная панель управления поверх видео в полноэкранном режиме.
Отдельное прозрачное окно: обычный виджет не нарисуется поверх видео.
"""

from PyQt6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    Qt,
)
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget
from core.i18n import bind

from ui.controls import (
    SeekSlider,
    SkipButton,
    control_styles,
    format_time,
    make_control_btn,
    make_icon_btn,
    make_play_btn,
)
from ui.glass import GlassPanel
from ui.styles import OVERLAY, Icons


class FullscreenControls(GlassPanel):
    """Плавающая стеклянная панель: время, прогресс и кнопки управления"""

    MAX_WIDTH = 720
    SIDE_WIDTH = 150  # одинаковая ширина краёв, чтобы кнопки стояли ровно по центру
    BOTTOM_MARGIN = 48
    SLIDE_OFFSET = 36  # на сколько пикселей ниже панель стартует при появлении
    SHOW_MS = 280
    HIDE_MS = 220

    def __init__(self, owner, skip_seconds: int):
        # Поверх видео панель всегда тёмная, в любой теме
        super().__init__(owner, radius=26, tint_alpha=150, palette=OVERLAY)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(132)

        self._shown = False
        self._setup_ui(skip_seconds)
        # Над видео иконки и время ярче, чем на нижней панели
        self.setStyleSheet(control_styles(OVERLAY) + f"""
            QPushButton#icon_btn, QPushButton#icon_btn:hover, QPushButton#icon_btn:pressed {{ font-size: 16px; }}
            QLabel#time_label {{ color: {OVERLAY.text}; font-size: 14px; }}
        """)
        self._setup_animation()

    def _setup_ui(self, skip_seconds: int):
        # ----- Время над прогрессом, по краям -----
        self.current_label = QLabel("0:00")
        self.total_label = QLabel("0:00")
        for label in (self.current_label, self.total_label):
            label.setObjectName("time_label")

        time_row = QHBoxLayout()
        time_row.setContentsMargins(4, 0, 4, 0)
        time_row.addWidget(self.current_label)
        time_row.addStretch()
        time_row.addWidget(self.total_label)

        self.position_slider = SeekSlider()
        self.position_slider.setRange(0, 0)
        self.position_slider.valueChanged.connect(
            lambda value: self.current_label.setText(format_time(value))
        )
        self.position_slider.setFixedHeight(16)

        # ----- Кнопки: звук и громкость | навигация | выход из полного экрана -----
        self.mute_button = make_icon_btn(Icons.VOLUME, 38, OVERLAY)
        bind(self.mute_button, "setToolTip", "Без звука (M)")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        bind(self.volume_slider, "setToolTip", "Громкость (↑/↓)")

        left = QWidget()
        left.setFixedWidth(self.SIDE_WIDTH)
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.mute_button)
        left_layout.addWidget(self.volume_slider)

        self.prev_button = make_control_btn(Icons.PREVIOUS, 40, OVERLAY)
        bind(self.prev_button, "setToolTip", "Предыдущее (P)")
        self.rewind_button = SkipButton(skip_seconds, forward=False, palette=OVERLAY)
        self.play_button = make_play_btn(OVERLAY)
        self.skip_button = SkipButton(skip_seconds, forward=True, palette=OVERLAY)
        self.next_button = make_control_btn(Icons.NEXT, 40, OVERLAY)
        bind(self.next_button, "setToolTip", "Следующее (N)")

        self.exit_button = make_icon_btn(Icons.EXIT_FULLSCREEN, 38, OVERLAY)
        bind(self.exit_button, "setToolTip", "Выйти из полного экрана (Esc)")

        right = QWidget()
        right.setFixedWidth(self.SIDE_WIDTH)
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch()
        right_layout.addWidget(self.exit_button)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(14)
        buttons_row.addWidget(left)
        buttons_row.addStretch()
        for btn in (self.prev_button, self.rewind_button, self.play_button,
                    self.skip_button, self.next_button):
            buttons_row.addWidget(btn)
        buttons_row.addStretch()
        buttons_row.addWidget(right)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(2)
        layout.addLayout(time_row)
        layout.addWidget(self.position_slider)
        layout.addSpacing(6)
        layout.addLayout(buttons_row)
        self.setLayout(layout)

    # ----- Состояние -----

    def set_play_button_state(self, is_playing: bool):
        self.play_button.setText(Icons.PAUSE if is_playing else Icons.PLAY)

    def set_muted(self, muted: bool):
        self.mute_button.setText(Icons.MUTE if muted else Icons.VOLUME)

    def set_volume(self, value: int):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(value)
        self.volume_slider.blockSignals(False)

    def set_duration(self, duration_ms: int):
        self.position_slider.setRange(0, max(duration_ms, 0))
        self.total_label.setText(format_time(duration_ms))

    def set_position(self, position_ms: int):
        self.position_slider.sync(position_ms)
        # Время — по ручке: пока её тянут, видно, куда будет перемотка
        self.current_label.setText(format_time(self.position_slider.value()))

    # ----- Появление и скрытие -----

    def is_shown(self) -> bool:
        return self._shown

    def _setup_animation(self):
        self._pos_anim = QPropertyAnimation(self, b"pos", self)
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim = QParallelAnimationGroup(self)
        self._anim.addAnimation(self._pos_anim)
        self._anim.addAnimation(self._opacity_anim)
        self._anim.finished.connect(self._on_anim_finished)

    def _target_rect(self) -> QRect:
        """Место панели: по центру снизу экрана, на котором окно плеера"""
        screen = self.parentWidget().screen().geometry()
        width = min(self.MAX_WIDTH, screen.width() - 80)
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + screen.height() - self.height() - self.BOTTOM_MARGIN
        return QRect(x, y, width, self.height())

    def _animate(self, end_pos: QPoint, end_opacity: float, duration: int, curve):
        self._anim.stop()
        for anim, start, end in (
            (self._pos_anim, self.pos(), end_pos),
            (self._opacity_anim, self.windowOpacity(), end_opacity),
        ):
            anim.setDuration(duration)
            anim.setEasingCurve(curve)
            anim.setStartValue(start)
            anim.setEndValue(end)
        self._anim.start()

    def show_animated(self):
        """Плавно поднимается снизу и проявляется"""
        if self._shown:
            return
        self._shown = True
        target = self._target_rect()
        if not self.isVisible():
            self.setFixedWidth(target.width())
            self.move(target.topLeft() + QPoint(0, self.SLIDE_OFFSET))
            self.setWindowOpacity(0.0)
            self.show()
        self._animate(target.topLeft(), 1.0, self.SHOW_MS, QEasingCurve.Type.OutCubic)

    def hide_animated(self):
        """Плавно опускается и растворяется"""
        if not self._shown:
            return
        self._shown = False
        end = self._target_rect().topLeft() + QPoint(0, self.SLIDE_OFFSET)
        self._animate(end, 0.0, self.HIDE_MS, QEasingCurve.Type.InCubic)

    def hide_now(self):
        self._anim.stop()
        self._shown = False
        self.hide()

    def _on_anim_finished(self):
        if not self._shown:
            self.hide()

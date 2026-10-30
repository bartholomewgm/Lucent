"""
Мини-плеер: маленькое окно поверх всех окон. Его можно двигать за любое место
и тянуть за края (пропорции видео сохраняются), вокруг него на рабочем столе
светятся цвета кадра.

Окна два. Само видео — обычное непрозрачное окно с настоящей рамкой Windows.
Свечение — отдельное прозрачное окно под ним, которое не ловит мышь: так
полупрозрачность не касается вывода видео, а перерисовка нужна только при смене цвета.
"""

import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication, QKeySequence, QPainter, QShortcut
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from core.i18n import bind
from ui.controls import SeekSlider, SkipButton, control_styles, make_icon_btn, make_play_btn
from ui.glass import GlassPanel, paint_halo
from ui.icons import Icons
from ui.styles import OVERLAY
from ui.video_frame import VideoFrame
from ui.window_frame import (
    GWL_STYLE, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT, HTCAPTION, HTCLIENT, HTLEFT, HTRIGHT,
    HTTOP, HTTOPLEFT, HTTOPRIGHT, WM_NCCALCSIZE, WM_NCHITTEST, WS_MAXIMIZEBOX, WS_MINIMIZEBOX,
    restore_native_frame,
)

WM_SIZING = 0x0214
WM_NCLBUTTONDBLCLK = 0x00A3
# Какой край тянут (wParam у WM_SIZING)
WMSZ_LEFT, WMSZ_RIGHT, WMSZ_TOP, WMSZ_TOPLEFT, WMSZ_TOPRIGHT = 1, 2, 3, 4, 5
WMSZ_BOTTOM, WMSZ_BOTTOMLEFT, WMSZ_BOTTOMRIGHT = 6, 7, 8


class MiniGlow(QWidget):
    """Цвета видео вокруг мини-плеера, прямо на рабочем столе"""

    MARGIN = 26
    STRENGTH = 0.42
    CORNER = 8  # как у скруглённых углов окна в Windows 11

    def __init__(self, background):
        super().__init__(None, Qt.WindowType.Tool
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._background = background
        background.colors_changed.connect(self.update)

    def follow(self, window_rect: QRect):
        m = self.MARGIN
        self.setGeometry(window_rect.adjusted(-m, -m, m, m))

    def paintEvent(self, event):
        colors = self._background.video_colors()
        if colors is None:
            return
        m = self.MARGIN
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        paint_halo(p, QRectF(self.rect()).adjusted(m, m, -m, -m), colors, self.STRENGTH, m - 4, self.CORNER)


class MiniControls(GlassPanel):
    """Панель управления: появляется, когда курсор над мини-плеером"""

    HEIGHT = 84

    def __init__(self, parent, skip_seconds: int):
        super().__init__(parent, radius=16, tint_alpha=170, palette=OVERLAY)
        self.setFixedHeight(self.HEIGHT)
        self.position_slider = SeekSlider()
        self.position_slider.setRange(0, 0)
        self.position_slider.setFixedHeight(14)

        self.rewind_button = SkipButton(skip_seconds, forward=False, palette=OVERLAY)
        self.play_button = make_play_btn(OVERLAY)
        self.play_button.setFixedSize(40, 40)
        self.play_button.icon_size_px = 18
        self.skip_button = SkipButton(skip_seconds, forward=True, palette=OVERLAY)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addStretch()
        row.addWidget(self.rewind_button)
        row.addWidget(self.play_button)
        row.addWidget(self.skip_button)
        row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 8)
        layout.setSpacing(2)
        layout.addWidget(self.position_slider)
        layout.addLayout(row)
        self.setStyleSheet(control_styles(OVERLAY))


class MiniPlayer(QWidget):
    back_requested = pyqtSignal()
    play_pause_requested = pyqtSignal()

    DEFAULT_WIDTH = 420
    MIN_WIDTH = 300
    RESIZE_BORDER = 8
    SCREEN_MARGIN = 40  # от края экрана: чтобы свечению было где поместиться

    def __init__(self, background, skip_seconds: int):
        self.glow = MiniGlow(background)
        # Окно принадлежит свечению: Windows всегда держит его выше
        super().__init__(self.glow, Qt.WindowType.Tool
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Lucent")
        self.setMinimumSize(self.MIN_WIDTH, 170)
        self._aspect = 16 / 9
        self._native_ready = False

        self.video = VideoFrame(0, stack_on_top=False)
        self.video.set_rounded(False)  # углы скругляет Windows вместе с окном
        self.video.double_clicked.connect(self.back_requested)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video)

        self.controls = MiniControls(self, skip_seconds)
        self.controls.hide()
        # Вернуть в большое окно: отдельно, в углу — как в других мини-плеерах
        self.back_button = make_icon_btn(Icons.EXPAND, 36, OVERLAY)
        self.back_button.setParent(self)
        self.back_button.setStyleSheet(control_styles(OVERLAY))
        bind(self.back_button, "setToolTip", "Вернуться в большое окно (Esc)")
        self.back_button.clicked.connect(self.back_requested)
        self.back_button.hide()
        self.controls.play_button.clicked.connect(self.play_pause_requested)

        self.video._sink.videoSizeChanged.connect(self._on_video_size_changed)
        QShortcut(QKeySequence("Esc"), self).activated.connect(self.back_requested)
        QShortcut(QKeySequence("Space"), self).activated.connect(self.play_pause_requested)

        # Панель показываем по положению курсора: над видео события мыши ненадёжны
        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(120)
        self._hover_timer.timeout.connect(self._update_controls)

    # ----- Показ -----

    def open_at(self, x: int, y: int, width: int):
        """Показать на сохранённом месте; вне экранов — в правом нижнем углу"""
        width = max(width, self.MIN_WIDTH)
        height = round(width / self._aspect)
        rect = QRect(x, y, width, height)
        if not any(s.availableGeometry().contains(rect.center()) for s in QGuiApplication.screens()):
            area = QGuiApplication.primaryScreen().availableGeometry()
            rect.moveBottomRight(area.bottomRight() - QRect(0, 0, self.SCREEN_MARGIN, self.SCREEN_MARGIN).bottomRight())
        self.setGeometry(rect)
        self.glow.follow(rect)
        self.glow.show()
        self.show()
        self._hover_timer.start()

    def close_window(self):
        self._hover_timer.stop()
        self.hide()
        self.glow.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._native_ready:
            self._native_ready = True
            # Настоящая рамка: тень, скругление, край для растягивания. Разворачивать незачем
            restore_native_frame(self)
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~(WS_MAXIMIZEBOX | WS_MINIMIZEBOX))

    # ----- Состояние от главного окна -----

    def set_play_button_state(self, is_playing: bool):
        self.controls.play_button.set_icon(Icons.PAUSE if is_playing else Icons.PLAY)

    def set_duration(self, duration_ms: int):
        self.controls.position_slider.setRange(0, max(duration_ms, 0))

    def set_position(self, position_ms: int):
        self.controls.position_slider.sync(position_ms)

    def set_skip_seconds(self, seconds: int):
        self.controls.rewind_button.set_seconds(seconds)
        self.controls.skip_button.set_seconds(seconds)

    # ----- Геометрия -----

    def _on_video_size_changed(self):
        size = self.video._sink.videoSize()
        if size.height() > 0:
            self._aspect = size.width() / size.height()
            self.resize(self.width(), round(self.width() / self._aspect))

    def moveEvent(self, event):
        super().moveEvent(event)
        self.glow.follow(self.frameGeometry())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.glow.follow(self.frameGeometry())
        c = self.controls
        c.setGeometry(8, self.height() - c.height() - 8, self.width() - 16, c.height())
        self.back_button.move(self.width() - self.back_button.width() - 10, 10)

    def _update_controls(self):
        over = self.frameGeometry().contains(QCursor.pos())
        visible = over or self.controls.position_slider.isSliderDown()
        self.controls.setVisible(visible)
        self.back_button.setVisible(visible)

    # ----- Рамка Windows -----

    def _keep_aspect(self, edge: int, rect):
        """Тянут за край или угол — вторую сторону подгоняем под пропорции видео"""
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if edge in (WMSZ_TOP, WMSZ_BOTTOM):
            width = round(height * self._aspect)
            rect.right = rect.left + width
        else:
            height = round(width / self._aspect)
            if edge in (WMSZ_TOPLEFT, WMSZ_TOPRIGHT):
                rect.top = rect.bottom - height
            else:
                rect.bottom = rect.top + height

    def _hit_test(self, hwnd, lparam) -> int:
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        x = ctypes.c_short(lparam & 0xFFFF).value - rect.left
        y = ctypes.c_short((lparam >> 16) & 0xFFFF).value - rect.top
        w, h = rect.right - rect.left, rect.bottom - rect.top
        b = round(self.RESIZE_BORDER * self.devicePixelRatio())
        left, right, top, bottom = x < b, x >= w - b, y < b, y >= h - b
        for hit, code in (((top and left), HTTOPLEFT), ((top and right), HTTOPRIGHT),
                          ((bottom and left), HTBOTTOMLEFT), ((bottom and right), HTBOTTOMRIGHT),
                          (left, HTLEFT), (right, HTRIGHT), (top, HTTOP), (bottom, HTBOTTOM)):
            if hit:
                return code
        if self.controls.isVisible():
            dpr = self.devicePixelRatio()
            point = QPoint(round(x / dpr), round(y / dpr))
            if self.controls.geometry().contains(point) or self.back_button.geometry().contains(point):
                return HTCLIENT
        return HTCAPTION  # за любое место окно перетаскивается

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_NCCALCSIZE and msg.wParam:
                return True, 0  # заголовка Windows нет: всё окно — наше
            if msg.message == WM_NCHITTEST:
                return True, self._hit_test(msg.hWnd, msg.lParam)
            if msg.message == WM_SIZING:
                self._keep_aspect(msg.wParam, wintypes.RECT.from_address(msg.lParam))
                return True, 1
            if msg.message == WM_NCLBUTTONDBLCLK and msg.wParam == HTCAPTION:
                self.back_requested.emit()  # двойной клик — как в главном окне по видео
                return True, 0
        # Не super(): см. MainWindow.nativeEvent
        return False, 0

"""
Свой заголовок окна поверх стеклянного фона.
Системный заголовок Windows убирается, но рамка окна остаётся настоящей:
изменение размера за края, прилипание к краям экрана (Snap), тень и
скруглённые углы Windows 11 работают как у обычного окна.
"""

import ctypes
import sys
from ctypes import wintypes

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget
from core.i18n import bind, tr

from ui.icons import IconButton, Icons
from ui.styles import T

IS_WINDOWS = sys.platform == "win32"

# --- Win32 ---
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
HTCLIENT, HTCAPTION = 1, 2
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT = 10, 11, 12, 13, 14
HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 15, 16, 17
GWL_STYLE = -16
WS_CAPTION, WS_THICKFRAME = 0x00C00000, 0x00040000
WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_SYSMENU = 0x00020000, 0x00010000, 0x00080000
SWP_FRAMECHANGED, SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER = 0x0020, 0x0002, 0x0001, 0x0004
SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CXPADDEDBORDER = 32, 33, 92
DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND = 33, 2

RESIZE_BORDER = 6  # толщина «хватательной» зоны по краям, логические пиксели


class NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


def restore_native_frame(window):
    """
    Окно создаётся без рамки (Qt не резервирует место под заголовок),
    затем ему возвращаются стили рамки — ради Snap, тени и анимаций Windows.
    """
    if not IS_WINDOWS:
        return
    user32 = ctypes.windll.user32
    hwnd = int(window.winId())
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style |= WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)
    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                        SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
    # Скруглённые углы окна Windows 11 — под них нарисован контур (GlassBackground)
    preference = ctypes.c_int(DWMWCP_ROUND)
    try:
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference), ctypes.sizeof(preference))
    except (AttributeError, OSError):
        pass  # Windows 10: углы прямые, атрибута нет


def _frame_thickness(hwnd) -> int:
    user32 = ctypes.windll.user32
    dpi = user32.GetDpiForWindow(hwnd)
    return (user32.GetSystemMetricsForDpi(SM_CYSIZEFRAME, dpi)
            + user32.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi))


def handle_native_event(window, title_bar, message):
    """Вызывается из nativeEvent окна. Возвращает (обработано, результат) или None."""
    msg = wintypes.MSG.from_address(int(message))

    if msg.message == WM_NCCALCSIZE and msg.wParam:
        # Весь прямоугольник окна — клиентская область (заголовка Windows нет).
        # Развёрнутое окно Windows выдвигает за экран на толщину рамки — поджимаем.
        # Состояние берём у самой Windows (IsZoomed): когда окно восстанавливают
        # двойным кликом, Snap или с панели задач, Qt ещё считает его развёрнутым,
        # и без этого у обычного окна оставался отступ — белая полоса сверху.
        if ctypes.windll.user32.IsZoomed(msg.hWnd) and not window.isFullScreen():
            params = NCCALCSIZE_PARAMS.from_address(msg.lParam)
            inset = _frame_thickness(msg.hWnd)
            rect = params.rgrc[0]
            rect.left += inset
            rect.top += inset
            rect.right -= inset
            rect.bottom -= inset
        return True, 0

    if msg.message == WM_NCHITTEST:
        if window.isFullScreen():
            return True, HTCLIENT
        dpr = window.devicePixelRatio()
        x = ctypes.c_short(msg.lParam & 0xFFFF).value / dpr
        y = ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value / dpr
        local = QPoint(round(x - window.x()), round(y - window.y()))
        w, h = window.width(), window.height()

        if not window.isMaximized():
            b = RESIZE_BORDER
            left, right = local.x() < b, local.x() >= w - b
            top, bottom = local.y() < b, local.y() >= h - b
            for hit, code in (((top and left), HTTOPLEFT), ((top and right), HTTOPRIGHT),
                              ((bottom and left), HTBOTTOMLEFT), ((bottom and right), HTBOTTOMRIGHT),
                              (left, HTLEFT), (right, HTRIGHT), (top, HTTOP), (bottom, HTBOTTOM)):
                if hit:
                    return True, code

        if title_bar.isVisible():
            bar_pos = title_bar.mapFrom(window, local)
            if title_bar.rect().contains(bar_pos):
                child = title_bar.childAt(bar_pos)
                if not isinstance(child, QPushButton):
                    return True, HTCAPTION  # перетаскивание, Snap, двойной клик
        return True, HTCLIENT

    return None


class CaptionButton(IconButton):
    """Кнопка окна. Значок 10×10 рисуется по сетке пикселей, как у Windows:
    в таком размере общие значки из сетки 24×24 расплываются между пикселями"""

    SIZE = 10

    def paintEvent(self, event):
        QPushButton.paintEvent(self, event)
        x, y = (self.width() - self.SIZE) // 2, (self.height() - self.SIZE) // 2
        p = QPainter(self)
        name = self.icon_name
        if name == Icons.CLOSE:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(self._current_color(), 1.25, cap=Qt.PenCapStyle.SquareCap))
            p.drawLine(QPointF(x + 0.5, y + 0.5), QPointF(x + 9.5, y + 9.5))
            p.drawLine(QPointF(x + 9.5, y + 0.5), QPointF(x + 0.5, y + 9.5))
            return
        p.setPen(QPen(self._current_color(), 1.0))
        if name == Icons.MINIMIZE:
            p.drawLine(x, y + 5, x + 9, y + 5)
        elif name == Icons.MAXIMIZE:
            p.drawRect(QRectF(x, y, 9, 9))
        else:  # Icons.RESTORE: окно и уголок второго за ним
            p.drawRect(QRectF(x, y + 2, 7, 7))
            p.drawLine(x + 2, y + 2, x + 2, y)
            p.drawLine(x + 2, y, x + 9, y)
            p.drawLine(x + 9, y, x + 9, y + 7)
            p.drawLine(x + 9, y + 7, x + 7, y + 7)


class TitleBar(QWidget):
    """Заголовок: пустая полоса для перетаскивания, справа настройки и кнопки окна"""

    HEIGHT = 32          # как у заголовка Windows 11

    def __init__(self, window):
        super().__init__()
        self._window = window
        self.setFixedHeight(self.HEIGHT)

        self.min_button = self._button(Icons.MINIMIZE, "Свернуть", window.showMinimized)
        self.max_button = self._button(Icons.MAXIMIZE, "Развернуть", self._toggle_maximized)
        self.close_button = self._button(Icons.CLOSE, "Закрыть", window.close, QColor("white"))
        self.close_button.setObjectName("close_btn")
        # Шестерёнка — отдельно от кнопок окна, как в приложениях Windows 11
        self.settings_button = IconButton(Icons.SETTINGS, 18, stroke=2.2)
        self.settings_button.setObjectName("settings_btn")
        self.settings_button.setFixedSize(36, 32)
        self.settings_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bind(self.settings_button, "setToolTip", "Настройки (Ctrl+,)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # справа — вплотную к краю окна
        layout.setSpacing(8)
        layout.addStretch()
        layout.addWidget(self.settings_button)
        layout.addSpacing(8)
        # Кнопки окна как у Windows: 46×32 без промежутков, до самого угла
        window_buttons = QHBoxLayout()
        window_buttons.setSpacing(0)
        for btn in (self.min_button, self.max_button, self.close_button):
            window_buttons.addWidget(btn)
        layout.addLayout(window_buttons)
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 0;
            }}
            QPushButton:hover {{ background-color: {T.fill_hover}; }}
            QPushButton:pressed {{ background-color: {T.fill_pressed}; }}
            QPushButton#settings_btn {{ border-radius: 8px; }}
            QPushButton#close_btn:hover {{ background-color: #c42b1c; }}
            QPushButton#close_btn:pressed {{ background-color: #a52618; }}
        """)


    def _button(self, icon: str, tip: str, slot, hover_color=None) -> QPushButton:
        btn = CaptionButton(icon, hover_color=hover_color)
        btn.setFixedSize(46, 32)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bind(btn, "setToolTip", tip)
        btn.clicked.connect(slot)
        return btn

    def _toggle_maximized(self):
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def update_state(self):
        maximized = self._window.isMaximized()
        self.max_button.set_icon(Icons.RESTORE if maximized else Icons.MAXIMIZE)
        self.max_button.setToolTip(tr("Свернуть в окно" if maximized else "Развернуть"))

    def mousePressEvent(self, event):
        # На Windows перетаскивание делает система (HTCAPTION); это — для других ОС
        if not IS_WINDOWS and event.button() == Qt.MouseButton.LeftButton:
            self._window.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        # На Windows двойной клик обрабатывает система (HTCAPTION); это — для других ОС
        if not IS_WINDOWS:
            self._toggle_maximized()

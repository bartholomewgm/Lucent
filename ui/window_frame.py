"""
Свой заголовок окна поверх стеклянного фона.
Системный заголовок Windows убирается, но рамка окна остаётся настоящей:
изменение размера за края, прилипание к краям экрана (Snap), тень и
скруглённые углы Windows 11 работают как у обычного окна.
"""

import ctypes
import sys
from ctypes import wintypes

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget

from ui.styles import GLASS_FILL_HOVER, GLASS_FILL_PRESSED, GLASS_TEXT, GLASS_TEXT_SUB, ICON_FONT, Icons

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
        if window.isMaximized() and not window.isFullScreen():
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


class TitleBar(QWidget):
    """Заголовок: значок и название слева, кнопки окна справа"""

    HEIGHT = 32          # как у заголовка Windows 11
    LEFT_INSET = 26      # значок — на одной линии с содержимым окна

    def __init__(self, window):
        super().__init__()
        self._window = window
        self.setFixedHeight(self.HEIGHT)

        icon = QLabel()
        app_icon = QApplication.windowIcon()
        if not app_icon.isNull():
            icon.setPixmap(app_icon.pixmap(18, 18))
        else:
            icon.setPixmap(QPixmap())
        title = QLabel("Lucent")
        title.setObjectName("window_title")

        self.min_button = self._button("\uE921", "Свернуть", window.showMinimized)
        self.max_button = self._button("\uE922", "Развернуть", self._toggle_maximized)
        self.close_button = self._button("\uE8BB", "Закрыть", window.close)
        self.close_button.setObjectName("close_btn")
        # Шестерёнка — отдельно от кнопок окна, как в приложениях Windows 11
        self.settings_button = QPushButton(Icons.SETTINGS)
        self.settings_button.setObjectName("settings_btn")
        self.settings_button.setFixedSize(36, 32)
        self.settings_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.settings_button.setToolTip("Настройки (Ctrl+,)")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(self.LEFT_INSET, 0, 0, 0)  # справа — вплотную к краю окна
        layout.setSpacing(8)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.settings_button)
        layout.addSpacing(8)
        # Кнопки окна как у Windows: 46×32 без промежутков, до самого угла
        window_buttons = QHBoxLayout()
        window_buttons.setSpacing(0)
        for btn in (self.min_button, self.max_button, self.close_button):
            window_buttons.addWidget(btn)
        layout.addLayout(window_buttons)

        self.setStyleSheet(f"""
            QLabel#window_title {{ color: {GLASS_TEXT_SUB}; font-size: 12px; }}
            QPushButton {{
                background: transparent; color: {GLASS_TEXT}; border: none;
                border-radius: 0; font-family: {ICON_FONT}; font-size: 10px;
            }}
            QPushButton:hover {{ background-color: {GLASS_FILL_HOVER}; }}
            QPushButton:pressed {{ background-color: {GLASS_FILL_PRESSED}; }}
            QPushButton#settings_btn {{
                font-size: 15px; color: {GLASS_TEXT_SUB}; border-radius: 8px;
            }}
            QPushButton#settings_btn:hover {{ color: {GLASS_TEXT}; }}
            QPushButton#close_btn:hover {{ background-color: #c42b1c; color: white; }}
            QPushButton#close_btn:pressed {{ background-color: #a52618; color: white; }}
        """)

    def _button(self, glyph: str, tip: str, slot) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setFixedSize(46, 32)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setToolTip(tip)
        btn.clicked.connect(slot)
        return btn

    def _toggle_maximized(self):
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def update_state(self):
        maximized = self._window.isMaximized()
        self.max_button.setText("\uE923" if maximized else "\uE922")
        self.max_button.setToolTip("Свернуть в окно" if maximized else "Развернуть")

    def mousePressEvent(self, event):
        # На Windows перетаскивание делает система (HTCAPTION); это — для других ОС
        if not IS_WINDOWS and event.button() == Qt.MouseButton.LeftButton:
            self._window.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        # На Windows двойной клик обрабатывает система (HTCAPTION); это — для других ОС
        if not IS_WINDOWS:
            self._toggle_maximized()

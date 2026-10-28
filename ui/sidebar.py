from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QWidget
from core.i18n import bind
from PyQt6.QtCore import Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve

from ui.glass import GlassPanel
from ui.glass_button import GlassLook
from ui.styles import T, ICON_FONT, Icons
from ui.playlist import PlaylistWidget


class SidebarWidget(GlassPanel):
    """Левая стеклянная панель: кнопка добавления видео и плейлист"""

    open_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # ===== КНОПКА ДОБАВЛЕНИЯ: только «+» =====
        self.open_button = QPushButton(Icons.ADD)
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.open_button.setFixedHeight(46)
        bind(self.open_button, "setToolTip", "Добавить видео (Ctrl+O)")
        self.open_button.clicked.connect(self.open_clicked.emit)
        GlassLook(self.open_button)
        layout.addWidget(self.open_button)

        # ===== ПЛЕЙЛИСТ =====
        self.playlist = PlaylistWidget()
        layout.addWidget(self.playlist, stretch=1)

        self.setLayout(layout)
        self.apply_theme()

    def apply_theme(self):
        """Перестроить стили под текущую тему"""
        self.open_button.setStyleSheet(f"""
            QPushButton, QPushButton:hover, QPushButton:pressed {{
                background: transparent;  /* объём и тень — GlassLook */
                color: {T.text};
                border: none;
                font-family: {ICON_FONT};
                font-size: 16px;
            }}
        """)
        self.playlist.apply_theme()
        self.update()


class SidebarDrawer(QWidget):
    """
    Выдвижной контейнер для боковой панели.
    Анимируется ширина контейнера, а сама панель не сжимается,
    а уезжает влево за край — содержимое не «мнётся».
    """

    toggled = pyqtSignal(bool)
    openness_changed = pyqtSignal(float)  # 0 — скрыта, 1 — открыта
    DURATION_MS = 320

    def __init__(self, sidebar: SidebarWidget, gap: int):
        super().__init__()
        self.sidebar = sidebar
        self.sidebar.setParent(self)
        self._full_width = sidebar.width() + gap  # панель + отступ до видео
        self._openness = 1.0
        self._open = True
        self.setFixedWidth(self._full_width)

        self._anim = QPropertyAnimation(self, b"openness", self)
        self._anim.setDuration(self.DURATION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def get_openness(self) -> float:
        return self._openness

    def set_openness(self, value: float):
        self._openness = value
        self.setFixedWidth(round(self._full_width * value))
        self._place_sidebar()
        self.openness_changed.emit(value)

    openness = pyqtProperty(float, fget=get_openness, fset=set_openness)

    def is_open(self) -> bool:
        return self._open

    def toggle(self):
        self.set_open(not self._open)

    def set_open(self, is_open: bool):
        if is_open == self._open:
            return
        self._open = is_open
        self._anim.stop()
        self._anim.setStartValue(self._openness)
        self._anim.setEndValue(1.0 if is_open else 0.0)
        self._anim.start()
        self.toggled.emit(is_open)

    def _place_sidebar(self):
        # При openness = 0 панель целиком за левым краем
        x = round(-self.sidebar.width() * (1 - self._openness))
        self.sidebar.setGeometry(x, 0, self.sidebar.width(), self.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_sidebar()

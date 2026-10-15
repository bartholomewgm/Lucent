from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtProperty, QPropertyAnimation, QEasingCurve

from ui.glass import GlassPanel
from ui.styles import (
    GLASS_TEXT, GLASS_TEXT_MUTED, GLASS_FILL, GLASS_FILL_HOVER,
    GLASS_FILL_PRESSED, ICON_FONT, Icons
)
from ui.playlist import PlaylistWidget


class SidebarWidget(GlassPanel):
    """Левая стеклянная панель: кнопка открытия, плейлист"""

    open_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(280)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(14)

        # ===== КНОПКА ОТКРЫТИЯ =====
        self.open_button = QPushButton()
        self.open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_button.setFixedHeight(46)
        self.open_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {GLASS_FILL};
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 23px;
            }}
            QPushButton:hover {{
                background-color: {GLASS_FILL_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {GLASS_FILL_PRESSED};
            }}
        """)
        # Иконка и текст разными шрифтами — собираем из двух подписей
        btn_layout = QHBoxLayout(self.open_button)
        btn_layout.setContentsMargins(18, 0, 18, 0)
        btn_layout.setSpacing(10)
        icon = QLabel(Icons.ADD)
        icon.setStyleSheet(f"font-family: {ICON_FONT}; font-size: 13px; color: {GLASS_TEXT};")
        text = QLabel("Открыть видео")
        text.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {GLASS_TEXT};")
        for label in (icon, text):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            btn_layout.addWidget(label)
        btn_layout.addStretch()
        self.open_button.clicked.connect(self.open_clicked.emit)
        layout.addWidget(self.open_button)

        # ===== ЗАГОЛОВОК СЕКЦИИ =====
        section_header = QLabel("Очередь")
        section_header.setStyleSheet(f"""
            color: {GLASS_TEXT};
            font-size: 20px;
            font-weight: 700;
            padding-left: 6px;
        """)
        layout.addWidget(section_header)

        # ===== ПЛЕЙЛИСТ =====
        self.playlist = PlaylistWidget()
        layout.addWidget(self.playlist, stretch=1)

        # ===== ПОДСКАЗКА =====
        hint = QLabel("Двойной клик — воспроизвести")
        hint.setStyleSheet(f"color: {GLASS_TEXT_MUTED}; font-size: 11px; padding-left: 6px;")
        layout.addWidget(hint)

        self.setLayout(layout)


class SidebarDrawer(QWidget):
    """
    Выдвижной контейнер для боковой панели.
    Анимируется ширина контейнера, а сама панель не сжимается,
    а уезжает влево за край — содержимое не «мнётся».
    """

    toggled = pyqtSignal(bool)
    DURATION_MS = 280

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
        x = self.width() - self._full_width
        self.sidebar.setGeometry(x, 0, self.sidebar.width(), self.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_sidebar()

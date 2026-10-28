"""
Окно «Свойства» видео — как в проигрывателе Windows, в стеклянном стиле плеера.
"""

from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.media_info import MediaInfoProbe
from ui.controls import format_time
from ui.glass import GlassPanel
from ui.glass_button import GlassLook
from ui.styles import T
from core.i18n import language, tr

CHANNELS = {1: "1 (моно)", 2: "2 (стерео)", 6: "6 (5.1)", 8: "8 (7.1)"}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip()


def _number(value: float, digits: int = 2) -> str:
    """59.94 -> «59,94», 30.0 -> «30»"""
    text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",") if language() == "ru" else text


def _size(size) -> str:
    if not size:
        return ""
    for unit, factor in (("ГБ", 1024 ** 3), ("МБ", 1024 ** 2), ("КБ", 1024)):
        if size >= factor:
            return f"{_number(size / factor, 1)} {tr(unit)}"
    return tr("{} Б").format(size)


def _bitrate(bps) -> str:
    if not bps:
        return ""
    if bps >= 1_000_000:
        return tr("{} Мбит/с").format(_number(bps / 1_000_000, 1))
    return tr("{} кбит/с").format(round(bps / 1000))


def describe(info: dict) -> list:
    """Пары (подпись, значение) в порядке окна; пустое значение показывается как «—»"""
    path = Path(info["path"])
    resolution = info.get("resolution")
    date = info.get("date")
    year = ""
    if date is not None and hasattr(date, "date"):
        year = str(date.date().year()) if date.isValid() else ""
    elif date is not None and hasattr(date, "year"):
        year = str(date.year())
    codecs = " / ".join(c.name for c in (info.get("video_codec"), info.get("audio_codec"))
                        if c is not None and c.name not in ("Unspecified",))
    bitrates = " · ".join(filter(None, (
        _bitrate(info.get("video_bitrate")) and tr("видео {}").format(_bitrate(info.get("video_bitrate"))),
        _bitrate(info.get("audio_bitrate")) and tr("звук {}").format(_bitrate(info.get("audio_bitrate"))),
    )))
    channels = info.get("channels")
    return [
        ("Название", _text(info.get("title")) or path.stem),
        ("Подзаголовок", _text(info.get("subtitle")) or _text(info.get("comment"))),
        ("Дополнительные исполнители", _text(info.get("artists")) or _text(info.get("author"))),
        ("Длительность", format_time(info["duration"]) if info.get("duration") else ""),
        ("Жанр", _text(info.get("genre"))),
        ("Год", year),
        ("Разрешение", f"{resolution.width()} × {resolution.height()}"
         if resolution is not None and resolution.isValid() else ""),
        ("Частота кадров", _number(info["frame_rate"]) if info.get("frame_rate") else ""),
        ("Звуковые каналы", tr(CHANNELS.get(channels, str(channels))) if channels else ""),
        ("Тип элемента", path.suffix.lower()),
        ("Размер", _size(info.get("size"))),
        ("Кодеки", codecs),
        ("Битрейт", bitrates),
    ]


class PropertiesDialog(QDialog):
    WIDTH = 640
    opened_folder = pyqtSignal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = str(Path(path))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(self.WIDTH)
        self._drag_from = None

        panel = GlassPanel(self, radius=26, tint_alpha=248)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 20, 28, 22)
        layout.setSpacing(14)

        title = QLabel(tr("Свойства"))
        title.setObjectName("title")
        layout.addWidget(title)

        # Сетка из двух колонок: подпись сверху, значение под ней
        self._values = {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(12)
        for index, (name, _) in enumerate(describe({"path": self.path})):
            cell = QVBoxLayout()
            cell.setSpacing(2)
            label = QLabel(tr(name))  # ключи полей — русские, подпись — на текущем языке
            label.setObjectName("field")
            value = QLabel("…")
            value.setObjectName("value")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            cell.addWidget(label)
            cell.addWidget(value)
            grid.addLayout(cell, index // 2, index % 2, Qt.AlignmentFlag.AlignTop)
            self._values[name] = value
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        # Расположение — на всю ширину, путь целиком
        place = QVBoxLayout()
        place.setSpacing(2)
        place_label = QLabel(tr("Расположение файла"))
        place_label.setObjectName("field")
        place_value = QLabel(self.path)
        place_value.setObjectName("value")
        place_value.setWordWrap(True)
        place_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        place.addWidget(place_label)
        place.addWidget(place_value)
        layout.addLayout(place)

        folder_link = QPushButton(tr("Открыть папку с файлом"))
        folder_link.setObjectName("link")
        folder_link.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_link.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        folder_link.clicked.connect(self.open_folder)
        link_row = QHBoxLayout()
        link_row.addWidget(folder_link)
        link_row.addStretch()
        layout.addLayout(link_row)

        close = QPushButton(tr("Закрыть"))
        close.setObjectName("close")
        close.setFixedSize(200, 36)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.accept)
        close.setDefault(True)
        GlassLook(close)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(close)
        layout.addSpacing(4)
        layout.addLayout(bottom)

        self.setStyleSheet(f"""
            QLabel#title {{ color: {T.text}; font-size: 22px; font-weight: 700; }}
            QLabel#field {{ color: {T.text_sub}; font-size: 12px; }}
            QLabel#value {{ color: {T.text}; font-size: 14px; }}
            QLabel#value[empty="true"] {{ color: {T.text_muted}; }}
            QPushButton#link {{
                background: transparent; border: none; padding: 0;
                color: {T.accent}; font-size: 13px; text-align: left;
            }}
            QPushButton#link:hover {{ text-decoration: underline; }}
            QPushButton#close, QPushButton#close:hover, QPushButton#close:pressed {{
                background: transparent; color: {T.text}; border: none;  /* объём — GlassLook */
                font-size: 13px; font-weight: 600;
            }}
        """)

        self._probe = MediaInfoProbe(self.path, self)
        self._probe.finished.connect(self._show_info)
        self._probe.start()

    def _show_info(self, info: dict):
        for name, value in describe(info):
            label = self._values[name]
            label.setText(value or "—")
            label.setProperty("empty", not value)
            label.style().unpolish(label)
            label.style().polish(label)
        self.adjustSize()

    def open_folder(self):
        """Проводник с выделенным файлом"""
        QProcess.startDetached("explorer.exe", [f"/select,{self.path}"])
        self.opened_folder.emit(self.path)

    # ----- Перетаскивание окна за пустое место -----

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_from is not None:
            self.move(event.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, event):
        self._drag_from = None

"""
Область видео на Qt Quick: картинка по своим пропорциям со скруглёнными
сглаженными углами (см. video.qml).

Видео рисуется видеокартой внутри нашего окна, без отдельного системного окна
Windows, — поэтому углы гладкие, а не вырезанные «лесенкой».
"""

from pathlib import Path

from PyQt6.QtCore import QObject, QRectF, Qt, QUrl, pyqtSignal
from PyQt6.QtQuickWidgets import QQuickWidget

QML_FILE = Path(__file__).resolve().parent / "video.qml"


# Форматы картинки: (подпись, значение, пропорции; 0 — без принудительных)
ASPECT_MODES = (
    ("Авто", "auto", 0),
    ("16:9", "16:9", 16 / 9),
    ("4:3", "4:3", 4 / 3),
    ("21:9", "21:9", 21 / 9),
    ("Растянуть", "stretch", 0),
)


class VideoFrame(QQuickWidget):
    double_clicked = pyqtSignal()
    picture_changed = pyqtSignal()  # картинка сдвинулась или сменила размер

    def __init__(self, radius: int):
        super().__init__()
        self.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        # Прозрачный фон: вокруг видео виден стеклянный фон окна
        self.setClearColor(Qt.GlobalColor.transparent)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setSource(QUrl.fromLocalFile(str(QML_FILE)))
        if self.status() == QQuickWidget.Status.Error:
            raise RuntimeError("video.qml: " + "; ".join(e.toString() for e in self.errors()))

        self.rootObject().setProperty("radius", radius)
        # Сюда QMediaPlayer выводит картинку (setVideoOutput)
        self.video_output = self.rootObject().findChild(QObject, "video")
        # Сигнал приходит из потока отрисовки видео — подключаем метод виджета
        # (не lambda), чтобы Qt доставил его в главный поток
        self._sink = self.video_output.property("videoSink")
        self._sink.videoSizeChanged.connect(self._on_video_size_changed)
        self.rootObject().pictureRectChanged.connect(self.picture_changed)

    def _on_video_size_changed(self):
        size = self._sink.videoSize()
        aspect = size.width() / size.height() if size.height() > 0 else 0
        self.rootObject().setProperty("videoAspect", aspect)

    def picture_rect(self) -> QRectF:
        """Видимая картинка в координатах виджета"""
        return QRectF(self.rootObject().property("pictureRect"))

    def set_placeholder_color(self, color):
        self.rootObject().setProperty("placeholderColor", color)

    def set_rounded(self, rounded: bool):
        """В окне — скругление; на весь экран — видео напрямую"""
        self.rootObject().setProperty("rounded", rounded)

    def set_aspect_mode(self, mode: str):
        aspect = next((a for _, value, a in ASPECT_MODES if value == mode), 0)
        root = self.rootObject()
        root.setProperty("mode", mode if aspect == 0 else "stretch")
        root.setProperty("forcedAspect", aspect)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

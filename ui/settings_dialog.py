"""
Окно настроек в стиле Liquid Glass.
Изменения применяются сразу — как в настройках iOS, без кнопки «Сохранить».
"""

from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import autostart
from ui.glass import GlassPanel
from ui.glass_button import GlassLook
from ui.video_frame import ASPECT_MODES
from ui.styles import T, THEME_NAMES


class ToggleSwitch(QAbstractButton):
    """Переключатель как в iOS: ручка плавно переезжает, дорожка окрашивается"""

    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(46, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float):
        self._offset = value
        self.update()

    offset = pyqtProperty(float, fget=get_offset, fset=set_offset)

    def _animate(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._offset
        off, on = T.color("toggle_off"), T.color("accent")
        track = QColor(
            round(off.red() + (on.red() - off.red()) * t),
            round(off.green() + (on.green() - off.green()) * t),
            round(off.blue() + (on.blue() - off.blue()) * t),
            round(off.alpha() + (on.alpha() - off.alpha()) * t),
        )
        rect = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob = rect.height() - 6
        x = 3 + (rect.width() - knob - 6) * t
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 3, knob, knob))


class SegmentedControl(QWidget):
    """Выбор одного варианта из нескольких — сегменты в стеклянной «капсуле»"""

    changed = pyqtSignal(object)

    def __init__(self, options, current):
        super().__init__()
        self.setObjectName("segmented")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        self._values = []
        for label, value in options:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setObjectName("segment")
            btn.setChecked(value == current)
            self._group.addButton(btn, len(self._values))
            self._values.append(value)
            layout.addWidget(btn)
        self._group.idClicked.connect(lambda i: self.changed.emit(self._values[i]))


class SettingsDialog(QDialog):
    """Стеклянное окно настроек"""

    WIDTH = 600
    history_cleared = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(self.WIDTH)
        self._drag_from = None

        self.panel = GlassPanel(self, radius=26, tint_alpha=248)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.panel)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(26, 16, 14, 20)
        panel_layout.setSpacing(6)
        header = self._header()
        header.setContentsMargins(0, 0, 12, 0)
        panel_layout.addLayout(header)

        # Содержимое прокручивается, если не помещается на экран
        content = QWidget()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(6)
        self._build(layout)
        scroll = QScrollArea()
        scroll.setObjectName("scroll")
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        panel_layout.addWidget(scroll)
        self.setStyleSheet(self._styles())
        # Тему меняют прямо здесь — перекрашиваемся сразу (MainWindow уже сменил палитру)
        settings.changed.connect(self._on_setting_changed)

        screen = (parent or self).screen().availableGeometry()
        max_content = screen.height() - 160
        scroll.setMinimumHeight(min(content.sizeHint().height(), max_content))
        self.setMaximumHeight(screen.height() - 40)

    # ----- Построение -----

    def _header(self):
        title = QLabel("Настройки")
        title.setObjectName("title")
        close = QPushButton("✕")
        close.setObjectName("close")
        close.setFixedSize(32, 32)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close.setToolTip("Закрыть (Esc)")
        close.clicked.connect(self.accept)
        GlassLook(close)
        row = QHBoxLayout()
        row.addWidget(title)
        row.addStretch()
        row.addWidget(close)
        return row

    def _section(self, layout, name: str):
        label = QLabel(name)
        label.setObjectName("section")
        layout.addSpacing(4)
        layout.addWidget(label)
        card = QWidget()
        card.setObjectName("card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 2, 16, 2)
        card_layout.setSpacing(0)
        layout.addWidget(card)
        return card_layout

    def _row(self, card_layout, text: str, control: QWidget, hint: str = ""):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 6, 0, 6)
        labels = QVBoxLayout()
        labels.setSpacing(1)
        label = QLabel(text)
        label.setObjectName("row_label")
        labels.addWidget(label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("hint")
            hint_label.setWordWrap(True)  # длинная подсказка не раздвигает окно
            labels.addWidget(hint_label)
        row_layout.addLayout(labels)
        row_layout.addStretch()
        row_layout.addWidget(control)
        card_layout.addWidget(row)
        return row

    def _stacked_row(self, card_layout, text: str, control: QWidget, hint: str = ""):
        """Подпись сверху, элемент управления на всю ширину под ней"""
        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 6, 0, 8)
        row_layout.setSpacing(6)
        label = QLabel(text)
        label.setObjectName("row_label")
        row_layout.addWidget(label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("hint")
            hint_label.setWordWrap(True)  # длинная подсказка не раздвигает окно
            row_layout.addWidget(hint_label)
        row_layout.addWidget(control)
        card_layout.addWidget(row)
        return row

    def _segmented(self, key: str, options):
        control = SegmentedControl(options, self.settings.get(key))
        control.changed.connect(lambda value: self.settings.set(key, value))
        return control

    def _toggle(self, key: str):
        control = ToggleSwitch(self.settings.get(key))
        control.toggled.connect(lambda value: self.settings.set(key, value))
        return control

    def _build(self, layout):
        card = self._section(layout, "Воспроизведение")
        self._row(card, "Продолжать с места остановки", self._segmented(
            "resume", [("Всегда", "always"), ("Спрашивать", "ask"), ("Никогда", "never")]))
        self._row(card, "Перемотка кнопками ↺ ↻", self._segmented(
            "skip_seconds", [("5 с", 5), ("10 с", 10), ("15 с", 15), ("30 с", 30)]))
        self._row(card, "Когда видео закончилось", self._segmented(
            "on_end", [("Стоп", "stop"), ("Следующее", "next"), ("Повтор", "repeat")]))

        card = self._section(layout, "Звук")
        self._row(card, "Запоминать громкость", self._toggle("remember_volume"),
                  "Громкость при следующем запуске будет той же")

        card = self._section(layout, "Оформление")
        self._row(card, "Тема", self._segmented("theme", [(label, value) for label, value in THEME_NAMES]),
                  "Светлая и тёмная: цвета видео — только вокруг него")
        self._stacked_row(card, "Формат картинки", self._segmented(
            "aspect_mode", [(label, value) for label, value, _ in ASPECT_MODES]),
            "Как видео вписывается в окно. Переключать на ходу — клавиша A")
        self._row(card, "Фон под цвета видео", self._toggle("ambient_background"),
                  "Цветные пятна фона подстраиваются под картинку")

        card = self._section(layout, "Полноэкранный режим")
        self._row(card, "Прятать панель и курсор", self._segmented(
            "fullscreen_hide_seconds", [("2 с", 2), ("3 с", 3), ("5 с", 5), ("Никогда", 0)]),
            "Через сколько секунд без движения мыши")

        card = self._section(layout, "Папки")
        self._folder_row(card, "playlist_folder", "Папка-плейлист",
                         "Не выбрана — очередь собирается вручную")
        self._row(card, "Следить за новыми видео", self._toggle("watch_folder"),
                  "Новые файлы из папки сами появятся в очереди")
        self._row(card, "Порядок в очереди", self._segmented(
            "folder_sort", [("По имени", "name"), ("По дате", "date")]))

        card = self._section(layout, "Система")
        startup = ToggleSwitch(autostart.is_enabled())
        startup.toggled.connect(self._set_autostart)
        startup.setEnabled(autostart.is_supported())
        self._row(card, "Запускать вместе с Windows", startup,
                  "Lucent откроется при входе в систему")

        card = self._section(layout, "История")
        self.clear_button = self._pill("Очистить", self._clear_history)
        self.clear_button.setObjectName("danger")
        self._row(card, "История просмотров", self.clear_button,
                  "Места остановки во всех видео")

    def _on_setting_changed(self, key, _value):
        if key == "theme":
            self.setStyleSheet(self._styles())
            GlassLook.retheme_all()
            for widget in self.findChildren(QWidget):
                widget.update()
            self.update()

    def _pill(self, text: str, slot):
        btn = QPushButton(text)
        btn.setObjectName("pill")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(slot)
        GlassLook(btn)
        return btn

    # ----- Действия -----

    def _folder_row(self, card, key: str, title: str, empty_text: str):
        """Строка «папка»: путь под названием, кнопки «Сбросить» и «Выбрать…»"""
        hint = QLabel()
        hint.setObjectName("hint")
        buttons = QWidget()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(6)
        reset = self._pill("Сбросить", lambda: update(""))
        choose = self._pill("Выбрать…", lambda: pick())
        buttons_layout.addWidget(reset)
        buttons_layout.addWidget(choose)
        row = self._row(card, title, buttons)
        row.layout().itemAt(0).layout().addWidget(hint)

        def update(folder: str):
            self.settings.set(key, folder)
            hint.setText((folder if len(folder) <= 46 else "…" + folder[-45:]) if folder else empty_text)
            hint.setToolTip(folder)
            reset.setVisible(bool(folder))

        def pick():
            start = self.settings.get(key) or str(Path.home())
            folder = QFileDialog.getExistingDirectory(self, title, start)
            if folder:
                update(folder)

        update(self.settings.get(key))

    def _set_autostart(self, enabled: bool):
        try:
            autostart.set_enabled(enabled)
        except OSError as e:
            QMessageBox.warning(self, "Lucent", f"Не удалось изменить автозапуск:\n{e}")

    def _clear_history(self):
        answer = QMessageBox.question(
            self, "Lucent", "Очистить историю просмотров?\nМеста остановки во всех видео забудутся."
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.history_cleared.emit()
            self.clear_button.setText("Очищено")
            self.clear_button.setEnabled(False)

    # ----- Перетаскивание окна за любое пустое место -----

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_from = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_from is not None:
            self.move(event.globalPosition().toPoint() - self._drag_from)

    def mouseReleaseEvent(self, event):
        self._drag_from = None

    # ----- Стили -----

    def _styles(self) -> str:
        return f"""
            QLabel#title {{ color: {T.text}; font-size: 22px; font-weight: 700; }}
            QLabel#section {{
                color: {T.text_sub}; font-size: 12px; font-weight: 600; padding-left: 6px;
            }}
            QScrollArea#scroll, QWidget#content {{ background: transparent; border: none; }}
            QWidget#card {{ background-color: {T.card}; border-radius: 16px; }}
            QLabel#row_label {{ color: {T.text}; font-size: 13px; }}
            QLabel#hint {{ color: {T.text_muted}; font-size: 11px; }}
            QWidget#segmented {{ background-color: {T.segmented}; border-radius: 10px; }}
            QPushButton#segment {{
                background: transparent; color: {T.text_sub}; border: none;
                border-radius: 8px; padding: 5px 11px; font-size: 12px;
            }}
            QPushButton#segment:hover {{ color: {T.text}; }}
            QPushButton#segment:checked {{
                background-color: {T.segment_checked}; color: {T.text}; font-weight: 600;
            }}
            /* Объём, блик и тень кнопок рисует GlassLook (ui/glass_button.py) */
            QPushButton#pill, QPushButton#danger, QPushButton#pill:hover, QPushButton#danger:hover,
            QPushButton#pill:pressed, QPushButton#danger:pressed {{
                background: transparent; color: {T.text}; border: none;
                padding: 6px 14px; font-size: 12px; font-weight: 600;
            }}
            QPushButton#danger, QPushButton#danger:hover, QPushButton#danger:pressed {{ color: {T.danger}; }}
            QPushButton#danger:disabled {{ color: {T.text_muted}; }}
            QPushButton#close, QPushButton#close:hover, QPushButton#close:pressed {{
                background: transparent; color: {T.text_sub}; border: none; font-size: 13px;
            }}
            QPushButton#close:hover {{ color: {T.text}; }}
        """

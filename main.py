"""
Точка входа в приложение
"""

import os

# КРИТИЧНО: выбор бэкенда ДО импорта PyQt6
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

import sys
import traceback
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from core.i18n import tr
from core.single_instance import InstanceServer, is_first_instance, send_to_running

APP_NAME = "Lucent"
# В собранном приложении файлы лежат в папке распаковки PyInstaller
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_ICON = _BASE_DIR / "resources" / "icons" / "lucent.ico"


def exception_hook(exc_type, exc_value, exc_tb):
    """Глобальный обработчик непойманных исключений"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(error_msg)
    QMessageBox.critical(None, tr("Критическая ошибка"), tr("Программа упала:\n{}").format(error_msg))


def main():
    sys.excepthook = exception_hook

    if sys.platform == "win32":
        # Своя «личность» процесса — иначе на панели задач значок Python, а не Lucent
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Lucent.VideoPlayer")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(APP_ICON)))

    # Файлы из командной строки: «Открыть с помощью», перетаскивание на значок.
    # Пути полные: запущенная копия работает в другой текущей папке
    files = [str(Path(arg).resolve()) for arg in sys.argv[1:] if Path(arg).is_file()]

    # Lucent уже открыт — отдать файлы ему и выйти, второе окно не нужно
    if not is_first_instance():
        send_to_running(files)
        return
    server = InstanceServer()
    server.listen()

    window = MainWindow()
    window.show()
    server.files_received.connect(window.open_external)
    window.open_files(files)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
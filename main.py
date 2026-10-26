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

APP_NAME = "Lucent"
# В собранном приложении файлы лежат в папке распаковки PyInstaller
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_ICON = _BASE_DIR / "resources" / "icons" / "lucent.ico"


def exception_hook(exc_type, exc_value, exc_tb):
    """Глобальный обработчик непойманных исключений"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(error_msg)
    QMessageBox.critical(None, "Критическая ошибка", f"Программа упала:\n{error_msg}")


def main():
    sys.excepthook = exception_hook

    if sys.platform == "win32":
        # Своя «личность» процесса — иначе на панели задач значок Python, а не Lucent
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Lucent.VideoPlayer")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(APP_ICON)))
    
    window = MainWindow()
    window.show()

    # Файлы из командной строки: «Открыть с помощью», перетаскивание на значок
    files = [arg for arg in sys.argv[1:] if Path(arg).is_file()]
    for path in files[1:]:
        window.playlist.add_video(path)
    if files:
        window.load_video(files[0])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
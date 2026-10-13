"""
Точка входа в приложение
"""

import os

# КРИТИЧНО: выбор бэкенда ДО импорта PyQt6
os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"

import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow


def exception_hook(exc_type, exc_value, exc_tb):
    """Глобальный обработчик непойманных исключений"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(error_msg)
    QMessageBox.critical(None, "Критическая ошибка", f"Программа упала:\n{error_msg}")


def main():
    sys.excepthook = exception_hook
    
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
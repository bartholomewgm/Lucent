"""
Модуль управления историей просмотров (SQLite)
"""

import os
import sqlite3
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Собранное приложение: папка программы может быть только для чтения
    _DB_PATH = Path(os.environ.get("APPDATA", Path.home())) / "Lucent" / "history.db"
else:
    # Запуск из исходников: БД в проекте (путь от корня проекта, а не от CWD)
    _DB_PATH = Path(__file__).resolve().parent.parent / "database" / "history.db"


class HistoryManager:
    """Управление историей просмотров"""

    def __init__(self):
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(_DB_PATH))
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                position INTEGER DEFAULT 0,
                last_opened TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.connection.commit()

    def save_video(self, file_path, position):
        file_path = str(Path(file_path).resolve())
        self.cursor.execute("""
            UPDATE history
            SET position = ?, last_opened = CURRENT_TIMESTAMP
            WHERE file_path = ?
        """, (position, file_path))

        if self.cursor.rowcount == 0:
            self.cursor.execute("""
                INSERT INTO history (file_path, position, last_opened)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (file_path, position))

        self.connection.commit()

    def get_position(self, file_path):
        file_path = str(Path(file_path).resolve())
        self.cursor.execute(
            "SELECT position FROM history WHERE file_path = ?", (file_path,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_last_video(self):
        self.cursor.execute("""
            SELECT file_path, position FROM history
            ORDER BY last_opened DESC LIMIT 1
        """)
        return self.cursor.fetchone()

    def clear_history(self):
        self.cursor.execute("DELETE FROM history")
        self.connection.commit()

    def close(self):
        self.connection.close()

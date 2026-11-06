"""
Одна копия приложения: повторный запуск не открывает второе окно,
а передаёт файлы уже запущенному Lucent и выводит его окно на передний план.

Связь — через QLocalServer (на Windows это именованный канал). Имя канала
включает имя пользователя: у разных пользователей одного компьютера свои копии.
"""

import getpass
import json
import sys

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

TIMEOUT_MS = 1000


def _server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return "Lucent-single-instance-" + "".join(c for c in user if c.isalnum())


_mutex = None  # держится до конца процесса: пока он есть, эта копия — первая


def is_first_instance() -> bool:
    """Первая ли это копия. Именованный мьютекс, а не канал: на Windows канал
    с занятым именем создаётся снова без ошибки, и две копии, запущенные
    одновременно, обе решили бы, что они первые"""
    global _mutex
    if sys.platform != "win32":
        return not _connect(QLocalSocket())
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    _mutex = kernel32.CreateMutexW(None, False, _server_name())
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


def _connect(socket: QLocalSocket) -> bool:
    socket.connectToServer(_server_name())
    return socket.waitForConnected(TIMEOUT_MS)


def send_to_running(files: list[str]) -> bool:
    """Передать файлы запущенной копии. Она могла только что стартовать
    и ещё не открыть канал — поэтому несколько попыток"""
    socket = QLocalSocket()
    for _ in range(10):
        if _connect(socket):
            break
        QThread.msleep(200)
    else:
        return False
    if sys.platform == "win32":
        # Разрешить запущенной копии вывести окно вперёд: Windows иначе
        # не даёт фоновому процессу забирать фокус и лишь мигает кнопкой на панели задач
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    socket.write(json.dumps(files).encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(TIMEOUT_MS)
    socket.disconnectFromServer()
    return True


class InstanceServer(QObject):
    """Принимает файлы от повторных запусков"""

    files_received = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_connection)
        self._buffers = {}

    def listen(self) -> bool:
        return self._server.listen(_server_name())

    def _on_connection(self):
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            self._buffers[socket] = b""
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(lambda s=socket: self._finish(s))

    def _read(self, socket):
        self._buffers[socket] = self._buffers.get(socket, b"") + bytes(socket.readAll())

    def _finish(self, socket):
        self._read(socket)
        data = self._buffers.pop(socket, b"")
        socket.deleteLater()
        try:
            files = json.loads(data.decode("utf-8")) if data else []
        except ValueError:
            return
        if isinstance(files, list):
            self.files_received.emit([str(f) for f in files])

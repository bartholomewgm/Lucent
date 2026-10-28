"""
Сборка Lucent в Windows-приложение (PyInstaller).

    venv\\Scripts\\python.exe -m pip install pyinstaller
    venv\\Scripts\\python.exe build.py

Результат: dist\\Lucent\\Lucent.exe и архив dist\\Lucent-windows.zip,
который можно просто отправить — Python у получателя не нужен.
"""

import shutil
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
ICON = ROOT / "resources" / "icons" / "lucent.ico"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
QT = DIST / "Lucent" / "_internal" / "PyQt6" / "Qt6"

# Вместе с Qt Quick PyInstaller забирает все QML-модули Qt. Плееру нужны только
# QtQml, QtQuick (+ Effects для скруглённого видео) и QtMultimedia — остальное лишнее.
UNUSED_QML = [
    "QtQuick3D", "QtPositioning", "QtRemoteObjects", "QtSensors", "QtTest",
    "QtTextToSpeech", "QtWebChannel", "QtWebSockets",
    "QtQuick/Controls", "QtQuick/Dialogs", "QtQuick/NativeStyle", "QtQuick/Particles",
    "QtQuick/Pdf", "QtQuick/Templates", "QtQuick/Timeline", "QtQuick/VectorImage",
    "QtQuick/Layouts",
]
UNUSED_DLL_PREFIXES = [
    "Qt6Pdf", "Qt6Positioning", "Qt6Quick3D", "Qt6QuickControls2", "Qt6QuickDialogs2",
    "Qt6QuickLayouts", "Qt6QuickParticles", "Qt6QuickTemplates2", "Qt6QuickTest",
    "Qt6QuickTimeline", "Qt6QuickVectorImage", "Qt6RemoteObjects", "Qt6Sensors",
    "Qt6SpatialAudio", "Qt6StateMachine", "Qt6Test", "Qt6TextToSpeech",
    "Qt6WebChannel", "Qt6WebSockets",
]


def prune():
    for name in UNUSED_QML:
        shutil.rmtree(QT / "qml" / name, ignore_errors=True)
    for dll in (QT / "bin").glob("Qt6*.dll"):
        if any(dll.stem.startswith(prefix) for prefix in UNUSED_DLL_PREFIXES):
            dll.unlink()


def main():
    PyInstaller.__main__.run([
        str(ROOT / "main.py"),
        "--name", "Lucent",
        "--windowed",            # без чёрного окна консоли
        "--noconfirm",
        "--clean",
        "--icon", str(ICON),
        "--add-data", f"{ICON};resources/icons",
        "--add-data", f"{ROOT / 'resources' / 'fonts'};resources/fonts",
        "--add-data", f"{ROOT / 'ui' / 'video.qml'};ui",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
    ])
    prune()
    archive =shutil.make_archive(str(DIST / "Lucent-windows"), "zip", DIST, "Lucent")
    # Промежуточная папка PyInstaller: там лежит нерабочая заготовка Lucent.exe
    # без библиотек — убираем, чтобы её не запустили по ошибке
    shutil.rmtree(BUILD, ignore_errors=True)
    print(f"\nГотово: {DIST / 'Lucent' / 'Lucent.exe'}\nАрхив:  {archive}")


if __name__ == "__main__":
    main()

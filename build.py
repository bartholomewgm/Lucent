"""
Сборка Lucent в Windows-приложение (PyInstaller).

    venv\\Scripts\\python.exe -m pip install pyinstaller
    venv\\Scripts\\python.exe build.py

Результат: dist\\Lucent\\Lucent.exe, архив dist\\Lucent-windows.zip и установщик
dist\\Lucent-Setup.exe (если есть Inno Setup 6). Python у получателя не нужен.
"""

import os
import shutil
import subprocess
from pathlib import Path

import PyInstaller.__main__

from core.media_formats import VIDEO_EXTENSIONS

APP_VERSION = "1.0.2"

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


def find_iscc():
    """Компилятор Inno Setup: в PATH или в стандартных папках установки"""
    found = shutil.which("ISCC")
    if found:
        return found
    roots = [os.environ.get("LOCALAPPDATA", "") + r"\Programs", os.environ.get("ProgramFiles(x86)", ""),
             os.environ.get("ProgramFiles", "")]
    for root in roots:
        path = Path(root) / "Inno Setup 6" / "ISCC.exe"
        if root and path.is_file():
            return str(path)
    return None


def build_installer():
    iscc = find_iscc()
    if not iscc:
        print("\nInno Setup 6 не найден — установщик не собран (winget install JRSoftware.InnoSetup)")
        return None
    types_key = r"Software\Classes\Applications\Lucent.exe\SupportedTypes"
    (DIST / "video_types.iss").write_text("".join(
        f'Root: HKCU; Subkey: "{types_key}"; ValueType: string; ValueName: "{ext}"; ValueData: ""\n'
        for ext in VIDEO_EXTENSIONS), encoding="utf-8")
    subprocess.run([iscc, "/Q", f"/DAppVersion={APP_VERSION}", str(ROOT / "installer" / "lucent.iss")],
                   check=True)
    return DIST / "Lucent-Setup.exe"


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
    setup = build_installer()
    print(f"\nГотово: {DIST / 'Lucent' / 'Lucent.exe'}\nАрхив:  {archive}\nУстановщик: {setup}")


if __name__ == "__main__":
    main()

"""
Языки интерфейса: русский (исходные строки в коде) и английский.

tr("русский текст") — перевод на текущий язык (ключ — сам русский текст,
с {} для подстановок). bind(виджет, "setText", "текст") — то же, но надпись
запоминается и обновляется сама при смене языка (retranslate).
"""

import weakref

LANGUAGES = (("Русский", "ru"), ("English", "en"))

_language = "ru"
_bindings = []  # (weakref на объект, имя метода, русский текст, подстановки)

EN = {
    # --- Ошибки ---
    "Файл не найден: {}": "File not found: {}",
    "Ошибка загрузки: {}": "Loading error: {}",
    "Ошибка: {}": "Error: {}",
    "Критическая ошибка": "Critical error",
    "Программа упала:\n{}": "The app crashed:\n{}",
    "Ошибка": "Error",
    "Ошибка плеера": "Player error",
    "Не удалось загрузить видео:\n{}": "Couldn't load the video:\n{}",
    "Не удалось изменить автозапуск:\n{}": "Couldn't change the start-up setting:\n{}",

    # --- Панель управления ---
    "Воспроизвести (Пробел)": "Play (Space)",
    "Вперёд на {} сек": "Forward {} s",
    "Назад на {} сек": "Back {} s",
    "Свойства (Ctrl+I)": "Properties (Ctrl+I)",
    "Скрыть плейлист (Ctrl+L)": "Hide playlist (Ctrl+L)",
    "Показать плейлист (Ctrl+L)": "Show playlist (Ctrl+L)",
    "Предыдущее (P)": "Previous (P)",
    "Следующее (N)": "Next (N)",
    "Скорость ([ / ])": "Speed ([ / ])",
    "Формат картинки (A)": "Aspect ratio (A)",
    "Без звука (M)": "Mute (M)",
    "Громкость (↑/↓)": "Volume (↑/↓)",
    "Полный экран (F)": "Full screen (F)",
    "Выйти из полного экрана (Esc)": "Exit full screen (Esc)",
    "Ничего не воспроизводится": "Nothing playing",
    "Откройте видео, чтобы начать": "Open a video to start",
    "Авто": "Auto",
    "Растянуть": "Stretch",

    # --- Окно, плейлист, файлы ---
    "Добавить видео": "Add video",
    "Добавить видео (Ctrl+O)": "Add video (Ctrl+O)",
    "Видео ({})": "Videos ({})",
    "Все файлы (*)": "All files (*)",
    "Продолжить с {}?\n\n{}": "Resume from {}?\n\n{}",
    "Свойства": "Properties",
    "Удалить из очереди": "Remove from queue",
    "Свернуть": "Minimize",
    "Развернуть": "Maximize",
    "Свернуть в окно": "Restore down",
    "Закрыть": "Close",
    "Настройки (Ctrl+,)": "Settings (Ctrl+,)",

    # --- Свойства ---
    "Название": "Title",
    "Подзаголовок": "Subtitle",
    "Дополнительные исполнители": "Contributing artists",
    "Длительность": "Length",
    "Жанр": "Genre",
    "Год": "Year",
    "Разрешение": "Resolution",
    "Частота кадров": "Frame rate",
    "Звуковые каналы": "Audio channels",
    "Тип элемента": "Item type",
    "Размер": "Size",
    "Кодеки": "Codecs",
    "Битрейт": "Bit rate",
    "Расположение файла": "File location",
    "Открыть папку с файлом": "Open file location",
    "1 (моно)": "1 (mono)",
    "2 (стерео)": "2 (stereo)",
    "ГБ": "GB", "МБ": "MB", "КБ": "KB", "{} Б": "{} B",
    "{} Мбит/с": "{} Mbps", "{} кбит/с": "{} kbps",
    "видео {}": "video {}", "звук {}": "audio {}",

    # --- Настройки ---
    "Настройки": "Settings",
    "Закрыть (Esc)": "Close (Esc)",
    "Воспроизведение": "Playback",
    "Продолжать с места остановки": "Resume where you left off",
    "Всегда": "Always", "Спрашивать": "Ask", "Никогда": "Never",
    "Шаг перемотки": "Skip step",
    "2 с": "2 s", "3 с": "3 s", "5 с": "5 s", "10 с": "10 s", "15 с": "15 s", "30 с": "30 s",
    "Когда видео закончилось": "When a video ends",
    "Стоп": "Stop", "Следующее": "Next", "Повтор": "Repeat",
    "Звук": "Sound",
    "Запоминать громкость": "Remember volume",
    "Громкость при следующем запуске будет той же": "The volume stays the same next time",
    "Оформление": "Appearance",
    "Язык": "Language",
    "Тема": "Theme",
    "Градиент": "Gradient", "Тёмная": "Dark", "Светлая": "Light",
    "Светлая и тёмная: цвета видео — только вокруг него": "Light and dark: video colours glow only around it",
    "Формат картинки": "Aspect ratio",
    "Как видео вписывается в окно. Переключать на ходу — клавиша A":
        "How the video fits the window. Switch on the fly with A",
    "Фон под цвета видео": "Background follows the video",
    "Цветные пятна фона подстраиваются под картинку": "Background colours adapt to the picture",
    "Полноэкранный режим": "Full screen",
    "Прятать панель и курсор": "Hide controls and cursor",
    "Через сколько секунд без движения мыши": "After this many seconds without mouse movement",
    "Папки": "Folders",
    "Папка-плейлист": "Playlist folder",
    "Не выбрана — очередь собирается вручную": "Not set — the queue is built by hand",
    "Видео, включая подпапки: {}": "Videos, including subfolders: {}",
    "В этой папке нет видео": "No videos in this folder",
    "Следить за новыми видео": "Watch for new videos",
    "Новые файлы из папки сами появятся в очереди": "New files in the folder join the queue automatically",
    "Порядок в очереди": "Queue order",
    "По имени": "By name", "По дате": "By date",
    "Система": "System",
    "Запускать вместе с Windows": "Start with Windows",
    "Lucent откроется при входе в систему": "Lucent opens when you sign in",
    "История": "History",
    "История просмотров": "Watch history",
    "Места остановки во всех видео": "Resume points of all videos",
    "Очистить": "Clear", "Очищено": "Cleared",
    "Сбросить": "Reset", "Выбрать…": "Choose…",
    "Очистить историю просмотров?\nМеста остановки во всех видео забудутся.":
        "Clear watch history?\nResume points of all videos will be forgotten.",
}


def language() -> str:
    return _language


def set_language(code: str):
    global _language
    _language = code if code in dict((c, n) for n, c in LANGUAGES) else "ru"


def tr(text: str) -> str:
    """Перевод на текущий язык; русский текст — ключ (и он же значение для русского)"""
    if _language == "en":
        return EN.get(text, text)
    return text


def _apply(obj, setter, text, args):
    value = tr(text)
    getattr(obj, setter)(value.format(*args) if args else value)


def bind(obj, setter: str, text: str, *args):
    """Установить переводимую надпись и обновлять её при смене языка"""
    _apply(obj, setter, text, args)
    _bindings.append((weakref.ref(obj), setter, text, args))


def retranslate():
    """Сменился язык — переписать все надписи, заданные через bind"""
    alive = []
    for ref, setter, text, args in _bindings:
        obj = ref()
        if obj is None:
            continue
        try:
            _apply(obj, setter, text, args)
        except RuntimeError:  # виджет уже удалён на стороне Qt
            continue
        alive.append((ref, setter, text, args))
    _bindings[:] = alive

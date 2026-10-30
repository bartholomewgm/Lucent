"""
Какие файлы плеер считает видео. Единый список для окна выбора файла,
перетаскивания, папки-плейлиста и установщика («Открыть с помощью»).
Декодирует их FFmpeg из состава Qt — он читает все эти контейнеры.
"""

VIDEO_EXTENSIONS = (
    ".mp4", ".m4v", ".mov", ".3gp", ".3g2", ".mkv", ".webm",
    ".avi", ".divx", ".wmv", ".asf", ".flv", ".f4v",
    ".mpg", ".mpeg", ".mpe", ".m1v", ".m2v", ".vob",
    ".ts", ".mts", ".m2ts", ".ogv", ".ogm",
    ".rm", ".rmvb", ".dv", ".mxf",
)

FILE_FILTER_PATTERNS = " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Lucent — Windows video player on PyQt6 (Python 3.14, Qt 6.11) with a "Liquid Glass" UI. Code comments, UI strings and README are in Russian; keep it that way.

## Commands

```bash
venv/Scripts/python.exe main.py                 # run (optionally: main.py "C:/path/video.mp4")
venv/Scripts/python.exe -m pip install -r requirements.txt
venv/Scripts/python.exe build.py                # PyInstaller build -> dist/Lucent/Lucent.exe + dist/Lucent-windows.zip
```

- `build.py` needs `pip install pyinstaller` in the venv. It deletes `build/` afterwards (the exe left there is a non-working stub without `_internal`), prunes unused Qt QML modules/DLLs, and must `--add-data` every non-Python file the app loads at runtime (currently `ui/video.qml`, `resources/icons/lucent.ico`).
- There is no test suite and no linter configured. Check code with `pyflakes` (not in requirements; install it to a temp `--target` dir rather than into the venv). Behaviour has been verified with throwaway scripts that drive a real `MainWindow` on screen; for video rendering, screen grabs of full-screen D3D output can be black — compare a `PrintWindow(..., PW_RENDERFULLCONTENT)` capture against `QVideoFrame.toImage()` instead.
- When testing, redirect state so the user's real data isn't touched: `QSettings.setPath(IniFormat, UserScope, tmp)` and set `core.history._DB_PATH` to a temp file before creating `MainWindow`.

## Architecture

`main.py` sets `QT_MEDIA_BACKEND=ffmpeg` **before any PyQt import**, sets the Windows AppUserModelID (taskbar icon), app icon, and opens files passed on the command line.

`ui/main_window.py` (`MainWindow`) is the orchestrator: it owns every component and wires all signals; components don't talk to each other directly.

- `core/player.py` — thin wrapper over `QMediaPlayer`. Video goes to the QML `VideoOutput` (`set_video_output`), not to a `QVideoWidget`.
- `ui/video_frame.py` + `ui/video.qml` — video is rendered by Qt Quick inside a `QQuickWidget` (transparent, `WA_AlwaysStackOnTop`). A `MultiEffect` mask gives antialiased rounded corners that follow the visible picture (`contentRect`); aspect modes (`ASPECT_MODES`) are QML properties. In full screen the mask is off (`set_rounded(False)`).
- `ui/glass.py` — `GlassBackground` (window wallpaper with three colour blobs; colours animate) and `GlassPanel` (base class of sidebar/controls/fullscreen overlay/settings). `core/ambient.py` samples video frames ~1/s and recolours the blobs.
- `ui/window_frame.py` — custom title bar. The window is created `FramelessWindowHint`, then the native frame styles are restored via `SetWindowLong` and `WM_NCCALCSIZE`/`WM_NCHITTEST` are handled in `MainWindow.nativeEvent`, so Snap, resize edges, shadow and rounded corners still work. Qt resets the style when leaving full screen — `restore_native_frame` is called again there.
- `ui/fullscreen_controls.py` — full-screen control panel is a separate translucent `Qt.Tool` top-level window (a child widget can't be shown over the video). Auto-hide polls `QCursor.pos()` on a timer instead of mouse events (layout changes generate fake moves).
- `ui/controls.py` — bottom bar plus shared building blocks (`SeekSlider`, `SkipButton`, `PlaylistToggleButton`, `control_styles()`, `format_time`). `SeekSlider` jumps on click and seeks once on release.
- `ui/sidebar.py` — playlist panel inside `SidebarDrawer`, which animates its own width so the panel slides out instead of squashing.
- `core/settings.py` — `Settings` wraps `QSettings` (INI at `%APPDATA%\Lucent\Lucent.ini`); every key and default lives in `DEFAULTS`, value types come from the defaults, and `changed(key, value)` is how `MainWindow` applies changes live. `ui/settings_dialog.py` writes straight to it.
- `core/history.py` — SQLite resume positions: `database/history.db` when run from source, `%APPDATA%\Lucent\history.db` when frozen.
- `core/folder_playlist.py` — "folder playlist" via `QFileSystemWatcher`; new files are added only after their size stops changing (downloads/copies in progress).
- `core/thumbnailer.py` — cover image from a hidden, silent second `QMediaPlayer` paused at ~10% of duration.
- `core/autostart.py` — HKCU `Run` key; command differs for source vs frozen exe.

## Pitfalls (each of these caused a real bug)

- **`nativeEvent` must return `(False, 0)` for unhandled messages, never `super().nativeEvent(...)`** — its `(False, None)` crashes the process (access violation) under PyQt6 + Python 3.14.
- Don't call `winId()` on a widget/window that isn't already native just to get a handle (it once blanked full-screen video). Same for setting DWM attributes on the full-screen overlay.
- `setPosition` is silently ignored while media is `LoadingMedia` (even if `isSeekable()` is already true): resume positions are applied from `mediaStatusChanged` once loaded (`_apply_pending_position`). Re-opening the same file emits no `durationChanged`, so `load_video` refreshes duration itself; it also sets `current_file_path`/pending position *before* `setSource`, because ffmpeg may report duration synchronously.
- Never keep `QVideoFrame` objects around — convert with `toImage()` inside the slot (stale frames crash after Qt Quick recreates graphics resources, e.g. on full-screen toggle).
- Frames can still arrive after `stop()`; guard frame-driven UI updates with `current_file_path`.
- Video sink signals (`videoSizeChanged`, …) are emitted from the render thread: connect them to a bound method of a `QObject` (queued into the GUI thread), never to a bare `lambda` — touching QML/widgets from there crashes.
- In `video.qml`, never use the `VideoOutput` item itself as `source` of more than one effect (the picture breaks); share one `ShaderEffectSource` (`fullPicture`) instead. A second `ShaderEffectSource` of the same item while another has `hideSource` renders black.
- `QMediaPlayer.metaData().keys()` crashes the process (access violation) — read only the keys you need with `.value(key)` (see `core/media_info.py`).
- Icon glyphs (Segoe Fluent Icons) must stay as `\uXXXX` escapes (`ui/styles.py` `Icons`, `ui/window_frame.py`). Some editing tools turn them into invisible private-use characters — check after editing.
- `QColor` doesn't parse CSS `rgba(...)` strings (the `GLASS_*` constants are for stylesheets); build `QColor` from components.
- Source files mix CRLF and LF line endings; preserve each file's existing endings when editing.

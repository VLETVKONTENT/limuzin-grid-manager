from __future__ import annotations

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

APP_NAME = "LIMUZIN GRID MANAGER"
APP_AUTHOR = "limuzin"
LOG_FILENAME = "runtime.log"
LOG_MAX_BYTES = 1_048_576
LOG_BACKUP_COUNT = 5
LOGGER_NAME = "limuzin_grid_manager"

_configured_log_path: Path | None = None
_previous_sys_excepthook = sys.excepthook
_previous_threading_excepthook = threading.excepthook
_previous_unraisablehook = getattr(sys, "unraisablehook", None)


def resolve_log_directory() -> Path:
    qt_directory = _qt_log_directory()
    if qt_directory is not None:
        return qt_directory

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_NAME / "logs"

    return _fallback_log_directory()


def configure_runtime_logging() -> Path:
    global _configured_log_path

    log_directory = _ensure_log_directory(resolve_log_directory())
    log_path = log_directory / LOG_FILENAME

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler_exists = False
    for handler in list(logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue
        if Path(handler.baseFilename) == log_path:
            handler_exists = True
            handler.setLevel(logging.INFO)
            continue
        logger.removeHandler(handler)
        handler.close()

    if not handler_exists:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    _configured_log_path = log_path
    logger.info("Runtime logging configured: %s", log_path)
    logger.info("Python: %s", sys.version.replace("\n", " "))
    return log_path


def install_exception_hooks() -> None:
    sys.excepthook = _sys_exception_hook
    threading.excepthook = _threading_exception_hook
    if hasattr(sys, "unraisablehook"):
        sys.unraisablehook = _unraisable_exception_hook


def get_runtime_logger(name: str | None = None) -> logging.Logger:
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def current_log_path() -> Path | None:
    return _configured_log_path


def diagnostics_hint() -> str:
    log_path = current_log_path()
    if log_path is None:
        return "Подробности записать в файл журнала не удалось."
    return f"Подробности записаны в журнал:\n{log_path}"


def build_diagnostics_message(message: str) -> str:
    hint = diagnostics_hint()
    return f"{message}\n\n{hint}"


def log_exception(
    context: str,
    *,
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None] | None = None,
    logger_name: str | None = None,
    level: int = logging.ERROR,
) -> None:
    logger = get_runtime_logger(logger_name)
    resolved_exc_info = exc_info if exc_info is not None else sys.exc_info()
    if resolved_exc_info[0] is None:
        logger.log(level, context)
        return
    logger.log(level, context, exc_info=resolved_exc_info)


def _qt_log_directory() -> Path | None:
    try:
        from PySide6.QtCore import QStandardPaths
    except Exception:
        return None

    app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not app_data:
        return None
    return Path(app_data) / "logs"


def _fallback_log_directory() -> Path:
    return Path.home() / f".{LOGGER_NAME}" / "logs"


def _ensure_log_directory(preferred_directory: Path) -> Path:
    try:
        preferred_directory.mkdir(parents=True, exist_ok=True)
        return preferred_directory
    except OSError:
        fallback_directory = _fallback_log_directory()
        fallback_directory.mkdir(parents=True, exist_ok=True)
        return fallback_directory


def _sys_exception_hook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        _previous_sys_excepthook(exc_type, exc_value, exc_traceback)
        return

    log_exception(
        "Unhandled exception on the main thread.",
        exc_info=(exc_type, exc_value, exc_traceback),
        logger_name="runtime",
        level=logging.CRITICAL,
    )
    _show_diagnostics_dialog(
        "Критическая ошибка",
        build_diagnostics_message(
            f"Приложение завершилось из-за непредвиденной ошибки:\n{_exception_text(exc_value)}"
        ),
    )


def _threading_exception_hook(args: threading.ExceptHookArgs) -> None:
    if issubclass(args.exc_type, KeyboardInterrupt):
        _previous_threading_excepthook(args)
        return

    thread_name = args.thread.name if args.thread is not None else "unknown"
    log_exception(
        f"Unhandled exception in Python thread '{thread_name}'.",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        logger_name="runtime",
        level=logging.CRITICAL,
    )
    _show_diagnostics_dialog(
        "Ошибка фонового потока",
        build_diagnostics_message(
            f"Фоновый поток завершился с ошибкой:\n{_exception_text(args.exc_value)}"
        ),
    )


def _unraisable_exception_hook(args: object) -> None:
    exc_type = getattr(args, "exc_type", None)
    exc_value = getattr(args, "exc_value", None)
    exc_traceback = getattr(args, "exc_traceback", None)
    err_msg = getattr(args, "err_msg", None)

    if exc_type is None or exc_value is None:
        return

    context = "Unraisable exception"
    if err_msg:
        context = f"{context}: {err_msg}"
    log_exception(
        context,
        exc_info=(exc_type, exc_value, exc_traceback),
        logger_name="runtime",
        level=logging.ERROR,
    )


def _show_diagnostics_dialog(title: str, message: str) -> None:
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
    except Exception:
        return

    app = QApplication.instance()
    if app is None:
        return

    QMessageBox.critical(None, title, message)


def _exception_text(exc: BaseException) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__

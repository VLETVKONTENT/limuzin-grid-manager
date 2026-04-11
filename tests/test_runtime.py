from __future__ import annotations

import sys
import threading

from PySide6.QtWidgets import QApplication

from limuzin_grid_manager.app import runtime


def _flush_runtime_handlers() -> None:
    logger = runtime.get_runtime_logger()
    for handler in logger.handlers:
        handler.flush()


def test_configure_runtime_logging_creates_log_file(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    log_directory = tmp_path / "runtime-logs"
    monkeypatch.setattr(runtime, "resolve_log_directory", lambda: log_directory)

    log_path = runtime.configure_runtime_logging()
    runtime.get_runtime_logger("tests.runtime").info("runtime smoke")
    _flush_runtime_handlers()

    assert log_path == log_directory / runtime.LOG_FILENAME
    assert log_path.exists()
    assert "runtime smoke" in log_path.read_text(encoding="utf-8")


def test_install_exception_hooks_logs_and_shows_diagnostics(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    log_directory = tmp_path / "runtime-logs"
    monkeypatch.setattr(runtime, "resolve_log_directory", lambda: log_directory)
    log_path = runtime.configure_runtime_logging()

    dialogs: list[tuple[str, str]] = []
    monkeypatch.setattr(runtime, "_show_diagnostics_dialog", lambda title, message: dialogs.append((title, message)))

    previous_sys_hook = sys.excepthook
    previous_thread_hook = threading.excepthook
    previous_unraisable_hook = getattr(sys, "unraisablehook", None)

    try:
        runtime.install_exception_hooks()

        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
    finally:
        sys.excepthook = previous_sys_hook
        threading.excepthook = previous_thread_hook
        if previous_unraisable_hook is not None:
            sys.unraisablehook = previous_unraisable_hook

    _flush_runtime_handlers()
    log_text = log_path.read_text(encoding="utf-8")

    assert dialogs
    assert dialogs[0][0] == "Критическая ошибка"
    assert "boom" in dialogs[0][1]
    assert str(log_path) in dialogs[0][1]
    assert "Unhandled exception on the main thread." in log_text
    assert "Traceback" in log_text
    assert "RuntimeError: boom" in log_text

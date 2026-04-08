from __future__ import annotations

from collections.abc import Callable


class ExportCancelled(RuntimeError):
    pass


class ProgressTracker:
    def __init__(
        self,
        progress: Callable[[int, int], None] | None,
        total: int,
        cancelled: Callable[[], bool] | None,
    ) -> None:
        self._progress = progress
        self._cancelled = cancelled
        self._total = max(1, int(total))
        self._done = 0
        self._emit_interval = max(1, self._total // 1000)
        self._next_emit = 0
        self.check_cancelled()
        self._emit(force=True)

    def step(self, amount: int = 1) -> None:
        self.check_cancelled()
        self._done = min(self._total, self._done + amount)
        self._emit(force=False)
        self.check_cancelled()

    def finish(self) -> None:
        self.check_cancelled()
        self._done = self._total
        self._emit(force=True)

    def check_cancelled(self) -> None:
        if self._cancelled is not None and self._cancelled():
            raise ExportCancelled("Экспорт отменен пользователем.")

    def _emit(self, force: bool) -> None:
        if self._progress is None:
            return
        if not force and self._done < self._next_emit and self._done < self._total:
            return
        self._progress(self._done, self._total)
        self._next_emit = self._done + self._emit_interval

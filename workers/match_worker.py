"""
match_worker — QThread-based worker that runs matcher.run() off the main thread.

Usage pattern (in the UI):
    self._thread = QThread()
    self._worker = MatchWorker(df_a, col_a, df_b, col_b)
    self._worker.moveToThread(self._thread)
    self._thread.started.connect(self._worker.run)
    self._worker.progress.connect(self._on_progress)
    self._worker.finished.connect(self._on_finished)
    self._worker.error.connect(self._on_error)
    self._worker.finished.connect(self._thread.quit)
    self._worker.finished.connect(self._worker.deleteLater)
    self._thread.finished.connect(self._thread.deleteLater)
    self._thread.start()

To cancel:
    self._worker.cancel()
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QObject, Signal

from core import matcher
from models.match_result import MatchResult


class MatchWorker(QObject):
    """Worker object moved to a QThread; runs matcher.run() and emits signals."""

    #: Emitted every _PROGRESS_INTERVAL rows: (current, total)
    progress = Signal(int, int)
    #: Emitted on successful completion with the full results list
    finished = Signal(list)
    #: Emitted if an unhandled exception occurs
    error = Signal(str)

    def __init__(
        self,
        df_a: pd.DataFrame,
        col_a: str,
        df_b: pd.DataFrame,
        col_b: str,
        threshold: float = 0.60,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._df_a = df_a
        self._col_a = col_a
        self._df_b = df_b
        self._col_b = col_b
        self._threshold = threshold
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation; the run loop will exit at the next checkpoint."""
        self._cancelled = True

    def run(self) -> None:
        """Called by QThread.started signal; performs matching off the main thread."""
        try:
            results = matcher.run(
                df_a=self._df_a,
                col_a=self._col_a,
                df_b=self._df_b,
                col_b=self._col_b,
                threshold=self._threshold,
                progress_cb=lambda cur, tot: self.progress.emit(cur, tot),
                interrupted_cb=lambda: self._cancelled,
            )
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))

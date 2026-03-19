"""Reusable QThread workers for background tasks (signal-safe UI updates)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class WorkerThread(QThread):
    """
    Runs ``run_fn()`` in a background thread. Override or pass ``run_fn`` in a subclass.

    Emits:
        progress: arbitrary progress payload (dict or tuple)
        log_line: (level: str, message: str)
        error: str
        finished_ok: bool — True if run_fn completed without exception
        result: Any — optional return value from run_fn
    """

    progress = pyqtSignal(object)
    log_line = pyqtSignal(str, str)
    error = pyqtSignal(str)
    finished_ok = pyqtSignal(bool)
    result = pyqtSignal(object)

    def __init__(
        self,
        run_fn: Optional[Callable[[], Any]] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._run_fn = run_fn

    def run(self) -> None:
        if self._run_fn is None:
            self.finished_ok.emit(True)
            return
        try:
            out = self._run_fn()
            self.result.emit(out)
            self.finished_ok.emit(True)
        except Exception as e:
            self.error.emit(str(e))
            self.finished_ok.emit(False)


class RunnableWorker(QThread):
    """Runs a callable with args/kwargs; emits result or error string."""

    finished_ok = pyqtSignal(bool)
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        fn: Callable[..., Any],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs or {}

    def run(self) -> None:
        try:
            self.result.emit(self._fn(*self._args, **self._kwargs))
            self.finished_ok.emit(True)
        except Exception as e:
            self.error.emit(str(e))
            self.finished_ok.emit(False)

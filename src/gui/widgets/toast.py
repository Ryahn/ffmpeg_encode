"""In-app toasts: QFrame overlay bottom-right of main window (thread-safe via signals)."""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QMainWindow, QVBoxLayout, QWidget

from ..theme import (
    APP_LOG_INFO,
    APP_LOG_SUCCESS,
    APP_LOG_WARN,
    APP_STATUS_ERROR,
)


class _ToastBridge(QObject):
    request_show = pyqtSignal(str, str, int)


def _toast_colors(message_type: str) -> Tuple[str, str]:
    colors = {
        "info": (APP_LOG_INFO, "#164a7a"),
        "success": (APP_LOG_SUCCESS, "#166534"),
        "warning": (APP_LOG_WARN, "#a16207"),
        "error": (APP_STATUS_ERROR, "#991b1b"),
    }
    return colors.get(message_type, colors["info"])


class ToastManager:
    """
    Queue toasts as QFrame children of the main window's central widget,
    stacked bottom-right. ``show()`` is safe from any thread.
    """

    def __init__(self, main_window: QMainWindow):
        self._main = main_window
        self._bridge = _ToastBridge(main_window)
        self._bridge.request_show.connect(self._show_impl)
        self._queue: List[Tuple[str, str, int]] = []
        self._lock = threading.Lock()
        self._current_timer: Optional[QTimer] = None

    def show(
        self,
        message: str,
        message_type: str = "info",
        duration: int = 3,
    ) -> None:
        self._bridge.request_show.emit(message, message_type, duration)

    def _show_impl(self, message: str, message_type: str, duration: int) -> None:
        with self._lock:
            self._queue.append((message, message_type, duration))
            if len(self._queue) == 1:
                self._display_next()

    def _display_next(self) -> None:
        with self._lock:
            if not self._queue:
                return
            message, message_type, duration = self._queue[0]

        central = self._main.centralWidget()
        if central is None:
            with self._lock:
                self._queue.pop(0)
            self._schedule_next_after_pop()
            return

        fg, border = _toast_colors(message_type)
        frame = QFrame(central)
        frame.setObjectName("ToastFrame")
        frame.setStyleSheet(
            f"QFrame#ToastFrame {{ background-color: {fg}; border: 2px solid {border}; "
            f"border-radius: 8px; padding: 8px; }}"
        )
        layout = QVBoxLayout(frame)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: white; font-size: 12px;")
        lbl.setMaximumWidth(380)
        layout.addWidget(lbl)

        frame.adjustSize()
        frame.raise_()
        self._position_toast(frame, central)

        if self._current_timer:
            self._current_timer.stop()
        self._current_timer = QTimer(self._main)
        self._current_timer.setSingleShot(True)
        self._current_timer.timeout.connect(lambda: self._dismiss_current(frame))
        self._current_timer.start(duration * 1000)

    def _position_toast(self, frame: QFrame, central: QWidget) -> None:
        frame.show()
        m = self._main.geometry()
        c = central.geometry()
        margin = 20
        x = c.width() - frame.width() - margin
        y = c.height() - frame.height() - margin
        if x < 0:
            x = 10
        if y < 0:
            y = 10
        frame.move(x, y)

    def _dismiss_current(self, frame: QFrame) -> None:
        try:
            frame.deleteLater()
        except Exception:
            pass
        with self._lock:
            if self._queue:
                self._queue.pop(0)
        self._schedule_next_after_pop()

    def _schedule_next_after_pop(self) -> None:
        with self._lock:
            has_next = bool(self._queue)
        if has_next:
            QTimer.singleShot(100, self._display_next)

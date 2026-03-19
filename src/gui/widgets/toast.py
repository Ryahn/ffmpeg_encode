"""In-app toasts: QFrame overlay bottom-right of main window (thread-safe via signals)."""

from __future__ import annotations

import threading
from typing import List, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class _ToastBridge(QObject):
    request_show = pyqtSignal(str, str, int)


def _toast_panel_colors(message_type: str) -> Tuple[str, str]:
    """Solid fill + accent border (dark enough for white text)."""
    colors = {
        "info": ("#1a4a7a", "#5ba4f5"),
        "success": ("#14532d", "#4ade80"),
        "warning": ("#5c420f", "#f0a500"),
        "error": ("#5c1a1a", "#ff5f57"),
    }
    return colors.get(message_type, colors["info"])

def _apply_toast_text_outline(lbl: QLabel) -> None:
    """Approximate 1-2px black text outline using a tight shadow effect."""
    effect = QGraphicsDropShadowEffect(lbl)
    effect.setBlurRadius(2)
    effect.setColor(QColor(0, 0, 0, 255))
    effect.setOffset(0, 0)
    lbl.setGraphicsEffect(effect)

class ToastManager:
    """
    Queue toasts as QFrame children of the main window's central widget,
    stacked bottom-right. ``show()`` is safe from any thread.
    """

    def __init__(self, main_window: QMainWindow):
        self._main = main_window
        self._bridge = _ToastBridge(main_window)
        self._bridge.request_show.connect(
            self._show_impl,
            Qt.ConnectionType.QueuedConnection,
        )
        self._queue: List[Tuple[str, str, int]] = []
        self._lock = threading.Lock()
        self._current_timer: Optional[QTimer] = None
        self._active_frame: Optional[QFrame] = None

    def show(
        self,
        message: str,
        message_type: str = "info",
        duration: int = 3,
    ) -> None:
        self._bridge.request_show.emit(message, message_type, duration)

    def _show_impl(self, message: str, message_type: str, duration: int) -> None:
        # Must not call _display_next while holding _lock: _display_next acquires the same Lock
        # (non-reentrant) and would deadlock the GUI thread.
        start_now = False
        with self._lock:
            self._queue.append((message, message_type, duration))
            if len(self._queue) == 1:
                start_now = True
        if start_now:
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

        bg, border = _toast_panel_colors(message_type)
        frame = QFrame(central)
        frame.setObjectName("ToastFrame")
        frame.setStyleSheet(
            f"QFrame#ToastFrame {{ background-color: {bg}; border: 2px solid {border}; "
            f"border-radius: 8px; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(0)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(380)
        lbl.setStyleSheet(
            "QLabel { background-color: transparent; color: #ffffff; border: none; "
            "padding: 0px; margin: 0px; font-size: 13px; font-weight: 600; }"
        )
        _apply_toast_text_outline(lbl)
        layout.addWidget(lbl)

        frame.adjustSize()
        frame.raise_()
        self._active_frame = frame
        self._position_toast(frame, central)

        if self._current_timer:
            self._current_timer.stop()
        self._current_timer = QTimer(self._main)
        self._current_timer.setSingleShot(True)
        self._current_timer.timeout.connect(lambda: self._dismiss_current(frame))
        self._current_timer.start(duration * 1000)

    def _position_toast(self, frame: QFrame, central: QWidget) -> None:
        frame.show()
        c = central.geometry()
        margin = 20
        x = c.width() - frame.width() - margin
        y = c.height() - frame.height() - margin
        if x < 0:
            x = 10
        if y < 0:
            y = 10
        frame.move(x, y)

    def reposition_active_toast(self) -> None:
        """Keep the visible toast anchored after main-window resize."""
        frame = self._active_frame
        central = self._main.centralWidget()
        if frame is None or central is None:
            return
        try:
            self._position_toast(frame, central)
        except Exception:
            pass

    def _dismiss_current(self, frame: QFrame) -> None:
        if self._active_frame is frame:
            self._active_frame = None
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

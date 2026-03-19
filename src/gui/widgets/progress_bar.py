"""Progress bar + status label (Qt)."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout


class ProgressDisplay(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._status = QLabel("Ready", self)
        lay = QVBoxLayout(self)
        lay.addWidget(self._bar)
        lay.addWidget(self._status)

    def set_progress(self, percent: float) -> None:
        self._bar.setValue(int(max(0, min(100, percent))))

    def set_status(self, status: str) -> None:
        self._status.setText(status)

    def get_status(self) -> str:
        return self._status.text()

    def reset(self) -> None:
        self._bar.setValue(0)
        self._status.setText("Ready")

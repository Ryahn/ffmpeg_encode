"""Lifetime encoding statistics tab (PyQt6)."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from storage import get_lifetime_totals, reset_lifetime_stats
from utils.byte_format import format_bytes


def format_duration(total_seconds: float) -> str:
    s = int(round(max(0.0, total_seconds)))
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


class StatsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll.setWidget(inner)
        v = QVBoxLayout(inner)

        v.addWidget(QLabel("<h2>Encoding statistics</h2>"))
        v.addWidget(
            QLabel(
                "Totals for successful encodes only (HandBrake and FFmpeg). "
                "Dry runs are not counted. Sizes are total output file bytes."
            )
        )
        v.addWidget(QLabel(""))  # spacer

        self._files_label = QLabel()
        self._bytes_label = QLabel()
        self._time_label = QLabel()
        self._updated_label = QLabel()
        for lb in (self._files_label, self._bytes_label, self._time_label, self._updated_label):
            lb.setWordWrap(True)
            v.addWidget(lb)

        btn_row = QWidget()
        h = QHBoxLayout(btn_row)
        h.setContentsMargins(0, 0, 0, 0)
        ref = QPushButton("Refresh")
        ref.clicked.connect(self.reload_from_db)
        h.addWidget(ref)
        rst = QPushButton("Reset statistics…")
        rst.clicked.connect(self._confirm_reset)
        h.addWidget(rst)
        h.addStretch()
        v.addWidget(btn_row)
        v.addStretch()

        out = QVBoxLayout(self)
        out.addWidget(scroll)

    def reload_from_db(self) -> None:
        try:
            t = get_lifetime_totals()
        except Exception as e:
            self._files_label.setText(f"<b>Files encoded:</b> (error: {e})")
            self._bytes_label.setText("")
            self._time_label.setText("")
            self._updated_label.setText("")
            return

        self._files_label.setText(f"<b>Files encoded:</b> {t.files_encoded_success:,}")
        self._bytes_label.setText(
            f"<b>Total output size:</b> {format_bytes(t.total_output_bytes)} "
            f"({t.total_output_bytes:,} bytes)"
        )
        self._time_label.setText(
            f"<b>Total encoding time:</b> {format_duration(t.total_encode_seconds)} "
            f"({t.total_encode_seconds:,.1f} s)"
        )
        if t.updated_at:
            self._updated_label.setText(
                f"<b>Last updated:</b> {t.updated_at.isoformat()}"
            )
        else:
            self._updated_label.setText("<b>Last updated:</b> —")

    def _confirm_reset(self) -> None:
        r = QMessageBox.question(
            self,
            "Reset statistics",
            "Clear all lifetime encoding statistics? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            reset_lifetime_stats()
            self.reload_from_db()
        except Exception as e:
            QMessageBox.warning(self, "Reset failed", str(e))

"""Log viewer using QPlainTextEdit."""

from __future__ import annotations

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout

MAX_LINES = 5000


class LogViewer(QWidget):
    """Append-only log view with optional copy."""

    def __init__(self, parent: QWidget | None = None, height: int = 200):
        super().__init__(parent)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setFixedHeight(height)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._text)

    def add_log(self, level: str, message: str) -> None:
        line = f"[{level}] {message}\n"
        self._text.moveCursor(QTextCursor.MoveOperation.End)
        self._text.insertPlainText(line)
        doc = self._text.document()
        if doc.blockCount() > MAX_LINES:
            cursor = self._text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(doc.blockCount() - MAX_LINES):
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()
        self._text.moveCursor(QTextCursor.MoveOperation.End)

    def clear(self) -> None:
        self._text.clear()

    def copy_to_clipboard(self) -> None:
        self._text.selectAll()
        self._text.copy()
        cur = self._text.textCursor()
        cur.clearSelection()
        self._text.setTextCursor(cur)

    def plain_text(self) -> str:
        return self._text.toPlainText()

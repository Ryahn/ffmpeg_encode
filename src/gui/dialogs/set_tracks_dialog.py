"""Modal dialog to pick audio and subtitle tracks (PyQt6)."""

from __future__ import annotations

from typing import List, Optional, Tuple

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


def show_set_tracks_dialog(
    parent: QWidget,
    audio_options: List[Tuple[str, Optional[int]]],
    subtitle_options: List[Tuple[str, Optional[int]]],
    multi_file_count: int,
) -> Optional[Tuple[Optional[int], Optional[int]]]:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Set tracks")
    dialog.setModal(True)
    layout = QVBoxLayout(dialog)

    if multi_file_count > 1:
        layout.addWidget(
            QLabel(
                f"Same track numbers will be applied to {multi_file_count} selected files. "
                "Other files may have different track layouts."
            )
        )

    audio_labels = [o[0] for o in audio_options]
    audio_values = [o[1] for o in audio_options]
    sub_labels = [o[0] for o in subtitle_options]
    sub_values = [o[1] for o in subtitle_options]

    form = QFormLayout()
    audio_combo = QComboBox()
    audio_combo.addItems(audio_labels)
    sub_combo = QComboBox()
    sub_combo.addItems(sub_labels)
    form.addRow("Audio track:", audio_combo)
    form.addRow("Subtitle track (burn-in):", sub_combo)
    layout.addLayout(form)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    ai = audio_combo.currentIndex()
    si = sub_combo.currentIndex()
    return (audio_values[ai], sub_values[si])

"""Modal dialog to pick audio and subtitle tracks (or none)."""

from typing import List, Optional, Tuple

import customtkinter as ctk


def show_set_tracks_dialog(
    parent,
    audio_options: List[Tuple[str, Optional[int]]],
    subtitle_options: List[Tuple[str, Optional[int]]],
    multi_file_count: int,
) -> Optional[Tuple[Optional[int], Optional[int]]]:
    """
    audio_options: (label, 1-based HandBrake audio track id or None).
    subtitle_options: (label, 0-based subtitle stream id or None).
    Returns (audio_track, subtitle_track) or None if cancelled.
    """
    result_holder: list = [None]

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Set tracks")
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()
    dialog.geometry("520x280")
    dialog.resizable(False, False)

    pad = {"padx": 12, "pady": 6}

    if multi_file_count > 1:
        ctk.CTkLabel(
            dialog,
            text=(
                f"Same track numbers will be applied to {multi_file_count} selected files. "
                "Other files may have different track layouts."
            ),
            wraplength=480,
            justify="left",
        ).pack(fill="x", **pad)

    ctk.CTkLabel(dialog, text="Audio track:").pack(anchor="w", padx=12, pady=(12, 0))
    audio_labels = [o[0] for o in audio_options]
    audio_values = [o[1] for o in audio_options]
    audio_var = ctk.StringVar(value=audio_labels[0])
    ctk.CTkOptionMenu(dialog, variable=audio_var, values=audio_labels, width=480).pack(
        fill="x", **pad
    )

    ctk.CTkLabel(dialog, text="Subtitle track (burn-in):").pack(anchor="w", padx=12, pady=(8, 0))
    sub_labels = [o[0] for o in subtitle_options]
    sub_values = [o[1] for o in subtitle_options]
    sub_var = ctk.StringVar(value=sub_labels[0])
    ctk.CTkOptionMenu(dialog, variable=sub_var, values=sub_labels, width=480).pack(
        fill="x", **pad
    )

    def on_ok():
        ai = audio_labels.index(audio_var.get())
        si = sub_labels.index(sub_var.get())
        result_holder[0] = (audio_values[ai], sub_values[si])
        dialog.destroy()

    def on_cancel():
        result_holder[0] = None
        dialog.destroy()

    btn_row = ctk.CTkFrame(dialog)
    btn_row.pack(fill="x", padx=12, pady=16)
    ctk.CTkButton(btn_row, text="Cancel", width=100, command=on_cancel).pack(
        side="right", padx=4
    )
    ctk.CTkButton(btn_row, text="OK", width=100, command=on_ok).pack(side="right", padx=4)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    parent.winfo_toplevel().wait_window(dialog)
    return result_holder[0]

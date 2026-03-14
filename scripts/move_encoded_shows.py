"""
Standalone GUI to scan a folder of shows (Show/Season 1, etc.), detect user-specified
video extensions (mp4, m4v, mkv, avi, etc.), and move each show folder that contains
them into a new folder called Encoded.

Run from project root (with venv active):
  python scripts/move_encoded_shows.py
"""

import shutil
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox
except ImportError:
    print("Install customtkinter: pip install customtkinter")
    sys.exit(1)

DEFAULT_EXTENSIONS = "mp4, m4v, mkv, avi"
ENCODED_FOLDER_NAME = "Encoded"


def parse_extensions(raw: str) -> set[str]:
    """Parse comma-separated extensions into a set of lowercase strings with leading dot."""
    result = set()
    for part in raw.replace(",", " ").split():
        ext = part.strip().lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        if ext:
            result.add(ext)
    return result


def show_contains_encoded_files(show_path: Path, extensions: set[str]) -> bool:
    """Return True if the show folder (or any subfolder) contains files with any of the given extensions."""
    if not show_path.is_dir() or not extensions:
        return False
    for ext in extensions:
        if next(show_path.rglob(f"*{ext}"), None) is not None:
            return True
        if ext != ext.upper() and next(show_path.rglob(f"*{ext.upper()}"), None) is not None:
            return True
    return False


def scan_and_move(
    root_path: Path, extensions: set[str], log_callback
) -> tuple[int, int]:
    """
    Scan root_path for show folders (direct subdirs). For each that contains
    any file with the given extensions, move the whole show folder into
    root_path/Encoded/ShowName. Returns (moved_count, skipped_count).
    """
    if not root_path.is_dir():
        log_callback(f"Not a directory: {root_path}\n")
        return 0, 0
    if not extensions:
        log_callback("No extensions specified.\n")
        return 0, 0

    encoded_base = root_path / ENCODED_FOLDER_NAME
    encoded_base.mkdir(parents=True, exist_ok=True)
    moved = 0
    skipped = 0
    ext_label = ", ".join(sorted(extensions))

    for item in sorted(root_path.iterdir()):
        if not item.is_dir() or item.name == ENCODED_FOLDER_NAME:
            continue
        if show_contains_encoded_files(item, extensions):
            dest = encoded_base / item.name
            if dest.exists():
                log_callback(f"Skip (destination exists): {item.name}\n")
                skipped += 1
                continue
            try:
                shutil.move(str(item), str(dest))
                log_callback(f"Moved: {item.name} -> {ENCODED_FOLDER_NAME}/\n")
                moved += 1
            except OSError as e:
                log_callback(f"Error moving {item.name}: {e}\n")
                skipped += 1
        else:
            log_callback(f"No {ext_label}: {item.name}\n")
            skipped += 1

    return moved, skipped


class MoveEncodedShowsScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Move encoded shows to Encoded folder")
        self.geometry("700x500")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root_path: Path | None = None

        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        path_frame = ctk.CTkFrame(main)
        path_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(path_frame, text="Shows folder:").pack(side="left", padx=5, pady=5)
        self.path_label = ctk.CTkLabel(path_frame, text="Not selected", anchor="w")
        self.path_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ctk.CTkButton(path_frame, text="Browse", command=self._browse, width=100).pack(
            side="right", padx=5, pady=5
        )

        ext_frame = ctk.CTkFrame(main)
        ext_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(ext_frame, text="Extensions:").pack(side="left", padx=5, pady=5)
        self.extensions_entry = ctk.CTkEntry(
            ext_frame,
            placeholder_text="e.g. mp4, m4v, mkv, avi",
            width=320,
        )
        self.extensions_entry.pack(side="left", padx=5, pady=5)
        self.extensions_entry.insert(0, DEFAULT_EXTENSIONS)
        ctk.CTkLabel(
            ext_frame,
            text="(comma-separated, with or without dot)",
            text_color="gray",
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            main,
            text="Scan and move shows with matching extensions into Encoded",
            command=self._scan_and_move,
            height=36,
        ).pack(fill="x", pady=(0, 10))

        self.log = ctk.CTkTextbox(main, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def _browse(self):
        path = filedialog.askdirectory(title="Select folder containing show folders")
        if path:
            self.root_path = Path(path)
            self.path_label.configure(text=str(self.root_path))

    def _log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _scan_and_move(self):
        if self.root_path is None:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return
        raw = self.extensions_entry.get().strip()
        extensions = parse_extensions(raw)
        if not extensions:
            messagebox.showwarning(
                "No extensions",
                "Enter at least one extension (e.g. mp4, m4v, mkv, avi).",
            )
            return
        self._log("\n--- Scan ---\n")
        moved, skipped = scan_and_move(self.root_path, extensions, self._log)
        self._log(f"\nDone: {moved} moved, {skipped} skipped.\n")


def main():
    app = MoveEncodedShowsScreen()
    app.mainloop()


if __name__ == "__main__":
    main()

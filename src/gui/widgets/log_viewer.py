"""Log viewer widget"""

import customtkinter as ctk
from typing import Optional

MAX_LINES = 5000


class LogViewer(ctk.CTkTextbox):
    """Real-time log viewer with color coding"""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(state="disabled")

    def add_log(self, level: str, message: str):
        """Add a log entry"""
        self.configure(state="normal")

        formatted = f"[{level}] {message}\n"
        self.insert("end", formatted)

        try:
            end_index = self.index("end-1c")
            line_num = int(end_index.split(".")[0])
            if line_num > MAX_LINES:
                drop_count = line_num - MAX_LINES
                self.delete("1.0", f"{drop_count + 1}.0")
        except (ValueError, IndexError):
            pass

        self.see("end")
        self.configure(state="disabled")
    
    def clear(self):
        """Clear all logs"""
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
    
    def export_logs(self, file_path: str):
        """Export logs to file"""
        try:
            content = self.get("1.0", "end-1c")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception:
            return False

    def copy_to_clipboard(self):
        """Copy log content to clipboard so user can paste (e.g. Ctrl+V)."""
        try:
            content = self.get("1.0", "end-1c")
            if content.strip():
                root = self.winfo_toplevel()
                root.clipboard_clear()
                root.clipboard_append(content)
        except Exception:
            pass


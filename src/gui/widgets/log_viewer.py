"""Log viewer widget"""

import customtkinter as ctk
from typing import Optional


class LogViewer(ctk.CTkTextbox):
    """Real-time log viewer with color coding"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(state="disabled")
        # Note: CTkTextbox doesn't support tag_config like tkinter Text
        # We'll use plain text for now, color coding can be added later
    
    def add_log(self, level: str, message: str):
        """Add a log entry"""
        self.configure(state="normal")
        
        # Format message
        formatted = f"[{level}] {message}\n"
        
        # Insert text
        self.insert("end", formatted)
        
        # Auto-scroll to bottom
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


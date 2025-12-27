"""Progress bar widget"""

import customtkinter as ctk
from typing import Optional


class ProgressDisplay(ctk.CTkFrame):
    """Progress display with bar and text"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.progress_var = ctk.DoubleVar(value=0.0)
        self.status_var = ctk.StringVar(value="Ready")
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            variable=self.progress_var,
            width=400
        )
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=5)
    
    def set_progress(self, percent: float):
        """Set progress percentage (0-100)"""
        self.progress_var.set(percent / 100.0)
    
    def set_status(self, status: str):
        """Set status text"""
        self.status_var.set(status)
    
    def reset(self):
        """Reset progress display"""
        self.progress_var.set(0.0)
        self.status_var.set("Ready")


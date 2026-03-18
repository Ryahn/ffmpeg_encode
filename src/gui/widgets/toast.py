"""In-app toast notifications for non-intrusive user feedback"""

import customtkinter as ctk
import threading
import time
from typing import Callable, Optional


class Toast(ctk.CTkToplevel):
    """
    Non-intrusive in-app toast notification that appears temporarily.
    Supports success, warning, and error message types.
    """

    def __init__(
        self,
        master,
        message: str,
        message_type: str = "info",
        duration: int = 3,
        width: int = 400,
        corner_radius: int = 8
    ):
        """
        Create a toast notification.

        Args:
            master: Parent widget
            message: Message text to display
            message_type: One of "info" (blue), "success" (green), "warning" (yellow), "error" (red)
            duration: How long to display in seconds (default 3)
            width: Width of toast in pixels
            corner_radius: Rounded corner radius
        """
        super().__init__(master)

        self.message = message
        self.message_type = message_type
        self.duration = duration

        # Configure window
        self.wm_overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-alpha", 0.95)

        # Set size
        self.geometry(f"{width}x120")
        self.resizable(False, False)

        # Color scheme based on message type
        colors = {
            "info": ("#3B82F6", "#1E40AF"),      # Blue
            "success": ("#10B981", "#047857"),   # Green
            "warning": ("#F59E0B", "#D97706"),   # Orange
            "error": ("#EF4444", "#DC2626"),     # Red
        }
        fg_color, border_color = colors.get(message_type, colors["info"])

        # Main frame
        main_frame = ctk.CTkFrame(
            self,
            fg_color=fg_color,
            corner_radius=corner_radius
        )
        main_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Text label
        self.text_label = ctk.CTkLabel(
            main_frame,
            text=message,
            text_color="white",
            font=ctk.CTkFont(size=12),
            wraplength=380,
            justify="left"
        )
        self.text_label.pack(fill="both", expand=True, padx=12, pady=12)

        # Position toast in bottom-right corner
        self._position_toast()

        # Auto-hide after duration
        self.hide_timer = threading.Timer(duration, self._fade_out)
        self.hide_timer.daemon = True
        self.hide_timer.start()

    def _position_toast(self):
        """Position toast in bottom-right corner of parent window"""
        self.update_idletasks()

        # Get parent window position and size
        parent = self.master
        if parent:
            parent.update_idletasks()
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            # Position in bottom-right with padding
            toast_width = self.winfo_width()
            toast_height = self.winfo_height()
            x = parent_x + parent_width - toast_width - 20
            y = parent_y + parent_height - toast_height - 20

            self.geometry(f"+{x}+{y}")
        else:
            # Fallback to screen bottom-right
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = screen_width - width - 20
            y = screen_height - height - 20
            self.geometry(f"+{x}+{y}")

    def _fade_out(self):
        """Fade out and close the toast"""
        try:
            self.destroy()
        except Exception:
            pass


class ToastManager:
    """Manager for displaying multiple toasts in sequence"""

    def __init__(self, master):
        """
        Create a toast manager.

        Args:
            master: Parent widget (typically the main window)
        """
        self.master = master
        self.toast_queue = []
        self.current_toast: Optional[Toast] = None
        self.queue_lock = threading.Lock()

    def show(
        self,
        message: str,
        message_type: str = "info",
        duration: int = 3
    ) -> None:
        """
        Show a toast notification.

        Args:
            message: Message text
            message_type: One of "info", "success", "warning", "error"
            duration: Display duration in seconds
        """
        with self.queue_lock:
            self.toast_queue.append((message, message_type, duration))

        if not self.current_toast:
            self._show_next()

    def show_sync(
        self,
        message: str,
        message_type: str = "info",
        duration: int = 3
    ) -> None:
        """
        Show a toast notification synchronously (wait for display completion).

        Args:
            message: Message text
            message_type: One of "info", "success", "warning", "error"
            duration: Display duration in seconds
        """
        try:
            self.current_toast = Toast(
                self.master,
                message,
                message_type=message_type,
                duration=duration
            )

            # Wait for duration before returning
            time.sleep(duration + 0.5)
        except Exception as e:
            import logging
            logging.debug(f"Toast display error: {e}")

    def _show_next(self) -> None:
        """Show next toast in queue"""
        with self.queue_lock:
            if not self.toast_queue:
                self.current_toast = None
                return

            message, message_type, duration = self.toast_queue.pop(0)

        try:
            self.current_toast = Toast(
                self.master,
                message,
                message_type=message_type,
                duration=duration
            )

            # Schedule next toast after current one finishes
            delay_ms = (duration + 0.5) * 1000
            self.master.after(int(delay_ms), self._show_next)
        except Exception as e:
            import logging
            logging.debug(f"Toast display error: {e}")
            self.current_toast = None
            self._show_next()

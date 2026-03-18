"""In-app toast notifications for batch encoding completion"""

from typing import Optional, Callable


class BatchNotification:
    """Send batch completion notifications via in-app toasts"""

    _toast_manager: Optional[object] = None

    @classmethod
    def set_toast_manager(cls, manager: object) -> None:
        """
        Set the toast manager for displaying notifications.

        Args:
            manager: ToastManager instance from gui.widgets.toast
        """
        cls._toast_manager = manager

    @staticmethod
    def send_completion(
        completed: int,
        skipped: int,
        errors: int,
        total: int,
        elapsed_time: str
    ) -> None:
        """
        Send a batch completion notification via in-app toast.

        Args:
            completed: Number of files successfully encoded
            skipped: Number of files skipped
            errors: Number of files that failed
            total: Total files in batch
            elapsed_time: Formatted elapsed time (e.g., "2h 15m 30s")
        """
        if BatchNotification._toast_manager is None:
            return

        message = BatchNotification._format_message(
            completed, skipped, errors, total, elapsed_time
        )

        # Determine toast type based on results
        if errors > 0:
            toast_type = "warning"
        elif skipped > 0 and completed > 0:
            toast_type = "info"
        else:
            toast_type = "success"

        BatchNotification._toast_manager.show(
            message,
            message_type=toast_type,
            duration=5
        )

    @staticmethod
    def _format_message(
        completed: int, skipped: int, errors: int, total: int, elapsed_time: str
    ) -> str:
        """Format notification message with batch statistics"""
        status_line = f"✓ Batch Complete: {completed}/{total} files encoded"

        details = []
        if skipped > 0:
            details.append(f"{skipped} skipped")
        if errors > 0:
            details.append(f"{errors} errors")

        if details:
            status_line += f"\n({', '.join(details)})"

        status_line += f"\n⏱ Time: {elapsed_time}"

        return status_line

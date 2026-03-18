"""Batch statistics tracking and reporting"""

import time
from typing import Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class FileResult:
    """Statistics for a single encoded file"""
    filename: str
    elapsed_time: float
    input_size: int
    output_size: int
    success: bool
    error_msg: Optional[str] = None


class BatchStats:
    """Track and calculate batch encoding statistics"""

    def __init__(self):
        """Initialize batch statistics tracker"""
        self.start_time: float = time.time()
        self.files: List[FileResult] = []
        self.completed_count: int = 0
        self.skipped_count: int = 0
        self.error_count: int = 0

    def add_file_result(
        self,
        filename: str,
        elapsed: float,
        input_size: int,
        output_size: int,
        success: bool,
        error_msg: Optional[str] = None,
        skipped: bool = False
    ) -> None:
        """
        Record the result of encoding a file.

        Args:
            filename: Name of the file
            elapsed: Time taken to encode in seconds
            input_size: Input file size in bytes
            output_size: Output file size in bytes
            success: Whether encoding succeeded
            error_msg: Error message if failed
            skipped: Whether file was skipped
        """
        result = FileResult(
            filename=filename,
            elapsed_time=elapsed,
            input_size=input_size,
            output_size=output_size,
            success=success,
            error_msg=error_msg
        )
        self.files.append(result)

        if skipped:
            self.skipped_count += 1
        elif success:
            self.completed_count += 1
        else:
            self.error_count += 1

    def get_elapsed_time_str(self) -> str:
        """Get total elapsed time formatted as human-readable string"""
        elapsed_seconds = int(time.time() - self.start_time)
        hours = elapsed_seconds // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_total_files(self) -> int:
        """Get total number of files processed"""
        return self.completed_count + self.skipped_count + self.error_count

    def get_compression_ratio(self) -> float:
        """
        Get overall compression ratio (input size / output size).
        Returns 0 if no output generated.
        """
        total_input = sum(f.input_size for f in self.files if f.success)
        total_output = sum(f.output_size for f in self.files if f.success)

        if total_input == 0:
            return 0.0

        return total_input / total_output if total_output > 0 else 0.0

    def get_total_input_size(self) -> int:
        """Get total input size in bytes for successful encodes"""
        return sum(f.input_size for f in self.files if f.success)

    def get_total_output_size(self) -> int:
        """Get total output size in bytes"""
        return sum(f.output_size for f in self.files if f.success)

    def format_size(self, size_bytes: int) -> str:
        """Format byte size to human-readable string"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

    def format_compression_percent(self) -> str:
        """Get compression percentage as formatted string"""
        ratio = self.get_compression_ratio()
        if ratio == 0:
            return "0%"

        percent = (1 - 1/ratio) * 100
        return f"{percent:.1f}%"

    def summary_text(self) -> str:
        """
        Generate formatted summary text for display.

        Returns:
            Multi-line summary string
        """
        total = self.get_total_files()
        elapsed = self.get_elapsed_time_str()
        input_size = self.format_size(self.get_total_input_size())
        output_size = self.format_size(self.get_total_output_size())
        compression = self.format_compression_percent()

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "Batch Encoding Complete",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"Files: {self.completed_count} completed",
        ]

        if self.skipped_count > 0:
            lines.append(f"        {self.skipped_count} skipped")
        if self.error_count > 0:
            lines.append(f"        {self.error_count} errors")

        lines.append(f"Total:  {total} files")
        lines.extend([
            "",
            f"Time:         {elapsed}",
            f"Input:        {input_size}",
            f"Output:       {output_size}",
            f"Compression:  {compression}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ])

        return "\n".join(lines)

    def calculate_batch_eta(
        self,
        total_files: int,
        completed_count: int
    ) -> Optional[str]:
        """
        Calculate estimated time remaining for batch.

        Returns None if insufficient data (< 3 files completed).
        Returns formatted ETA string like "1h 30m" if available.

        Args:
            total_files: Total files in batch
            completed_count: Number of files completed so far
        """
        if completed_count < 3 or not self.files:
            return None

        # Calculate average time per file
        total_time = sum(f.elapsed_time for f in self.files[:completed_count])
        avg_time = total_time / completed_count

        # Calculate remaining files and time
        remaining_files = total_files - completed_count
        if remaining_files <= 0:
            return None

        remaining_seconds = int(avg_time * remaining_files)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"

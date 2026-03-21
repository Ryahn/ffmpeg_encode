"""Human-readable byte sizes (shared by batch stats and lifetime stats UI)."""


def format_bytes(size_bytes: int) -> str:
    """Format a non-negative byte count using B … TB with PB for overflow."""
    if size_bytes < 0:
        size_bytes = 0
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

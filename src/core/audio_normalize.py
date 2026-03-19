"""Audio loudness helpers for FFmpeg (single-pass integrated loudnorm)."""


def build_integrated_loudnorm_filter(
    integrated_lufs: float,
    true_peak_db_tp: float,
    loudness_range: float,
) -> str:
    """Return an ``loudnorm`` filter string for single-pass EBU R128-style normalization."""
    return (
        f"loudnorm=I={integrated_lufs}:TP={true_peak_db_tp}:LRA={loudness_range}"
    )

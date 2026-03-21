"""Persistent storage (SQLite stats, etc.)."""

from .stats_store import (
    LifetimeTotals,
    dispose_engine,
    ensure_engine,
    get_lifetime_totals,
    record_successful_encode,
    reset_lifetime_stats,
    stats_database_path,
)

__all__ = [
    "LifetimeTotals",
    "dispose_engine",
    "ensure_engine",
    "get_lifetime_totals",
    "record_successful_encode",
    "reset_lifetime_stats",
    "stats_database_path",
]

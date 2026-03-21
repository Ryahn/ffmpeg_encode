"""SQLite-backed lifetime encoding statistics (thread-safe)."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from utils.config import config

from .models import Base, LifetimeStats

_engine = None
_session_factory: Optional[sessionmaker] = None
_lock = threading.RLock()


@dataclass(frozen=True)
class LifetimeTotals:
    files_encoded_success: int
    total_output_bytes: int
    total_encode_seconds: float
    updated_at: Optional[datetime]


def _db_path() -> Path:
    return config.config_dir / "stats.db"


def _migrate(conn) -> None:
    raw = conn.execute(text("PRAGMA user_version")).scalar()
    v = int(raw or 0)
    if v < 1:
        Base.metadata.create_all(conn)
        conn.execute(text("PRAGMA user_version = 1"))
    # Future: elif v < 2: ...


def ensure_engine():
    """Create engine and run migrations if needed. Idempotent."""
    global _engine, _session_factory
    with _lock:
        if _engine is not None:
            return
        config.config_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{_db_path().as_posix()}"
        eng = create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )
        with eng.begin() as conn:
            _migrate(conn)
        _engine = eng
        _session_factory = sessionmaker(_engine, expire_on_commit=False, future=True)


def dispose_engine() -> None:
    """Close DB connections (e.g. before replacing stats.db on disk)."""
    global _engine, _session_factory
    with _lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None
            _session_factory = None


def _session() -> Session:
    ensure_engine()
    assert _session_factory is not None
    return _session_factory()


def _ensure_row(session: Session) -> LifetimeStats:
    row = session.get(LifetimeStats, 1)
    if row is None:
        row = LifetimeStats(
            id=1,
            files_encoded_success=0,
            total_output_bytes=0,
            total_encode_seconds=0.0,
            updated_at=None,
        )
        session.add(row)
        session.flush()
    return row


def record_successful_encode(output_bytes: int, elapsed_seconds: float) -> None:
    """Increment totals after one successful, non-dry-run encode."""
    ob = max(0, int(output_bytes))
    es = max(0.0, float(elapsed_seconds))
    with _lock:
        ensure_engine()
        with _session() as session:
            row = _ensure_row(session)
            row.files_encoded_success += 1
            row.total_output_bytes += ob
            row.total_encode_seconds += es
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
    try:
        from core.stats_api_client import schedule_sync_lifetime_stats_if_enabled

        schedule_sync_lifetime_stats_if_enabled()
    except Exception:
        pass


def get_lifetime_totals() -> LifetimeTotals:
    with _lock:
        ensure_engine()
        with _session() as session:
            row = _ensure_row(session)
            session.commit()
            return LifetimeTotals(
                files_encoded_success=row.files_encoded_success,
                total_output_bytes=int(row.total_output_bytes),
                total_encode_seconds=float(row.total_encode_seconds),
                updated_at=row.updated_at,
            )


def reset_lifetime_stats() -> None:
    with _lock:
        ensure_engine()
        with _session() as session:
            row = _ensure_row(session)
            row.files_encoded_success = 0
            row.total_output_bytes = 0
            row.total_encode_seconds = 0.0
            row.updated_at = datetime.now(timezone.utc)
            session.commit()


def stats_database_path() -> Path:
    return _db_path()

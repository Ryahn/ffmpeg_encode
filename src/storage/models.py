"""SQLAlchemy ORM models for application statistics."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LifetimeStats(Base):
    """Singleton aggregate row (id=1) for successful encodes."""

    __tablename__ = "lifetime_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    files_encoded_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_output_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_encode_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

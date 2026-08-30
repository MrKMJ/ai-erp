from __future__ import annotations

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantMixin, UUIDAuditBase


class DocumentSequence(UUIDAuditBase, TenantMixin):
    """One counter per (tenant, prefix, period). Incremented under a row lock so
    document numbers are gap-free even under concurrency."""

    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "prefix", "period", name="uq_sequence_key"),
    )

    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    period: Mapped[str] = mapped_column(String(8), nullable=False)  # e.g. "2026"
    last_value: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

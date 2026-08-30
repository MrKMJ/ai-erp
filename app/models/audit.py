from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantMixin, UUIDAuditBase


class AuditLog(UUIDAuditBase, TenantMixin):
    """ERP audit: who changed what, when, old/new values."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[str | None] = mapped_column(String(36), index=True)
    actor_kind: Mapped[str] = mapped_column(String(16), default="user")  # user | ai | system
    action: Mapped[str] = mapped_column(String(64), index=True)  # create | update | post | ...
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    changes: Mapped[dict] = mapped_column(JSON, default=dict)

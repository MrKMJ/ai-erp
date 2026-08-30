from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantMixin, UUIDAuditBase


class ApprovalRequest(UUIDAuditBase, TenantMixin):
    """Generic approval task. The workflow engine controls execution;
    AI may only *initiate* these, never bypass them."""

    __tablename__ = "approval_requests"

    entity_type: Mapped[str] = mapped_column(String(40), index=True)  # purchase_order ...
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    requested_by: Mapped[str] = mapped_column(String(36))
    requested_by_kind: Mapped[str] = mapped_column(String(12), default="user")  # user | ai
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | rejected
    decided_by: Mapped[str | None] = mapped_column(String(36))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context: Mapped[dict] = mapped_column(JSON, default=dict)

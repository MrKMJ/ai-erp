from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantMixin, UUIDAuditBase


class AIConversation(UUIDAuditBase, TenantMixin):
    __tablename__ = "ai_conversations"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    module: Mapped[str | None] = mapped_column(String(32))

    messages: Mapped[list[AIMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )


class AIMessage(UUIDAuditBase, TenantMixin):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSON, default=list)

    conversation: Mapped[AIConversation] = relationship(back_populates="messages")


class AIToolCall(UUIDAuditBase, TenantMixin):
    """AI audit: which tool, which args, what result, at whose request."""

    __tablename__ = "ai_tool_calls"

    conversation_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    tool_name: Mapped[str] = mapped_column(String(64), index=True)
    risk: Mapped[str] = mapped_column(String(16), default="read")
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | denied | error | pending
    model: Mapped[str | None] = mapped_column(String(64))


class AIRecommendation(UUIDAuditBase, TenantMixin):
    __tablename__ = "ai_recommendations"

    type: Mapped[str] = mapped_column(String(40), index=True)
    # STOCKOUT_RISK | CASH_FLOW_RISK | SUPPLIER_ANOMALY | MARGIN_DECLINE | DEAD_STOCK ...
    severity: Mapped[str] = mapped_column(String(12), default="info")  # info | low | medium | high
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=0.5)
    estimated_impact: Mapped[str] = mapped_column(String(120), default="")
    suggested_action: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | accepted | dismissed
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIPrediction(UUIDAuditBase, TenantMixin):
    __tablename__ = "ai_predictions"

    model_name: Mapped[str] = mapped_column(String(48), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    horizon_days: Mapped[int] = mapped_column(default=30)
    value: Mapped[float] = mapped_column(Numeric(18, 4))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

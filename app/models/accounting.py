from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantMixin, UUIDAuditBase


class Account(UUIDAuditBase, TenantMixin):
    __tablename__ = "chart_of_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_account_code"),)

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(20), index=True)
    # asset | liability | equity | income | expense
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    system_tag: Mapped[str | None] = mapped_column(String(40), index=True)
    # ar, ap, sales, cogs, inventory, tax_output, tax_input, bank, retained_earnings


class JournalEntry(UUIDAuditBase, TenantMixin):
    __tablename__ = "journal_entries"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_je_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(16), default="posted")  # draft | posted | reversed
    reversed_by_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str | None] = mapped_column(String(36))

    lines: Mapped[list["JournalEntryLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class JournalEntryLine(UUIDAuditBase, TenantMixin):
    __tablename__ = "journal_entry_lines"

    entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entries.id", ondelete="CASCADE"))
    account_id: Mapped[str] = mapped_column(ForeignKey("chart_of_accounts.id"), index=True)
    debit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    credit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    memo: Mapped[str] = mapped_column(String(255), default="")

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")

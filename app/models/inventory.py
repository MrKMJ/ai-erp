from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantMixin, UUIDAuditBase


class InventoryTransaction(UUIDAuditBase, TenantMixin):
    """Append-only inventory ledger. Current stock is derived from this."""

    __tablename__ = "inventory_transactions"

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(32), index=True)
    # purchase_receipt | sales_delivery | adjustment | transfer_in | transfer_out | production
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))  # signed: + in, - out
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[str | None] = mapped_column(String(36), index=True)
    note: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str | None] = mapped_column(String(36))


class InventoryBalance(UUIDAuditBase, TenantMixin):
    """Cached balance for performance. Ledger remains the source of truth."""

    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", "warehouse_id", name="uq_balance_pw"),
    )

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), index=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    avg_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantMixin, UUIDAuditBase


class PurchaseOrder(UUIDAuditBase, TenantMixin):
    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_po_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"))
    order_date: Mapped[date] = mapped_column(Date)
    expected_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft | pending_approval | approved | received | billed | cancelled
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    created_by: Mapped[str | None] = mapped_column(String(36))
    approved_by: Mapped[str | None] = mapped_column(String(36))
    source: Mapped[str] = mapped_column(String(16), default="user")  # user | ai

    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class PurchaseOrderLine(UUIDAuditBase, TenantMixin):
    __tablename__ = "purchase_order_lines"

    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 4))
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    qty_received: Mapped[float] = mapped_column(Numeric(18, 4), default=0)

    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")


class GoodsReceipt(UUIDAuditBase, TenantMixin):
    __tablename__ = "goods_receipts"

    number: Mapped[str] = mapped_column(String(32))
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    receipt_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(255), default="")


class SupplierBill(UUIDAuditBase, TenantMixin):
    __tablename__ = "supplier_bills"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_bill_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_orders.id"))
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    bill_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | posted | paid
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    journal_entry_id: Mapped[str | None] = mapped_column(String(36))


class SupplierPayment(UUIDAuditBase, TenantMixin):
    __tablename__ = "supplier_payments"

    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id"), index=True)
    bill_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_bills.id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    method: Mapped[str] = mapped_column(String(20), default="bank")
    journal_entry_id: Mapped[str | None] = mapped_column(String(36))

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantMixin, UUIDAuditBase


class SalesOrder(UUIDAuditBase, TenantMixin):
    __tablename__ = "sales_orders"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_so_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"))
    order_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft | confirmed | delivered | invoiced | cancelled
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    notes: Mapped[str] = mapped_column(String(500), default="")

    lines: Mapped[list[SalesOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesOrderLine(UUIDAuditBase, TenantMixin):
    __tablename__ = "sales_order_lines"

    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4))
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    order: Mapped[SalesOrder] = relationship(back_populates="lines")


class SalesInvoice(UUIDAuditBase, TenantMixin):
    __tablename__ = "sales_invoices"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_si_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("sales_orders.id"))
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | posted | paid | void
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    journal_entry_id: Mapped[str | None] = mapped_column(String(36))

    lines: Mapped[list[SalesInvoiceLine]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesInvoiceLine(UUIDAuditBase, TenantMixin):
    __tablename__ = "sales_invoice_lines"

    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id", ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    description: Mapped[str] = mapped_column(String(255), default="")
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4))
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)
    line_total: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    invoice: Mapped[SalesInvoice] = relationship(back_populates="lines")


class CustomerPayment(UUIDAuditBase, TenantMixin):
    __tablename__ = "customer_payments"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("sales_invoices.id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    method: Mapped[str] = mapped_column(String(20), default="bank")
    journal_entry_id: Mapped[str | None] = mapped_column(String(36))

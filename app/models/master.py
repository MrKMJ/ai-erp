from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TenantMixin, UUIDAuditBase


class Customer(UUIDAuditBase, TenantMixin):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_customer_code"),)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(100))
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    payment_terms_days: Mapped[int] = mapped_column(default=30)
    credit_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="active")


class Supplier(UUIDAuditBase, TenantMixin):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_supplier_code"),)

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(100))
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")
    payment_terms_days: Mapped[int] = mapped_column(default=30)
    lead_time_days: Mapped[int] = mapped_column(default=14)
    reliability: Mapped[float] = mapped_column(Numeric(5, 4), default=0.95)
    status: Mapped[str] = mapped_column(String(30), default="active")


class ProductCategory(UUIDAuditBase, TenantMixin):
    __tablename__ = "product_categories"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_category_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Unit(UUIDAuditBase, TenantMixin):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_unit_code"),)

    code: Mapped[str] = mapped_column(String(16), nullable=False)  # ea, kg, box
    name: Mapped[str] = mapped_column(String(60), nullable=False)


class TaxCode(UUIDAuditBase, TenantMixin):
    __tablename__ = "tax_codes"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_tax_code"),)

    code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)  # 0.15 = 15%


class Product(UUIDAuditBase, TenantMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_product_sku"),)

    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("product_categories.id"))
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units.id"))
    tax_code_id: Mapped[str | None] = mapped_column(ForeignKey("tax_codes.id"))
    preferred_supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id"))

    cost_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    selling_price: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    reorder_level: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    safety_stock: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    is_stocked: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(30), default="active")


class Warehouse(UUIDAuditBase, TenantMixin):
    __tablename__ = "warehouses"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_warehouse_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

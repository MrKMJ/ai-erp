from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantMixin, UUIDAuditBase


class WorkCenter(UUIDAuditBase, TenantMixin):
    __tablename__ = "work_centers"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_work_center_code"),)

    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity_per_day: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    cost_per_hour: Mapped[float] = mapped_column(Numeric(18, 4), default=0)


class BillOfMaterials(UUIDAuditBase, TenantMixin):
    __tablename__ = "bills_of_materials"
    __table_args__ = (UniqueConstraint("tenant_id", "product_id", "version", name="uq_bom_ver"),)

    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    version: Mapped[int] = mapped_column(default=1)
    output_quantity: Mapped[float] = mapped_column(Numeric(18, 4), default=1)
    work_center_id: Mapped[str | None] = mapped_column(ForeignKey("work_centers.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    lines: Mapped[list[BomLine]] = relationship(
        back_populates="bom", cascade="all, delete-orphan", lazy="selectin"
    )


class BomLine(UUIDAuditBase, TenantMixin):
    __tablename__ = "bom_lines"

    bom_id: Mapped[str] = mapped_column(ForeignKey("bills_of_materials.id", ondelete="CASCADE"))
    component_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    scrap_rate: Mapped[float] = mapped_column(Numeric(6, 4), default=0)

    bom: Mapped[BillOfMaterials] = relationship(back_populates="lines")


class ProductionOrder(UUIDAuditBase, TenantMixin):
    __tablename__ = "production_orders"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_production_number"),)

    number: Mapped[str] = mapped_column(String(32), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    bom_id: Mapped[str] = mapped_column(ForeignKey("bills_of_materials.id"))
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    quantity_produced: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    # planned | released | in_progress | done | cancelled
    planned_date: Mapped[date] = mapped_column(Date)
    material_cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    created_by: Mapped[str | None] = mapped_column(String(36))
    source: Mapped[str] = mapped_column(String(16), default="user")

    materials: Mapped[list[ProductionMaterial]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductionMaterial(UUIDAuditBase, TenantMixin):
    __tablename__ = "production_order_materials"

    order_id: Mapped[str] = mapped_column(ForeignKey("production_orders.id", ondelete="CASCADE"))
    component_id: Mapped[str] = mapped_column(ForeignKey("products.id"))
    quantity_required: Mapped[float] = mapped_column(Numeric(18, 4))
    quantity_issued: Mapped[float] = mapped_column(Numeric(18, 4), default=0)

    order: Mapped[ProductionOrder] = relationship(back_populates="materials")


class ProductionOutput(UUIDAuditBase, TenantMixin):
    __tablename__ = "production_outputs"

    order_id: Mapped[str] = mapped_column(ForeignKey("production_orders.id"), index=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4))
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    output_date: Mapped[date] = mapped_column(Date)

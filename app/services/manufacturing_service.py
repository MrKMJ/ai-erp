from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.events import DomainEvent, bus
from app.core.exceptions import BusinessRuleError, NotFound
from app.models.manufacturing import (
    BillOfMaterials,
    BomLine,
    ProductionMaterial,
    ProductionOrder,
    ProductionOutput,
)
from app.models.master import Product
from app.services import accounting_service as acc
from app.services import inventory_service as inv
from app.services.numbering import next_number

CENT = Decimal("0.01")


def create_bom(db: Session, tenant_id: str, actor_id: str, data: dict) -> BillOfMaterials:
    product = db.get(Product, data["product_id"])
    if product is None or product.tenant_id != tenant_id:
        raise NotFound("Product")
    if not data.get("lines"):
        raise BusinessRuleError("A BOM needs at least one component line")

    existing = db.execute(
        select(BillOfMaterials).where(
            BillOfMaterials.tenant_id == tenant_id,
            BillOfMaterials.product_id == product.id,
        )
    ).scalars().all()
    version = max((b.version for b in existing), default=0) + 1
    for b in existing:
        b.is_active = False

    bom = BillOfMaterials(
        tenant_id=tenant_id, product_id=product.id, version=version,
        output_quantity=Decimal(str(data.get("output_quantity", 1))),
        work_center_id=data.get("work_center_id"), is_active=True,
        lines=[
            BomLine(
                tenant_id=tenant_id, component_id=ln["component_id"],
                quantity=Decimal(str(ln["quantity"])),
                scrap_rate=Decimal(str(ln.get("scrap_rate", 0))),
            )
            for ln in data["lines"]
        ],
    )
    db.add(bom)
    db.flush()
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="create",
           entity_type="bom", entity_id=bom.id,
           summary=f"BOM v{version} for {product.name}, {len(bom.lines)} components")
    return bom


def _active_bom(db: Session, tenant_id: str, product_id: str) -> BillOfMaterials:
    bom = db.execute(
        select(BillOfMaterials).where(
            BillOfMaterials.tenant_id == tenant_id,
            BillOfMaterials.product_id == product_id,
            BillOfMaterials.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if bom is None:
        raise BusinessRuleError("No active BOM for this product")
    return bom


def create_order(db: Session, tenant_id: str, actor_id: str, data: dict,
                 source: str = "user") -> ProductionOrder:
    product = db.get(Product, data["product_id"])
    if product is None or product.tenant_id != tenant_id:
        raise NotFound("Product")
    qty = Decimal(str(data["quantity"]))
    if qty <= 0:
        raise BusinessRuleError("Quantity must be positive")
    bom = _active_bom(db, tenant_id, product.id)
    batches = qty / Decimal(str(bom.output_quantity or 1))

    order = ProductionOrder(
        tenant_id=tenant_id,
        number=next_number(db, ProductionOrder, tenant_id, "MO"),
        product_id=product.id, bom_id=bom.id,
        warehouse_id=data["warehouse_id"],
        quantity=qty, status="planned",
        planned_date=data.get("planned_date") or date.today(),
        created_by=actor_id, source=source,
        materials=[
            ProductionMaterial(
                tenant_id=tenant_id, component_id=ln.component_id,
                quantity_required=(
                    batches * Decimal(str(ln.quantity)) * (1 + Decimal(str(ln.scrap_rate)))
                ).quantize(Decimal("0.0001")),
            )
            for ln in bom.lines
        ],
    )
    db.add(order)
    db.flush()
    record(db, tenant_id=tenant_id, actor_id=actor_id,
           actor_kind="ai" if source == "ai" else "user", action="create",
           entity_type="production_order", entity_id=order.id,
           summary=f"MO {order.number}: {qty} x {product.name}")
    bus.publish(DomainEvent("ProductionOrderCreated", tenant_id, {"order_id": order.id}))
    return order


def material_availability(db: Session, tenant_id: str, order_id: str) -> list[dict]:
    order = _get_order(db, tenant_id, order_id)
    out = []
    for m in order.materials:
        product = db.get(Product, m.component_id)
        on_hand = inv.on_hand(db, tenant_id, m.component_id, order.warehouse_id)
        need = float(m.quantity_required) - float(m.quantity_issued)
        out.append({
            "component_id": m.component_id,
            "sku": product.sku if product else "?",
            "name": product.name if product else "?",
            "required": float(m.quantity_required),
            "issued": float(m.quantity_issued),
            "outstanding": round(need, 4),
            "on_hand": on_hand,
            "shortfall": round(max(need - on_hand, 0), 4),
        })
    return out


def release(db: Session, tenant_id: str, actor_id: str, order_id: str) -> ProductionOrder:
    order = _get_order(db, tenant_id, order_id)
    if order.status != "planned":
        raise BusinessRuleError(f"MO is {order.status}")
    order.status = "released"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="update",
           entity_type="production_order", entity_id=order.id, summary="Released to shop floor")
    return order


def issue_materials(db: Session, tenant_id: str, actor_id: str, order_id: str) -> ProductionOrder:
    """Consume outstanding component quantities from stock (DR WIP / CR Inventory)."""
    order = _get_order(db, tenant_id, order_id)
    if order.status not in ("released", "in_progress"):
        raise BusinessRuleError("MO must be released before issuing materials")

    total_cost = Decimal("0")
    for m in order.materials:
        outstanding = Decimal(str(m.quantity_required)) - Decimal(str(m.quantity_issued))
        if outstanding <= 0:
            continue
        txn = inv.post_movement(
            db, tenant_id=tenant_id, product_id=m.component_id, warehouse_id=order.warehouse_id,
            quantity=-outstanding, transaction_type="production_consumption",
            reference_type="production_order", reference_id=order.id, created_by=actor_id,
        )
        m.quantity_issued = Decimal(str(m.quantity_required))
        total_cost += (outstanding * Decimal(str(txn.unit_cost))).quantize(CENT)

    order.material_cost = Decimal(str(order.material_cost)) + total_cost
    order.status = "in_progress"
    if total_cost > 0:
        acc.post_journal(
            db, tenant_id=tenant_id, entry_date=date.today(),
            description=f"Material issue for {order.number}",
            reference_type="production_order", reference_id=order.id, created_by=actor_id,
            lines=[
                {"tag": "wip", "debit": total_cost},
                {"tag": "inventory", "credit": total_cost},
            ],
        )
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="update",
           entity_type="production_order", entity_id=order.id,
           summary=f"Issued materials, cost {total_cost}")
    return order


def complete(db: Session, tenant_id: str, actor_id: str, order_id: str,
             produced_quantity: float | None = None) -> ProductionOutput:
    """Receive finished goods into stock at accumulated cost (DR Inventory / CR WIP)."""
    order = _get_order(db, tenant_id, order_id)
    if order.status != "in_progress":
        raise BusinessRuleError("Issue materials before completing the order")

    produced = Decimal(str(produced_quantity if produced_quantity is not None else order.quantity))
    if produced <= 0:
        raise BusinessRuleError("Produced quantity must be positive")

    unit_cost = (Decimal(str(order.material_cost)) / produced).quantize(Decimal("0.0001"))
    inv.post_movement(
        db, tenant_id=tenant_id, product_id=order.product_id, warehouse_id=order.warehouse_id,
        quantity=produced, transaction_type="production_output", unit_cost=unit_cost,
        reference_type="production_order", reference_id=order.id, created_by=actor_id,
    )
    value = (produced * unit_cost).quantize(CENT)
    acc.post_journal(
        db, tenant_id=tenant_id, entry_date=date.today(),
        description=f"Finished goods from {order.number}",
        reference_type="production_order", reference_id=order.id, created_by=actor_id,
        lines=[{"tag": "inventory", "debit": value}, {"tag": "wip", "credit": value}],
    )

    output = ProductionOutput(
        tenant_id=tenant_id, order_id=order.id, quantity=produced,
        unit_cost=unit_cost, output_date=date.today(),
    )
    db.add(output)
    order.quantity_produced = Decimal(str(order.quantity_produced)) + produced
    order.status = "done"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="post",
           entity_type="production_order", entity_id=order.id,
           summary=f"Completed {produced} units @ {unit_cost}")
    bus.publish(DomainEvent("ProductionCompleted", tenant_id,
                            {"order_id": order.id, "quantity": float(produced)}))
    return output


def _get_order(db: Session, tenant_id: str, order_id: str) -> ProductionOrder:
    order = db.get(ProductionOrder, order_id)
    if order is None or order.tenant_id != tenant_id:
        raise NotFound("Production order")
    return order

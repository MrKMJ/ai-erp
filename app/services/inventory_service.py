from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, bus
from app.core.exceptions import BusinessRuleError
from app.models.inventory import InventoryBalance, InventoryTransaction
from app.models.master import Product

D0 = Decimal("0")


def _get_balance(db: Session, tenant_id: str, product_id: str, warehouse_id: str) -> InventoryBalance:
    bal = db.execute(
        select(InventoryBalance).where(
            InventoryBalance.tenant_id == tenant_id,
            InventoryBalance.product_id == product_id,
            InventoryBalance.warehouse_id == warehouse_id,
        )
    ).scalar_one_or_none()
    if bal is None:
        bal = InventoryBalance(
            tenant_id=tenant_id, product_id=product_id, warehouse_id=warehouse_id,
            quantity=D0, avg_cost=D0,
        )
        db.add(bal)
        db.flush()
    return bal


def post_movement(
    db: Session,
    *,
    tenant_id: str,
    product_id: str,
    warehouse_id: str,
    quantity: Decimal | float,
    transaction_type: str,
    unit_cost: Decimal | float = 0,
    reference_type: str | None = None,
    reference_id: str | None = None,
    note: str = "",
    created_by: str | None = None,
    allow_negative: bool = True,
) -> InventoryTransaction:
    """Append one row to the inventory ledger and refresh the cached balance."""
    qty = Decimal(str(quantity))
    cost = Decimal(str(unit_cost))
    if qty == 0:
        raise BusinessRuleError("Inventory movement quantity cannot be zero")

    bal = _get_balance(db, tenant_id, product_id, warehouse_id)
    new_qty = Decimal(str(bal.quantity)) + qty
    if not allow_negative and new_qty < 0:
        raise BusinessRuleError("Insufficient stock for this movement")

    # Weighted-average cost, updated only on inbound movements with a cost.
    if qty > 0 and cost > 0:
        prev_val = Decimal(str(bal.quantity)) * Decimal(str(bal.avg_cost))
        bal.avg_cost = (prev_val + qty * cost) / new_qty if new_qty > 0 else cost
    bal.quantity = new_qty

    txn = InventoryTransaction(
        tenant_id=tenant_id,
        product_id=product_id,
        warehouse_id=warehouse_id,
        transaction_type=transaction_type,
        quantity=qty,
        unit_cost=cost or Decimal(str(bal.avg_cost)),
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=created_by,
    )
    db.add(txn)
    db.flush()

    bus.publish(DomainEvent(
        name="InventoryChanged",
        tenant_id=tenant_id,
        payload={
            "product_id": product_id,
            "warehouse_id": warehouse_id,
            "quantity_delta": float(qty),
            "on_hand": float(bal.quantity),
        },
    ))
    return txn


def on_hand(db: Session, tenant_id: str, product_id: str, warehouse_id: str | None = None) -> float:
    q = select(InventoryBalance).where(
        InventoryBalance.tenant_id == tenant_id, InventoryBalance.product_id == product_id
    )
    if warehouse_id:
        q = q.where(InventoryBalance.warehouse_id == warehouse_id)
    return float(sum(Decimal(str(b.quantity)) for b in db.execute(q).scalars()))


def position(db: Session, tenant_id: str) -> list[dict]:
    """Full stock position with reorder flags, joined to product master."""
    rows = db.execute(
        select(Product, InventoryBalance)
        .join(InventoryBalance, InventoryBalance.product_id == Product.id, isouter=True)
        .where(Product.tenant_id == tenant_id)
    ).all()
    agg: dict[str, dict] = {}
    for product, bal in rows:
        entry = agg.setdefault(product.id, {
            "product_id": product.id,
            "sku": product.sku,
            "name": product.name,
            "on_hand": 0.0,
            "reorder_level": float(product.reorder_level),
            "safety_stock": float(product.safety_stock),
            "avg_cost": 0.0,
        })
        if bal is not None:
            entry["on_hand"] += float(bal.quantity)
            entry["avg_cost"] = float(bal.avg_cost)
    for e in agg.values():
        e["below_reorder"] = e["on_hand"] <= e["reorder_level"]
    return sorted(agg.values(), key=lambda e: (not e["below_reorder"], e["name"]))

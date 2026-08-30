from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.models.inventory import InventoryTransaction
from app.schemas.common import InventoryAdjustIn
from app.services import forecasting
from app.services import inventory_service as svc

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/position")
def position(current: CurrentUser = Depends(require("inventory.read")),
             db: Session = Depends(get_db)):
    return svc.position(db, current.tenant_id)


@router.get("/ledger")
def ledger(product_id: str | None = None, limit: int = 200,
           current: CurrentUser = Depends(require("inventory.read")),
           db: Session = Depends(get_db)):
    q = select(InventoryTransaction).where(InventoryTransaction.tenant_id == current.tenant_id)
    if product_id:
        q = q.where(InventoryTransaction.product_id == product_id)
    q = q.order_by(InventoryTransaction.created_at.desc()).limit(limit)
    return [
        {"id": t.id, "product_id": t.product_id, "warehouse_id": t.warehouse_id,
         "type": t.transaction_type, "quantity": float(t.quantity),
         "unit_cost": float(t.unit_cost), "reference_type": t.reference_type,
         "reference_id": t.reference_id, "created_at": t.created_at.isoformat()}
        for t in db.execute(q).scalars().all()
    ]


@router.post("/adjust", status_code=201)
def adjust(body: InventoryAdjustIn, current: CurrentUser = Depends(require("inventory.adjust")),
           db: Session = Depends(get_db)):
    txn = svc.post_movement(
        db, tenant_id=current.tenant_id, product_id=body.product_id,
        warehouse_id=body.warehouse_id, quantity=body.quantity, unit_cost=body.unit_cost,
        transaction_type="adjustment", note=body.note, created_by=current.id,
    )
    record(db, tenant_id=current.tenant_id, actor_id=current.id, action="adjust",
           entity_type="inventory", entity_id=body.product_id,
           summary=f"Adjust {body.quantity} of product {body.product_id}")
    db.commit()
    return {"transaction_id": txn.id, "quantity": float(txn.quantity)}


@router.get("/forecast/{product_id}")
def forecast(product_id: str, horizon_days: int = 30,
             current: CurrentUser = Depends(require("inventory.read")),
             db: Session = Depends(get_db)):
    return forecasting.stockout_risk(db, current.tenant_id, product_id, horizon_days)

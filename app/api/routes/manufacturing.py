from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.models.manufacturing import BillOfMaterials, ProductionOrder, WorkCenter
from app.schemas.common import BomIn, ProductionOrderIn
from app.services import manufacturing_service as svc

router = APIRouter(prefix="/manufacturing", tags=["manufacturing"])


def _bom_dump(b: BillOfMaterials) -> dict:
    return {
        "id": b.id, "product_id": b.product_id, "version": b.version,
        "output_quantity": float(b.output_quantity), "is_active": b.is_active,
        "work_center_id": b.work_center_id,
        "lines": [
            {"component_id": l.component_id, "quantity": float(l.quantity),
             "scrap_rate": float(l.scrap_rate)}
            for l in b.lines
        ],
    }


def _mo_dump(o: ProductionOrder) -> dict:
    return {
        "id": o.id, "number": o.number, "product_id": o.product_id, "status": o.status,
        "quantity": float(o.quantity), "quantity_produced": float(o.quantity_produced),
        "material_cost": float(o.material_cost), "source": o.source,
        "planned_date": o.planned_date.isoformat(),
        "materials": [
            {"component_id": m.component_id, "quantity_required": float(m.quantity_required),
             "quantity_issued": float(m.quantity_issued)}
            for m in o.materials
        ],
    }


# ---- work centers ----
@router.get("/work-centers")
def work_centers(current: CurrentUser = Depends(require("manufacturing.read")),
                 db: Session = Depends(get_db)):
    rows = db.execute(
        select(WorkCenter).where(WorkCenter.tenant_id == current.tenant_id)
    ).scalars().all()
    return [{"id": w.id, "code": w.code, "name": w.name,
             "capacity_per_day": float(w.capacity_per_day)} for w in rows]


@router.post("/work-centers", status_code=201)
def create_work_center(body: dict, current: CurrentUser = Depends(require("manufacturing.bom.write")),
                       db: Session = Depends(get_db)):
    w = WorkCenter(tenant_id=current.tenant_id, code=body["code"], name=body["name"],
                   capacity_per_day=body.get("capacity_per_day", 0),
                   cost_per_hour=body.get("cost_per_hour", 0))
    db.add(w)
    db.commit()
    return {"id": w.id, "code": w.code, "name": w.name}


# ---- BOMs ----
@router.get("/boms")
def list_boms(current: CurrentUser = Depends(require("manufacturing.read")),
              db: Session = Depends(get_db),
              limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    rows = db.execute(
        select(BillOfMaterials).where(BillOfMaterials.tenant_id == current.tenant_id)
        .order_by(BillOfMaterials.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return [_bom_dump(b) for b in rows]


@router.post("/boms", status_code=201)
def create_bom(body: BomIn, current: CurrentUser = Depends(require("manufacturing.bom.write")),
               db: Session = Depends(get_db)):
    bom = svc.create_bom(db, current.tenant_id, current.id, body.model_dump())
    db.commit()
    return _bom_dump(bom)


# ---- production orders ----
@router.get("/orders")
def list_orders(current: CurrentUser = Depends(require("manufacturing.read")),
                db: Session = Depends(get_db),
                limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    rows = db.execute(
        select(ProductionOrder).where(ProductionOrder.tenant_id == current.tenant_id)
        .order_by(ProductionOrder.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return [_mo_dump(o) for o in rows]


@router.post("/orders", status_code=201)
def create_order(body: ProductionOrderIn,
                 current: CurrentUser = Depends(require("manufacturing.order.write")),
                 db: Session = Depends(get_db)):
    order = svc.create_order(db, current.tenant_id, current.id, body.model_dump())
    db.commit()
    return _mo_dump(order)


@router.get("/orders/{order_id}/materials")
def materials(order_id: str, current: CurrentUser = Depends(require("manufacturing.read")),
              db: Session = Depends(get_db)):
    return svc.material_availability(db, current.tenant_id, order_id)


@router.post("/orders/{order_id}/release")
def release(order_id: str, current: CurrentUser = Depends(require("manufacturing.execute")),
            db: Session = Depends(get_db)):
    o = svc.release(db, current.tenant_id, current.id, order_id)
    db.commit()
    return _mo_dump(o)


@router.post("/orders/{order_id}/issue-materials")
def issue(order_id: str, current: CurrentUser = Depends(require("manufacturing.execute")),
          db: Session = Depends(get_db)):
    o = svc.issue_materials(db, current.tenant_id, current.id, order_id)
    db.commit()
    return _mo_dump(o)


@router.post("/orders/{order_id}/complete")
def complete(order_id: str, produced_quantity: float | None = None,
             current: CurrentUser = Depends(require("manufacturing.execute")),
             db: Session = Depends(get_db)):
    out = svc.complete(db, current.tenant_id, current.id, order_id, produced_quantity)
    db.commit()
    return {"output_id": out.id, "quantity": float(out.quantity),
            "unit_cost": float(out.unit_cost)}

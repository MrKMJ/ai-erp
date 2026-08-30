from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.models.purchasing import PurchaseOrder, SupplierBill
from app.models.workflow import ApprovalRequest
from app.schemas.common import ApprovalDecisionIn, PurchaseOrderIn, ReceiptLineIn
from app.services import purchasing_service as svc

router = APIRouter(prefix="/purchasing", tags=["purchasing"])


def _po_dump(o: PurchaseOrder) -> dict:
    return {
        "id": o.id, "number": o.number, "supplier_id": o.supplier_id, "status": o.status,
        "total": float(o.total), "source": o.source, "expected_date":
        o.expected_date.isoformat() if o.expected_date else None,
        "lines": [
            {"product_id": l.product_id, "quantity": float(l.quantity),
             "unit_cost": float(l.unit_cost), "qty_received": float(l.qty_received)}
            for l in o.lines
        ],
    }


@router.get("/orders")
def list_orders(current: CurrentUser = Depends(require("purchase.read")),
                db: Session = Depends(get_db),
                limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                status: str | None = None):
    stmt = select(PurchaseOrder).where(PurchaseOrder.tenant_id == current.tenant_id)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    stmt = stmt.order_by(PurchaseOrder.created_at.desc()).limit(limit).offset(offset)
    return [_po_dump(o) for o in db.execute(stmt).scalars().all()]


@router.post("/orders", status_code=201)
def create_order(body: PurchaseOrderIn,
                 current: CurrentUser = Depends(require("purchase.order.write")),
                 db: Session = Depends(get_db)):
    order = svc.create_order(db, current.tenant_id, current.id, body.model_dump())
    db.commit()
    return _po_dump(order)


@router.post("/orders/{order_id}/submit")
def submit(order_id: str, current: CurrentUser = Depends(require("purchase.order.write")),
           db: Session = Depends(get_db)):
    result = svc.submit_for_approval(db, current.tenant_id, current.id, order_id)
    db.commit()
    return result


@router.get("/approvals")
def approvals(current: CurrentUser = Depends(require("purchase.order.approve")),
              db: Session = Depends(get_db)):
    rows = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == current.tenant_id, ApprovalRequest.status == "pending"
        )
    ).scalars().all()
    return [
        {"id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id, "reason": r.reason,
         "requested_by_kind": r.requested_by_kind, "context": r.context}
        for r in rows
    ]


@router.post("/approvals/{request_id}/decide")
def decide(request_id: str, body: ApprovalDecisionIn,
           current: CurrentUser = Depends(require("purchase.order.approve")),
           db: Session = Depends(get_db)):
    req = svc.decide_approval(db, current.tenant_id, current.id, request_id, body.approve, body.note)
    db.commit()
    return {"id": req.id, "status": req.status}


@router.post("/orders/{order_id}/receive")
def receive(order_id: str, lines: list[ReceiptLineIn] | None = None,
            current: CurrentUser = Depends(require("purchase.receipt.write")),
            db: Session = Depends(get_db)):
    gr = svc.receive(db, current.tenant_id, current.id, order_id,
                     [l.model_dump() for l in lines] if lines else None)
    db.commit()
    return {"goods_receipt_id": gr.id, "number": gr.number}


@router.post("/orders/{order_id}/bill")
def bill(order_id: str, current: CurrentUser = Depends(require("purchase.bill.post")),
         db: Session = Depends(get_db)):
    b = svc.create_bill(db, current.tenant_id, current.id, order_id)
    db.commit()
    return {"bill_id": b.id, "number": b.number, "total": float(b.total),
            "journal_entry_id": b.journal_entry_id}


@router.post("/bills/{bill_id}/pay")
def pay(bill_id: str, amount: float | None = None,
        current: CurrentUser = Depends(require("purchase.payment.create")),
        db: Session = Depends(get_db)):
    p = svc.pay_bill(db, current.tenant_id, current.id, bill_id, amount)
    db.commit()
    return {"payment_id": p.id, "amount": float(p.amount)}


@router.get("/bills")
def list_bills(current: CurrentUser = Depends(require("purchase.read")),
               db: Session = Depends(get_db)):
    rows = db.execute(
        select(SupplierBill).where(SupplierBill.tenant_id == current.tenant_id)
    ).scalars().all()
    return [
        {"id": b.id, "number": b.number, "supplier_id": b.supplier_id, "status": b.status,
         "total": float(b.total), "amount_paid": float(b.amount_paid)}
        for b in rows
    ]


@router.get("/payables")
def payables(current: CurrentUser = Depends(require("purchase.read")),
             db: Session = Depends(get_db)):
    return svc.outstanding_payables(db, current.tenant_id)

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.core.exceptions import NotFound
from app.models.sales import SalesInvoice, SalesOrder
from app.schemas.common import PaymentIn, SalesOrderIn
from app.services import sales_service as svc

router = APIRouter(prefix="/sales", tags=["sales"])


def _order_dump(o: SalesOrder) -> dict:
    return {
        "id": o.id, "number": o.number, "customer_id": o.customer_id, "status": o.status,
        "order_date": o.order_date.isoformat(), "subtotal": float(o.subtotal),
        "tax_total": float(o.tax_total), "total": float(o.total),
        "lines": [
            {"product_id": l.product_id, "quantity": float(l.quantity),
             "unit_price": float(l.unit_price), "line_total": float(l.line_total)}
            for l in o.lines
        ],
    }


@router.get("/orders")
def list_orders(current: CurrentUser = Depends(require("sales.read")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(SalesOrder).where(SalesOrder.tenant_id == current.tenant_id)
        .order_by(SalesOrder.created_at.desc())
    ).scalars().all()
    return [_order_dump(o) for o in rows]


@router.post("/orders", status_code=201)
def create_order(body: SalesOrderIn, current: CurrentUser = Depends(require("sales.order.write")),
                 db: Session = Depends(get_db)):
    order = svc.create_order(db, current.tenant_id, current.id, body.model_dump())
    db.commit()
    return _order_dump(order)


@router.post("/orders/{order_id}/confirm")
def confirm(order_id: str, current: CurrentUser = Depends(require("sales.order.write")),
            db: Session = Depends(get_db)):
    order = svc.confirm_order(db, current.tenant_id, current.id, order_id)
    db.commit()
    return _order_dump(order)


@router.post("/orders/{order_id}/deliver-invoice")
def deliver_invoice(order_id: str, current: CurrentUser = Depends(require("sales.invoice.post")),
                    db: Session = Depends(get_db)):
    invoice = svc.deliver_and_invoice(db, current.tenant_id, current.id, order_id)
    db.commit()
    return {"invoice_id": invoice.id, "number": invoice.number, "total": float(invoice.total),
            "status": invoice.status, "journal_entry_id": invoice.journal_entry_id}


@router.get("/invoices")
def list_invoices(current: CurrentUser = Depends(require("sales.read")),
                  db: Session = Depends(get_db)):
    rows = db.execute(
        select(SalesInvoice).where(SalesInvoice.tenant_id == current.tenant_id)
        .order_by(SalesInvoice.created_at.desc())
    ).scalars().all()
    return [
        {"id": i.id, "number": i.number, "customer_id": i.customer_id, "status": i.status,
         "total": float(i.total), "amount_paid": float(i.amount_paid),
         "due_date": i.due_date.isoformat()}
        for i in rows
    ]


@router.post("/payments", status_code=201)
def record_payment(body: PaymentIn, current: CurrentUser = Depends(require("sales.payment.create")),
                   db: Session = Depends(get_db)):
    payment = svc.record_payment(db, current.tenant_id, current.id, body.model_dump())
    db.commit()
    return {"id": payment.id, "amount": float(payment.amount),
            "journal_entry_id": payment.journal_entry_id}


@router.get("/receivables")
def receivables(current: CurrentUser = Depends(require("sales.read")),
                db: Session = Depends(get_db)):
    return svc.outstanding_receivables(db, current.tenant_id)

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.config import settings
from app.core.events import DomainEvent, bus
from app.core.exceptions import BusinessRuleError, NotFound
from app.models.master import Product, Supplier
from app.models.purchasing import (
    GoodsReceipt,
    PurchaseOrder,
    PurchaseOrderLine,
    SupplierBill,
    SupplierPayment,
)
from app.models.workflow import ApprovalRequest
from app.services import accounting_service as acc
from app.services import inventory_service as inv
from app.services.numbering import next_number

CENT = Decimal("0.01")
AUTO_APPROVE_LIMIT = Decimal("5000")


def create_order(
    db: Session, tenant_id: str, actor_id: str, data: dict, source: str = "user"
) -> PurchaseOrder:
    supplier = db.get(Supplier, data["supplier_id"])
    if supplier is None or supplier.tenant_id != tenant_id:
        raise NotFound("Supplier")

    lines, subtotal, tax_total = [], Decimal("0"), Decimal("0")
    for rl in data["lines"]:
        product = db.get(Product, rl["product_id"])
        if product is None or product.tenant_id != tenant_id:
            raise NotFound("Product")
        qty = Decimal(str(rl["quantity"]))
        cost = Decimal(str(rl.get("unit_cost") or product.cost_price))
        tax_rate = Decimal(str(rl.get("tax_rate") or 0))
        net = (qty * cost).quantize(CENT)
        subtotal += net
        tax_total += (net * tax_rate).quantize(CENT)
        lines.append(PurchaseOrderLine(
            tenant_id=tenant_id, product_id=product.id, quantity=qty,
            unit_cost=cost, tax_rate=tax_rate, line_total=net,
        ))

    total = subtotal + tax_total
    order = PurchaseOrder(
        tenant_id=tenant_id,
        number=next_number(db, PurchaseOrder, tenant_id, "PO"),
        supplier_id=supplier.id,
        warehouse_id=data["warehouse_id"],
        order_date=data.get("order_date") or date.today(),
        expected_date=date.today() + timedelta(days=supplier.lead_time_days),
        currency_code=supplier.currency_code,
        subtotal=subtotal, tax_total=tax_total, total=total,
        created_by=actor_id, source=source,
        status="draft",
        lines=lines,
    )
    db.add(order)
    db.flush()
    record(db, tenant_id=tenant_id, actor_id=actor_id,
           actor_kind="ai" if source == "ai" else "user", action="create",
           entity_type="purchase_order", entity_id=order.id,
           summary=f"PO {order.number} to {supplier.name}, total {total}")
    bus.publish(DomainEvent("PurchaseOrderCreated", tenant_id,
                            {"order_id": order.id, "total": float(total), "source": source}))
    return order


def submit_for_approval(db: Session, tenant_id: str, actor_id: str, order_id: str,
                        actor_kind: str = "user") -> dict:
    order = _get_order(db, tenant_id, order_id)
    if order.status not in ("draft",):
        raise BusinessRuleError(f"PO is {order.status}")

    if Decimal(str(order.total)) < AUTO_APPROVE_LIMIT and actor_kind != "ai":
        order.status = "approved"
        order.approved_by = actor_id
        record(db, tenant_id=tenant_id, actor_id=actor_id, action="approve",
               entity_type="purchase_order", entity_id=order.id,
               summary=f"Auto-approved {order.number} (< {AUTO_APPROVE_LIMIT})")
        return {"status": "approved", "approval_request_id": None}

    order.status = "pending_approval"
    req = ApprovalRequest(
        tenant_id=tenant_id, entity_type="purchase_order", entity_id=order.id,
        reason=f"PO {order.number} total {order.total} needs approval",
        requested_by=actor_id, requested_by_kind=actor_kind, status="pending",
        context={"total": float(order.total), "supplier_id": order.supplier_id},
    )
    db.add(req)
    db.flush()
    bus.publish(DomainEvent("ApprovalRequested", tenant_id,
                            {"entity_type": "purchase_order", "entity_id": order.id}))
    return {"status": "pending_approval", "approval_request_id": req.id}


def decide_approval(db: Session, tenant_id: str, actor_id: str, request_id: str,
                    approve: bool, note: str = "") -> ApprovalRequest:
    from app.models.base import utcnow

    req = db.get(ApprovalRequest, request_id)
    if req is None or req.tenant_id != tenant_id:
        raise NotFound("Approval request")
    if req.status != "pending":
        raise BusinessRuleError("Already decided")
    req.status = "approved" if approve else "rejected"
    req.decided_by = actor_id
    req.decided_at = utcnow()
    if req.entity_type == "purchase_order":
        order = _get_order(db, tenant_id, req.entity_id)
        order.status = "approved" if approve else "cancelled"
        if approve:
            order.approved_by = actor_id
    record(db, tenant_id=tenant_id, actor_id=actor_id,
           action="approve" if approve else "reject",
           entity_type=req.entity_type, entity_id=req.entity_id, summary=note)
    return req


def receive(db: Session, tenant_id: str, actor_id: str, order_id: str,
            receipt_lines: list[dict] | None = None) -> GoodsReceipt:
    order = _get_order(db, tenant_id, order_id)
    if order.status not in ("approved", "received"):
        raise BusinessRuleError(f"PO is {order.status}, must be approved before receiving")

    wanted = {rl["product_id"]: Decimal(str(rl["quantity"])) for rl in (receipt_lines or [])}
    gr = GoodsReceipt(
        tenant_id=tenant_id, number=next_number(db, GoodsReceipt, tenant_id, "GR"),
        order_id=order.id, receipt_date=date.today(),
    )
    db.add(gr)
    for ln in order.lines:
        outstanding = Decimal(str(ln.quantity)) - Decimal(str(ln.qty_received))
        qty = wanted.get(ln.product_id, outstanding)
        qty = min(qty, outstanding)
        if qty <= 0:
            continue
        inv.post_movement(
            db, tenant_id=tenant_id, product_id=ln.product_id, warehouse_id=order.warehouse_id,
            quantity=qty, transaction_type="purchase_receipt", unit_cost=Decimal(str(ln.unit_cost)),
            reference_type="purchase_order", reference_id=order.id, created_by=actor_id,
        )
        ln.qty_received = Decimal(str(ln.qty_received)) + qty

    fully = all(Decimal(str(l.qty_received)) >= Decimal(str(l.quantity)) for l in order.lines)
    order.status = "received" if fully else "approved"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="receive",
           entity_type="purchase_order", entity_id=order.id, summary=f"Goods receipt {gr.number}")
    bus.publish(DomainEvent("GoodsReceived", tenant_id, {"order_id": order.id}))
    return gr


def create_bill(db: Session, tenant_id: str, actor_id: str, order_id: str) -> SupplierBill:
    order = _get_order(db, tenant_id, order_id)
    supplier = db.get(Supplier, order.supplier_id)
    bill = SupplierBill(
        tenant_id=tenant_id, number=next_number(db, SupplierBill, tenant_id, "BILL"),
        order_id=order.id, supplier_id=order.supplier_id, bill_date=date.today(),
        due_date=date.today() + timedelta(days=supplier.payment_terms_days if supplier else 30),
        subtotal=order.subtotal, tax_total=order.tax_total, total=order.total, status="draft",
    )
    db.add(bill)
    db.flush()
    je_lines = [{"tag": "inventory", "debit": bill.subtotal}]
    if Decimal(str(bill.tax_total)) > 0:
        je_lines.append({"tag": "tax_input", "debit": bill.tax_total})
    je_lines.append({"tag": "ap", "credit": bill.total})
    je = acc.post_journal(
        db, tenant_id=tenant_id, entry_date=bill.bill_date,
        description=f"Supplier bill {bill.number}",
        reference_type="supplier_bill", reference_id=bill.id, created_by=actor_id, lines=je_lines,
    )
    bill.journal_entry_id = je.id
    bill.status = "posted"
    order.status = "billed"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="post",
           entity_type="supplier_bill", entity_id=bill.id, summary=f"Posted {bill.number}")
    return bill


def pay_bill(db: Session, tenant_id: str, actor_id: str, bill_id: str,
             amount: float | None = None) -> SupplierPayment:
    bill = db.get(SupplierBill, bill_id)
    if bill is None or bill.tenant_id != tenant_id:
        raise NotFound("Supplier bill")
    pay_amount = Decimal(str(amount)) if amount is not None else (
        Decimal(str(bill.total)) - Decimal(str(bill.amount_paid))
    )
    if pay_amount <= 0:
        raise BusinessRuleError("Nothing to pay")
    payment = SupplierPayment(
        tenant_id=tenant_id, supplier_id=bill.supplier_id, bill_id=bill.id,
        payment_date=date.today(), amount=pay_amount.quantize(CENT), method="bank",
    )
    db.add(payment)
    je = acc.post_journal(
        db, tenant_id=tenant_id, entry_date=payment.payment_date, description="Supplier payment",
        reference_type="supplier_payment", reference_id=payment.id, created_by=actor_id,
        lines=[{"tag": "ap", "debit": payment.amount}, {"tag": "bank", "credit": payment.amount}],
    )
    payment.journal_entry_id = je.id
    bill.amount_paid = Decimal(str(bill.amount_paid)) + pay_amount
    if Decimal(str(bill.amount_paid)) >= Decimal(str(bill.total)):
        bill.status = "paid"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="pay",
           entity_type="supplier_bill", entity_id=bill.id, summary=f"Paid {pay_amount}")
    return payment


def outstanding_payables(db: Session, tenant_id: str) -> list[dict]:
    rows = db.execute(
        select(SupplierBill, Supplier)
        .join(Supplier, Supplier.id == SupplierBill.supplier_id)
        .where(SupplierBill.tenant_id == tenant_id, SupplierBill.status == "posted")
    ).all()
    out = []
    for bill, supplier in rows:
        bal = float(Decimal(str(bill.total)) - Decimal(str(bill.amount_paid)))
        if bal <= 0:
            continue
        out.append({
            "bill_number": bill.number, "supplier": supplier.name,
            "due_date": bill.due_date.isoformat(), "balance": round(bal, 2),
            "overdue": bill.due_date < date.today(),
        })
    return sorted(out, key=lambda r: r["due_date"])


def _get_order(db: Session, tenant_id: str, order_id: str) -> PurchaseOrder:
    order = db.get(PurchaseOrder, order_id)
    if order is None or order.tenant_id != tenant_id:
        raise NotFound("Purchase order")
    return order

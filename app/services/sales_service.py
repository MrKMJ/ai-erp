from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.events import DomainEvent, bus
from app.core.exceptions import BusinessRuleError, NotFound
from app.models.master import Customer, Product
from app.models.sales import (
    CustomerPayment,
    SalesInvoice,
    SalesInvoiceLine,
    SalesOrder,
    SalesOrderLine,
)
from app.services import accounting_service as acc
from app.services import inventory_service as inv
from app.services.numbering import next_number

CENT = Decimal("0.01")


def _price_lines(db: Session, tenant_id: str, raw_lines: list[dict]) -> tuple[list, Decimal, Decimal]:
    lines, subtotal, tax_total = [], Decimal("0"), Decimal("0")
    for rl in raw_lines:
        product = db.get(Product, rl["product_id"])
        if product is None or product.tenant_id != tenant_id:
            raise NotFound("Product")
        qty = Decimal(str(rl["quantity"]))
        price = Decimal(str(rl.get("unit_price") or product.selling_price))
        tax_rate = Decimal(str(rl.get("tax_rate") or 0))
        net = (qty * price).quantize(CENT)
        tax = (net * tax_rate).quantize(CENT)
        subtotal += net
        tax_total += tax
        lines.append({
            "product_id": product.id, "quantity": qty, "unit_price": price,
            "tax_rate": tax_rate, "line_total": net,
        })
    return lines, subtotal, tax_total


def create_order(db: Session, tenant_id: str, actor_id: str, data: dict) -> SalesOrder:
    customer = db.get(Customer, data["customer_id"])
    if customer is None or customer.tenant_id != tenant_id:
        raise NotFound("Customer")
    lines, subtotal, tax_total = _price_lines(db, tenant_id, data["lines"])
    order = SalesOrder(
        tenant_id=tenant_id,
        number=next_number(db, SalesOrder, tenant_id, "SO"),
        customer_id=customer.id,
        warehouse_id=data["warehouse_id"],
        order_date=data.get("order_date") or date.today(),
        currency_code=customer.currency_code,
        status="draft",
        subtotal=subtotal, tax_total=tax_total, total=subtotal + tax_total,
        notes=data.get("notes", ""),
        lines=[SalesOrderLine(tenant_id=tenant_id, **ln) for ln in lines],
    )
    db.add(order)
    db.flush()
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="create",
           entity_type="sales_order", entity_id=order.id,
           summary=f"SO {order.number} for {customer.name}, total {order.total}")
    bus.publish(DomainEvent("SalesOrderCreated", tenant_id,
                            {"order_id": order.id, "total": float(order.total)}))
    return order


def confirm_order(db: Session, tenant_id: str, actor_id: str, order_id: str) -> SalesOrder:
    order = db.get(SalesOrder, order_id)
    if order is None or order.tenant_id != tenant_id:
        raise NotFound("Sales order")
    if order.status != "draft":
        raise BusinessRuleError(f"Order is {order.status}, cannot confirm")
    order.status = "confirmed"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="update",
           entity_type="sales_order", entity_id=order.id, summary=f"Confirmed {order.number}")
    return order


def deliver_and_invoice(db: Session, tenant_id: str, actor_id: str, order_id: str) -> SalesInvoice:
    """Deliver stock (inventory ledger + COGS journal) then raise & post the invoice."""
    order = db.get(SalesOrder, order_id)
    if order is None or order.tenant_id != tenant_id:
        raise NotFound("Sales order")
    if order.status not in ("confirmed", "draft"):
        raise BusinessRuleError(f"Order is {order.status}, cannot deliver")

    cogs_total = Decimal("0")
    for ln in order.lines:
        txn = inv.post_movement(
            db, tenant_id=tenant_id, product_id=ln.product_id,
            warehouse_id=order.warehouse_id, quantity=-Decimal(str(ln.quantity)),
            transaction_type="sales_delivery", reference_type="sales_order",
            reference_id=order.id, created_by=actor_id, allow_negative=True,
        )
        cogs_total += (Decimal(str(ln.quantity)) * Decimal(str(txn.unit_cost))).quantize(CENT)

    invoice = SalesInvoice(
        tenant_id=tenant_id,
        number=next_number(db, SalesInvoice, tenant_id, "INV"),
        order_id=order.id,
        customer_id=order.customer_id,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=_terms(db, order.customer_id)),
        subtotal=order.subtotal, tax_total=order.tax_total, total=order.total,
        status="draft",
        lines=[
            SalesInvoiceLine(
                tenant_id=tenant_id, product_id=ln.product_id, quantity=ln.quantity,
                unit_price=ln.unit_price, tax_rate=ln.tax_rate, line_total=ln.line_total,
            )
            for ln in order.lines
        ],
    )
    db.add(invoice)
    db.flush()

    # Revenue recognition journal: DR AR / CR Sales / CR Output tax
    je_lines = [
        {"tag": "ar", "debit": invoice.total, "memo": f"Invoice {invoice.number}"},
        {"tag": "sales", "credit": invoice.subtotal},
    ]
    if Decimal(str(invoice.tax_total)) > 0:
        je_lines.append({"tag": "tax_output", "credit": invoice.tax_total})
    je = acc.post_journal(
        db, tenant_id=tenant_id, entry_date=invoice.invoice_date,
        description=f"Sales invoice {invoice.number}",
        reference_type="sales_invoice", reference_id=invoice.id,
        created_by=actor_id, lines=je_lines,
    )
    invoice.journal_entry_id = je.id

    # COGS journal: DR COGS / CR Inventory
    if cogs_total > 0:
        acc.post_journal(
            db, tenant_id=tenant_id, entry_date=invoice.invoice_date,
            description=f"COGS for {invoice.number}",
            reference_type="sales_invoice", reference_id=invoice.id, created_by=actor_id,
            lines=[
                {"tag": "cogs", "debit": cogs_total},
                {"tag": "inventory", "credit": cogs_total},
            ],
        )

    invoice.status = "posted"
    order.status = "invoiced"
    record(db, tenant_id=tenant_id, actor_id=actor_id, action="post",
           entity_type="sales_invoice", entity_id=invoice.id,
           summary=f"Posted {invoice.number}, total {invoice.total}, COGS {cogs_total}")
    bus.publish(DomainEvent("InvoiceCreated", tenant_id,
                            {"invoice_id": invoice.id, "total": float(invoice.total)}))
    return invoice


def record_payment(db: Session, tenant_id: str, actor_id: str, data: dict) -> CustomerPayment:
    invoice = db.get(SalesInvoice, data["invoice_id"]) if data.get("invoice_id") else None
    if invoice is not None and invoice.tenant_id != tenant_id:
        raise NotFound("Invoice")
    amount = Decimal(str(data["amount"])).quantize(CENT)
    if amount <= 0:
        raise BusinessRuleError("Payment amount must be positive")

    payment = CustomerPayment(
        tenant_id=tenant_id,
        customer_id=data["customer_id"],
        invoice_id=data.get("invoice_id"),
        payment_date=data.get("payment_date") or date.today(),
        amount=amount, method=data.get("method", "bank"),
    )
    db.add(payment)
    je = acc.post_journal(
        db, tenant_id=tenant_id, entry_date=payment.payment_date,
        description="Customer payment",
        reference_type="customer_payment", reference_id=payment.id, created_by=actor_id,
        lines=[{"tag": "bank", "debit": amount}, {"tag": "ar", "credit": amount}],
    )
    payment.journal_entry_id = je.id
    if invoice is not None:
        invoice.amount_paid = Decimal(str(invoice.amount_paid)) + amount
        if Decimal(str(invoice.amount_paid)) >= Decimal(str(invoice.total)):
            invoice.status = "paid"
    db.flush()
    bus.publish(DomainEvent("PaymentReceived", tenant_id,
                            {"payment_id": payment.id, "amount": float(amount)}))
    return payment


def _terms(db: Session, customer_id: str) -> int:
    c = db.get(Customer, customer_id)
    return c.payment_terms_days if c else 30


def outstanding_receivables(db: Session, tenant_id: str) -> list[dict]:
    rows = db.execute(
        select(SalesInvoice, Customer)
        .join(Customer, Customer.id == SalesInvoice.customer_id)
        .where(
            SalesInvoice.tenant_id == tenant_id,
            SalesInvoice.status.in_(("posted", "draft")),
        )
    ).all()
    out = []
    for inv_row, customer in rows:
        bal = float(Decimal(str(inv_row.total)) - Decimal(str(inv_row.amount_paid)))
        if bal <= 0:
            continue
        out.append({
            "invoice_number": inv_row.number, "customer": customer.name,
            "due_date": inv_row.due_date.isoformat(), "balance": round(bal, 2),
            "overdue": inv_row.due_date < date.today(),
        })
    return sorted(out, key=lambda r: r["due_date"])

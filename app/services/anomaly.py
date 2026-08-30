"""Statistical anomaly detection over ERP transactions (z-score / IQR).

Dependency-free. Later: IsolationForest / seasonal decomposition per series.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.master import Product, Supplier
from app.models.purchasing import PurchaseOrder, PurchaseOrderLine


def supplier_price_anomalies(db: Session, tenant_id: str, lookback_days: int = 365) -> list[dict]:
    since = date.today() - timedelta(days=lookback_days)
    rows = db.execute(
        select(PurchaseOrderLine, PurchaseOrder, Product, Supplier)
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.order_id)
        .join(Product, Product.id == PurchaseOrderLine.product_id)
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .where(PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.order_date >= since)
        .order_by(PurchaseOrder.order_date)
    ).all()

    history: dict[tuple[str, str], list[float]] = defaultdict(list)
    latest: dict[tuple[str, str], dict] = {}
    for line, order, product, supplier in rows:
        key = (supplier.id, product.id)
        history[key].append(float(line.unit_cost))
        latest[key] = {
            "supplier": supplier.name, "product": product.name, "sku": product.sku,
            "date": order.order_date.isoformat(), "unit_cost": float(line.unit_cost),
        }

    out = []
    for key, prices in history.items():
        if len(prices) < 4:
            continue
        baseline = prices[:-1]
        current = prices[-1]
        mu = mean(baseline)
        sigma = pstdev(baseline) or 1e-9
        z = (current - mu) / sigma
        pct = (current - mu) / mu * 100 if mu else 0.0
        if abs(z) >= 2.5 and abs(pct) >= 8:
            info = latest[key]
            out.append({
                **info,
                "baseline_avg": round(mu, 4),
                "z_score": round(z, 2),
                "pct_change": round(pct, 1),
                "direction": "increase" if current > mu else "decrease",
            })
    return sorted(out, key=lambda r: -abs(r["pct_change"]))


def expense_anomalies(db: Session, tenant_id: str) -> list[dict]:
    """Flag journal expense postings that are large outliers vs history per account."""
    from app.models.accounting import Account, JournalEntry, JournalEntryLine

    rows = db.execute(
        select(JournalEntryLine, JournalEntry, Account)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.entry_id)
        .join(Account, Account.id == JournalEntryLine.account_id)
        .where(Account.tenant_id == tenant_id, Account.type == "expense",
               JournalEntry.status == "posted")
    ).all()
    by_account: dict[str, list] = defaultdict(list)
    for line, entry, account in rows:
        amt = float(line.debit) - float(line.credit)
        if amt > 0:
            by_account[account.name].append((entry, amt))

    out = []
    for name, items in by_account.items():
        amounts = [a for _, a in items]
        if len(amounts) < 4:
            continue
        mu, sigma = mean(amounts), pstdev(amounts) or 1e-9
        for entry, amt in items:
            z = (amt - mu) / sigma
            if z >= 3:
                out.append({
                    "account": name, "entry_number": entry.number,
                    "date": entry.entry_date.isoformat(), "amount": round(amt, 2),
                    "account_avg": round(mu, 2), "z_score": round(z, 2),
                })
    return sorted(out, key=lambda r: -r["z_score"])

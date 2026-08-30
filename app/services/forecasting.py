"""Deterministic predictive models.

Intentionally simple (moving average + linear trend) and dependency-free so the
project runs out of the box. Swap the internals for scikit-learn / XGBoost /
Prophet later — the service interface stays the same.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import InventoryTransaction
from app.models.master import Product, Supplier
from app.services import inventory_service as inv


def _daily_outflow(db: Session, tenant_id: str, product_id: str, days: int = 90) -> list[float]:
    since = date.today() - timedelta(days=days)
    rows = db.execute(
        select(InventoryTransaction).where(
            InventoryTransaction.tenant_id == tenant_id,
            InventoryTransaction.product_id == product_id,
            InventoryTransaction.transaction_type == "sales_delivery",
            InventoryTransaction.created_at >= since,
        )
    ).scalars().all()
    buckets: dict[date, float] = defaultdict(float)
    for r in rows:
        buckets[r.created_at.date()] += abs(float(r.quantity))
    return [buckets.get(since + timedelta(days=i), 0.0) for i in range(days)]


def demand_forecast(db: Session, tenant_id: str, product_id: str, horizon_days: int = 30) -> dict:
    series = _daily_outflow(db, tenant_id, product_id)
    n = len(series)
    total = sum(series)
    avg = total / n if n else 0.0

    # light linear trend over the window
    if n >= 14:
        xs = list(range(n))
        mean_x = sum(xs) / n
        mean_y = avg
        denom = sum((x - mean_x) ** 2 for x in xs) or 1.0
        slope = sum((xs[i] - mean_x) * (series[i] - mean_y) for i in range(n)) / denom
    else:
        slope = 0.0

    daily = max(avg + slope * (n / 2), 0.0)
    forecast = round(daily * horizon_days, 2)
    return {
        "product_id": product_id,
        "horizon_days": horizon_days,
        "avg_daily_demand": round(avg, 3),
        "trend_per_day": round(slope, 4),
        "forecast_qty": forecast,
        "history_days": n,
        "observed_total": round(total, 2),
    }


def stockout_risk(db: Session, tenant_id: str, product_id: str, horizon_days: int = 30) -> dict:
    product = db.get(Product, product_id)
    fc = demand_forecast(db, tenant_id, product_id, horizon_days)
    on_hand = inv.on_hand(db, tenant_id, product_id)

    lead_days = 14
    if product and product.preferred_supplier_id:
        sup = db.get(Supplier, product.preferred_supplier_id)
        if sup:
            lead_days = sup.lead_time_days

    daily = fc["avg_daily_demand"]
    demand_over_lead = daily * lead_days
    safety = float(product.safety_stock) if product else 0.0
    projected = on_hand - fc["forecast_qty"]
    days_cover = (on_hand / daily) if daily > 0 else 999

    if daily <= 0:
        level = "none"
    elif on_hand <= demand_over_lead + safety:
        level = "high"
    elif projected < safety:
        level = "medium"
    else:
        level = "low"

    return {
        **fc,
        "on_hand": round(on_hand, 2),
        "lead_time_days": lead_days,
        "days_of_cover": round(days_cover, 1),
        "projected_balance": round(projected, 2),
        "risk": level,
        "suggested_order_qty": round(max(fc["forecast_qty"] + safety - on_hand, 0), 2),
    }


def cash_flow_forecast(db: Session, tenant_id: str, horizon_days: int = 30) -> dict:
    from app.services import purchasing_service as pur
    from app.services import sales_service as sal

    inflow = sum(
        r["balance"] for r in sal.outstanding_receivables(db, tenant_id)
        if date.fromisoformat(r["due_date"]) <= date.today() + timedelta(days=horizon_days)
    )
    outflow = sum(
        r["balance"] for r in pur.outstanding_payables(db, tenant_id)
        if date.fromisoformat(r["due_date"]) <= date.today() + timedelta(days=horizon_days)
    )
    from app.services.accounting_service import account_by_tag, trial_balance

    bank = next(
        (r["balance"] for r in trial_balance(db, tenant_id)
         if r["account_id"] == account_by_tag(db, tenant_id, "bank").id),
        0.0,
    )
    projected = bank + inflow - outflow
    return {
        "horizon_days": horizon_days,
        "opening_bank": round(bank, 2),
        "expected_inflow": round(inflow, 2),
        "expected_outflow": round(outflow, 2),
        "projected_balance": round(projected, 2),
        "shortfall": round(projected, 2) < 0,
    }

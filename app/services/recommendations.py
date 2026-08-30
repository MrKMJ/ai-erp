"""Turn model/analysis output into first-class AI recommendations.

Called by the scheduled monitor job and by event handlers.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import AIRecommendation
from app.models.base import utcnow
from app.models.master import Product
from app.services import anomaly, forecasting


def _upsert(db: Session, tenant_id: str, *, type_: str, entity_type: str | None,
            entity_id: str | None, **fields) -> AIRecommendation:
    existing = db.execute(
        select(AIRecommendation).where(
            AIRecommendation.tenant_id == tenant_id,
            AIRecommendation.type == type_,
            AIRecommendation.entity_type == entity_type,
            AIRecommendation.entity_id == entity_id,
            AIRecommendation.status == "open",
        )
    ).scalar_one_or_none()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.updated_at = utcnow()
        return existing
    rec = AIRecommendation(
        tenant_id=tenant_id, type=type_, entity_type=entity_type, entity_id=entity_id,
        expires_at=utcnow() + timedelta(days=7), **fields,
    )
    db.add(rec)
    return rec


def run_monitor(db: Session, tenant_id: str) -> dict:
    """Full sweep: stockout risk, supplier price anomalies, cash flow, expense anomalies."""
    created = 0

    products = db.execute(
        select(Product).where(Product.tenant_id == tenant_id, Product.is_stocked.is_(True))
    ).scalars().all()
    for p in products:
        risk = forecasting.stockout_risk(db, tenant_id, p.id, horizon_days=30)
        if risk["risk"] in ("high", "medium"):
            _upsert(
                db, tenant_id, type_="STOCKOUT_RISK", entity_type="product", entity_id=p.id,
                severity="high" if risk["risk"] == "high" else "medium",
                title=f"Stockout risk: {p.name}",
                description=(
                    f"{p.sku}: {risk['on_hand']} on hand, forecast demand "
                    f"{risk['forecast_qty']} over 30d, lead time {risk['lead_time_days']}d. "
                    f"Days of cover: {risk['days_of_cover']}."
                ),
                confidence=0.7,
                estimated_impact=f"~{risk['suggested_order_qty']} units short",
                suggested_action={
                    "tool": "create_purchase_order",
                    "product_id": p.id,
                    "quantity": risk["suggested_order_qty"],
                    "supplier_id": p.preferred_supplier_id,
                },
            )
            created += 1

    for a in anomaly.supplier_price_anomalies(db, tenant_id):
        _upsert(
            db, tenant_id, type_="SUPPLIER_ANOMALY", entity_type="product", entity_id=a["sku"],
            severity="medium",
            title=f"Supplier price {a['direction']}: {a['product']}",
            description=(
                f"{a['supplier']} quoted {a['unit_cost']} for {a['product']} "
                f"({a['pct_change']:+.1f}% vs avg {a['baseline_avg']}, z={a['z_score']})."
            ),
            confidence=0.6, estimated_impact=f"{a['pct_change']:+.1f}% unit cost",
            suggested_action={"tool": "get_supplier_performance"},
        )
        created += 1

    cf = forecasting.cash_flow_forecast(db, tenant_id, horizon_days=30)
    if cf["shortfall"]:
        _upsert(
            db, tenant_id, type_="CASH_FLOW_RISK", entity_type=None, entity_id=None,
            severity="high", title="Projected cash shortfall in 30 days",
            description=(
                f"Opening bank {cf['opening_bank']}, +{cf['expected_inflow']} in, "
                f"-{cf['expected_outflow']} out => {cf['projected_balance']}."
            ),
            confidence=0.65, estimated_impact=f"{cf['projected_balance']} projected balance",
            suggested_action={"tool": "get_cash_flow"},
        )
        created += 1

    for e in anomaly.expense_anomalies(db, tenant_id):
        _upsert(
            db, tenant_id, type_="EXPENSE_ANOMALY", entity_type="journal_entry",
            entity_id=e["entry_number"], severity="low",
            title=f"Unusual expense in {e['account']}",
            description=f"{e['entry_number']} on {e['date']}: {e['amount']} vs avg {e['account_avg']} (z={e['z_score']}).",
            confidence=0.55, estimated_impact=f"{e['amount']}",
            suggested_action={},
        )
        created += 1

    db.flush()
    return {"recommendations_touched": created}

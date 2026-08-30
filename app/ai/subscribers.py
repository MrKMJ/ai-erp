"""Wire domain events to AI reactions (architecture section 29).

Kept deliberately light: on InventoryChanged we flag stockout risk for the one
affected product using its own DB session, so the ERP transaction that produced
the event is never coupled to AI work.
"""
from __future__ import annotations

import logging

from app.core.database import SessionLocal
from app.core.events import DomainEvent, bus

logger = logging.getLogger("erp.ai.subscribers")


@bus.on("InventoryChanged")
def _on_inventory_changed(event: DomainEvent) -> None:
    from app.services import forecasting
    from app.services.recommendations import _upsert

    product_id = event.payload.get("product_id")
    if not product_id:
        return
    db = SessionLocal()
    try:
        risk = forecasting.stockout_risk(db, event.tenant_id, product_id)
        if risk["risk"] in ("high", "medium"):
            _upsert(
                db, event.tenant_id, type_="STOCKOUT_RISK", entity_type="product",
                entity_id=product_id,
                severity="high" if risk["risk"] == "high" else "medium",
                title="Stockout risk detected",
                description=(
                    f"On hand {risk['on_hand']}, 30d forecast {risk['forecast_qty']}, "
                    f"lead time {risk['lead_time_days']}d, cover {risk['days_of_cover']}d."
                ),
                confidence=0.7,
                estimated_impact=f"~{risk['suggested_order_qty']} units short",
                suggested_action={
                    "tool": "create_purchase_order", "product_id": product_id,
                    "quantity": risk["suggested_order_qty"],
                },
            )
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("AI inventory subscriber failed")
        db.rollback()
    finally:
        db.close()


def register() -> None:
    """Import side effect registers the handlers above."""
    logger.info("AI event subscribers registered")

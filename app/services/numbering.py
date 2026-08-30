from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_number(db: Session, model, tenant_id: str, prefix: str) -> str:
    """Simple per-tenant sequential document numbers: PREFIX-YYYY-000123.

    Good enough for the MVP; a production system uses a dedicated sequence table
    with row locking to avoid gaps/races under concurrency.
    """
    year = date.today().year
    like = f"{prefix}-{year}-%"
    count = db.execute(
        select(func.count())
        .select_from(model)
        .where(model.tenant_id == tenant_id, model.number.like(like))
    ).scalar_one()
    return f"{prefix}-{year}-{count + 1:06d}"

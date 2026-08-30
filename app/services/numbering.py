from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.sequence import DocumentSequence


def next_number(db: Session, model=None, tenant_id: str = "", prefix: str = "") -> str:
    """Gap-free per-tenant document number: PREFIX-YYYY-000123.

    Uses a dedicated counter row locked FOR UPDATE (Postgres) so concurrent
    requests cannot produce duplicates or gaps. `model` is accepted for
    backwards-compatible call sites and ignored.
    """
    period = str(date.today().year)
    stmt = select(DocumentSequence).where(
        DocumentSequence.tenant_id == tenant_id,
        DocumentSequence.prefix == prefix,
        DocumentSequence.period == period,
    )
    if not settings.is_sqlite:
        stmt = stmt.with_for_update()

    seq = db.execute(stmt).scalar_one_or_none()
    if seq is None:
        seq = DocumentSequence(tenant_id=tenant_id, prefix=prefix, period=period, last_value=0)
        db.add(seq)
        db.flush()
        if not settings.is_sqlite:
            seq = db.execute(stmt).scalar_one()

    seq.last_value += 1
    db.flush()
    return f"{prefix}-{period}-{seq.last_value:06d}"

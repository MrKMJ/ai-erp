from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass
class Pagination:
    limit: int
    offset: int


def paginate(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


def page(db: Session, stmt, pg: Pagination) -> dict:
    """Return {items, total, limit, offset} for a SELECT statement."""
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.limit(pg.limit).offset(pg.offset)).scalars().all()
    return {"items": rows, "total": total, "limit": pg.limit, "offset": pg.offset}

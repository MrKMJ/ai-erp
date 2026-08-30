from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.models.accounting import Account, JournalEntry
from app.schemas.common import JournalEntryIn
from app.services import accounting_service as svc

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("/accounts")
def chart_of_accounts(current: CurrentUser = Depends(require("accounting.read")),
                      db: Session = Depends(get_db)):
    rows = db.execute(
        select(Account).where(Account.tenant_id == current.tenant_id).order_by(Account.code)
    ).scalars().all()
    return [
        {"id": a.id, "code": a.code, "name": a.name, "type": a.type, "system_tag": a.system_tag}
        for a in rows
    ]


@router.get("/journal")
def journal(limit: int = 100, current: CurrentUser = Depends(require("accounting.read")),
            db: Session = Depends(get_db)):
    rows = db.execute(
        select(JournalEntry).where(JournalEntry.tenant_id == current.tenant_id)
        .order_by(JournalEntry.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {"id": e.id, "number": e.number, "date": e.entry_date.isoformat(),
         "description": e.description, "status": e.status,
         "reference_type": e.reference_type,
         "lines": [
             {"account_id": l.account_id, "debit": float(l.debit), "credit": float(l.credit),
              "memo": l.memo}
             for l in e.lines
         ]}
        for e in rows
    ]


@router.post("/journal", status_code=201)
def post_journal(body: JournalEntryIn,
                 current: CurrentUser = Depends(require("accounting.journal.post")),
                 db: Session = Depends(get_db)):
    entry = svc.post_journal(
        db, tenant_id=current.tenant_id, entry_date=body.entry_date,
        description=body.description, created_by=current.id,
        lines=[l.model_dump() for l in body.lines],
    )
    db.commit()
    return {"id": entry.id, "number": entry.number, "status": entry.status}


@router.post("/journal/{entry_id}/reverse")
def reverse(entry_id: str, current: CurrentUser = Depends(require("accounting.journal.post")),
            db: Session = Depends(get_db)):
    from datetime import date

    rev = svc.reverse_journal(db, current.tenant_id, entry_id, date.today(), current.id)
    db.commit()
    return {"id": rev.id, "number": rev.number}


@router.get("/reports/trial-balance")
def trial_balance(current: CurrentUser = Depends(require("accounting.report.read")),
                  db: Session = Depends(get_db)):
    return svc.trial_balance(db, current.tenant_id)


@router.get("/reports/profit-loss")
def profit_loss(current: CurrentUser = Depends(require("accounting.report.read")),
                db: Session = Depends(get_db)):
    return svc.profit_and_loss(db, current.tenant_id)

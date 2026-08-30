from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import DomainEvent, bus
from app.core.exceptions import BusinessRuleError, NotFound
from app.models.accounting import Account, JournalEntry, JournalEntryLine
from app.services.numbering import next_number

CENT = Decimal("0.01")

# system_tag -> (code, name, type)
DEFAULT_ACCOUNTS = [
    ("1000", "Bank", "asset", "bank"),
    ("1100", "Accounts Receivable", "asset", "ar"),
    ("1200", "Inventory", "asset", "inventory"),
    ("1250", "Work In Progress", "asset", "wip"),
    ("1300", "Input Tax (VAT receivable)", "asset", "tax_input"),
    ("2000", "Accounts Payable", "liability", "ap"),
    ("2100", "Output Tax (VAT payable)", "liability", "tax_output"),
    ("2200", "Goods Received Not Invoiced", "liability", "grni"),
    ("3000", "Retained Earnings", "equity", "retained_earnings"),
    ("4000", "Sales Revenue", "income", "sales"),
    ("5000", "Cost of Goods Sold", "expense", "cogs"),
    ("6000", "Operating Expenses", "expense", "opex"),
]


def ensure_chart_of_accounts(db: Session, tenant_id: str) -> None:
    existing = {
        a.system_tag
        for a in db.execute(
            select(Account).where(Account.tenant_id == tenant_id)
        ).scalars()
    }
    for code, name, type_, tag in DEFAULT_ACCOUNTS:
        if tag in existing:
            continue
        db.add(Account(tenant_id=tenant_id, code=code, name=name, type=type_, system_tag=tag))
    db.flush()


def account_by_tag(db: Session, tenant_id: str, tag: str) -> Account:
    acc = db.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.system_tag == tag)
    ).scalar_one_or_none()
    if acc is None:
        raise NotFound(f"System account '{tag}'")
    return acc


def post_journal(
    db: Session,
    *,
    tenant_id: str,
    entry_date: date,
    description: str,
    lines: list[dict],
    reference_type: str | None = None,
    reference_id: str | None = None,
    created_by: str | None = None,
) -> JournalEntry:
    """Create a balanced, posted journal entry.

    lines: [{"account_id"|"tag": ..., "debit": x, "credit": y, "memo": ""}]
    Invariant enforced here (never by AI): SUM(debit) == SUM(credit).
    """
    if len(lines) < 2:
        raise BusinessRuleError("A journal entry needs at least two lines")

    total_debit = Decimal("0")
    total_credit = Decimal("0")
    resolved: list[JournalEntryLine] = []
    for ln in lines:
        account_id = ln.get("account_id")
        if account_id is None and ln.get("tag"):
            account_id = account_by_tag(db, tenant_id, ln["tag"]).id
        if account_id is None:
            raise BusinessRuleError("Each journal line needs account_id or tag")
        debit = Decimal(str(ln.get("debit", 0) or 0)).quantize(CENT)
        credit = Decimal(str(ln.get("credit", 0) or 0)).quantize(CENT)
        if debit < 0 or credit < 0 or (debit > 0 and credit > 0):
            raise BusinessRuleError("Each line is either a debit or a credit, non-negative")
        total_debit += debit
        total_credit += credit
        resolved.append(
            JournalEntryLine(
                tenant_id=tenant_id, account_id=account_id,
                debit=debit, credit=credit, memo=ln.get("memo", ""),
            )
        )

    if total_debit != total_credit:
        raise BusinessRuleError(
            f"Unbalanced journal entry: debit {total_debit} != credit {total_credit}"
        )
    if total_debit == 0:
        raise BusinessRuleError("Journal entry total cannot be zero")

    entry = JournalEntry(
        tenant_id=tenant_id,
        number=next_number(db, JournalEntry, tenant_id, "JE"),
        entry_date=entry_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        status="posted",
        created_by=created_by,
        lines=resolved,
    )
    db.add(entry)
    db.flush()
    bus.publish(DomainEvent(
        name="JournalPosted",
        tenant_id=tenant_id,
        payload={"entry_id": entry.id, "amount": float(total_debit)},
    ))
    return entry


def reverse_journal(db: Session, tenant_id: str, entry_id: str, on: date, created_by: str | None) -> JournalEntry:
    original = db.get(JournalEntry, entry_id)
    if original is None or original.tenant_id != tenant_id:
        raise NotFound("Journal entry")
    if original.status != "posted":
        raise BusinessRuleError("Only posted entries can be reversed")
    rev = post_journal(
        db,
        tenant_id=tenant_id,
        entry_date=on,
        description=f"Reversal of {original.number}",
        reference_type="reversal",
        reference_id=original.id,
        created_by=created_by,
        lines=[
            {"account_id": ln.account_id, "debit": ln.credit, "credit": ln.debit, "memo": "reversal"}
            for ln in original.lines
        ],
    )
    original.status = "reversed"
    original.reversed_by_id = rev.id
    return rev


def trial_balance(db: Session, tenant_id: str) -> list[dict]:
    rows = db.execute(
        select(Account, JournalEntryLine)
        .join(JournalEntryLine, JournalEntryLine.account_id == Account.id, isouter=True)
        .where(Account.tenant_id == tenant_id)
    ).all()
    agg: dict[str, dict] = {}
    for account, line in rows:
        e = agg.setdefault(account.id, {
            "account_id": account.id, "code": account.code, "name": account.name,
            "type": account.type, "debit": Decimal("0"), "credit": Decimal("0"),
        })
        if line is not None:
            e["debit"] += Decimal(str(line.debit))
            e["credit"] += Decimal(str(line.credit))
    out = []
    for e in sorted(agg.values(), key=lambda x: x["code"]):
        e["balance"] = float(e["debit"] - e["credit"])
        e["debit"] = float(e["debit"])
        e["credit"] = float(e["credit"])
        out.append(e)
    return out


def profit_and_loss(db: Session, tenant_id: str) -> dict:
    tb = trial_balance(db, tenant_id)
    income = sum(-r["balance"] for r in tb if r["type"] == "income")
    expense = sum(r["balance"] for r in tb if r["type"] == "expense")
    return {
        "revenue": round(income, 2),
        "expenses": round(expense, 2),
        "net_profit": round(income - expense, 2),
        "lines": [r for r in tb if r["type"] in ("income", "expense")],
    }

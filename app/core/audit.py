from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    tenant_id: str,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    summary: str = "",
    changes: dict | None = None,
    actor_kind: str = "user",
) -> AuditLog:
    log = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_kind=actor_kind,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        changes=changes or {},
    )
    db.add(log)
    return log

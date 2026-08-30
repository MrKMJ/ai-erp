from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.gateway import AIGateway
from app.ai.tools import tool_specs
from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require
from app.core.exceptions import NotFound
from app.models.ai import AIConversation, AIRecommendation, AIToolCall
from app.schemas.common import ChatIn, ToolCallIn
from app.services import recommendations as rec_svc

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/tools")
def tools(current: CurrentUser = Depends(require("ai.chat"))):
    specs = tool_specs()
    for s in specs:
        s["allowed_for_you"] = current.has(s["permission"])
    return specs


@router.post("/chat")
def chat(body: ChatIn, current: CurrentUser = Depends(get_current_user),
         db: Session = Depends(get_db)):
    gw = AIGateway(db, current)
    result = gw.chat(body.message, body.conversation_id, body.module)
    db.commit()
    return result


@router.post("/execute")
def execute(body: ToolCallIn, current: CurrentUser = Depends(require("ai.chat")),
            db: Session = Depends(get_db)):
    gw = AIGateway(db, current)
    result = gw.execute_tool(body.tool, body.arguments)
    db.commit()
    return {"tool": body.tool, "result": result}


@router.get("/conversations")
def conversations(current: CurrentUser = Depends(require("ai.chat")),
                  db: Session = Depends(get_db)):
    rows = db.execute(
        select(AIConversation).where(
            AIConversation.tenant_id == current.tenant_id,
            AIConversation.user_id == current.id,
        ).order_by(AIConversation.updated_at.desc())
    ).scalars().all()
    return [{"id": c.id, "title": c.title, "module": c.module,
             "updated_at": c.updated_at.isoformat()} for c in rows]


@router.get("/conversations/{cid}")
def conversation(cid: str, current: CurrentUser = Depends(require("ai.chat")),
                 db: Session = Depends(get_db)):
    c = db.get(AIConversation, cid)
    if c is None or c.tenant_id != current.tenant_id:
        raise NotFound("Conversation")
    return {
        "id": c.id, "title": c.title,
        "messages": [
            {"role": m.role, "content": m.content, "evidence": m.evidence,
             "at": m.created_at.isoformat()}
            for m in c.messages
        ],
    }


@router.get("/audit/tool-calls")
def tool_call_audit(limit: int = 100, current: CurrentUser = Depends(require("admin.settings")),
                    db: Session = Depends(get_db)):
    rows = db.execute(
        select(AIToolCall).where(AIToolCall.tenant_id == current.tenant_id)
        .order_by(AIToolCall.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {"id": r.id, "tool": r.tool_name, "risk": r.risk, "status": r.status,
         "user_id": r.user_id, "arguments": r.arguments, "result": r.result,
         "model": r.model, "at": r.created_at.isoformat()}
        for r in rows
    ]


# --------------------------------------------------------------- recommendations
@router.get("/recommendations")
def recommendations(status: str = "open",
                    current: CurrentUser = Depends(require("ai.recommendation.read")),
                    db: Session = Depends(get_db)):
    rows = db.execute(
        select(AIRecommendation).where(
            AIRecommendation.tenant_id == current.tenant_id,
            AIRecommendation.status == status,
        ).order_by(AIRecommendation.severity.desc(), AIRecommendation.created_at.desc())
    ).scalars().all()
    return [
        {"id": r.id, "type": r.type, "severity": r.severity, "title": r.title,
         "description": r.description, "confidence": float(r.confidence),
         "estimated_impact": r.estimated_impact, "suggested_action": r.suggested_action,
         "entity_type": r.entity_type, "entity_id": r.entity_id, "status": r.status}
        for r in rows
    ]


@router.post("/recommendations/{rid}/{decision}")
def decide_recommendation(rid: str, decision: str,
                          current: CurrentUser = Depends(require("ai.recommendation.read")),
                          db: Session = Depends(get_db)):
    if decision not in ("accepted", "dismissed"):
        raise NotFound("decision must be 'accepted' or 'dismissed'")
    r = db.get(AIRecommendation, rid)
    if r is None or r.tenant_id != current.tenant_id:
        raise NotFound("Recommendation")
    r.status = decision
    db.commit()
    return {"id": r.id, "status": r.status}


@router.post("/monitor/run")
def run_monitor(current: CurrentUser = Depends(require("ai.recommendation.read")),
                db: Session = Depends(get_db)):
    """Trigger the AI monitoring sweep (normally a scheduled job)."""
    result = rec_svc.run_monitor(db, current.tenant_id)
    db.commit()
    return result

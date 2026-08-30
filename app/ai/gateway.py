"""AI Gateway: the single entry point for every AI request.

Responsibilities (per architecture doc section 18):
  - authentication / tenant isolation (caller passes an authorized CurrentUser)
  - permission + risk policy enforcement per tool
  - tool execution against deterministic ERP services
  - full audit logging (AIToolCall rows)
  - conversation persistence
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai import tools as toolmod
from app.ai.llm import RuleProvider, get_provider
from app.core.audit import record
from app.core.deps import CurrentUser
from app.models.ai import AIConversation, AIMessage, AIToolCall

# Risk levels the gateway will execute without a separate approval gesture.
# Anything higher must go through the workflow engine (the tools already do this).
_AUTO_RISK = {"read", "low"}


class AIGateway:
    def __init__(self, db: Session, current: CurrentUser):
        self.db = db
        self.current = current
        self.provider = get_provider()

    # ------------------------------------------------------------------ tools
    def _ctx(self) -> toolmod.ToolContext:
        return toolmod.ToolContext(
            db=self.db,
            tenant_id=self.current.tenant_id,
            user_id=self.current.id,
            has_permission=self.current.has,
        )

    def execute_tool(self, name: str, arguments: dict, conversation_id: str | None = None) -> dict:
        tool = toolmod.REGISTRY.get(name)
        call = AIToolCall(
            tenant_id=self.current.tenant_id, conversation_id=conversation_id,
            user_id=self.current.id, tool_name=name,
            risk=tool.risk if tool else "unknown", arguments=arguments,
            model=getattr(self.provider, "name", "rule"),
        )
        self.db.add(call)

        if tool is None:
            call.status = "error"
            call.result = {"error": f"unknown tool {name}"}
            return call.result

        # Permission gate — the AI may only use tools the user is authorized for.
        if not self.current.has(tool.permission):
            call.status = "denied"
            call.result = {"error": f"permission denied: requires {tool.permission}"}
            return call.result

        # Risk gate.
        if tool.risk not in _AUTO_RISK:
            if not self.current.has("ai.action"):
                call.status = "denied"
                call.result = {"error": f"tool risk '{tool.risk}' requires human execution"}
                return call.result

        if tool.risk != "read" and not self.current.has("ai.action"):
            call.status = "denied"
            call.result = {"error": "creating drafts via AI requires the 'ai.action' permission"}
            return call.result

        try:
            result = tool.handler(self._ctx(), arguments)
            call.status = "ok"
            call.result = _jsonify(result)
            if tool.risk != "read":
                record(self.db, tenant_id=self.current.tenant_id, actor_id=self.current.id,
                       actor_kind="ai", action="ai_tool", entity_type=name,
                       summary=f"AI executed {name} args={arguments}")
            return call.result
        except Exception as exc:  # noqa: BLE001
            call.status = "error"
            call.result = {"error": str(exc)}
            return call.result

    # --------------------------------------------------------------- chat
    def chat(self, message: str, conversation_id: str | None = None,
             module: str | None = None) -> dict:
        self.current.require("ai.chat")
        convo = self._conversation(conversation_id, message, module)
        history = [
            {"role": m.role, "content": m.content}
            for m in convo.messages[-10:]
        ]
        self.db.add(AIMessage(tenant_id=self.current.tenant_id, conversation_id=convo.id,
                              role="user", content=message))

        evidence: list[dict] = []
        if isinstance(self.provider, RuleProvider):
            plan = self.provider.plan(message, history)
            if plan["tool_calls"]:
                for tc in plan["tool_calls"]:
                    result = self.execute_tool(tc["name"], tc.get("arguments", {}), convo.id)
                    evidence.append({"name": tc["name"], "result": result})
                answer = self.provider.narrate(message, evidence)
            else:
                answer = plan["text"]
        else:
            out = self.provider.run(
                message, history,
                lambda n, a: self.execute_tool(n, a, convo.id),
            )
            answer = out["text"]
            evidence = out.get("evidence", [])

        self.db.add(AIMessage(tenant_id=self.current.tenant_id, conversation_id=convo.id,
                              role="assistant", content=answer, evidence=_jsonify(evidence)))
        self.db.flush()
        return {"conversation_id": convo.id, "answer": answer, "evidence": _jsonify(evidence)}

    def _conversation(self, conversation_id, first_message, module) -> AIConversation:
        if conversation_id:
            convo = self.db.get(AIConversation, conversation_id)
            if convo and convo.tenant_id == self.current.tenant_id:
                return convo
        convo = AIConversation(
            tenant_id=self.current.tenant_id, user_id=self.current.id,
            title=first_message[:60], module=module,
        )
        self.db.add(convo)
        self.db.flush()
        return convo


def _jsonify(obj):
    import json

    return json.loads(json.dumps(obj, default=str))

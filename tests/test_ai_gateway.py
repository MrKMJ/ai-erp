"""The AI chat endpoint must never 500 when the LLM provider misbehaves."""


def _make_env(client, tenant):
    h = tenant["headers"]
    wh = client.post("/api/v1/warehouses", headers=h,
                     json={"code": "M", "name": "M", "is_default": True}).json()
    client.post("/api/v1/products", headers=h,
                json={"sku": "P", "name": "P", "cost_price": 5, "selling_price": 9}).json()
    return h, wh


def test_chat_degrades_when_llm_provider_raises(client, tenant, monkeypatch):
    h, _ = _make_env(client, tenant)

    class Boom:
        name = "anthropic"

        def run(self, *a, **kw):
            raise RuntimeError("model exploded")

    import app.ai.gateway as gw

    monkeypatch.setattr(gw, "get_provider", lambda: Boom())

    r = client.post("/api/v1/ai/chat", headers=h, json={"message": "what is our profit?"})
    assert r.status_code == 200
    assert "unavailable" in r.json()["answer"].lower()


def test_chat_works_with_rule_provider(client, tenant):
    h, _ = _make_env(client, tenant)
    r = client.post("/api/v1/ai/chat", headers=h, json={"message": "show me the cash flow forecast"})
    assert r.status_code == 200
    assert r.json()["evidence"][0]["name"] == "get_cash_flow"


def test_intent_routing_is_whole_word():
    from app.ai.llm import RuleProvider

    p = RuleProvider()

    def routed(msg):
        plan = p.plan(msg, [])
        return plan["tool_calls"][0]["name"] if plan["tool_calls"] else None

    # "summary" must not trigger receivables via a substring "ar"
    assert routed("Give me a summary of inventory") == "get_inventory_position"
    assert routed("which products will stock out") == "get_stockout_risk"
    assert routed("summary of our suppliers") == "get_supplier_performance"  # plural tolerated
    assert routed("who owes us money") == "get_receivables"
    assert routed("what do we owe suppliers") == "get_payables"


def test_chat_answer_is_plain_language_not_json(client, tenant):
    h, _ = _make_env(client, tenant)
    answer = client.post(
        "/api/v1/ai/chat", headers=h, json={"message": "what is our profit and loss?"}
    ).json()["answer"]
    # readable prose, not a JSON dump
    assert "```json" not in answer
    assert '"net_profit"' not in answer
    assert "profit" in answer.lower() and "$" in answer

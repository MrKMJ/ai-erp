import pytest


@pytest.fixture()
def env(client, tenant):
    h = tenant["headers"]

    def post(url, body=None):
        return client.post(url, headers=h, json=body)

    def get(url):
        return client.get(url, headers=h)

    wh = post("/api/v1/warehouses", {"code": "MAIN", "name": "Main", "is_default": True}).json()
    sup = post("/api/v1/suppliers", {"code": "S1", "name": "Supplier 1", "lead_time_days": 7}).json()
    cust = post("/api/v1/customers", {"code": "C1", "name": "Customer 1"}).json()
    prod = post("/api/v1/products", {
        "sku": "SKU1", "name": "Product 1", "cost_price": 10, "selling_price": 25,
        "reorder_level": 20, "safety_stock": 5, "preferred_supplier_id": sup["id"],
    }).json()
    return {"post": post, "get": get, "wh": wh, "sup": sup, "cust": cust, "prod": prod}


def _receive_stock(env, qty=100):
    po = env["post"]("/api/v1/purchasing/orders", {
        "supplier_id": env["sup"]["id"], "warehouse_id": env["wh"]["id"],
        "lines": [{"product_id": env["prod"]["id"], "quantity": qty, "unit_cost": 10}],
    }).json()
    env["post"](f"/api/v1/purchasing/orders/{po['id']}/submit")
    env["post"](f"/api/v1/purchasing/orders/{po['id']}/receive")
    return po


def test_purchase_to_stock_flow(env):
    _receive_stock(env, 100)
    pos = env["get"]("/api/v1/inventory/position").json()
    assert pos[0]["on_hand"] == 100
    assert pos[0]["avg_cost"] == 10


def test_sales_flow_posts_balanced_journals(env):
    _receive_stock(env, 100)
    so = env["post"]("/api/v1/sales/orders", {
        "customer_id": env["cust"]["id"], "warehouse_id": env["wh"]["id"],
        "lines": [{"product_id": env["prod"]["id"], "quantity": 10, "tax_rate": 0.1}],
    }).json()
    assert so["total"] == pytest.approx(275.0)
    env["post"](f"/api/v1/sales/orders/{so['id']}/confirm")
    inv = env["post"](f"/api/v1/sales/orders/{so['id']}/deliver-invoice").json()
    assert inv["status"] == "posted"

    tb = env["get"]("/api/v1/accounting/reports/trial-balance").json()
    assert sum(round(r["debit"] - r["credit"], 2) for r in tb) == pytest.approx(0.0)

    pnl = env["get"]("/api/v1/accounting/reports/profit-loss").json()
    assert pnl["revenue"] == pytest.approx(250.0)
    assert pnl["net_profit"] == pytest.approx(150.0)


def test_unbalanced_journal_rejected(env):
    r = env["post"]("/api/v1/accounting/journal", {
        "entry_date": "2026-01-01", "description": "bad",
        "lines": [{"tag": "bank", "debit": 100}, {"tag": "sales", "credit": 90}],
    })
    assert r.status_code == 400
    assert "Unbalanced" in r.json()["detail"]


def test_large_po_needs_approval(env):
    po = env["post"]("/api/v1/purchasing/orders", {
        "supplier_id": env["sup"]["id"], "warehouse_id": env["wh"]["id"],
        "lines": [{"product_id": env["prod"]["id"], "quantity": 1000, "unit_cost": 10}],
    }).json()
    sub = env["post"](f"/api/v1/purchasing/orders/{po['id']}/submit").json()
    assert sub["status"] == "pending_approval"
    assert sub["approval_request_id"]


def test_ai_chat_cites_evidence(env):
    _receive_stock(env, 100)
    r = env["post"]("/api/v1/ai/chat", {"message": "what is our profit and loss?"})
    assert r.status_code == 200
    body = r.json()
    assert body["evidence"]
    assert body["evidence"][0]["name"] == "get_profit_loss"


def test_ai_create_po_is_draft_and_routed(env):
    _receive_stock(env, 5)  # low stock to make a plausible reorder
    r = env["post"]("/api/v1/ai/execute", {
        "tool": "create_purchase_order",
        "arguments": {"sku": "SKU1", "quantity": 50},
    })
    assert r.status_code == 200
    result = r.json()["result"]
    assert "purchase_order_id" in result
    assert result["workflow"]["status"] in ("pending_approval", "approved")


def test_ai_denied_without_permission(client, tenant, env):
    # a sales rep can chat, but get_profit_loss needs accounting.report.read
    client.post("/api/v1/auth/users", headers=tenant["headers"], json={
        "email": "rep@acme-erp.com", "password": "password123", "roles": ["sales_rep"]})
    login = client.post("/api/v1/auth/login",
                        data={"username": "rep@acme-erp.com", "password": "password123"}).json()
    h = {"Authorization": f"Bearer {login['access_token']}"}
    r = client.post("/api/v1/ai/execute", headers=h,
                    json={"tool": "get_profit_loss", "arguments": {}})
    assert r.status_code == 200
    assert "permission denied" in r.json()["result"]["error"]

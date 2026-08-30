import pytest


@pytest.fixture()
def mfg(client, tenant):
    h = tenant["headers"]

    def post(url, body=None):
        return client.post(url, headers=h, json=body)

    def get(url):
        return client.get(url, headers=h)

    wh = post("/api/v1/warehouses", {"code": "MAIN", "name": "Main", "is_default": True}).json()
    sup = post("/api/v1/suppliers", {"code": "S1", "name": "S1"}).json()
    # two raw components + one finished good
    comp1 = post("/api/v1/products", {"sku": "RAW-1", "name": "Raw 1", "cost_price": 2}).json()
    comp2 = post("/api/v1/products", {"sku": "RAW-2", "name": "Raw 2", "cost_price": 5}).json()
    fg = post("/api/v1/products", {"sku": "FG-1", "name": "Finished 1", "selling_price": 50}).json()

    # stock the components (keep each PO under the 5000 auto-approval limit)
    for c, qty in ((comp1, 400), (comp2, 400)):
        po = post("/api/v1/purchasing/orders", {
            "supplier_id": sup["id"], "warehouse_id": wh["id"],
            "lines": [{"product_id": c["id"], "quantity": qty, "unit_cost": c["cost_price"]}],
        }).json()
        post(f"/api/v1/purchasing/orders/{po['id']}/submit")
        post(f"/api/v1/purchasing/orders/{po['id']}/receive")

    bom = post("/api/v1/manufacturing/boms", {
        "product_id": fg["id"], "output_quantity": 1,
        "lines": [
            {"component_id": comp1["id"], "quantity": 3},
            {"component_id": comp2["id"], "quantity": 2},
        ],
    }).json()
    return {"post": post, "get": get, "wh": wh, "comp1": comp1, "comp2": comp2, "fg": fg, "bom": bom}


def test_bom_created_active(mfg):
    assert mfg["bom"]["is_active"] is True
    assert len(mfg["bom"]["lines"]) == 2


def test_production_order_full_cycle(mfg):
    mo = mfg["post"]("/api/v1/manufacturing/orders", {
        "product_id": mfg["fg"]["id"], "warehouse_id": mfg["wh"]["id"], "quantity": 10,
    }).json()
    assert mo["status"] == "planned"
    # material requirements exploded from BOM: 10*3 and 10*2
    reqs = {m["component_id"]: m["quantity_required"] for m in mo["materials"]}
    assert reqs[mfg["comp1"]["id"]] == 30
    assert reqs[mfg["comp2"]["id"]] == 20

    avail = mfg["get"](f"/api/v1/manufacturing/orders/{mo['id']}/materials").json()
    assert all(m["shortfall"] == 0 for m in avail)

    mfg["post"](f"/api/v1/manufacturing/orders/{mo['id']}/release")
    issued = mfg["post"](f"/api/v1/manufacturing/orders/{mo['id']}/issue-materials").json()
    # material cost = 30*2 + 20*5 = 160
    assert issued["material_cost"] == pytest.approx(160.0)
    assert issued["status"] == "in_progress"

    done = mfg["post"](f"/api/v1/manufacturing/orders/{mo['id']}/complete").json()
    assert done["quantity"] == 10
    assert done["unit_cost"] == pytest.approx(16.0)  # 160 / 10

    # finished goods now on hand, ledger balanced
    pos = {p["sku"]: p for p in mfg["get"]("/api/v1/inventory/position").json()}
    assert pos["FG-1"]["on_hand"] == 10
    assert pos["FG-1"]["avg_cost"] == pytest.approx(16.0)

    tb = mfg["get"]("/api/v1/accounting/reports/trial-balance").json()
    assert sum(round(r["debit"] - r["credit"], 2) for r in tb) == pytest.approx(0.0)
    # WIP fully cleared back to zero
    wip = next(r for r in tb if r["name"] == "Work In Progress")
    assert wip["balance"] == pytest.approx(0.0)


def test_grni_cleared_on_billing(client, tenant):
    h = tenant["headers"]
    wh = client.post("/api/v1/warehouses", headers=h,
                     json={"code": "M", "name": "M", "is_default": True}).json()
    sup = client.post("/api/v1/suppliers", headers=h, json={"code": "S", "name": "S"}).json()
    p = client.post("/api/v1/products", headers=h,
                    json={"sku": "P", "name": "P", "cost_price": 10}).json()
    po = client.post("/api/v1/purchasing/orders", headers=h, json={
        "supplier_id": sup["id"], "warehouse_id": wh["id"],
        "lines": [{"product_id": p["id"], "quantity": 100, "unit_cost": 10}],
    }).json()
    client.post(f"/api/v1/purchasing/orders/{po['id']}/submit", headers=h)
    client.post(f"/api/v1/purchasing/orders/{po['id']}/receive", headers=h)

    tb = {r["name"]: r for r in
          client.get("/api/v1/accounting/reports/trial-balance", headers=h).json()}
    assert tb["Inventory"]["balance"] == pytest.approx(1000.0)
    assert tb["Goods Received Not Invoiced"]["balance"] == pytest.approx(-1000.0)

    client.post(f"/api/v1/purchasing/orders/{po['id']}/bill", headers=h)
    tb = {r["name"]: r for r in
          client.get("/api/v1/accounting/reports/trial-balance", headers=h).json()}
    assert tb["Goods Received Not Invoiced"]["balance"] == pytest.approx(0.0)
    assert tb["Accounts Payable"]["balance"] == pytest.approx(-1000.0)

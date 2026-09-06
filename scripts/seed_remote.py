"""Seed a demo tenant on a RUNNING instance over HTTP — no shell access needed.

    python -m scripts.seed_remote --api https://your-api.example.com

Useful on hosts where you can't open a shell (or just from your laptop).
Mirrors scripts/seed.py but drives the public REST API. Idempotent-ish: it
aborts cleanly if the slug is already taken.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta

import httpx

random.seed(42)


class Client:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/")
        self.token = token
        self.http = httpx.Client(timeout=60.0)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def post(self, path: str, json=None, data=None):
        for attempt in range(5):
            try:
                r = self.http.post(f"{self.base}{path}", json=json, data=data,
                                   headers=self._headers())
            except httpx.HTTPError as exc:
                if attempt == 4:
                    raise
                print(f"  ... {path} network error, retrying ({exc.__class__.__name__})")
                continue
            if r.status_code in (502, 503, 504):
                print(f"  ... {path} {r.status_code} (API waking up), retrying")
                continue
            if r.status_code >= 400:
                raise SystemExit(f"POST {path} -> {r.status_code}: {r.text[:300]}")
            return r.json() if r.text else {}
        raise SystemExit(f"POST {path} kept failing")

    def get(self, path: str):
        r = self.http.get(f"{self.base}{path}", headers=self._headers())
        r.raise_for_status()
        return r.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True, help="base URL of the running API")
    ap.add_argument("--slug", default="demo")
    ap.add_argument("--email", default="owner@demo-erp.com")
    ap.add_argument("--password", default="demo12345")
    ap.add_argument("--days", type=int, default=25)
    args = ap.parse_args()

    c = Client(args.api)
    print(f"==> {args.api}  (waking the service if asleep, ~50s on free tiers)")

    reg = c.post("/api/v1/auth/register", json={
        "company_name": "Demo Manufacturing Co", "slug": args.slug,
        "admin_email": args.email, "admin_password": args.password,
        "admin_name": "Demo Owner",
    })
    c.token = reg["access_token"]
    print(f"==> tenant created: {args.slug}")

    wh = c.post("/api/v1/warehouses", json={"code": "MAIN", "name": "Main Warehouse",
                                            "is_default": True})
    suppliers = [
        c.post("/api/v1/suppliers", json={"code": f"SUP{i+1}", "name": n,
                                          "lead_time_days": lt, "reliability": rel})
        for i, (n, lt, rel) in enumerate([
            ("Acme Components", 21, 0.97),
            ("Global Parts Ltd", 30, 0.74),
            ("QuickSupply Inc", 10, 0.90),
        ])
    ]
    customers = [
        c.post("/api/v1/customers", json={"code": f"CUST{i+1}", "name": n})
        for i, n in enumerate(["Northwind Retail", "Contoso Stores", "Fabrikam Wholesale"])
    ]
    catalog = [
        ("WIDGET-A", "Widget A", 6.0, 12.0, 120, 40),
        ("WIDGET-B", "Widget B", 3.5, 8.0, 200, 60),
        ("GADGET-X", "Gadget X", 20.0, 45.0, 30, 10),
        ("PART-42", "Part 42", 1.2, 3.0, 500, 150),
    ]
    products = [
        c.post("/api/v1/products", json={
            "sku": sku, "name": name, "cost_price": cost, "selling_price": price,
            "reorder_level": ro, "safety_stock": ss,
            "preferred_supplier_id": suppliers[0]["id"],
        })
        for sku, name, cost, price, ro, ss in catalog
    ]
    print("==> master data created")

    # opening stock via purchase orders (qty capped so each stays under the
    # 5000 auto-approval limit -> no manual approval step needed)
    for p in products:
        qty = min(400, max(50, int(2500 / max(p["cost_price"], 1))))
        po = c.post("/api/v1/purchasing/orders", json={
            "supplier_id": suppliers[0]["id"], "warehouse_id": wh["id"],
            "lines": [{"product_id": p["id"], "quantity": qty, "unit_cost": p["cost_price"]}],
        })
        c.post(f"/api/v1/purchasing/orders/{po['id']}/submit")
        c.post(f"/api/v1/purchasing/orders/{po['id']}/receive")
        c.post(f"/api/v1/purchasing/orders/{po['id']}/bill")
    print("==> opening stock received")

    start = date.today() - timedelta(days=args.days)
    made = 0
    for d in range(args.days):
        day = (start + timedelta(days=d)).isoformat()
        for _ in range(random.randint(1, 2)):
            lines = [
                {"product_id": p["id"], "quantity": random.randint(2, 12), "tax_rate": 0.1}
                for p in random.sample(products, random.randint(1, 3))
            ]
            so = c.post("/api/v1/sales/orders", json={
                "customer_id": random.choice(customers)["id"],
                "warehouse_id": wh["id"], "order_date": day, "lines": lines,
            })
            c.post(f"/api/v1/sales/orders/{so['id']}/confirm")
            c.post(f"/api/v1/sales/orders/{so['id']}/deliver-invoice")
            made += 1
    print(f"==> {made} sales orders delivered & invoiced")

    # supplier price anomaly: repeat buys from one supplier, last two spiked
    for k in range(9):
        spike = 1.0 if k < 7 else 1.45
        po = c.post("/api/v1/purchasing/orders", json={
            "supplier_id": suppliers[1]["id"], "warehouse_id": wh["id"],
            "lines": [{"product_id": products[0]["id"], "quantity": 60,
                       "unit_cost": round(products[0]["cost_price"] * spike, 4), "tax_rate": 0.1}],
        })
        c.post(f"/api/v1/purchasing/orders/{po['id']}/submit")
        c.post(f"/api/v1/purchasing/orders/{po['id']}/receive")
        c.post(f"/api/v1/purchasing/orders/{po['id']}/bill")

    # manufacturing: Gadget X = 2x Widget A + 4x Part 42
    c.post("/api/v1/manufacturing/boms", json={
        "product_id": products[2]["id"], "output_quantity": 1,
        "lines": [
            {"component_id": products[0]["id"], "quantity": 2},
            {"component_id": products[3]["id"], "quantity": 4, "scrap_rate": 0.05},
        ],
    })
    mo = c.post("/api/v1/manufacturing/orders", json={
        "product_id": products[2]["id"], "warehouse_id": wh["id"], "quantity": 25,
    })
    c.post(f"/api/v1/manufacturing/orders/{mo['id']}/release")
    c.post(f"/api/v1/manufacturing/orders/{mo['id']}/issue-materials")
    c.post(f"/api/v1/manufacturing/orders/{mo['id']}/complete")
    c.post("/api/v1/manufacturing/orders", json={
        "product_id": products[2]["id"], "warehouse_id": wh["id"], "quantity": 40,
    })
    print("==> manufacturing: 1 BOM, 2 production orders")

    c.post("/api/v1/ai/monitor/run")
    pnl = c.get("/api/v1/accounting/reports/profit-loss")
    print("\n=== Demo data ready ===")
    print("  Web:      (your frontend URL)")
    print(f"  email:    {args.email}")
    print(f"  password: {args.password}")
    print(f"  revenue {pnl['revenue']}  net profit {pnl['net_profit']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

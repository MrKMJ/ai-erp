"""Seed a demo tenant with master data, ~90 days of transactions and a BOM.

    python -m scripts.seed            # create demo tenant if absent
    python -m scripts.seed --reset    # delete the existing demo tenant first

Prints login credentials at the end.
"""
from __future__ import annotations

import random
import sys
from datetime import date, timedelta

from sqlalchemy import delete, select

from app.core.database import SessionLocal, create_all
from app.core.security import hash_password
from app.models.master import Product, Supplier, Warehouse
from app.models.tenant import Tenant
from app.models.user import User
from app.services import inventory_service as inv
from app.services import manufacturing_service as mfg
from app.services import purchasing_service as pur
from app.services import sales_service as sal
from app.services.accounting_service import ensure_chart_of_accounts
from app.services.recommendations import run_monitor

DEMO_EMAIL = "owner@demo-erp.com"
DEMO_PASSWORD = "demo12345"
random.seed(42)


def _reset(db, tenant_id: str) -> None:
    """Delete every row belonging to the demo tenant, across all tenant tables."""
    import app.models  # noqa: F401
    from app.models.base import Base

    db.execute(delete(Tenant).where(Tenant.id == tenant_id))
    for table in reversed(Base.metadata.sorted_tables):
        if "tenant_id" in table.c:
            db.execute(delete(table).where(table.c.tenant_id == tenant_id))
    db.commit()


def _provision(db):
    from app.api.routes.auth import _provision_roles

    tenant = db.execute(select(Tenant).where(Tenant.slug == "demo")).scalar_one_or_none()
    if tenant and "--reset" in sys.argv:
        print("Resetting existing demo tenant...")
        _reset(db, tenant.id)
        tenant = None
    if tenant:
        print("Demo tenant already exists; run with --reset to rebuild it.")
        return None
    tenant = Tenant(name="Demo Manufacturing Co", slug="demo", base_currency="USD")
    db.add(tenant)
    db.flush()
    roles = _provision_roles(db, tenant.id)
    owner = User(tenant_id=tenant.id, email=DEMO_EMAIL, full_name="Demo Owner",
                 hashed_password=hash_password(DEMO_PASSWORD), is_owner=True)
    owner.roles = [roles["owner"]]
    db.add(owner)
    ensure_chart_of_accounts(db, tenant.id)
    db.flush()
    return tenant, owner


def main() -> None:
    create_all()
    db = SessionLocal()
    try:
        provisioned = _provision(db)
        if provisioned is None:
            return
        tenant, owner = provisioned
        tid, uid = tenant.id, owner.id

        wh = Warehouse(tenant_id=tid, code="MAIN", name="Main Warehouse", is_default=True)
        db.add(wh)
        db.flush()

        suppliers = []
        for i, (name, lead, rel) in enumerate([
            ("Acme Components", 21, 0.97),
            ("Global Parts Ltd", 30, 0.74),
            ("QuickSupply Inc", 10, 0.90),
        ]):
            s = Supplier(tenant_id=tid, code=f"SUP{i+1}", name=name, lead_time_days=lead,
                         reliability=rel, payment_terms_days=30)
            db.add(s)
            suppliers.append(s)
        db.flush()

        customers = []
        from app.models.master import Customer
        for i, name in enumerate(["Northwind Retail", "Contoso Stores", "Fabrikam Wholesale"]):
            c = Customer(tenant_id=tid, code=f"CUST{i+1}", name=name, payment_terms_days=30)
            db.add(c)
            customers.append(c)
        db.flush()

        products = []
        catalog = [
            ("WIDGET-A", "Widget A", 6.0, 12.0, 120, 40),
            ("WIDGET-B", "Widget B", 3.5, 8.0, 200, 60),
            ("GADGET-X", "Gadget X", 20.0, 45.0, 30, 10),
            ("PART-42", "Part 42", 1.2, 3.0, 500, 150),
        ]
        for sku, name, cost, price, reorder, safety in catalog:
            p = Product(tenant_id=tid, sku=sku, name=name, cost_price=cost, selling_price=price,
                        reorder_level=reorder, safety_stock=safety,
                        preferred_supplier_id=suppliers[0].id)
            db.add(p)
            products.append(p)
        db.flush()

        # opening stock — deliberately lean so some products drift toward reorder
        for p in products:
            inv.post_movement(db, tenant_id=tid, product_id=p.id, warehouse_id=wh.id,
                              quantity=float(p.reorder_level) * 2 + 40,
                              transaction_type="adjustment",
                              unit_cost=float(p.cost_price), note="opening balance", created_by=uid)
        db.commit()

        # ~90 days of sales
        start = date.today() - timedelta(days=90)
        for day in range(90):
            d = start + timedelta(days=day)
            for _ in range(random.randint(1, 3)):
                cust = random.choice(customers)
                lines = []
                for p in random.sample(products, random.randint(1, 3)):
                    lines.append({"product_id": p.id,
                                  "quantity": random.randint(2, 15),
                                  "tax_rate": 0.1})
                order = sal.create_order(db, tid, uid, {
                    "customer_id": cust.id, "warehouse_id": wh.id,
                    "order_date": d, "lines": lines,
                })
                sal.confirm_order(db, tid, uid, order.id)
                sal.deliver_and_invoice(db, tid, uid, order.id)
            db.commit()

        # recurring purchases from one supplier for product[0], last two spiked
        # -> produces a clean SUPPLIER_ANOMALY recommendation
        from app.models.purchasing import PurchaseOrder

        for k in range(9):
            sup = suppliers[1]
            spike = 1.0 if k < 7 else 1.45
            po = pur.create_order(db, tid, uid, {
                "supplier_id": sup.id, "warehouse_id": wh.id,
                "lines": [{"product_id": products[0].id, "quantity": 60,
                           "unit_cost": round(float(products[0].cost_price) * spike, 4),
                           "tax_rate": 0.1}],
            })
            pur.submit_for_approval(db, tid, uid, po.id)
            po = db.get(PurchaseOrder, po.id)
            if po.status == "approved":
                pur.receive(db, tid, uid, po.id)
                pur.create_bill(db, tid, uid, po.id)
            db.commit()

        # Manufacturing: Gadget X is assembled from 2x Widget A + 4x Part 42
        bom = mfg.create_bom(db, tid, uid, {
            "product_id": products[2].id, "output_quantity": 1,
            "lines": [
                {"component_id": products[0].id, "quantity": 2},
                {"component_id": products[3].id, "quantity": 4, "scrap_rate": 0.05},
            ],
        })
        db.commit()
        mo = mfg.create_order(db, tid, uid, {
            "product_id": products[2].id, "warehouse_id": wh.id, "quantity": 25,
        })
        mfg.release(db, tid, uid, mo.id)
        mfg.issue_materials(db, tid, uid, mo.id)
        mfg.complete(db, tid, uid, mo.id)
        db.commit()
        # a second one left planned so the UI shows the lifecycle
        mfg.create_order(db, tid, uid, {
            "product_id": products[2].id, "warehouse_id": wh.id, "quantity": 40,
        })
        db.commit()

        run_monitor(db, tid)
        db.commit()

        print("\n=== Demo data ready ===")
        print("  API:      http://localhost:8000/docs")
        print(f"  email:    {DEMO_EMAIL}")
        print(f"  password: {DEMO_PASSWORD}")
        print(f"  tenant:   {tid}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

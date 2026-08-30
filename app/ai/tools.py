"""AI tool layer.

Every tool is an explicit, deterministic function over ERP services. The LLM
never computes financial figures itself — it selects tools, passes arguments,
and narrates the structured results.

Each tool declares:
  - required permission (checked against the calling user)
  - risk level (read | low | medium | high | very_high)
  - JSON schema of arguments (for the LLM / API validation)
Write tools with risk >= "low" only produce DRAFTS or approval requests.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import AIRecommendation
from app.models.master import Product, Supplier, Warehouse
from app.services import accounting_service as acc
from app.services import forecasting
from app.services import inventory_service as inv
from app.services import purchasing_service as pur
from app.services import sales_service as sal


@dataclass
class ToolContext:
    db: Session
    tenant_id: str
    user_id: str
    has_permission: Callable[[str], bool]


@dataclass
class Tool:
    name: str
    description: str
    permission: str
    risk: str
    parameters: dict[str, Any]
    handler: Callable[[ToolContext, dict], Any]
    keywords: list[str] = field(default_factory=list)


REGISTRY: dict[str, Tool] = {}


def tool(**kw):
    def deco(fn):
        REGISTRY[kw["name"]] = Tool(handler=fn, **kw)
        return fn

    return deco


def _default_warehouse(ctx: ToolContext) -> str:
    wh = ctx.db.execute(
        select(Warehouse).where(Warehouse.tenant_id == ctx.tenant_id)
        .order_by(Warehouse.is_default.desc())
    ).scalars().first()
    if wh is None:
        raise ValueError("No warehouse configured")
    return wh.id


# --------------------------------------------------------------------------- READ
@tool(
    name="get_sales_summary", description="Total sales revenue and invoice count for the period.",
    permission="sales.read", risk="read",
    parameters={"type": "object", "properties": {}}, keywords=["sales", "revenue", "sold"],
)
def _sales_summary(ctx: ToolContext, args: dict):
    pnl = acc.profit_and_loss(ctx.db, ctx.tenant_id)
    return {"revenue": pnl["revenue"], "net_profit": pnl["net_profit"]}


@tool(
    name="get_profit_loss", description="Profit & loss statement (revenue, expenses, net profit).",
    permission="accounting.report.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["profit", "loss", "p&l", "pnl", "margin", "net income", "earnings"],
)
def _pnl(ctx: ToolContext, args: dict):
    return acc.profit_and_loss(ctx.db, ctx.tenant_id)


@tool(
    name="get_trial_balance", description="Trial balance: every account with its net balance.",
    permission="accounting.read", risk="read",
    parameters={"type": "object", "properties": {}}, keywords=["trial balance", "ledger", "accounts"],
)
def _tb(ctx: ToolContext, args: dict):
    return {"accounts": acc.trial_balance(ctx.db, ctx.tenant_id)}


@tool(
    name="get_receivables", description="Outstanding customer invoices (who owes us money).",
    permission="sales.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["receivable", "owes us", "ar", "unpaid invoice", "collect"],
)
def _ar(ctx: ToolContext, args: dict):
    rows = sal.outstanding_receivables(ctx.db, ctx.tenant_id)
    return {"total": round(sum(r["balance"] for r in rows), 2), "invoices": rows}


@tool(
    name="get_payables", description="Outstanding supplier bills (who we owe money to).",
    permission="purchase.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["payable", "we owe", "ap", "supplier bill", "pay supplier"],
)
def _ap(ctx: ToolContext, args: dict):
    rows = pur.outstanding_payables(ctx.db, ctx.tenant_id)
    return {"total": round(sum(r["balance"] for r in rows), 2), "bills": rows}


@tool(
    name="get_cash_flow", description="Short-term cash flow forecast from AR, AP and bank balance.",
    permission="accounting.report.read", risk="read",
    parameters={"type": "object", "properties": {
        "horizon_days": {"type": "integer", "default": 30}}},
    keywords=["cash", "cash flow", "liquidity", "runway", "shortfall"],
)
def _cash(ctx: ToolContext, args: dict):
    return forecasting.cash_flow_forecast(ctx.db, ctx.tenant_id, int(args.get("horizon_days", 30)))


@tool(
    name="get_inventory_position", description="Stock on hand per product with reorder flags.",
    permission="inventory.read", risk="read",
    parameters={"type": "object", "properties": {
        "only_below_reorder": {"type": "boolean", "default": False}}},
    keywords=["inventory", "stock", "on hand", "low stock", "reorder", "warehouse"],
)
def _inv_pos(ctx: ToolContext, args: dict):
    rows = inv.position(ctx.db, ctx.tenant_id)
    if args.get("only_below_reorder"):
        rows = [r for r in rows if r["below_reorder"]]
    return {"products": rows}


@tool(
    name="get_demand_forecast", description="Forecast demand for a product over a horizon.",
    permission="inventory.read", risk="read",
    parameters={"type": "object", "properties": {
        "product_id": {"type": "string"}, "sku": {"type": "string"},
        "horizon_days": {"type": "integer", "default": 30}}},
    keywords=["forecast", "demand", "predict sales", "how much will we sell"],
)
def _demand(ctx: ToolContext, args: dict):
    pid = _resolve_product(ctx, args)
    return forecasting.demand_forecast(ctx.db, ctx.tenant_id, pid, int(args.get("horizon_days", 30)))


@tool(
    name="get_stockout_risk", description="Stockout risk assessment for one or all stocked products.",
    permission="inventory.read", risk="read",
    parameters={"type": "object", "properties": {
        "product_id": {"type": "string"}, "sku": {"type": "string"}}},
    keywords=["stockout", "run out", "shortage", "will we have enough"],
)
def _risk(ctx: ToolContext, args: dict):
    if args.get("product_id") or args.get("sku"):
        pid = _resolve_product(ctx, args)
        return forecasting.stockout_risk(ctx.db, ctx.tenant_id, pid)
    out = []
    for r in inv.position(ctx.db, ctx.tenant_id):
        assessment = forecasting.stockout_risk(ctx.db, ctx.tenant_id, r["product_id"])
        if assessment["risk"] in ("high", "medium"):
            out.append({"sku": r["sku"], "name": r["name"], **assessment})
    return {"at_risk": out}


@tool(
    name="get_supplier_performance", description="Suppliers with lead time, reliability and price anomalies.",
    permission="purchase.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["supplier", "vendor", "price increase", "reliability", "lead time"],
)
def _supplier_perf(ctx: ToolContext, args: dict):
    from app.services import anomaly

    suppliers = ctx.db.execute(
        select(Supplier).where(Supplier.tenant_id == ctx.tenant_id)
    ).scalars().all()
    return {
        "suppliers": [
            {"name": s.name, "lead_time_days": s.lead_time_days,
             "reliability": float(s.reliability), "payment_terms_days": s.payment_terms_days}
            for s in suppliers
        ],
        "price_anomalies": anomaly.supplier_price_anomalies(ctx.db, ctx.tenant_id),
    }


@tool(
    name="get_recommendations", description="Open AI recommendations for the tenant.",
    permission="ai.recommendation.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["recommendation", "alerts", "what should i do", "issues"],
)
def _recs(ctx: ToolContext, args: dict):
    rows = ctx.db.execute(
        select(AIRecommendation).where(
            AIRecommendation.tenant_id == ctx.tenant_id, AIRecommendation.status == "open"
        ).order_by(AIRecommendation.severity.desc())
    ).scalars().all()
    return {"recommendations": [
        {"id": r.id, "type": r.type, "severity": r.severity, "title": r.title,
         "description": r.description, "estimated_impact": r.estimated_impact}
        for r in rows
    ]}


@tool(
    name="get_production_plan",
    description="Open production orders with material shortfalls against current stock.",
    permission="manufacturing.read", risk="read",
    parameters={"type": "object", "properties": {}},
    keywords=["production", "manufacturing", "work order", "shop floor", "make", "bom"],
)
def _production_plan(ctx: ToolContext, args: dict):
    from app.models.manufacturing import ProductionOrder
    from app.services import manufacturing_service as mfg

    orders = ctx.db.execute(
        select(ProductionOrder).where(
            ProductionOrder.tenant_id == ctx.tenant_id,
            ProductionOrder.status.in_(("planned", "released", "in_progress")),
        )
    ).scalars().all()
    out = []
    for o in orders:
        product = ctx.db.get(Product, o.product_id)
        mats = mfg.material_availability(ctx.db, ctx.tenant_id, o.id)
        out.append({
            "number": o.number, "product": product.name if product else "?",
            "quantity": float(o.quantity), "status": o.status,
            "shortfalls": [m for m in mats if m["shortfall"] > 0],
        })
    return {"orders": out}


# ----------------------------------------------------------------------- ACTIONS (draft only)
@tool(
    name="create_purchase_order",
    description="Create a DRAFT purchase order and submit it to the approval workflow. "
                "Never executes payment; a human approves it.",
    permission="purchase.order.write", risk="low",
    parameters={"type": "object", "required": ["product_id", "quantity"], "properties": {
        "product_id": {"type": "string"}, "sku": {"type": "string"},
        "quantity": {"type": "number"}, "supplier_id": {"type": "string"},
        "unit_cost": {"type": "number"}}},
    keywords=["create po", "order stock", "purchase order", "reorder"],
)
def _create_po(ctx: ToolContext, args: dict):
    pid = _resolve_product(ctx, args)
    product = ctx.db.get(Product, pid)
    supplier_id = args.get("supplier_id") or product.preferred_supplier_id
    if not supplier_id:
        raise ValueError("No supplier specified and product has no preferred supplier")
    order = pur.create_order(
        ctx.db, ctx.tenant_id, ctx.user_id,
        {
            "supplier_id": supplier_id,
            "warehouse_id": _default_warehouse(ctx),
            "lines": [{
                "product_id": pid, "quantity": args["quantity"],
                "unit_cost": args.get("unit_cost", float(product.cost_price)),
            }],
        },
        source="ai",
    )
    decision = pur.submit_for_approval(ctx.db, ctx.tenant_id, ctx.user_id, order.id, actor_kind="ai")
    return {
        "purchase_order_id": order.id, "number": order.number, "total": float(order.total),
        "workflow": decision,
        "note": "Draft PO created and routed for human approval. Nothing is committed yet.",
    }


@tool(
    name="create_sales_quote",
    description="Create a DRAFT sales order (quotation) for a customer.",
    permission="sales.order.write", risk="low",
    parameters={"type": "object", "required": ["customer_id", "lines"], "properties": {
        "customer_id": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "object"}}}},
    keywords=["quote", "quotation", "sales order", "draft order"],
)
def _create_quote(ctx: ToolContext, args: dict):
    order = sal.create_order(
        ctx.db, ctx.tenant_id, ctx.user_id,
        {"customer_id": args["customer_id"], "warehouse_id": _default_warehouse(ctx),
         "lines": args["lines"]},
    )
    return {"sales_order_id": order.id, "number": order.number, "total": float(order.total),
            "status": order.status}


def _resolve_product(ctx: ToolContext, args: dict) -> str:
    if args.get("product_id"):
        return args["product_id"]
    if args.get("sku"):
        p = ctx.db.execute(
            select(Product).where(Product.tenant_id == ctx.tenant_id, Product.sku == args["sku"])
        ).scalar_one_or_none()
        if p:
            return p.id
    raise ValueError("Provide product_id or a valid sku")


def tool_specs() -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "risk": t.risk,
         "permission": t.permission, "parameters": t.parameters}
        for t in REGISTRY.values()
    ]

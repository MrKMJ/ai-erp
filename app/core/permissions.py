"""Granular permission catalogue (resource.action) + role templates.

Permissions are stored in the DB (see models/rbac.py) but this module is the
source of truth for what exists and which roles get what by default.
"""
from __future__ import annotations

# resource.action -> human description
PERMISSIONS: dict[str, str] = {
    # master data
    "customer.read": "View customers",
    "customer.write": "Create / edit customers",
    "supplier.read": "View suppliers",
    "supplier.write": "Create / edit suppliers",
    "product.read": "View products",
    "product.write": "Create / edit products",
    "warehouse.read": "View warehouses",
    "warehouse.write": "Create / edit warehouses",
    # sales
    "sales.read": "View sales orders and invoices",
    "sales.order.write": "Create / edit sales orders",
    "sales.invoice.post": "Post sales invoices to the ledger",
    "sales.payment.create": "Record customer payments",
    # purchasing
    "purchase.read": "View purchase orders and bills",
    "purchase.order.write": "Create / edit purchase orders",
    "purchase.order.approve": "Approve purchase orders",
    "purchase.receipt.write": "Record goods receipts",
    "purchase.bill.post": "Post supplier bills to the ledger",
    "purchase.payment.create": "Record supplier payments",
    # inventory
    "inventory.read": "View inventory positions and ledger",
    "inventory.adjust": "Post inventory adjustments",
    # accounting
    "accounting.read": "View chart of accounts and journals",
    "accounting.journal.post": "Post manual journal entries",
    "accounting.report.read": "View financial reports (P&L, balance sheet)",
    # manufacturing
    "manufacturing.read": "View BOMs and production orders",
    "manufacturing.bom.write": "Create / edit bills of materials",
    "manufacturing.order.write": "Create production orders",
    "manufacturing.execute": "Release, issue materials, complete production orders",
    # AI
    "ai.chat": "Use the AI assistant (read-only tools)",
    "ai.action": "Let the AI create drafts / initiate workflows",
    "ai.recommendation.read": "View AI recommendations",
    # admin
    "admin.users": "Manage users and roles",
    "admin.settings": "Manage tenant settings",
}

# Tool risk classification used by the AI policy engine.
TOOL_RISK = {
    "READ": "read",
    "CREATE_DRAFT": "low",
    "MODIFY_TRANSACTION": "medium",
    "POST_ACCOUNTING": "high",
    "PAY_MONEY": "very_high",
}

ROLE_TEMPLATES: dict[str, list[str]] = {
    "owner": list(PERMISSIONS.keys()),
    "admin": list(PERMISSIONS.keys()),
    "accountant": [
        "customer.read", "supplier.read", "product.read", "warehouse.read",
        "sales.read", "purchase.read", "inventory.read",
        "accounting.read", "accounting.journal.post", "accounting.report.read",
        "sales.invoice.post", "purchase.bill.post",
        "sales.payment.create", "purchase.payment.create",
        "ai.chat", "ai.recommendation.read",
    ],
    "sales_rep": [
        "customer.read", "customer.write", "product.read", "inventory.read",
        "sales.read", "sales.order.write",
        "ai.chat", "ai.recommendation.read",
    ],
    "purchaser": [
        "supplier.read", "supplier.write", "product.read", "inventory.read",
        "purchase.read", "purchase.order.write", "purchase.receipt.write",
        "ai.chat", "ai.action", "ai.recommendation.read",
    ],
    "warehouse": [
        "product.read", "warehouse.read", "inventory.read", "inventory.adjust",
        "purchase.receipt.write", "manufacturing.read", "ai.chat",
    ],
    "production": [
        "product.read", "warehouse.read", "inventory.read",
        "manufacturing.read", "manufacturing.bom.write", "manufacturing.order.write",
        "manufacturing.execute", "ai.chat", "ai.recommendation.read",
    ],
    "viewer": [k for k in PERMISSIONS if k.endswith(".read")],
}

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class OrmModel(BaseModel):
    model_config = {"from_attributes": True}


# ---- master data ----
class CustomerIn(BaseModel):
    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    currency_code: str = "USD"
    payment_terms_days: int = 30
    credit_limit: float = 0


class SupplierIn(BaseModel):
    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    currency_code: str = "USD"
    payment_terms_days: int = 30
    lead_time_days: int = 14
    reliability: float = 0.95


class ProductIn(BaseModel):
    sku: str
    name: str
    category_id: str | None = None
    unit_id: str | None = None
    tax_code_id: str | None = None
    preferred_supplier_id: str | None = None
    cost_price: float = 0
    selling_price: float = 0
    reorder_level: float = 0
    safety_stock: float = 0
    is_stocked: bool = True


class WarehouseIn(BaseModel):
    code: str
    name: str
    is_default: bool = False


# ---- sales ----
class OrderLineIn(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float | None = None
    tax_rate: float = 0


class SalesOrderIn(BaseModel):
    customer_id: str
    warehouse_id: str
    order_date: date | None = None
    notes: str = ""
    lines: list[OrderLineIn]


class PaymentIn(BaseModel):
    customer_id: str
    invoice_id: str | None = None
    amount: float = Field(gt=0)
    method: str = "bank"
    payment_date: date | None = None


# ---- purchasing ----
class POLineIn(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_cost: float | None = None
    tax_rate: float = 0


class PurchaseOrderIn(BaseModel):
    supplier_id: str
    warehouse_id: str
    order_date: date | None = None
    lines: list[POLineIn]


class ReceiptLineIn(BaseModel):
    product_id: str
    quantity: float


class ApprovalDecisionIn(BaseModel):
    approve: bool
    note: str = ""


# ---- accounting ----
class JournalLineIn(BaseModel):
    account_id: str | None = None
    tag: str | None = None
    debit: float = 0
    credit: float = 0
    memo: str = ""


class JournalEntryIn(BaseModel):
    entry_date: date
    description: str
    lines: list[JournalLineIn]


class InventoryAdjustIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: float
    unit_cost: float = 0
    note: str = ""


# ---- AI ----
class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None
    module: str | None = None


class ToolCallIn(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}

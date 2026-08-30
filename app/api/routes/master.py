from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.database import get_db
from app.core.deps import CurrentUser, require
from app.core.exceptions import NotFound
from app.models.master import (
    Customer,
    Product,
    ProductCategory,
    Supplier,
    TaxCode,
    Unit,
    Warehouse,
)
from app.schemas.common import CustomerIn, ProductIn, SupplierIn, WarehouseIn

router = APIRouter(tags=["master-data"])


def _crud(path: str, model, schema: type[BaseModel], read_perm: str, write_perm: str, name: str):
    sub = APIRouter(prefix=f"/{path}")

    @sub.get("")
    def list_(current: CurrentUser = Depends(require(read_perm)), db: Session = Depends(get_db),
              limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
              q: str | None = Query(None, description="case-insensitive name/code filter")):
        stmt = select(model).where(model.tenant_id == current.tenant_id)
        if q and hasattr(model, "name"):
            stmt = stmt.where(model.name.ilike(f"%{q}%"))
        stmt = stmt.order_by(model.created_at.desc()).limit(limit).offset(offset)
        return [_dump(r) for r in db.execute(stmt).scalars().all()]

    @sub.post("", status_code=201)
    def create_(body: schema, current: CurrentUser = Depends(require(write_perm)),
                db: Session = Depends(get_db)):
        obj = model(tenant_id=current.tenant_id, **body.model_dump(exclude_none=True))
        db.add(obj)
        db.flush()
        record(db, tenant_id=current.tenant_id, actor_id=current.id, action="create",
               entity_type=name, entity_id=obj.id, summary=f"Created {name}")
        db.commit()
        return _dump(obj)

    @sub.get("/{item_id}")
    def get_(item_id: str, current: CurrentUser = Depends(require(read_perm)),
             db: Session = Depends(get_db)):
        obj = db.get(model, item_id)
        if obj is None or obj.tenant_id != current.tenant_id:
            raise NotFound(name)
        return _dump(obj)

    @sub.patch("/{item_id}")
    def update_(item_id: str, body: schema,
                current: CurrentUser = Depends(require(write_perm)), db: Session = Depends(get_db)):
        obj = db.get(model, item_id)
        if obj is None or obj.tenant_id != current.tenant_id:
            raise NotFound(name)
        changes = {}
        for k, v in body.model_dump(exclude_unset=True).items():
            if getattr(obj, k, None) != v:
                changes[k] = [getattr(obj, k, None), v]
                setattr(obj, k, v)
        record(db, tenant_id=current.tenant_id, actor_id=current.id, action="update",
               entity_type=name, entity_id=obj.id, changes=_json(changes))
        db.commit()
        return _dump(obj)

    router.include_router(sub)


def _dump(obj) -> dict[str, Any]:
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        out[col.name] = float(val) if hasattr(val, "quantize") else val
    return out


def _json(d):
    import json
    return json.loads(json.dumps(d, default=str))


_crud("customers", Customer, CustomerIn, "customer.read", "customer.write", "customer")
_crud("suppliers", Supplier, SupplierIn, "supplier.read", "supplier.write", "supplier")
_crud("products", Product, ProductIn, "product.read", "product.write", "product")
_crud("warehouses", Warehouse, WarehouseIn, "warehouse.read", "warehouse.write", "warehouse")


class _NamedIn(BaseModel):
    name: str


class _CodeNameIn(BaseModel):
    code: str
    name: str
    rate: float = 0


@router.get("/product-categories")
def list_categories(current: CurrentUser = Depends(require("product.read")),
                    db: Session = Depends(get_db)):
    rows = db.execute(
        select(ProductCategory).where(ProductCategory.tenant_id == current.tenant_id)
    ).scalars().all()
    return [_dump(r) for r in rows]


@router.post("/product-categories", status_code=201)
def create_category(body: _NamedIn, current: CurrentUser = Depends(require("product.write")),
                    db: Session = Depends(get_db)):
    obj = ProductCategory(tenant_id=current.tenant_id, name=body.name)
    db.add(obj)
    db.commit()
    return _dump(obj)


@router.get("/units")
def list_units(current: CurrentUser = Depends(require("product.read")),
               db: Session = Depends(get_db)):
    return [_dump(r) for r in db.execute(
        select(Unit).where(Unit.tenant_id == current.tenant_id)
    ).scalars().all()]


@router.post("/units", status_code=201)
def create_unit(body: _CodeNameIn, current: CurrentUser = Depends(require("product.write")),
                db: Session = Depends(get_db)):
    obj = Unit(tenant_id=current.tenant_id, code=body.code, name=body.name)
    db.add(obj)
    db.commit()
    return _dump(obj)


@router.get("/tax-codes")
def list_tax(current: CurrentUser = Depends(require("product.read")),
             db: Session = Depends(get_db)):
    return [_dump(r) for r in db.execute(
        select(TaxCode).where(TaxCode.tenant_id == current.tenant_id)
    ).scalars().all()]


@router.post("/tax-codes", status_code=201)
def create_tax(body: _CodeNameIn, current: CurrentUser = Depends(require("product.write")),
               db: Session = Depends(get_db)):
    obj = TaxCode(tenant_id=current.tenant_id, code=body.code, name=body.name, rate=body.rate)
    db.add(obj)
    db.commit()
    return _dump(obj)

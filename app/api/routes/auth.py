from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require
from app.core.exceptions import ERPError
from app.core.permissions import PERMISSIONS, ROLE_TEMPLATES
from app.core.security import create_access_token, hash_password, verify_password
from app.models.rbac import Permission, Role
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import CreateUser, RegisterTenant, Token, UserOut
from app.services.accounting_service import ensure_chart_of_accounts

router = APIRouter(prefix="/auth", tags=["auth"])


def _sync_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.execute(select(Permission)).scalars()}
    for code, desc in PERMISSIONS.items():
        if code not in existing:
            p = Permission(code=code, description=desc)
            db.add(p)
            existing[code] = p
    db.flush()
    return existing


def _provision_roles(db: Session, tenant_id: str) -> dict[str, Role]:
    perms = _sync_permissions(db)
    roles: dict[str, Role] = {}
    for name, codes in ROLE_TEMPLATES.items():
        role = Role(tenant_id=tenant_id, name=name, description=f"{name} role")
        role.permissions = [perms[c] for c in codes if c in perms]
        db.add(role)
        roles[name] = role
    db.flush()
    return roles


@router.post("/register", response_model=Token, status_code=201)
def register_tenant(body: RegisterTenant, db: Session = Depends(get_db)):
    if db.execute(select(Tenant).where(Tenant.slug == body.slug)).scalar_one_or_none():
        raise ERPError("Slug already taken")
    tenant = Tenant(name=body.company_name, slug=body.slug, base_currency=body.base_currency)
    db.add(tenant)
    db.flush()

    roles = _provision_roles(db, tenant.id)
    admin = User(
        tenant_id=tenant.id, email=body.admin_email.lower(), full_name=body.admin_name,
        hashed_password=hash_password(body.admin_password), is_owner=True,
    )
    admin.roles = [roles["owner"]]
    db.add(admin)

    ensure_chart_of_accounts(db, tenant.id)
    db.commit()

    token = create_access_token(admin.id, tenant.id)
    return Token(access_token=token, tenant_id=tenant.id, user_id=admin.id)


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.email == form.username.lower())
    ).scalars().first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise ERPError("Incorrect email or password", status_code=401)
    if not user.is_active:
        raise ERPError("User is inactive", status_code=403)
    token = create_access_token(user.id, user.tenant_id)
    return Token(access_token=token, tenant_id=user.tenant_id, user_id=user.id)


@router.get("/me", response_model=UserOut)
def me(current: CurrentUser = Depends(get_current_user)):
    return UserOut(
        id=current.user.id, email=current.user.email, full_name=current.user.full_name,
        is_owner=current.user.is_owner,
        roles=[r.name for r in current.user.roles],
        permissions=sorted(current.permissions) if not current.user.is_owner
        else sorted(PERMISSIONS.keys()),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(current: CurrentUser = Depends(require("admin.users")),
               db: Session = Depends(get_db)):
    users = db.execute(select(User).where(User.tenant_id == current.tenant_id)).scalars().all()
    out = []
    for u in users:
        perms = {p.code for r in u.roles for p in r.permissions}
        out.append(UserOut(id=u.id, email=u.email, full_name=u.full_name, is_owner=u.is_owner,
                           roles=[r.name for r in u.roles], permissions=sorted(perms)))
    return out


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: CreateUser, current: CurrentUser = Depends(require("admin.users")),
                db: Session = Depends(get_db)):
    if db.execute(
        select(User).where(User.tenant_id == current.tenant_id, User.email == body.email.lower())
    ).scalar_one_or_none():
        raise ERPError("Email already exists in this tenant")
    roles = db.execute(
        select(Role).where(Role.tenant_id == current.tenant_id, Role.name.in_(body.roles))
    ).scalars().all()
    user = User(
        tenant_id=current.tenant_id, email=body.email.lower(), full_name=body.full_name,
        hashed_password=hash_password(body.password),
    )
    user.roles = list(roles)
    db.add(user)
    db.commit()
    perms = {p.code for r in user.roles for p in r.permissions}
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, is_owner=False,
                   roles=[r.name for r in user.roles], permissions=sorted(perms))


@router.get("/roles")
def list_roles(current: CurrentUser = Depends(require("admin.users")),
               db: Session = Depends(get_db)):
    roles = db.execute(select(Role).where(Role.tenant_id == current.tenant_id)).scalars().all()
    return [{"name": r.name, "permissions": [p.code for p in r.permissions]} for r in roles]

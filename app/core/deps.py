from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import ERPError, PermissionDenied
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


@dataclass
class CurrentUser:
    user: User
    tenant_id: str
    permissions: set[str]

    @property
    def id(self) -> str:
        return self.user.id

    def has(self, code: str) -> bool:
        return self.user.is_owner or code in self.permissions

    def require(self, code: str) -> None:
        if not self.has(code):
            raise PermissionDenied(f"Missing permission: {code}")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> CurrentUser:
    try:
        payload = decode_access_token(token)
    except Exception as exc:  # noqa: BLE001
        raise ERPError("Invalid or expired token", status_code=401) from exc

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active or user.tenant_id != payload.get("tid"):
        raise ERPError("User not found or inactive", status_code=401)

    perms: set[str] = set()
    for role in user.roles:
        perms.update(p.code for p in role.permissions)
    return CurrentUser(user=user, tenant_id=user.tenant_id, permissions=perms)


def require(permission: str):
    def _dep(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        current.require(permission)
        return current

    return _dep

from __future__ import annotations

import os

import pytest

_DB_PATH = os.path.join(os.path.dirname(__file__), "_test_ai_erp.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _DB_PATH.replace("\\", "/")
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["AI_PROVIDER"] = "rule"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.database import create_all, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)
    create_all()
    yield
    engine.dispose()
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def tenant(client):
    import uuid

    slug = f"acme-{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/v1/auth/register", json={
        "company_name": "Acme Co", "slug": slug,
        "admin_email": f"admin-{slug}@acme-erp.com", "admin_password": "password123",
        "admin_name": "Admin",
    })
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"token": data["access_token"], "tenant_id": data["tenant_id"],
            "user_id": data["user_id"], "headers": {"Authorization": f"Bearer {data['access_token']}"}}

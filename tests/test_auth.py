def test_register_and_me(client, tenant):
    r = client.get("/api/v1/auth/me", headers=tenant["headers"])
    assert r.status_code == 200
    body = r.json()
    assert body["is_owner"] is True
    assert "accounting.journal.post" in body["permissions"]


def test_login(client, tenant):
    # register created admin-<slug>@acme-erp.com / password123
    me = client.get("/api/v1/auth/me", headers=tenant["headers"]).json()
    r = client.post("/api/v1/auth/login", data={"username": me["email"], "password": "password123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_permission_enforced(client, tenant):
    # create a viewer user, confirm they cannot post journals
    r = client.post("/api/v1/auth/users", headers=tenant["headers"], json={
        "email": "viewer@acme-erp.com", "password": "password123", "roles": ["viewer"],
    })
    assert r.status_code == 201
    login = client.post("/api/v1/auth/login",
                        data={"username": "viewer@acme-erp.com", "password": "password123"}).json()
    h = {"Authorization": f"Bearer {login['access_token']}"}
    r = client.post("/api/v1/accounting/journal", headers=h, json={
        "entry_date": "2026-01-01", "description": "x",
        "lines": [{"tag": "bank", "debit": 10}, {"tag": "sales", "credit": 10}],
    })
    assert r.status_code == 403

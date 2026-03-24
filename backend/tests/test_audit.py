"""Tests for audit log generation on mutations."""
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_agent_create_generates_audit(client, admin_token):
    await client.post(
        "/api/agents",
        json={"name": "Audited", "role": "qa_inspector"},
        headers=auth_header(admin_token),
    )
    r = await client.get("/api/admin/audit-logs?action=create_agent", headers=auth_header(admin_token))
    assert r.status_code == 200
    logs = r.json()
    assert any(log["action"] == "create_agent" for log in logs)


@pytest.mark.asyncio
async def test_task_create_generates_audit(client, admin_token):
    await client.post(
        "/api/tasks",
        json={"title": "Audited Task"},
        headers=auth_header(admin_token),
    )
    r = await client.get("/api/admin/audit-logs?action=create_task", headers=auth_header(admin_token))
    assert r.status_code == 200
    logs = r.json()
    assert any(log["action"] == "create_task" for log in logs)


@pytest.mark.asyncio
async def test_login_success_generates_audit(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "testpass123"})
    # Need a token to read audit logs
    r = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "testpass123"})
    token = r.json()["access_token"]

    r = await client.get("/api/admin/audit-logs?action=login_success", headers=auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_login_failure_generates_audit(client, admin_user):
    await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})

    # Login to check audit logs
    r = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "testpass123"})
    token = r.json()["access_token"]

    r = await client.get("/api/admin/audit-logs?action=login_failed", headers=auth_header(token))
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_approval_decision_generates_audit(client, admin_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "test"},
        headers=auth_header(admin_token),
    )
    aid = r.json()["id"]
    await client.post(
        f"/api/approvals/{aid}/decide",
        json={"status": "approved"},
        headers=auth_header(admin_token),
    )

    r = await client.get("/api/admin/audit-logs?action=decide_approval", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert any(log["action"] == "decide_approval" for log in r.json())

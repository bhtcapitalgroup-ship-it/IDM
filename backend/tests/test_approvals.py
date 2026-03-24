"""Tests for approval creation, decision, and permission enforcement."""
import uuid
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_approval(client, admin_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "production_deployment", "description": "Deploy v1"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["action_type"] == "production_deployment"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_approve(client, admin_token):
    # Create
    r = await client.post(
        "/api/approvals",
        json={"action_type": "billing_change"},
        headers=auth_header(admin_token),
    )
    approval_id = r.json()["id"]

    # Approve
    r = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Looks good"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert r.json()["decision_reason"] == "Looks good"


@pytest.mark.asyncio
async def test_reject(client, admin_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "payout_change"},
        headers=auth_header(admin_token),
    )
    approval_id = r.json()["id"]

    r = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "rejected", "decision_reason": "Not safe"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_cannot_decide_twice(client, admin_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "test"},
        headers=auth_header(admin_token),
    )
    approval_id = r.json()["id"]

    # First decision
    await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved"},
        headers=auth_header(admin_token),
    )

    # Second decision should fail
    r = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "rejected"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "already decided" in r.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_decision_status(client, admin_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "test"},
        headers=auth_header(admin_token),
    )
    approval_id = r.json()["id"]

    r = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "maybe"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_list_approvals_pagination(client, admin_token):
    r = await client.get("/api/approvals?limit=5&offset=0", headers=auth_header(admin_token))
    assert r.status_code == 200

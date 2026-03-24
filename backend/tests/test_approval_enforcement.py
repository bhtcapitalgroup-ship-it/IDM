"""Tests proving approval enforcement actually blocks actions."""
import uuid
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_delete_agent_blocked_without_approval(client, admin_token, sample_agent):
    """Deleting an agent should be blocked and return 409 with approval ID."""
    r = await client.delete(f"/api/agents/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 409
    assert "Approval required" in r.json()["detail"]
    assert "Approval ID:" in r.json()["detail"]


@pytest.mark.asyncio
async def test_delete_agent_succeeds_after_approval(client, admin_token, sample_agent):
    """After approving the destruction, the delete should proceed."""
    # First attempt — blocked, creates approval
    r = await client.delete(f"/api/agents/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 409
    detail = r.json()["detail"]
    approval_id = detail.split("Approval ID: ")[1]

    # Approve it
    r = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Confirmed by admin"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200

    # Now delete should succeed
    r = await client.delete(f"/api/agents/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_review_required_task_blocked_before_approval(client, admin_token):
    """A review-required task cannot be completed without approval."""
    # Create task with review_required
    r = await client.post(
        "/api/tasks",
        json={"title": "Deploy to prod", "review_required": True},
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]
    h = auth_header(admin_token)

    # Advance to in_progress
    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=h)
    await client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"}, headers=h)

    # Try to complete — should be blocked
    r = await client.patch(f"/api/tasks/{task_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 409
    assert "Approval required" in r.json()["detail"]


@pytest.mark.asyncio
async def test_review_required_task_completes_after_approval(client, admin_token):
    """After approval, a review-required task can be completed."""
    r = await client.post(
        "/api/tasks",
        json={"title": "Deploy to prod", "review_required": True},
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]
    h = auth_header(admin_token)

    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=h)
    await client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"}, headers=h)

    # First attempt creates approval
    r = await client.patch(f"/api/tasks/{task_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 409
    approval_id = r.json()["detail"].split("Approval ID: ")[1]

    # Approve
    await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved"},
        headers=h,
    )

    # Now complete should succeed
    r = await client.patch(f"/api/tasks/{task_id}", json={"status": "completed"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_sensitive_action_task_blocked(client, admin_token):
    """A task with sensitive_action in payload is blocked without approval."""
    r = await client.post(
        "/api/tasks",
        json={
            "title": "Change billing rates",
            "input_payload": {"sensitive_action": "billing_change"},
        },
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]
    h = auth_header(admin_token)

    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=h)

    # Try to start — blocked by sensitive action
    r = await client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"}, headers=h)
    assert r.status_code == 409
    assert "billing_change" in r.json()["detail"]


@pytest.mark.asyncio
async def test_non_sensitive_task_not_blocked(client, admin_token):
    """A normal task should not trigger any approval gate."""
    r = await client.post(
        "/api/tasks",
        json={"title": "Write unit tests"},
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]
    h = auth_header(admin_token)

    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=h)
    r = await client.patch(f"/api/tasks/{task_id}", json={"status": "in_progress"}, headers=h)
    assert r.status_code == 200  # No approval needed

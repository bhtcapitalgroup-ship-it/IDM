"""Tests for role-based permission enforcement."""
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_viewer_cannot_create_agent(client, viewer_user, viewer_token):
    r = await client.post(
        "/api/agents",
        json={"name": "X", "role": "backend_builder"},
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_create_task(client, viewer_user, viewer_token):
    r = await client.post(
        "/api/tasks",
        json={"title": "X"},
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_read_agents(client, viewer_user, viewer_token):
    r = await client.get("/api/agents", headers=auth_header(viewer_token))
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_read_tasks(client, viewer_user, viewer_token):
    r = await client.get("/api/tasks", headers=auth_header(viewer_token))
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_create_approval(client, viewer_user, viewer_token):
    r = await client.post(
        "/api/approvals",
        json={"action_type": "test"},
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_write_memory(client, viewer_user, viewer_token, sample_agent):
    r = await client.post(
        "/api/memory",
        json={"agent_id": str(sample_agent.id), "key": "test", "value": {}},
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_delete_memory(client, viewer_user, viewer_token):
    import uuid
    r = await client.delete(
        f"/api/memory/{uuid.uuid4()}",
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_do_everything(client, admin_user, admin_token):
    # Create agent
    r = await client.post(
        "/api/agents",
        json={"name": "AdminAgent", "role": "qa_inspector"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201

    # Create task
    r = await client.post(
        "/api/tasks",
        json={"title": "Admin Task"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201

    # Create approval
    r = await client.post(
        "/api/approvals",
        json={"action_type": "test_action"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201

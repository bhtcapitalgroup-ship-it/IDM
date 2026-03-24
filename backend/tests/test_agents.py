"""Tests for Agent CRUD operations."""
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_agent(client, admin_token):
    r = await client.post(
        "/api/agents",
        json={"name": "Test Bot", "role": "frontend_builder", "description": "A test agent"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Bot"
    assert data["role"] == "frontend_builder"
    assert data["status"] == "active"
    assert data["type"] == "specialist"


@pytest.mark.asyncio
async def test_create_agent_invalid_role(client, admin_token):
    r = await client.post(
        "/api/agents",
        json={"name": "Bad", "role": "nonexistent_role"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422  # Literal validation


@pytest.mark.asyncio
async def test_create_agent_empty_name(client, admin_token):
    r = await client.post(
        "/api/agents",
        json={"name": "", "role": "qa_inspector"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_agents(client, admin_token, sample_agent):
    r = await client.get("/api/agents", headers=auth_header(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_agents_pagination(client, admin_token, sample_agent):
    r = await client.get("/api/agents?limit=1&offset=0", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert len(r.json()) <= 1


@pytest.mark.asyncio
async def test_get_agent(client, admin_token, sample_agent):
    r = await client.get(f"/api/agents/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["name"] == "Test Agent"


@pytest.mark.asyncio
async def test_get_agent_not_found(client, admin_token):
    import uuid
    r = await client.get(f"/api/agents/{uuid.uuid4()}", headers=auth_header(admin_token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_agent(client, admin_token, sample_agent):
    r = await client.patch(
        f"/api/agents/{sample_agent.id}",
        json={"status": "inactive"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"


@pytest.mark.asyncio
async def test_delete_agent_requires_approval(client, admin_token, sample_agent):
    """Agent deletion is now gated by approval enforcement."""
    r = await client.delete(f"/api/agents/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 409  # Blocked — approval required

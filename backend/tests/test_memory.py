"""Tests for memory endpoints and permission enforcement."""
import uuid
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_store_and_retrieve_memory(client, admin_token, sample_agent):
    # Store
    r = await client.post(
        "/api/memory",
        json={
            "agent_id": str(sample_agent.id),
            "key": "test_key",
            "value": {"data": "hello"},
            "scope": "session",
            "content": "Some text content",
        },
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    entry = r.json()
    assert entry["key"] == "test_key"
    assert entry["value"]["data"] == "hello"

    # Retrieve
    r = await client.get(f"/api/memory/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 200
    entries = r.json()
    assert len(entries) >= 1
    assert entries[0]["key"] == "test_key"


@pytest.mark.asyncio
async def test_delete_memory(client, admin_token, sample_agent):
    r = await client.post(
        "/api/memory",
        json={"agent_id": str(sample_agent.id), "key": "to_delete", "value": {}},
        headers=auth_header(admin_token),
    )
    entry_id = r.json()["id"]

    r = await client.delete(f"/api/memory/{entry_id}", headers=auth_header(admin_token))
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_memory_not_found(client, admin_token):
    r = await client.delete(f"/api/memory/{uuid.uuid4()}", headers=auth_header(admin_token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_memory_scope_filter(client, admin_token, sample_agent):
    for scope in ["session", "role"]:
        await client.post(
            "/api/memory",
            json={"agent_id": str(sample_agent.id), "key": f"key_{scope}", "value": {}, "scope": scope},
            headers=auth_header(admin_token),
        )

    r = await client.get(f"/api/memory/{sample_agent.id}?scope=role", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert all(e["scope"] == "role" for e in r.json())


@pytest.mark.asyncio
async def test_viewer_cannot_store_memory(client, viewer_token, sample_agent):
    r = await client.post(
        "/api/memory",
        json={"agent_id": str(sample_agent.id), "key": "hack", "value": {}},
        headers=auth_header(viewer_token),
    )
    assert r.status_code == 403

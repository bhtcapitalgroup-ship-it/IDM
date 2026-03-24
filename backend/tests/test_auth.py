"""Tests for authentication, login, token validation, and seed endpoint."""
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    r = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "testpass123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    r = await client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    r = await client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "anything"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_email_format(client):
    r = await client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert r.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_get_me(client, admin_user, admin_token):
    r = await client.get("/api/auth/me", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_get_me_no_token(client):
    r = await client.get("/api/auth/me")
    assert r.status_code in (401, 403)  # HTTPBearer behavior varies by version


@pytest.mark.asyncio
async def test_get_me_invalid_token(client):
    r = await client.get("/api/auth/me", headers=auth_header("garbage.token.here"))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_seed_endpoint_local(client):
    """Seed should work in local environment."""
    r = await client.post("/api/auth/seed")
    assert r.status_code == 200
    assert r.json()["email"] == "admin@agentic.dev"


@pytest.mark.asyncio
async def test_seed_idempotent(client):
    """Running seed twice should return existing user."""
    r1 = await client.post("/api/auth/seed")
    r2 = await client.post("/api/auth/seed")
    assert r1.json()["id"] == r2.json()["id"]

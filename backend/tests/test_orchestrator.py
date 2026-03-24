"""Tests for orchestrator plan creation and AI failure handling.

These tests mock the AI service to avoid hitting real APIs.
"""
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import auth_header
from app.services.ai_service import AIError


MOCK_PLAN = {
    "plan_summary": "Build a login system",
    "rationale": "Users need authentication before accessing the platform",
    "subtasks": [
        {
            "title": "Design auth database schema",
            "description": "Create user table with email, password hash, roles",
            "priority": "high",
            "agent_role": "database_builder",
            "review_required": False,
            "dependencies": [],
        },
        {
            "title": "Implement login API endpoint",
            "description": "POST /auth/login with JWT token response",
            "priority": "high",
            "agent_role": "backend_builder",
            "review_required": False,
            "dependencies": [0],
        },
        {
            "title": "Build login page UI",
            "description": "Email/password form with error handling",
            "priority": "medium",
            "agent_role": "frontend_builder",
            "review_required": True,
            "dependencies": [1],
        },
    ],
}


@pytest.mark.asyncio
@patch("app.services.orchestrator.ai_service")
async def test_orchestrator_creates_plan(mock_ai, client, admin_token, sample_agent):
    """Orchestrator should create parent task + subtasks from AI plan."""
    mock_ai.complete_json = AsyncMock(return_value=MOCK_PLAN)

    r = await client.post(
        "/api/orchestrator/decompose",
        json={"goal": "Build a user login system"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    data = r.json()

    assert data["parent_task"]["title"] == "Build a user login system"
    assert len(data["subtasks"]) == 3
    assert data["plan"]["summary"] == "Build a login system"
    assert data["plan"]["rationale"] == "Users need authentication before accessing the platform"

    # Verify subtask details
    assert data["subtasks"][0]["title"] == "Design auth database schema"
    assert data["subtasks"][0]["priority"] == "high"
    assert data["subtasks"][2]["review_required"] is True


@pytest.mark.asyncio
@patch("app.services.orchestrator.ai_service")
async def test_orchestrator_wires_dependencies(mock_ai, client, admin_token, sample_agent):
    """Subtask dependencies should reference real task IDs."""
    mock_ai.complete_json = AsyncMock(return_value=MOCK_PLAN)

    r = await client.post(
        "/api/orchestrator/decompose",
        json={"goal": "Build login"},
        headers=auth_header(admin_token),
    )
    data = r.json()

    # Subtask 1 (index 1) depends on subtask 0
    subtask_1_deps = data["subtasks"][1]["dependencies"]
    subtask_0_id = data["subtasks"][0]["id"]
    assert subtask_0_id in subtask_1_deps

    # Subtask 2 depends on subtask 1
    subtask_2_deps = data["subtasks"][2]["dependencies"]
    subtask_1_id = data["subtasks"][1]["id"]
    assert subtask_1_id in subtask_2_deps


@pytest.mark.asyncio
@patch("app.services.orchestrator.ai_service")
async def test_orchestrator_falls_back_to_deterministic_on_ai_failure(mock_ai, client, admin_token):
    """When AI fails, orchestrator falls back to deterministic planner."""
    mock_ai.complete_json = AsyncMock(
        return_value=AIError(error="API key invalid", status_code=401)
    )

    r = await client.post(
        "/api/orchestrator/decompose",
        json={"goal": "Build a backend API service"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert "Deterministic plan" in data["plan"]["summary"]
    assert len(data["subtasks"]) >= 3


@pytest.mark.asyncio
@patch("app.services.orchestrator.ai_service")
async def test_orchestrator_handles_invalid_ai_response(mock_ai, client, admin_token):
    """When AI returns garbage, orchestrator should return 502."""
    mock_ai.complete_json = AsyncMock(return_value={"not_a_plan": True})

    r = await client.post(
        "/api/orchestrator/decompose",
        json={"goal": "Build something"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 502


@pytest.mark.asyncio
@patch("app.services.orchestrator.ai_service")
async def test_orchestrator_validates_bad_roles(mock_ai, client, admin_token, sample_agent):
    """Invalid agent_role in AI output should be safely defaulted."""
    plan = {
        "plan_summary": "test",
        "rationale": "test",
        "subtasks": [
            {
                "title": "Do something",
                "description": "test",
                "priority": "high",
                "agent_role": "nonexistent_fake_role",
                "review_required": False,
                "dependencies": [],
            }
        ],
    }
    mock_ai.complete_json = AsyncMock(return_value=plan)

    r = await client.post(
        "/api/orchestrator/decompose",
        json={"goal": "Test bad roles"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    # Should default to product_architect, not crash
    assert len(r.json()["subtasks"]) == 1

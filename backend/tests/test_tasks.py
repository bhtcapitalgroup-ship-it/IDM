"""Tests for Task CRUD, status transitions, dependency enforcement, completion cascading."""
import uuid
import pytest
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_create_task(client, admin_token):
    r = await client.post(
        "/api/tasks",
        json={"title": "Build login page", "priority": "high"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Build login page"
    assert data["priority"] == "high"
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_create_task_invalid_priority(client, admin_token):
    r = await client.post(
        "/api/tasks",
        json={"title": "X", "priority": "mega-urgent"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_task_with_nonexistent_agent(client, admin_token):
    r = await client.post(
        "/api/tasks",
        json={"title": "X", "assigned_agent_id": str(uuid.uuid4())},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "not found" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_task_with_inactive_agent(client, admin_token, sample_agent, db):
    # Deactivate agent
    sample_agent.status = "inactive"
    db.add(sample_agent)
    await db.commit()

    r = await client.post(
        "/api/tasks",
        json={"title": "X", "assigned_agent_id": str(sample_agent.id)},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "inactive" in r.json()["detail"]


# --- Status Transition Tests ---

async def _create_task(client, token, **kwargs) -> dict:
    defaults = {"title": "Test Task"}
    defaults.update(kwargs)
    r = await client.post("/api/tasks", json=defaults, headers=auth_header(token))
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_valid_transition_created_to_pending(client, admin_token):
    task = await _create_task(client, admin_token)
    r = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "pending"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_valid_transition_created_to_assigned(client, admin_token):
    task = await _create_task(client, admin_token)
    r = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "assigned"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_invalid_transition_created_to_completed(client, admin_token):
    task = await _create_task(client, admin_token)
    r = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "completed"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "Cannot transition" in r.json()["detail"]


@pytest.mark.asyncio
async def test_invalid_transition_created_to_in_progress(client, admin_token):
    task = await _create_task(client, admin_token)
    r = await client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "in_progress"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_full_lifecycle(client, admin_token):
    task = await _create_task(client, admin_token)
    tid = task["id"]
    h = auth_header(admin_token)

    for status in ["assigned", "in_progress", "completed"]:
        r = await client.patch(f"/api/tasks/{tid}", json={"status": status}, headers=h)
        assert r.status_code == 200, f"Failed to transition to {status}: {r.json()}"
        assert r.json()["status"] == status


# --- Dependency Enforcement ---

@pytest.mark.asyncio
async def test_dependency_blocks_in_progress(client, admin_token):
    """Task with unmet dependency cannot move to in_progress."""
    dep = await _create_task(client, admin_token, title="Dependency")
    task = await _create_task(client, admin_token, title="Blocked", dependencies=[dep["id"]])
    h = auth_header(admin_token)

    # Move to assigned first
    await client.patch(f"/api/tasks/{task['id']}", json={"status": "assigned"}, headers=h)

    # Try to move to in_progress — should fail because dep is not completed
    r = await client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"}, headers=h)
    assert r.status_code == 400
    assert "dependencies" in r.json()["detail"]


@pytest.mark.asyncio
async def test_dependency_met_allows_in_progress(client, admin_token):
    """Task with completed dependency can move to in_progress."""
    dep = await _create_task(client, admin_token, title="Dependency")
    task = await _create_task(client, admin_token, title="Waiting", dependencies=[dep["id"]])
    h = auth_header(admin_token)

    # Complete the dependency
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "assigned"}, headers=h)
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "in_progress"}, headers=h)
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "completed"}, headers=h)

    # Now the waiting task should be able to start
    await client.patch(f"/api/tasks/{task['id']}", json={"status": "assigned"}, headers=h)
    r = await client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"}, headers=h)
    assert r.status_code == 200


# --- Completion Cascading ---

@pytest.mark.asyncio
async def test_completion_unblocks_dependent(client, admin_token, db):
    """Completing a task should unblock tasks that depend on it."""
    dep = await _create_task(client, admin_token, title="Blocker")
    blocked = await _create_task(client, admin_token, title="Blocked", dependencies=[dep["id"]])
    h = auth_header(admin_token)

    # Move blocked to assigned then blocked state
    await client.patch(f"/api/tasks/{blocked['id']}", json={"status": "assigned"}, headers=h)
    await client.patch(f"/api/tasks/{blocked['id']}", json={"status": "blocked"}, headers=h)

    # Complete the blocker
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "assigned"}, headers=h)
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "in_progress"}, headers=h)
    await client.patch(f"/api/tasks/{dep['id']}", json={"status": "completed"}, headers=h)

    # Check blocked task was unblocked
    r = await client.get(f"/api/tasks/{blocked['id']}", headers=h)
    # Should have been moved out of "blocked" by process_task_completion
    assert r.json()["status"] in ("assigned", "in_progress", "pending")

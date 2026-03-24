"""Tests for background worker job enqueue/dequeue lifecycle.

Worker internals require real Redis/PG so we test the API surface
(enqueue endpoint) and validate error handling of the parse logic.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import auth_header


@pytest.mark.asyncio
async def test_enqueue_only_assigned_tasks(client, admin_token):
    """Cannot enqueue a task that isn't in 'assigned' status."""
    r = await client.post(
        "/api/tasks",
        json={"title": "Not assigned yet"},
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]

    with patch("app.workers.task_worker.enqueue_task", new_callable=AsyncMock) as mock_enqueue:
        r = await client.post(
            f"/api/tasks/{task_id}/enqueue",
            headers=auth_header(admin_token),
        )
        assert r.status_code == 400
        assert "Only assigned tasks" in r.json()["detail"]
        mock_enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_assigned_task(client, admin_token, sample_agent):
    """An assigned task can be enqueued for background execution."""
    r = await client.post(
        "/api/tasks",
        json={"title": "Worker task", "assigned_agent_id": str(sample_agent.id)},
        headers=auth_header(admin_token),
    )
    task_id = r.json()["id"]
    h = auth_header(admin_token)

    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=h)

    with patch("app.workers.task_worker.enqueue_task", new_callable=AsyncMock) as mock_enqueue:
        r = await client.post(f"/api/tasks/{task_id}/enqueue", headers=h)
        assert r.status_code == 200
        mock_enqueue.assert_called_once_with(task_id)


@pytest.mark.asyncio
async def test_enqueue_nonexistent_task(client, admin_token):
    """Enqueue on nonexistent task returns 404."""
    import uuid
    with patch("app.workers.task_worker.enqueue_task", new_callable=AsyncMock):
        r = await client.post(
            f"/api/tasks/{uuid.uuid4()}/enqueue",
            headers=auth_header(admin_token),
        )
        assert r.status_code == 404

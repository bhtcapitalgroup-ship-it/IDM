"""Tests for collaboration: threads, messages, artifacts, handoffs, review loops."""
import uuid
import pytest
from tests.conftest import auth_header


# === Helpers ===

async def _create_thread(client, token, title="Test Thread", task_id=None):
    body = {"title": title}
    if task_id:
        body["task_id"] = task_id
    r = await client.post("/api/collab/threads", json=body, headers=auth_header(token))
    assert r.status_code == 201
    return r.json()


async def _send_msg(client, token, thread_id, content="Hello", msg_type="status_update", agent_id=None):
    body = {"thread_id": thread_id, "content": content, "message_type": msg_type}
    if agent_id:
        body["sender_agent_id"] = agent_id
    r = await client.post("/api/collab/messages", json=body, headers=auth_header(token))
    assert r.status_code == 201
    return r.json()


async def _create_artifact(client, token, title="Spec Doc", atype="spec", content="# Spec"):
    r = await client.post("/api/collab/artifacts", json={
        "title": title, "artifact_type": atype, "content": content,
    }, headers=auth_header(token))
    assert r.status_code == 201
    return r.json()


# === Thread Tests ===

@pytest.mark.asyncio
async def test_create_and_list_threads(client, admin_token):
    await _create_thread(client, admin_token, "Thread A")
    await _create_thread(client, admin_token, "Thread B")
    r = await client.get("/api/collab/threads", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert len(r.json()) >= 2


# === Message Tests ===

@pytest.mark.asyncio
async def test_send_and_read_messages(client, admin_token):
    thread = await _create_thread(client, admin_token)
    await _send_msg(client, admin_token, thread["id"], "First message")
    await _send_msg(client, admin_token, thread["id"], "Second message", "clarification")
    r = await client.get(f"/api/collab/threads/{thread['id']}/messages", headers=auth_header(admin_token))
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) == 2
    assert msgs[0]["content"] == "First message"
    assert msgs[1]["message_type"] == "clarification"


@pytest.mark.asyncio
async def test_agent_can_send_message(client, admin_token, sample_agent):
    thread = await _create_thread(client, admin_token)
    msg = await _send_msg(client, admin_token, thread["id"], "Agent reporting in", agent_id=str(sample_agent.id))
    assert msg["sender_agent_id"] == str(sample_agent.id)
    assert msg["sender_user_id"] is None


@pytest.mark.asyncio
async def test_message_types(client, admin_token):
    thread = await _create_thread(client, admin_token)
    for mtype in ["clarification", "handoff", "review", "escalation", "status_update"]:
        msg = await _send_msg(client, admin_token, thread["id"], f"Test {mtype}", mtype)
        assert msg["message_type"] == mtype


# === Artifact Tests ===

@pytest.mark.asyncio
async def test_create_artifact(client, admin_token):
    art = await _create_artifact(client, admin_token)
    assert art["artifact_type"] == "spec"
    assert art["version"] == 1
    assert art["status"] == "draft"


@pytest.mark.asyncio
async def test_artifact_versioning(client, admin_token):
    art = await _create_artifact(client, admin_token, content="v1 content")
    r = await client.patch(f"/api/collab/artifacts/{art['id']}", json={"content": "v2 content"}, headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["content"] == "v2 content"


@pytest.mark.asyncio
async def test_artifact_status_transitions(client, admin_token):
    art = await _create_artifact(client, admin_token)
    assert art["status"] == "draft"
    r = await client.patch(f"/api/collab/artifacts/{art['id']}", json={"status": "review"}, headers=auth_header(admin_token))
    assert r.json()["status"] == "review"
    r = await client.patch(f"/api/collab/artifacts/{art['id']}", json={"status": "approved"}, headers=auth_header(admin_token))
    assert r.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_list_artifacts_by_type(client, admin_token):
    await _create_artifact(client, admin_token, atype="spec")
    await _create_artifact(client, admin_token, title="API Docs", atype="api_contract", content="openapi: 3.0")
    r = await client.get("/api/collab/artifacts?artifact_type=api_contract", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert all(a["artifact_type"] == "api_contract" for a in r.json())


# === Handoff Tests ===

@pytest.mark.asyncio
async def test_create_handoff(client, admin_token, sample_agent, db):
    # Create a second agent
    from app.models.agent import Agent
    target = Agent(id=uuid.uuid4(), name="QA Agent", role="qa_inspector", type="specialist", status="active")
    db.add(target)
    await db.commit()

    r = await client.post("/api/collab/handoffs", json={
        "source_agent_id": str(sample_agent.id),
        "target_agent_id": str(target.id),
        "reason": "Backend complete, needs QA review",
        "handoff_type": "review",
    }, headers=auth_header(admin_token))
    assert r.status_code == 201
    data = r.json()
    assert data["handoff_type"] == "review"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_handoff_reassigns_task(client, admin_token, sample_agent, db):
    from app.models.agent import Agent
    target = Agent(id=uuid.uuid4(), name="Frontend Agent", role="frontend_builder", type="specialist", status="active")
    db.add(target)
    await db.commit()

    # Create and assign a task
    r = await client.post("/api/tasks", json={"title": "Build UI", "assigned_agent_id": str(sample_agent.id)}, headers=auth_header(admin_token))
    task_id = r.json()["id"]
    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=auth_header(admin_token))

    # Handoff to target
    await client.post("/api/collab/handoffs", json={
        "source_agent_id": str(sample_agent.id),
        "target_agent_id": str(target.id),
        "task_id": task_id,
        "reason": "Reassigning to frontend specialist",
    }, headers=auth_header(admin_token))

    # Task should now be assigned to target
    r = await client.get(f"/api/tasks/{task_id}", headers=auth_header(admin_token))
    assert r.json()["assigned_agent_id"] == str(target.id)


@pytest.mark.asyncio
async def test_review_send_back(client, admin_token, sample_agent, db):
    """QA rejects a handoff, task goes back to source agent."""
    from app.models.agent import Agent
    qa = Agent(id=uuid.uuid4(), name="QA", role="qa_inspector", type="specialist", status="active")
    db.add(qa)
    await db.commit()

    # Create task assigned to sample_agent
    r = await client.post("/api/tasks", json={"title": "Build API", "assigned_agent_id": str(sample_agent.id)}, headers=auth_header(admin_token))
    task_id = r.json()["id"]
    await client.patch(f"/api/tasks/{task_id}", json={"status": "assigned"}, headers=auth_header(admin_token))

    # Handoff to QA for review
    r = await client.post("/api/collab/handoffs", json={
        "source_agent_id": str(sample_agent.id),
        "target_agent_id": str(qa.id),
        "task_id": task_id,
        "reason": "Ready for QA",
        "handoff_type": "review",
    }, headers=auth_header(admin_token))
    handoff_id = r.json()["id"]

    # QA rejects — send back
    r = await client.post(f"/api/collab/handoffs/{handoff_id}/resolve", json={
        "status": "rejected",
        "notes": "Tests failing, fix and resubmit",
    }, headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    # Task should be back with source agent
    r = await client.get(f"/api/tasks/{task_id}", headers=auth_header(admin_token))
    assert r.json()["assigned_agent_id"] == str(sample_agent.id)
    assert r.json()["status"] == "assigned"


# === Inbox Tests ===

@pytest.mark.asyncio
async def test_agent_inbox(client, admin_token, sample_agent):
    # Create a task for the agent
    r = await client.post("/api/tasks", json={"title": "Inbox task", "assigned_agent_id": str(sample_agent.id)}, headers=auth_header(admin_token))
    await client.patch(f"/api/tasks/{r.json()['id']}", json={"status": "assigned"}, headers=auth_header(admin_token))

    r = await client.get(f"/api/collab/inbox/{sample_agent.id}", headers=auth_header(admin_token))
    assert r.status_code == 200
    inbox = r.json()
    assert inbox["assigned_tasks"] >= 1

"""Collaboration API: threads, messages, artifacts, handoffs, agent inbox."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.collaboration import AgentThread, AgentMessage, Artifact, Handoff
from app.schemas.collaboration import (
    ThreadCreate, ThreadResponse,
    MessageCreate, MessageResponse,
    ArtifactCreate, ArtifactUpdate, ArtifactResponse,
    HandoffCreate, HandoffResolve, HandoffResponse,
    InboxResponse,
)
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action

router = APIRouter(prefix="/collab", tags=["collaboration"])


# ==================== Threads ====================

@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    task_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    q = select(AgentThread)
    if task_id:
        q = q.where(AgentThread.task_id == task_id)
    if status:
        q = q.where(AgentThread.status == status)
    result = await db.execute(q.order_by(AgentThread.updated_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    body: ThreadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tasks")
    thread = AgentThread(id=uuid.uuid4(), created_by=str(user.id), **body.model_dump())
    db.add(thread)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_thread",
        resource_type="agent_thread", resource_id=str(thread.id),
        after_state={"title": body.title},
    )
    return thread


# ==================== Messages ====================

@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: uuid.UUID,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.thread_id == thread_id)
        .order_by(AgentMessage.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tasks")
    msg = AgentMessage(
        id=uuid.uuid4(),
        thread_id=body.thread_id,
        sender_agent_id=body.sender_agent_id,
        sender_user_id=user.id if not body.sender_agent_id else None,
        message_type=body.message_type,
        content=body.content,
        metadata_=body.metadata,
    )
    db.add(msg)
    await db.flush()

    # Update thread timestamp
    result = await db.execute(select(AgentThread).where(AgentThread.id == body.thread_id))
    thread = result.scalar_one_or_none()
    if thread:
        thread.updated_at = datetime.now(timezone.utc)
        await db.flush()

    await log_action(
        db, actor=str(body.sender_agent_id or user.id), actor_type="agent" if body.sender_agent_id else "user",
        action="send_message", resource_type="agent_message", resource_id=str(msg.id),
        after_state={"thread_id": str(body.thread_id), "type": body.message_type},
    )
    return msg


# ==================== Artifacts ====================

@router.get("/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    artifact_type: str | None = None,
    task_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    q = select(Artifact)
    if artifact_type:
        q = q.where(Artifact.artifact_type == artifact_type)
    if task_id:
        q = q.where(Artifact.task_id == task_id)
    if status:
        q = q.where(Artifact.status == status)
    result = await db.execute(q.order_by(Artifact.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/artifacts", response_model=ArtifactResponse, status_code=201)
async def create_artifact(
    body: ArtifactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tasks")
    artifact = Artifact(
        id=uuid.uuid4(),
        title=body.title,
        artifact_type=body.artifact_type,
        content=body.content,
        creator_agent_id=body.creator_agent_id,
        task_id=body.task_id,
        thread_id=body.thread_id,
        metadata_=body.metadata,
    )
    db.add(artifact)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_artifact",
        resource_type="artifact", resource_id=str(artifact.id),
        after_state={"type": body.artifact_type, "title": body.title},
    )
    return artifact


@router.patch("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: uuid.UUID,
    body: ArtifactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    updates = body.model_dump(exclude_unset=True)
    # Bump version on content change
    if "content" in updates and updates["content"] != artifact.content:
        artifact.version += 1
    if "metadata" in updates:
        artifact.metadata_ = updates.pop("metadata")
    for k, v in updates.items():
        setattr(artifact, k, v)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_artifact",
        resource_type="artifact", resource_id=str(artifact.id),
        after_state={"version": artifact.version, "status": artifact.status},
    )
    return artifact


# ==================== Handoffs ====================

@router.get("/handoffs", response_model=list[HandoffResponse])
async def list_handoffs(
    agent_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    q = select(Handoff)
    if agent_id:
        q = q.where((Handoff.source_agent_id == agent_id) | (Handoff.target_agent_id == agent_id))
    if status:
        q = q.where(Handoff.status == status)
    result = await db.execute(q.order_by(Handoff.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/handoffs", response_model=HandoffResponse, status_code=201)
async def create_handoff(
    body: HandoffCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tasks")
    handoff = Handoff(id=uuid.uuid4(), **body.model_dump())
    db.add(handoff)
    await db.flush()

    # If linked to a task, reassign it to the target agent
    if body.task_id:
        result = await db.execute(select(Task).where(Task.id == body.task_id))
        task = result.scalar_one_or_none()
        if task:
            task.assigned_agent_id = body.target_agent_id
            if task.status in ("in_progress", "review"):
                task.status = "assigned"
            await db.flush()

    # Auto-create a thread message for visibility
    if body.task_id:
        # Find or create thread for task
        result = await db.execute(select(AgentThread).where(AgentThread.task_id == body.task_id))
        thread = result.scalar_one_or_none()
        if not thread:
            thread = AgentThread(
                id=uuid.uuid4(), title=f"Handoff: {body.reason[:100]}",
                task_id=body.task_id, created_by=str(user.id),
            )
            db.add(thread)
            await db.flush()
        msg = AgentMessage(
            id=uuid.uuid4(), thread_id=thread.id, sender_agent_id=body.source_agent_id,
            message_type="handoff",
            content=f"Handing off to target agent. Reason: {body.reason}",
        )
        db.add(msg)
        await db.flush()

    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_handoff",
        resource_type="handoff", resource_id=str(handoff.id),
        after_state={"type": body.handoff_type, "source": str(body.source_agent_id), "target": str(body.target_agent_id)},
    )
    return handoff


@router.post("/handoffs/{handoff_id}/resolve", response_model=HandoffResponse)
async def resolve_handoff(
    handoff_id: uuid.UUID,
    body: HandoffResolve,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_tasks")
    result = await db.execute(select(Handoff).where(Handoff.id == handoff_id))
    handoff = result.scalar_one_or_none()
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    if handoff.status != "pending":
        raise HTTPException(status_code=400, detail="Handoff already resolved")

    handoff.status = body.status
    handoff.notes = body.notes
    handoff.resolved_at = datetime.now(timezone.utc)
    await db.flush()

    # On rejection (send-back), reassign task to source agent
    if body.status == "rejected" and handoff.task_id:
        result = await db.execute(select(Task).where(Task.id == handoff.task_id))
        task = result.scalar_one_or_none()
        if task:
            task.assigned_agent_id = handoff.source_agent_id
            task.status = "assigned"
            await db.flush()

    await log_action(
        db, actor=str(user.id), actor_type="user", action="resolve_handoff",
        resource_type="handoff", resource_id=str(handoff.id),
        after_state={"status": body.status},
    )
    return handoff


# ==================== Agent Inbox ====================

@router.get("/inbox/{agent_id}", response_model=InboxResponse)
async def get_agent_inbox(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")

    assigned = await db.execute(
        select(func.count(Task.id)).where(Task.assigned_agent_id == agent_id, Task.status.in_(["assigned", "in_progress"]))
    )
    messages = await db.execute(
        select(func.count(AgentMessage.id)).where(AgentMessage.sender_agent_id != agent_id)
        .join(AgentThread, AgentMessage.thread_id == AgentThread.id)
        .join(Task, AgentThread.task_id == Task.id)
        .where(Task.assigned_agent_id == agent_id)
    )
    handoffs = await db.execute(
        select(func.count(Handoff.id)).where(Handoff.target_agent_id == agent_id, Handoff.status == "pending")
    )
    reviews = await db.execute(
        select(func.count(Handoff.id)).where(
            Handoff.target_agent_id == agent_id, Handoff.handoff_type == "review", Handoff.status == "pending"
        )
    )
    blocked = await db.execute(
        select(func.count(Task.id)).where(Task.assigned_agent_id == agent_id, Task.status == "blocked")
    )

    return InboxResponse(
        assigned_tasks=assigned.scalar() or 0,
        pending_messages=messages.scalar() or 0,
        pending_handoffs=handoffs.scalar() or 0,
        pending_reviews=reviews.scalar() or 0,
        blocked_tasks=blocked.scalar() or 0,
    )

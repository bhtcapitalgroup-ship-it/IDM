import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.task import Task
from app.models.agent import Agent
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action
from app.services.workflow_engine import check_dependencies_met, process_task_completion, require_approval_or_block

router = APIRouter(prefix="/tasks", tags=["tasks"])

VALID_STATUSES = {"created", "pending", "assigned", "in_progress", "review", "approved", "rejected", "completed", "blocked", "failed", "cancelled"}
VALID_TRANSITIONS = {
    "created": {"pending", "assigned", "cancelled"},
    "pending": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled", "blocked"},
    "in_progress": {"review", "completed", "failed", "blocked", "cancelled"},
    "review": {"approved", "rejected"},
    "approved": {"completed"},
    "rejected": {"assigned"},
    "blocked": {"assigned", "in_progress", "cancelled"},
    "failed": {"assigned", "cancelled"},
}


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status: str | None = None,
    assigned_agent_id: uuid.UUID | None = None,
    priority: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_tasks")
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if assigned_agent_id:
        query = query.where(Task.assigned_agent_id == assigned_agent_id)
    if priority:
        query = query.where(Task.priority == priority)
    result = await db.execute(query.order_by(Task.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_tasks")
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tasks")
    # Validate assigned agent if provided
    if body.assigned_agent_id:
        agent_result = await db.execute(select(Agent).where(Agent.id == body.assigned_agent_id))
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=400, detail="Assigned agent not found")
        if agent.status != "active":
            raise HTTPException(status_code=400, detail="Cannot assign task to inactive agent")
    task = Task(id=uuid.uuid4(), created_by=str(user.id), **body.model_dump())
    db.add(task)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_task",
        resource_type="task", resource_id=str(task.id),
        after_state=body.model_dump(mode="json"),
    )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_tasks")
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = body.model_dump(exclude_unset=True)

    # Validate assigned agent exists and is active
    if "assigned_agent_id" in updates and updates["assigned_agent_id"]:
        agent_result = await db.execute(
            select(Agent).where(Agent.id == updates["assigned_agent_id"])
        )
        agent = agent_result.scalar_one_or_none()
        if not agent:
            raise HTTPException(status_code=400, detail="Assigned agent not found")
        if agent.status != "active":
            raise HTTPException(status_code=400, detail="Cannot assign task to inactive agent")

    # Validate status transitions
    if "status" in updates:
        new_status = updates["status"]
        if new_status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")
        allowed = VALID_TRANSITIONS.get(task.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{task.status}' to '{new_status}'",
            )
        # Enforce dependency checking before advancing to in_progress
        if new_status == "in_progress" and not await check_dependencies_met(db, task):
            raise HTTPException(
                status_code=400,
                detail="Cannot start task: dependencies not yet completed",
            )

        # Enforce approval for review-required tasks being completed
        if new_status == "completed" and task.review_required:
            pending = await require_approval_or_block(
                db,
                action_type="destructive_action",
                description=f"Complete review-required task: {task.title}",
                requested_by=str(user.id),
                task_id=str(task.id),
            )
            if pending:
                await db.commit()
                raise HTTPException(
                    status_code=409,
                    detail=f"Approval required before completing this task. Approval ID: {pending.id}",
                )

        # Enforce approval for tasks tagged with sensitive action types
        sensitive_action = (task.input_payload or {}).get("sensitive_action")
        if sensitive_action and new_status in ("in_progress", "completed"):
            pending = await require_approval_or_block(
                db,
                action_type=sensitive_action,
                description=f"Sensitive action '{sensitive_action}' on task: {task.title}",
                requested_by=str(user.id),
                task_id=str(task.id),
            )
            if pending:
                await db.commit()
                raise HTTPException(
                    status_code=409,
                    detail=f"Approval required for sensitive action '{sensitive_action}'. Approval ID: {pending.id}",
                )

    before = {k: getattr(task, k) for k in updates}
    for k, v in updates.items():
        setattr(task, k, v)
    await db.flush()

    # If task completed, unblock dependent tasks
    if updates.get("status") == "completed":
        await process_task_completion(db, task, str(user.id))

    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_task",
        resource_type="task", resource_id=str(task.id),
        before_state={k: str(v) if isinstance(v, uuid.UUID) else v for k, v in before.items()},
        after_state={k: str(v) if isinstance(v, uuid.UUID) else v for k, v in updates.items()},
    )
    return task


@router.post("/{task_id}/enqueue", response_model=TaskResponse)
async def enqueue_task_for_execution(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Queue an assigned task for background worker execution."""
    check_permission(user.role, "update_tasks")
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "assigned":
        raise HTTPException(status_code=400, detail=f"Only assigned tasks can be enqueued, current status: {task.status}")

    from app.workers.task_worker import enqueue_task as _enqueue
    await _enqueue(str(task.id))

    await log_action(
        db, actor=str(user.id), actor_type="user", action="enqueue_task",
        resource_type="task", resource_id=str(task.id),
    )
    return task

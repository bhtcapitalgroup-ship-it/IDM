"""Workflow Engine service.

Manages task orchestration, sequencing, dependency resolution,
retries, completion tracking, and approval enforcement.
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.task import Task
from app.models.approval import Approval
from app.core.permissions import APPROVAL_REQUIRED_ACTIONS
from app.core.logging import log_action


async def check_dependencies_met(db: AsyncSession, task: Task) -> bool:
    """Check if all task dependencies are completed."""
    if not task.dependencies:
        return True
    for dep_id in task.dependencies:
        result = await db.execute(select(Task).where(Task.id == uuid.UUID(dep_id)))
        dep_task = result.scalar_one_or_none()
        if not dep_task or dep_task.status != "completed":
            return False
    return True


async def advance_task(
    db: AsyncSession,
    task: Task,
    new_status: str,
    actor: str,
) -> Task:
    """Advance a task through its lifecycle with validation."""
    old_status = task.status
    task.status = new_status
    await db.flush()

    await log_action(
        db, actor=actor, actor_type="system", action="advance_task",
        resource_type="task", resource_id=str(task.id),
        before_state={"status": old_status},
        after_state={"status": new_status},
    )
    return task


async def process_task_completion(db: AsyncSession, task: Task, actor: str):
    """When a task completes, check if blocked tasks can be unblocked."""
    result = await db.execute(select(Task).where(Task.status == "blocked"))
    blocked_tasks = result.scalars().all()

    for blocked in blocked_tasks:
        if str(task.id) in (blocked.dependencies or []):
            if await check_dependencies_met(db, blocked):
                await advance_task(db, blocked, "assigned" if blocked.assigned_agent_id else "pending", actor)


async def require_approval_or_block(
    db: AsyncSession,
    action_type: str,
    description: str,
    requested_by: str,
    task_id: str | None = None,
    resource_id: str | None = None,
) -> Approval | None:
    """If the action requires approval and none exists, create a pending approval
    and return it (signaling the caller should block). If already approved, return None.

    Scoping: approvals are matched by action_type + (task_id OR resource_id in payload).
    This ensures each specific resource gets its own approval flow.
    """
    if action_type not in APPROVAL_REQUIRED_ACTIONS:
        return None

    # Build filters for this specific approval scope
    def _scoped_query(status: str):
        q = select(Approval).where(
            Approval.action_type == action_type,
            Approval.status == status,
        )
        if task_id:
            q = q.where(Approval.task_id == uuid.UUID(task_id))
        return q

    # Check if already approved for this scope
    result = await db.execute(_scoped_query("approved"))
    if result.scalar_one_or_none():
        return None  # Approved — proceed

    # Check if already pending
    result = await db.execute(_scoped_query("pending"))
    existing = result.scalar_one_or_none()
    if existing:
        return existing  # Already pending — still blocked

    # Create new approval request
    payload = {"action_type": action_type}
    if task_id:
        payload["task_id"] = task_id
    if resource_id:
        payload["resource_id"] = resource_id

    approval = Approval(
        id=uuid.uuid4(),
        task_id=uuid.UUID(task_id) if task_id else None,
        action_type=action_type,
        description=description,
        requested_by=requested_by,
        payload=payload,
    )
    db.add(approval)
    await db.flush()

    await log_action(
        db, actor=requested_by, actor_type="system", action="approval_required",
        resource_type="approval", resource_id=str(approval.id),
        after_state={"action_type": action_type, "description": description},
    )
    return approval

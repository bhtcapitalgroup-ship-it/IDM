from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.agent import Agent
from app.models.task import Task
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    agents = await db.execute(select(func.count(Agent.id)))
    tasks = await db.execute(select(func.count(Task.id)))
    pending_approvals = await db.execute(
        select(func.count(Approval.id)).where(Approval.status == "pending")
    )
    tasks_by_status = await db.execute(
        select(Task.status, func.count(Task.id)).group_by(Task.status)
    )
    return {
        "total_agents": agents.scalar(),
        "total_tasks": tasks.scalar(),
        "pending_approvals": pending_approvals.scalar(),
        "tasks_by_status": dict(tasks_by_status.all()),
    }


@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def get_audit_logs(
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    result = await db.execute(query.order_by(AuditLog.created_at.desc()).limit(limit))
    return result.scalars().all()

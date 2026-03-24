import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.agent_memory import AgentMemory
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{agent_id}", response_model=list[MemoryResponse])
async def get_agent_memory(
    agent_id: uuid.UUID,
    scope: str | None = None,
    scope_id: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(AgentMemory).where(AgentMemory.agent_id == agent_id)
    if scope:
        query = query.where(AgentMemory.scope == scope)
    if scope_id:
        query = query.where(AgentMemory.scope_id == scope_id)
    result = await db.execute(query.order_by(AgentMemory.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("", response_model=MemoryResponse, status_code=201)
async def store_memory(
    body: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    entry = AgentMemory(id=uuid.uuid4(), **body.model_dump())
    db.add(entry)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="store_memory",
        resource_type="agent_memory", resource_id=str(entry.id),
        after_state={"agent_id": str(body.agent_id), "key": body.key, "scope": body.scope},
    )
    return entry


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    result = await db.execute(select(AgentMemory).where(AgentMemory.id == memory_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Memory entry not found")
    await log_action(
        db, actor=str(user.id), actor_type="user", action="delete_memory",
        resource_type="agent_memory", resource_id=str(memory_id),
        before_state={"agent_id": str(entry.agent_id), "key": entry.key},
    )
    await db.delete(entry)
    await db.flush()

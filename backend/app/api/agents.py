import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.services.workflow_engine import require_approval_or_block
from app.core.logging import log_action

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    role: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(Agent)
    if role:
        query = query.where(Agent.role == role)
    if status:
        query = query.where(Agent.status == status)
    result = await db.execute(query.order_by(Agent.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_agents")
    agent = Agent(id=uuid.uuid4(), **body.model_dump())
    db.add(agent)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_agent",
        resource_type="agent", resource_id=str(agent.id),
        after_state=body.model_dump(),
    )
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    updates = body.model_dump(exclude_unset=True)
    before = {k: getattr(agent, k) for k in updates}
    for k, v in updates.items():
        setattr(agent, k, v)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_agent",
        resource_type="agent", resource_id=str(agent.id),
        before_state=before, after_state=updates,
    )
    return agent


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "delete_agents")
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Require approval for agent deletion (destructive action)
    pending = await require_approval_or_block(
        db,
        action_type="destructive_action",
        description=f"Delete agent: {agent.name} ({agent.role})",
        requested_by=str(user.id),
    )
    if pending:
        await db.commit()  # Persist the approval before blocking
        raise HTTPException(
            status_code=409,
            detail=f"Approval required before deleting this agent. Approval ID: {pending.id}",
        )

    await log_action(
        db, actor=str(user.id), actor_type="user", action="delete_agent",
        resource_type="agent", resource_id=str(agent.id),
        before_state={"name": agent.name, "role": agent.role},
    )
    await db.delete(agent)
    await db.flush()

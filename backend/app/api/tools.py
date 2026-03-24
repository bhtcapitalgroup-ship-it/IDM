import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.tool import Tool
from app.models.user import User
from app.schemas.tool import ToolCreate, ToolUpdate, ToolResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    role: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_tools")
    query = select(Tool)
    if active_only:
        query = query.where(Tool.is_active == True)
    result = await db.execute(query.order_by(Tool.name))
    tools = result.scalars().all()
    if role:
        tools = [t for t in tools if role in t.allowed_roles]
    return tools


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    body: ToolCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_tools")
    tool = Tool(id=uuid.uuid4(), **body.model_dump())
    db.add(tool)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_tool",
        resource_type="tool", resource_id=str(tool.id),
        after_state=body.model_dump(),
    )
    return tool


@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: uuid.UUID,
    body: ToolUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_tools")
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(tool, k, v)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_tool",
        resource_type="tool", resource_id=str(tool.id),
        after_state=updates,
    )
    return tool

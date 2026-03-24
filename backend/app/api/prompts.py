import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.prompt import Prompt
from app.models.user import User
from app.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    category: str | None = None,
    role: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_prompts")
    query = select(Prompt)
    if category:
        query = query.where(Prompt.category == category)
    if role:
        query = query.where(Prompt.role == role)
    if active_only:
        query = query.where(Prompt.is_active == True)
    result = await db.execute(query.order_by(Prompt.name, Prompt.version.desc()))
    return result.scalars().all()


@router.post("", response_model=PromptResponse, status_code=201)
async def create_prompt(
    body: PromptCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_prompts")
    prompt = Prompt(id=uuid.uuid4(), **body.model_dump())
    db.add(prompt)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_prompt",
        resource_type="prompt", resource_id=str(prompt.id),
        after_state=body.model_dump(),
    )
    return prompt


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_prompts")
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    updates = body.model_dump(exclude_unset=True)
    # If template changes, bump version
    if "template" in updates and updates["template"] != prompt.template:
        prompt.version += 1
    for k, v in updates.items():
        setattr(prompt, k, v)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_prompt",
        resource_type="prompt", resource_id=str(prompt.id),
        after_state=updates,
    )
    return prompt

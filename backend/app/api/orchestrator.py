from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.task import TaskResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.services.orchestrator import decompose_goal

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


class GoalRequest(BaseModel):
    goal: str = Field(..., min_length=5, max_length=2000)


class PlanInfo(BaseModel):
    summary: str
    rationale: str


class DecomposeResponse(BaseModel):
    parent_task: TaskResponse
    subtasks: list[TaskResponse]
    plan: PlanInfo
    ai_metadata: dict


@router.post("/decompose", response_model=DecomposeResponse)
async def decompose(
    body: GoalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Decompose a high-level goal into subtasks using AI-driven planning."""
    check_permission(user.role, "create_tasks")
    result = await decompose_goal(db, body.goal, str(user.id))

    if "error" in result and result.get("parent_task") is None:
        raise HTTPException(
            status_code=502,
            detail=f"Orchestrator failed: {result['error']}",
        )

    return DecomposeResponse(
        parent_task=result["parent_task"],
        subtasks=result["subtasks"],
        plan=PlanInfo(
            summary=result["plan"].get("summary", ""),
            rationale=result["plan"].get("rationale", ""),
        ),
        ai_metadata=result.get("ai_metadata", {}),
    )

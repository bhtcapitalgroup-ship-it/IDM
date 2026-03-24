import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.approval import Approval
from app.models.user import User
from app.schemas.approval import ApprovalCreate, ApprovalDecision, ApprovalResponse
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_approvals")
    query = select(Approval)
    if status:
        query = query.where(Approval.status == status)
    result = await db.execute(query.order_by(Approval.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.post("", response_model=ApprovalResponse, status_code=201)
async def create_approval(
    body: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_approvals")
    approval = Approval(
        id=uuid.uuid4(),
        requested_by=str(user.id),
        **body.model_dump(),
    )
    db.add(approval)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_approval",
        resource_type="approval", resource_id=str(approval.id),
        after_state=body.model_dump(mode="json"),
    )
    return approval


@router.post("/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "review_approvals")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")

    approval.status = body.status
    approval.reviewed_by = str(user.id)
    approval.decision_reason = body.decision_reason
    approval.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="decide_approval",
        resource_type="approval", resource_id=str(approval.id),
        after_state={"status": body.status, "reason": body.decision_reason},
    )
    return approval

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ApprovalCreate(BaseModel):
    task_id: UUID | None = None
    action_type: str
    description: str | None = None
    payload: dict = {}


class ApprovalDecision(BaseModel):
    status: str  # "approved" or "rejected"
    decision_reason: str | None = None


class ApprovalResponse(BaseModel):
    id: UUID
    task_id: UUID | None
    action_type: str
    description: str | None
    requested_by: str
    reviewed_by: str | None
    status: str
    payload: dict
    decision_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}

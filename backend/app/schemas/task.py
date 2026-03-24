from typing import Literal
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

TaskPriority = Literal["low", "medium", "high", "critical"]
TaskStatus = Literal[
    "created", "pending", "assigned", "in_progress", "review",
    "approved", "rejected", "completed", "blocked", "failed", "cancelled",
]


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    parent_task_id: UUID | None = None
    assigned_agent_id: UUID | None = None
    priority: TaskPriority = "medium"
    dependencies: list[str] = []
    input_payload: dict = {}
    review_required: bool = False


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    assigned_agent_id: UUID | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    dependencies: list[str] | None = None
    input_payload: dict | None = None
    output_payload: dict | None = None
    review_required: bool | None = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    parent_task_id: UUID | None
    assigned_agent_id: UUID | None
    created_by: str
    priority: str
    status: str
    dependencies: list
    input_payload: dict
    output_payload: dict
    review_required: bool
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

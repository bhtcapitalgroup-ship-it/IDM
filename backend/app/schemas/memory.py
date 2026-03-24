from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class MemoryCreate(BaseModel):
    agent_id: UUID
    scope: str = "session"
    scope_id: str | None = None
    key: str
    value: dict = {}
    content: str | None = None


class MemoryResponse(BaseModel):
    id: UUID
    agent_id: UUID
    scope: str
    scope_id: str | None
    key: str
    value: dict
    content: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

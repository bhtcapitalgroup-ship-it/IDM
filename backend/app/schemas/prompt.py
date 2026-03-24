from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class PromptCreate(BaseModel):
    name: str
    category: str = "base"
    role: str | None = None
    template: str
    output_schema: dict | None = None
    guardrails: dict = {}


class PromptUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    role: str | None = None
    template: str | None = None
    output_schema: dict | None = None
    guardrails: dict | None = None
    is_active: bool | None = None


class PromptResponse(BaseModel):
    id: UUID
    name: str
    category: str
    role: str | None
    template: str
    output_schema: dict | None
    guardrails: dict
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

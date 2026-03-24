from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ToolCreate(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict = {}
    output_schema: dict = {}
    allowed_roles: list = []
    permission_level: str = "standard"
    environment_access: list = []
    requires_approval: bool = False


class ToolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    allowed_roles: list | None = None
    permission_level: str | None = None
    environment_access: list | None = None
    requires_approval: bool | None = None
    is_active: bool | None = None


class ToolResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    input_schema: dict
    output_schema: dict
    allowed_roles: list
    permission_level: str
    environment_access: list
    requires_approval: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

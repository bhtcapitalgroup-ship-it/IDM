from typing import Literal
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

AgentRole = Literal[
    "executive_orchestrator", "product_architect", "frontend_builder",
    "backend_builder", "database_builder", "qa_inspector",
    "devops_operator", "compliance_reviewer",
]
AgentType = Literal["manager", "specialist"]
AgentStatus = Literal["active", "inactive", "error"]
MemoryScope = Literal["session", "task", "role", "global"]


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: AgentRole
    type: AgentType = "specialist"
    description: str | None = Field(default=None, max_length=2000)
    permissions: dict = {}
    tools: list = []
    version: str = Field(default="1.0.0", max_length=20)
    owner: str | None = Field(default=None, max_length=255)
    memory_scope: MemoryScope = "session"
    creation_source: str = Field(default="manual", max_length=50)
    config: dict = {}


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: AgentRole | None = None
    type: AgentType | None = None
    status: AgentStatus | None = None
    description: str | None = Field(default=None, max_length=2000)
    permissions: dict | None = None
    tools: list | None = None
    version: str | None = Field(default=None, max_length=20)
    owner: str | None = Field(default=None, max_length=255)
    memory_scope: MemoryScope | None = None
    config: dict | None = None


class AgentResponse(BaseModel):
    id: UUID
    name: str
    role: str
    type: str
    status: str
    description: str | None
    permissions: dict
    tools: list
    version: str
    owner: str | None
    memory_scope: str
    creation_source: str
    config: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

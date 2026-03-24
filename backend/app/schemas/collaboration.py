"""Pydantic schemas for collaboration: threads, messages, artifacts, handoffs."""
from typing import Literal
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

MessageType = Literal["clarification", "handoff", "review", "escalation", "status_update"]
ArtifactType = Literal["spec", "api_contract", "db_change", "ui_component", "qa_report", "compliance_note", "deployment_plan"]
ArtifactStatus = Literal["draft", "review", "approved", "rejected", "final"]
HandoffType = Literal["handoff", "review", "escalation", "send_back"]
HandoffStatus = Literal["pending", "accepted", "rejected", "completed"]

# --- Threads ---
class ThreadCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    task_id: UUID | None = None

class ThreadResponse(BaseModel):
    id: UUID; title: str; task_id: UUID | None; status: str
    created_by: str; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}

# --- Messages ---
class MessageCreate(BaseModel):
    thread_id: UUID
    sender_agent_id: UUID | None = None
    message_type: MessageType = "status_update"
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: dict = {}

class MessageResponse(BaseModel):
    id: UUID; thread_id: UUID; sender_agent_id: UUID | None
    sender_user_id: UUID | None; message_type: str; content: str
    metadata_: dict; created_at: datetime
    model_config = {"from_attributes": True}

# --- Artifacts ---
class ArtifactCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    artifact_type: ArtifactType
    content: str = Field(..., min_length=1)
    creator_agent_id: UUID | None = None
    task_id: UUID | None = None
    thread_id: UUID | None = None
    metadata: dict = {}

class ArtifactUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    content: str | None = None
    status: ArtifactStatus | None = None
    metadata: dict | None = None

class ArtifactResponse(BaseModel):
    id: UUID; title: str; artifact_type: str; status: str; version: int
    content: str; creator_agent_id: UUID | None; task_id: UUID | None
    thread_id: UUID | None; metadata_: dict; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}

# --- Handoffs ---
class HandoffCreate(BaseModel):
    source_agent_id: UUID
    target_agent_id: UUID
    task_id: UUID | None = None
    artifact_id: UUID | None = None
    reason: str = Field(..., min_length=1, max_length=2000)
    handoff_type: HandoffType = "handoff"

class HandoffResolve(BaseModel):
    status: Literal["accepted", "rejected", "completed"]
    notes: str | None = None

class HandoffResponse(BaseModel):
    id: UUID; source_agent_id: UUID; target_agent_id: UUID
    task_id: UUID | None; artifact_id: UUID | None; reason: str
    handoff_type: str; status: str; notes: str | None
    created_at: datetime; resolved_at: datetime | None
    model_config = {"from_attributes": True}

# --- Inbox ---
class InboxResponse(BaseModel):
    assigned_tasks: int
    pending_messages: int
    pending_handoffs: int
    pending_reviews: int
    blocked_tasks: int

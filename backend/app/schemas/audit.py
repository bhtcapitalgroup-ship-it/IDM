from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: UUID
    actor: str
    actor_type: str
    action: str
    resource_type: str
    resource_id: str
    before_state: dict | None
    after_state: dict | None
    metadata_: dict
    created_at: datetime

    model_config = {"from_attributes": True}

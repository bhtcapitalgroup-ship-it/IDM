import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    actor: str,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
):
    entry = AuditLog(
        id=uuid.uuid4(),
        actor=actor,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_state=before_state,
        after_state=after_state,
        metadata_=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry

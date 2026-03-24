import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="specialist")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tools: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    memory_scope: Mapped[str] = mapped_column(String(50), nullable=False, default="session")
    creation_source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

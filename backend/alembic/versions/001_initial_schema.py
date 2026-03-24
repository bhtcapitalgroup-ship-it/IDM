"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False, server_default="specialist"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("permissions", JSONB, nullable=False, server_default="{}"),
        sa.Column("tools", JSONB, nullable=False, server_default="[]"),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("memory_scope", sa.String(50), nullable=False, server_default="session"),
        sa.Column("creation_source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parent_task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("assigned_agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True, index=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(50), nullable=False, server_default="created", index=True),
        sa.Column("dependencies", JSONB, nullable=False, server_default="[]"),
        sa.Column("input_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("review_required", sa.Boolean, server_default="false"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("max_retries", sa.Integer, server_default="3"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Prompts
    op.create_table(
        "prompts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="base"),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("output_schema", JSONB, nullable=True),
        sa.Column("guardrails", JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Tools
    op.create_table(
        "tools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("input_schema", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_schema", JSONB, nullable=False, server_default="{}"),
        sa.Column("allowed_roles", JSONB, nullable=False, server_default="[]"),
        sa.Column("permission_level", sa.String(50), nullable=False, server_default="standard"),
        sa.Column("environment_access", JSONB, nullable=False, server_default="[]"),
        sa.Column("requires_approval", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Approvals
    op.create_table(
        "approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False, index=True),
        sa.Column("actor_type", sa.String(50), nullable=False, server_default="user"),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("before_state", JSONB, nullable=True),
        sa.Column("after_state", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )

    # Agent Memory
    op.create_table(
        "agent_memory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False, index=True),
        sa.Column("scope", sa.String(50), nullable=False, server_default="session"),
        sa.Column("scope_id", sa.String(255), nullable=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", JSONB, nullable=False, server_default="{}"),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("agent_memory")
    op.drop_table("audit_logs")
    op.drop_table("approvals")
    op.drop_table("tools")
    op.drop_table("prompts")
    op.drop_table("tasks")
    op.drop_table("agents")
    op.drop_table("users")

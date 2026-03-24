"""Schema hardening: timezone-aware timestamps, Numeric financials, FK cascades, indexes

Revision ID: 003
Revises: 002
Create Date: 2026-03-24

Changes:
- All DateTime columns → DateTime(timezone=True) via ALTER TYPE
- User.role default changed from 'admin' to 'viewer'
- Float financial fields → Numeric in trader_eval tables
- FK ondelete rules added (SET NULL for tasks/approvals, CASCADE for memory/trader)
- Missing indexes added (agent.name, agent.status, approval.action_type, approval.status, etc.)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# All tables with timestamp columns to convert
TIMESTAMP_ALTERATIONS = [
    ("users", ["created_at", "updated_at"]),
    ("agents", ["created_at", "updated_at"]),
    ("tasks", ["created_at", "updated_at"]),
    ("prompts", ["created_at", "updated_at"]),
    ("tools", ["created_at", "updated_at"]),
    ("approvals", ["created_at", "reviewed_at"]),
    ("audit_logs", ["created_at"]),
    ("agent_memory", ["created_at", "updated_at"]),
    ("trading_accounts", ["created_at", "updated_at", "expires_at"]),
    ("trade_records", ["opened_at", "closed_at"]),
    ("payout_requests", ["created_at", "reviewed_at", "paid_at"]),
    ("rule_violations", ["detected_at"]),
    ("fraud_alerts", ["created_at", "resolved_at"]),
]


def upgrade() -> None:
    # 1. Convert all DateTime columns to timezone-aware
    for table, columns in TIMESTAMP_ALTERATIONS:
        for col in columns:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMPTZ USING {col} AT TIME ZONE \'UTC\'')

    # 2. Fix User.role default from 'admin' to 'viewer'
    op.alter_column("users", "role", server_default="viewer")

    # 3. Convert Float → Numeric for financial fields in trading tables
    # trading_accounts
    for col in ["starting_balance", "current_balance"]:
        op.alter_column("trading_accounts", col, type_=sa.Numeric(15, 2), existing_type=sa.Float)
    for col in ["max_drawdown_pct", "daily_loss_limit_pct", "profit_target_pct"]:
        op.alter_column("trading_accounts", col, type_=sa.Numeric(6, 2), existing_type=sa.Float)

    # trade_records
    for col in ["entry_price", "exit_price", "quantity"]:
        op.alter_column("trade_records", col, type_=sa.Numeric(15, 6), existing_type=sa.Float)
    op.alter_column("trade_records", "pnl", type_=sa.Numeric(15, 2), existing_type=sa.Float)

    # payout_requests
    op.alter_column("payout_requests", "amount", type_=sa.Numeric(15, 2), existing_type=sa.Float)

    # 4. Drop and recreate FKs with ondelete rules
    # tasks.parent_task_id → SET NULL
    op.drop_constraint("tasks_parent_task_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key("tasks_parent_task_id_fkey", "tasks", "tasks", ["parent_task_id"], ["id"], ondelete="SET NULL")

    # tasks.assigned_agent_id → SET NULL
    op.drop_constraint("tasks_assigned_agent_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key("tasks_assigned_agent_id_fkey", "tasks", "agents", ["assigned_agent_id"], ["id"], ondelete="SET NULL")

    # approvals.task_id → SET NULL
    op.drop_constraint("approvals_task_id_fkey", "approvals", type_="foreignkey")
    op.create_foreign_key("approvals_task_id_fkey", "approvals", "tasks", ["task_id"], ["id"], ondelete="SET NULL")

    # agent_memory.agent_id → CASCADE
    op.drop_constraint("agent_memory_agent_id_fkey", "agent_memory", type_="foreignkey")
    op.create_foreign_key("agent_memory_agent_id_fkey", "agent_memory", "agents", ["agent_id"], ["id"], ondelete="CASCADE")

    # trader eval FKs → CASCADE
    for table in ["trade_records", "payout_requests", "rule_violations", "fraud_alerts"]:
        constraint = f"{table}_account_id_fkey"
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "trading_accounts", ["account_id"], ["id"], ondelete="CASCADE")

    # 5. Add missing indexes
    op.create_index("ix_agents_name", "agents", ["name"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_approvals_action_type", "approvals", ["action_type"])
    op.create_index("ix_approvals_status", "approvals", ["status"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_trading_accounts_status", "trading_accounts", ["status"])
    op.create_index("ix_trade_records_symbol", "trade_records", ["symbol"])
    op.create_index("ix_payout_requests_status", "payout_requests", ["status"])
    op.create_index("ix_fraud_alerts_status", "fraud_alerts", ["status"])


def downgrade() -> None:
    # Drop new indexes
    for idx in [
        "ix_agents_name", "ix_agents_status", "ix_approvals_action_type",
        "ix_approvals_status", "ix_audit_logs_resource_type",
        "ix_trading_accounts_status", "ix_trade_records_symbol",
        "ix_payout_requests_status", "ix_fraud_alerts_status",
    ]:
        op.drop_index(idx)

    # Revert FK cascades (remove ondelete rules)
    for table in ["fraud_alerts", "rule_violations", "payout_requests", "trade_records"]:
        constraint = f"{table}_account_id_fkey"
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "trading_accounts", ["account_id"], ["id"])

    op.drop_constraint("agent_memory_agent_id_fkey", "agent_memory", type_="foreignkey")
    op.create_foreign_key("agent_memory_agent_id_fkey", "agent_memory", "agents", ["agent_id"], ["id"])

    op.drop_constraint("approvals_task_id_fkey", "approvals", type_="foreignkey")
    op.create_foreign_key("approvals_task_id_fkey", "approvals", "tasks", ["task_id"], ["id"])

    op.drop_constraint("tasks_assigned_agent_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key("tasks_assigned_agent_id_fkey", "tasks", "agents", ["assigned_agent_id"], ["id"])

    op.drop_constraint("tasks_parent_task_id_fkey", "tasks", type_="foreignkey")
    op.create_foreign_key("tasks_parent_task_id_fkey", "tasks", "tasks", ["parent_task_id"], ["id"])

    # Revert Numeric → Float
    op.alter_column("payout_requests", "amount", type_=sa.Float, existing_type=sa.Numeric(15, 2))
    op.alter_column("trade_records", "pnl", type_=sa.Float, existing_type=sa.Numeric(15, 2))
    for col in ["entry_price", "exit_price", "quantity"]:
        op.alter_column("trade_records", col, type_=sa.Float, existing_type=sa.Numeric(15, 6))
    for col in ["max_drawdown_pct", "daily_loss_limit_pct", "profit_target_pct"]:
        op.alter_column("trading_accounts", col, type_=sa.Float, existing_type=sa.Numeric(6, 2))
    for col in ["starting_balance", "current_balance"]:
        op.alter_column("trading_accounts", col, type_=sa.Float, existing_type=sa.Numeric(15, 2))

    # Revert user.role default
    op.alter_column("users", "role", server_default="admin")

    # Revert TIMESTAMPTZ → TIMESTAMP (lossy but structurally valid)
    for table, columns in TIMESTAMP_ALTERATIONS:
        for col in columns:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {col} TYPE TIMESTAMP USING {col} AT TIME ZONE \'UTC\'')

"""Trader evaluation domain tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trading_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_email", sa.String(255), nullable=False, index=True),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("plan", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("starting_balance", sa.Float, nullable=False),
        sa.Column("current_balance", sa.Float, nullable=False),
        sa.Column("max_drawdown_pct", sa.Float, nullable=False, server_default="10.0"),
        sa.Column("daily_loss_limit_pct", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("profit_target_pct", sa.Float, nullable=False, server_default="8.0"),
        sa.Column("trading_days", sa.Integer, server_default="0"),
        sa.Column("min_trading_days", sa.Integer, server_default="5"),
        sa.Column("rules", JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "trade_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("trading_accounts.id"), nullable=False, index=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("quantity", sa.Float, nullable=False),
        sa.Column("pnl", sa.Float, server_default="0.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("opened_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "payout_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("trading_accounts.id"), nullable=False, index=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("fraud_flags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("paid_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "rule_violations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("trading_accounts.id"), nullable=False, index=True),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("auto_action", sa.String(50), nullable=True),
        sa.Column("resolved", sa.Boolean, server_default="false"),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column("detected_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "fraud_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("trading_accounts.id"), nullable=False, index=True),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("risk_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("evidence", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("fraud_alerts")
    op.drop_table("rule_violations")
    op.drop_table("payout_requests")
    op.drop_table("trade_records")
    op.drop_table("trading_accounts")

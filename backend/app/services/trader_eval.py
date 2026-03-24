"""Trader Evaluation business logic.

Rule evaluation, violation tracking, account lifecycle, and fraud detection.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.trader_eval import (
    TradingAccount, TradeRecord, PayoutRequest, RuleViolation, FraudAlert,
)
from app.core.logging import log_action


def _utcnow():
    return datetime.now(timezone.utc)


# --- Rule Evaluation ---

async def evaluate_account_rules(db: AsyncSession, account: TradingAccount) -> list[RuleViolation]:
    """Evaluate all rules on a trading account. Returns newly created violations."""
    violations = []

    # Rule 1: Max drawdown
    drawdown_pct = ((account.starting_balance - account.current_balance) / account.starting_balance) * 100
    if drawdown_pct >= account.max_drawdown_pct:
        v = await _create_violation(
            db, account,
            rule_type="max_drawdown_breach",
            description=f"Account drawdown {drawdown_pct:.2f}% exceeds limit {account.max_drawdown_pct}%",
            severity="fatal",
            auto_action="fail_account",
            details={"drawdown_pct": float(drawdown_pct), "limit": float(account.max_drawdown_pct)},
        )
        violations.append(v)

    # Rule 2: Daily loss limit (check today's PnL)
    today_start = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(TradeRecord.pnl), 0)).where(
            TradeRecord.account_id == account.id,
            TradeRecord.status == "closed",
            TradeRecord.closed_at >= today_start,
        )
    )
    daily_pnl = Decimal(str(result.scalar()))
    if daily_pnl < 0:
        daily_loss_pct = abs(daily_pnl) / account.starting_balance * 100
        if daily_loss_pct >= account.daily_loss_limit_pct:
            v = await _create_violation(
                db, account,
                rule_type="daily_loss_breach",
                description=f"Daily loss {daily_loss_pct:.2f}% exceeds limit {account.daily_loss_limit_pct}%",
                severity="fatal",
                auto_action="fail_account",
                details={"daily_loss_pct": float(daily_loss_pct), "daily_pnl": float(daily_pnl)},
            )
            violations.append(v)

    # Rule 3: Profit target reached (positive outcome)
    profit_pct = ((account.current_balance - account.starting_balance) / account.starting_balance) * 100
    if profit_pct >= account.profit_target_pct and account.trading_days >= account.min_trading_days:
        if account.status == "active" and account.account_type in ("challenge", "verification"):
            account.status = "passed"
            await db.flush()
            await log_action(
                db, actor="system", actor_type="system", action="account_passed",
                resource_type="trading_account", resource_id=str(account.id),
                after_state={"profit_pct": float(profit_pct), "trading_days": account.trading_days},
            )

    # Apply auto-actions
    for v in violations:
        if v.auto_action == "fail_account" and account.status == "active":
            account.status = "failed"
            await db.flush()
            await log_action(
                db, actor="system", actor_type="system", action="account_failed",
                resource_type="trading_account", resource_id=str(account.id),
                after_state={"rule_type": v.rule_type, "severity": v.severity},
            )

    return violations


async def _create_violation(
    db: AsyncSession,
    account: TradingAccount,
    rule_type: str,
    description: str,
    severity: str,
    auto_action: str | None = None,
    details: dict | None = None,
) -> RuleViolation:
    violation = RuleViolation(
        id=uuid.uuid4(),
        account_id=account.id,
        rule_type=rule_type,
        description=description,
        severity=severity,
        auto_action=auto_action,
        details=details or {},
    )
    db.add(violation)
    await db.flush()
    await log_action(
        db, actor="system", actor_type="system", action="rule_violation",
        resource_type="rule_violation", resource_id=str(violation.id),
        after_state={"rule_type": rule_type, "severity": severity, "account_id": str(account.id)},
    )
    return violation


# --- Trade Processing ---

async def close_trade(db: AsyncSession, trade: TradeRecord, exit_price: Decimal) -> TradeRecord:
    """Close an open trade, calculate PnL, update account balance."""
    if trade.direction == "long":
        pnl = (exit_price - trade.entry_price) * trade.quantity
    else:
        pnl = (trade.entry_price - exit_price) * trade.quantity

    trade.exit_price = exit_price
    trade.pnl = pnl
    trade.status = "closed"
    trade.closed_at = _utcnow()
    await db.flush()

    # Update account balance
    result = await db.execute(select(TradingAccount).where(TradingAccount.id == trade.account_id))
    account = result.scalar_one()
    account.current_balance += pnl
    await db.flush()

    # Check for new trading day
    result = await db.execute(
        select(func.count(func.distinct(func.date(TradeRecord.opened_at)))).where(
            TradeRecord.account_id == account.id,
        )
    )
    account.trading_days = result.scalar() or 0
    await db.flush()

    # Evaluate rules after trade close
    await evaluate_account_rules(db, account)

    return trade


# --- Fraud Detection Foundations ---

async def check_trade_for_fraud(db: AsyncSession, trade: TradeRecord) -> FraudAlert | None:
    """Run basic fraud heuristics on a new trade. Returns alert if suspicious."""
    account_result = await db.execute(
        select(TradingAccount).where(TradingAccount.id == trade.account_id)
    )
    account = account_result.scalar_one()

    # Heuristic 1: Trade size > 50% of account balance
    trade_value = trade.entry_price * trade.quantity
    if trade_value > account.current_balance * Decimal("0.5"):
        alert = FraudAlert(
            id=uuid.uuid4(),
            account_id=account.id,
            alert_type="oversized_position",
            risk_score=0.7,
            description=f"Trade value ${trade_value:.2f} exceeds 50% of balance ${account.current_balance:.2f}",
            evidence={"trade_id": str(trade.id), "trade_value": float(trade_value), "balance": float(account.current_balance)},
        )
        db.add(alert)
        await db.flush()
        await log_action(
            db, actor="system", actor_type="system", action="fraud_alert",
            resource_type="fraud_alert", resource_id=str(alert.id),
            after_state={"alert_type": "oversized_position", "risk_score": 0.7},
        )
        return alert

    # Heuristic 2: Rapid trading (>20 trades in same day)
    today = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(TradeRecord.id)).where(
            TradeRecord.account_id == account.id,
            TradeRecord.opened_at >= today,
        )
    )
    today_count = result.scalar() or 0
    if today_count > 20:
        alert = FraudAlert(
            id=uuid.uuid4(),
            account_id=account.id,
            alert_type="rapid_trading",
            risk_score=0.5,
            description=f"{today_count} trades today — possible bot or copy-trade activity",
            evidence={"trade_count_today": today_count, "trade_id": str(trade.id)},
        )
        db.add(alert)
        await db.flush()
        await log_action(
            db, actor="system", actor_type="system", action="fraud_alert",
            resource_type="fraud_alert", resource_id=str(alert.id),
            after_state={"alert_type": "rapid_trading", "risk_score": 0.5},
        )
        return alert

    return None

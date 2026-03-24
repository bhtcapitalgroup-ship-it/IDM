"""Trader Evaluation API routes.

Account management, trade ingestion, payout flow, violation inspection, fraud alerts.
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.trader_eval import (
    TradingAccount, TradeRecord, PayoutRequest, RuleViolation, FraudAlert,
)
from app.schemas.trader_eval import (
    AccountCreate, AccountResponse, AccountUpdate,
    TradeCreate, TradeClose, TradeResponse,
    PayoutCreate, PayoutDecision, PayoutResponse,
    ViolationResponse, FraudAlertResponse,
)
from app.core.auth import get_current_user
from app.core.permissions import check_permission
from app.core.logging import log_action
from app.services.trader_eval import close_trade, evaluate_account_rules, check_trade_for_fraud
from app.services.workflow_engine import require_approval_or_block

router = APIRouter(prefix="/trader", tags=["trader-eval"])


# ==================== Accounts ====================

@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    status: str | None = None,
    user_email: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(TradingAccount)
    if status:
        query = query.where(TradingAccount.status == status)
    if user_email:
        query = query.where(TradingAccount.user_email == user_email)
    result = await db.execute(query.order_by(TradingAccount.created_at.desc()).limit(limit).offset(offset))
    return result.scalars().all()


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    result = await db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_agents")
    account = TradingAccount(
        id=uuid.uuid4(),
        user_email=body.user_email,
        account_type=body.account_type,
        plan=body.plan,
        starting_balance=body.starting_balance,
        current_balance=body.starting_balance,
        max_drawdown_pct=body.max_drawdown_pct,
        daily_loss_limit_pct=body.daily_loss_limit_pct,
        profit_target_pct=body.profit_target_pct,
        min_trading_days=body.min_trading_days,
        rules=body.rules,
    )
    db.add(account)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_account",
        resource_type="trading_account", resource_id=str(account.id),
        after_state={"email": body.user_email, "plan": body.plan, "balance": float(body.starting_balance)},
    )
    return account


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    result = await db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(account, k, v)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="update_account",
        resource_type="trading_account", resource_id=str(account.id),
        after_state={k: float(v) if isinstance(v, __import__('decimal').Decimal) else v for k, v in updates.items()},
    )
    return account


# ==================== Trades ====================

@router.get("/accounts/{account_id}/trades", response_model=list[TradeResponse])
async def list_trades(
    account_id: uuid.UUID,
    status: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(TradeRecord).where(TradeRecord.account_id == account_id)
    if status:
        query = query.where(TradeRecord.status == status)
    result = await db.execute(query.order_by(TradeRecord.opened_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/trades", response_model=TradeResponse, status_code=201)
async def open_trade(
    body: TradeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_agents")
    # Verify account exists and is active
    result = await db.execute(select(TradingAccount).where(TradingAccount.id == body.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.status != "active":
        raise HTTPException(status_code=400, detail=f"Account is {account.status}, cannot open trades")

    trade = TradeRecord(
        id=uuid.uuid4(),
        account_id=body.account_id,
        symbol=body.symbol.upper(),
        direction=body.direction,
        entry_price=body.entry_price,
        quantity=body.quantity,
    )
    db.add(trade)
    await db.flush()

    # Check for fraud patterns
    await check_trade_for_fraud(db, trade)

    await log_action(
        db, actor=str(user.id), actor_type="user", action="open_trade",
        resource_type="trade_record", resource_id=str(trade.id),
        after_state={"symbol": trade.symbol, "direction": body.direction, "entry_price": float(body.entry_price)},
    )
    return trade


@router.post("/trades/{trade_id}/close", response_model=TradeResponse)
async def close_trade_endpoint(
    trade_id: uuid.UUID,
    body: TradeClose,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "update_agents")
    result = await db.execute(select(TradeRecord).where(TradeRecord.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status != "open":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    trade = await close_trade(db, trade, body.exit_price)

    await log_action(
        db, actor=str(user.id), actor_type="user", action="close_trade",
        resource_type="trade_record", resource_id=str(trade.id),
        after_state={"exit_price": float(body.exit_price), "pnl": float(trade.pnl)},
    )
    return trade


# ==================== Payouts ====================

@router.get("/payouts", response_model=list[PayoutResponse])
async def list_payouts(
    status: str | None = None,
    account_id: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(PayoutRequest)
    if status:
        query = query.where(PayoutRequest.status == status)
    if account_id:
        query = query.where(PayoutRequest.account_id == account_id)
    result = await db.execute(query.order_by(PayoutRequest.created_at.desc()).limit(limit))
    return result.scalars().all()


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
async def create_payout(
    body: PayoutCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "create_agents")
    # Verify account is funded
    result = await db.execute(select(TradingAccount).where(TradingAccount.id == body.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.account_type != "funded":
        raise HTTPException(status_code=400, detail="Payouts only available for funded accounts")
    if body.amount > account.current_balance:
        raise HTTPException(status_code=400, detail="Payout amount exceeds account balance")

    payout = PayoutRequest(
        id=uuid.uuid4(),
        account_id=body.account_id,
        amount=body.amount,
        method=body.method,
    )
    db.add(payout)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="create_payout",
        resource_type="payout_request", resource_id=str(payout.id),
        after_state={"amount": float(body.amount), "method": body.method},
    )
    return payout


@router.post("/payouts/{payout_id}/decide", response_model=PayoutResponse)
async def decide_payout(
    payout_id: uuid.UUID,
    body: PayoutDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "review_approvals")
    result = await db.execute(select(PayoutRequest).where(PayoutRequest.id == payout_id))
    payout = result.scalar_one_or_none()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    if payout.status != "pending":
        raise HTTPException(status_code=400, detail="Payout already decided")

    # Payout approval is gated
    pending_approval = await require_approval_or_block(
        db,
        action_type="payout_change",
        description=f"Payout ${payout.amount} via {payout.method}",
        requested_by=str(user.id),
        task_id=None,
    )
    if pending_approval:
        await db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Platform approval required for payout decisions. Approval ID: {pending_approval.id}",
        )

    payout.status = body.status
    payout.reviewed_by = str(user.id)
    payout.review_notes = body.review_notes
    payout.reviewed_at = datetime.now(timezone.utc)
    if body.status == "approved":
        payout.paid_at = datetime.now(timezone.utc)
    await db.flush()
    await log_action(
        db, actor=str(user.id), actor_type="user", action="decide_payout",
        resource_type="payout_request", resource_id=str(payout.id),
        after_state={"status": body.status, "notes": body.review_notes},
    )
    return payout


# ==================== Violations ====================

@router.get("/violations", response_model=list[ViolationResponse])
async def list_violations(
    account_id: uuid.UUID | None = None,
    severity: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(RuleViolation)
    if account_id:
        query = query.where(RuleViolation.account_id == account_id)
    if severity:
        query = query.where(RuleViolation.severity == severity)
    result = await db.execute(query.order_by(RuleViolation.detected_at.desc()).limit(limit))
    return result.scalars().all()


# ==================== Fraud Alerts ====================

@router.get("/fraud-alerts", response_model=list[FraudAlertResponse])
async def list_fraud_alerts(
    status: str | None = None,
    account_id: uuid.UUID | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_permission(user.role, "read_agents")
    query = select(FraudAlert)
    if status:
        query = query.where(FraudAlert.status == status)
    if account_id:
        query = query.where(FraudAlert.account_id == account_id)
    result = await db.execute(query.order_by(FraudAlert.created_at.desc()).limit(limit))
    return result.scalars().all()

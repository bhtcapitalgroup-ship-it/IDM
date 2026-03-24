"""Pydantic schemas for the trader evaluation domain."""
from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr
from uuid import UUID
from datetime import datetime


# --- Trading Account ---

AccountType = Literal["challenge", "verification", "funded"]
AccountStatus = Literal["active", "passed", "failed", "suspended", "closed"]

class AccountCreate(BaseModel):
    user_email: EmailStr
    account_type: AccountType
    plan: str = Field(..., min_length=1, max_length=100)
    starting_balance: Decimal = Field(..., gt=0, le=1_000_000)
    max_drawdown_pct: Decimal = Field(default=Decimal("10.00"), gt=0, le=100)
    daily_loss_limit_pct: Decimal = Field(default=Decimal("5.00"), gt=0, le=100)
    profit_target_pct: Decimal = Field(default=Decimal("8.00"), gt=0, le=100)
    min_trading_days: int = Field(default=5, ge=0, le=365)
    rules: dict = {}

class AccountResponse(BaseModel):
    id: UUID
    user_email: str
    account_type: str
    plan: str
    status: str
    starting_balance: Decimal
    current_balance: Decimal
    max_drawdown_pct: Decimal
    daily_loss_limit_pct: Decimal
    profit_target_pct: Decimal
    trading_days: int
    min_trading_days: int
    rules: dict
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    model_config = {"from_attributes": True}

class AccountUpdate(BaseModel):
    status: AccountStatus | None = None
    current_balance: Decimal | None = None
    rules: dict | None = None


# --- Trade Record ---

TradeDirection = Literal["long", "short"]
TradeStatus = Literal["open", "closed"]

class TradeCreate(BaseModel):
    account_id: UUID
    symbol: str = Field(..., min_length=1, max_length=20)
    direction: TradeDirection
    entry_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)

class TradeClose(BaseModel):
    exit_price: Decimal = Field(..., gt=0)

class TradeResponse(BaseModel):
    id: UUID
    account_id: UUID
    symbol: str
    direction: str
    entry_price: Decimal
    exit_price: Decimal | None
    quantity: Decimal
    pnl: Decimal
    status: str
    opened_at: datetime
    closed_at: datetime | None
    model_config = {"from_attributes": True}


# --- Payout Request ---

PayoutStatus = Literal["pending", "approved", "rejected", "paid"]
PayoutMethod = Literal["bank_transfer", "crypto", "paypal"]

class PayoutCreate(BaseModel):
    account_id: UUID
    amount: Decimal = Field(..., gt=0)
    method: PayoutMethod

class PayoutDecision(BaseModel):
    status: Literal["approved", "rejected"]
    review_notes: str | None = None

class PayoutResponse(BaseModel):
    id: UUID
    account_id: UUID
    amount: Decimal
    method: str
    status: str
    reviewed_by: str | None
    review_notes: str | None
    fraud_flags: list
    created_at: datetime
    reviewed_at: datetime | None
    paid_at: datetime | None
    model_config = {"from_attributes": True}


# --- Rule Violation ---

ViolationSeverity = Literal["warning", "critical", "fatal"]

class ViolationResponse(BaseModel):
    id: UUID
    account_id: UUID
    rule_type: str
    description: str
    severity: str
    auto_action: str | None
    resolved: bool
    details: dict
    detected_at: datetime
    model_config = {"from_attributes": True}


# --- Fraud Alert ---

class FraudAlertResponse(BaseModel):
    id: UUID
    account_id: UUID
    alert_type: str
    risk_score: float
    description: str
    evidence: dict
    status: str
    reviewed_by: str | None
    created_at: datetime
    resolved_at: datetime | None
    model_config = {"from_attributes": True}

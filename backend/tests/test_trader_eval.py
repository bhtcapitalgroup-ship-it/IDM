"""Tests for trader evaluation flows: accounts, trades, rules, payouts, fraud."""
import uuid
import pytest
from decimal import Decimal
from tests.conftest import auth_header


# === Helpers ===

async def _create_account(client, token, **overrides):
    defaults = {
        "user_email": "trader@example.com",
        "account_type": "challenge",
        "plan": "50k_standard",
        "starting_balance": 50000,
    }
    defaults.update(overrides)
    r = await client.post("/api/trader/accounts", json=defaults, headers=auth_header(token))
    assert r.status_code == 201, r.json()
    return r.json()


async def _open_trade(client, token, account_id, **overrides):
    defaults = {
        "account_id": account_id,
        "symbol": "NQ",
        "direction": "long",
        "entry_price": 100,
        "quantity": 10,
    }
    defaults.update(overrides)
    r = await client.post("/api/trader/trades", json=defaults, headers=auth_header(token))
    assert r.status_code == 201, r.json()
    return r.json()


# === Account Lifecycle ===

@pytest.mark.asyncio
async def test_create_account(client, admin_token):
    acct = await _create_account(client, admin_token)
    assert acct["status"] == "active"
    assert Decimal(str(acct["current_balance"])) == Decimal("50000")
    assert acct["account_type"] == "challenge"


@pytest.mark.asyncio
async def test_list_accounts(client, admin_token):
    await _create_account(client, admin_token)
    r = await client.get("/api/trader/accounts", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_get_account(client, admin_token):
    acct = await _create_account(client, admin_token)
    r = await client.get(f"/api/trader/accounts/{acct['id']}", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["plan"] == "50k_standard"


@pytest.mark.asyncio
async def test_update_account_status(client, admin_token):
    acct = await _create_account(client, admin_token)
    r = await client.patch(
        f"/api/trader/accounts/{acct['id']}",
        json={"status": "suspended"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "suspended"


# === Trade Ingestion ===

@pytest.mark.asyncio
async def test_open_trade(client, admin_token):
    acct = await _create_account(client, admin_token)
    trade = await _open_trade(client, admin_token, acct["id"])
    assert trade["status"] == "open"
    assert trade["symbol"] == "NQ"
    assert Decimal(str(trade["pnl"])) == 0


@pytest.mark.asyncio
async def test_cannot_trade_on_inactive_account(client, admin_token):
    acct = await _create_account(client, admin_token)
    await client.patch(f"/api/trader/accounts/{acct['id']}", json={"status": "failed"}, headers=auth_header(admin_token))
    r = await client.post(
        "/api/trader/trades",
        json={"account_id": acct["id"], "symbol": "ES", "direction": "long", "entry_price": 100, "quantity": 1},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "failed" in r.json()["detail"]


@pytest.mark.asyncio
async def test_close_trade_calculates_pnl(client, admin_token):
    acct = await _create_account(client, admin_token)
    trade = await _open_trade(client, admin_token, acct["id"], entry_price=100, quantity=10)
    r = await client.post(
        f"/api/trader/trades/{trade['id']}/close",
        json={"exit_price": 110},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "closed"
    # Long: (110 - 100) * 10 = 100
    assert Decimal(str(data["pnl"])) == Decimal("100")


@pytest.mark.asyncio
async def test_close_short_trade_pnl(client, admin_token):
    acct = await _create_account(client, admin_token)
    trade = await _open_trade(client, admin_token, acct["id"], direction="short", entry_price=100, quantity=5)
    r = await client.post(
        f"/api/trader/trades/{trade['id']}/close",
        json={"exit_price": 90},
        headers=auth_header(admin_token),
    )
    # Short: (100 - 90) * 5 = 50
    assert Decimal(str(r.json()["pnl"])) == Decimal("50")


@pytest.mark.asyncio
async def test_close_trade_updates_account_balance(client, admin_token):
    acct = await _create_account(client, admin_token, starting_balance=10000)
    trade = await _open_trade(client, admin_token, acct["id"], entry_price=100, quantity=10)
    await client.post(f"/api/trader/trades/{trade['id']}/close", json={"exit_price": 110}, headers=auth_header(admin_token))
    r = await client.get(f"/api/trader/accounts/{acct['id']}", headers=auth_header(admin_token))
    # 10000 + (110-100)*10 = 10100
    assert Decimal(str(r.json()["current_balance"])) == Decimal("10100")


# === Rule Evaluation ===

@pytest.mark.asyncio
async def test_max_drawdown_fails_account(client, admin_token):
    """Losing enough to breach max drawdown should fail the account."""
    acct = await _create_account(client, admin_token, starting_balance=10000)
    trade = await _open_trade(client, admin_token, acct["id"], entry_price=100, quantity=100)
    # Close at huge loss: (90 - 100) * 100 = -1000 = 10% drawdown
    await client.post(f"/api/trader/trades/{trade['id']}/close", json={"exit_price": 90}, headers=auth_header(admin_token))
    r = await client.get(f"/api/trader/accounts/{acct['id']}", headers=auth_header(admin_token))
    assert r.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_violation_created_on_drawdown_breach(client, admin_token):
    acct = await _create_account(client, admin_token, starting_balance=10000)
    trade = await _open_trade(client, admin_token, acct["id"], entry_price=100, quantity=100)
    await client.post(f"/api/trader/trades/{trade['id']}/close", json={"exit_price": 90}, headers=auth_header(admin_token))
    r = await client.get(f"/api/trader/violations?account_id={acct['id']}", headers=auth_header(admin_token))
    assert r.status_code == 200
    violations = r.json()
    assert len(violations) >= 1
    assert any(v["rule_type"] == "max_drawdown_breach" for v in violations)


# === Payouts ===

@pytest.mark.asyncio
async def test_payout_only_for_funded_accounts(client, admin_token):
    acct = await _create_account(client, admin_token, account_type="challenge")
    r = await client.post(
        "/api/trader/payouts",
        json={"account_id": acct["id"], "amount": 100, "method": "bank_transfer"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "funded" in r.json()["detail"]


@pytest.mark.asyncio
async def test_payout_created_for_funded_account(client, admin_token):
    acct = await _create_account(client, admin_token, account_type="funded", starting_balance=100000)
    r = await client.post(
        "/api/trader/payouts",
        json={"account_id": acct["id"], "amount": 5000, "method": "crypto"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_payout_exceeding_balance_rejected(client, admin_token):
    acct = await _create_account(client, admin_token, account_type="funded", starting_balance=1000)
    r = await client.post(
        "/api/trader/payouts",
        json={"account_id": acct["id"], "amount": 5000, "method": "bank_transfer"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 400
    assert "exceeds" in r.json()["detail"]


@pytest.mark.asyncio
async def test_payout_decision_requires_approval(client, admin_token):
    """Payout decisions are approval-gated."""
    acct = await _create_account(client, admin_token, account_type="funded", starting_balance=100000)
    r = await client.post(
        "/api/trader/payouts",
        json={"account_id": acct["id"], "amount": 5000, "method": "crypto"},
        headers=auth_header(admin_token),
    )
    payout_id = r.json()["id"]
    r = await client.post(
        f"/api/trader/payouts/{payout_id}/decide",
        json={"status": "approved"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 409
    assert "approval required" in r.json()["detail"].lower()


# === Fraud Detection ===

@pytest.mark.asyncio
async def test_oversized_position_triggers_fraud_alert(client, admin_token):
    """Trade value > 50% of balance should create a fraud alert."""
    acct = await _create_account(client, admin_token, starting_balance=10000)
    # Trade value: 100 * 100 = 10000, which is 100% of balance (> 50%)
    await _open_trade(client, admin_token, acct["id"], entry_price=100, quantity=100)
    r = await client.get(f"/api/trader/fraud-alerts?account_id={acct['id']}", headers=auth_header(admin_token))
    assert r.status_code == 200
    alerts = r.json()
    assert len(alerts) >= 1
    assert any(a["alert_type"] == "oversized_position" for a in alerts)

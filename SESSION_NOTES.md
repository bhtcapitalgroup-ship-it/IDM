# Session Notes — 2026-03-24

## 1. Current Verified Status

**Everything below was verified on this date against real running infrastructure.**

- PostgreSQL (pgvector:pg16) and Redis (7-alpine) running via Colima/Docker
- All 4 Alembic migrations applied successfully against real PostgreSQL
- Database seeded: 1 admin user, 8 agents, 16 tools
- Backend running on http://localhost:8000 (56 routes, hot reload)
- Frontend running on http://localhost:3000 (17 pages, Turbopack)
- 96 automated tests passing (SQLite in-memory)
- End-to-end smoke test passed against real PostgreSQL:
  - Login, token auth, get me
  - List agents (8 returned)
  - Create task, transition to assigned
  - Create trading account ($50k challenge)
  - Open trade (NQ long), close at profit, PnL = $200 correct
  - Account balance updated to $50,200
  - Fraud alert auto-generated (oversized position)
  - Audit log captured all actions
- Code pushed to https://github.com/bhtcapitalgroup-ship-it/IDM.git (2 commits)
- Admin login: admin@agentic.dev / admin123

## 2. What Is Implemented

### Backend (56 API routes)

| Module | Routes | Tests |
|---|---|---|
| Auth (login, me, seed) | 3 | 9 |
| Agents CRUD | 5 | 9 |
| Tasks CRUD + enqueue | 5 | 12 |
| Approvals (create, decide) | 3 | 6 |
| Approval enforcement gates | in tasks + agents | 6 |
| Admin (stats, audit logs) | 2 | 5 (indirect) |
| Orchestrator (AI decompose) | 1 | 5 |
| Prompts CRUD | 3 | 0 |
| Tools CRUD | 3 | 0 |
| Memory CRUD | 3 | 5 |
| Trader eval (accounts, trades, payouts, violations, fraud) | 12 | 16 |
| Collaboration (threads, messages, artifacts, handoffs, inbox) | 11 | 12 |
| Health | 1 | 0 |
| Worker enqueue | 1 | 3 |

### Database (17 models, 4 migrations)

Core: users, agents, tasks, prompts, tools, approvals, audit_logs, agent_memory
Trader: trading_accounts, trade_records, payout_requests, rule_violations, fraud_alerts
Collaboration: agent_threads, agent_messages, artifacts, handoffs

All timestamps are timezone-aware (TIMESTAMPTZ). Financial fields use Numeric. FK cascades defined. 9 additional indexes for common queries.

### Frontend (17 pages)

Dashboard, Operations, Orchestrator, Agents (list + detail), Tasks (list + detail),
Conversations, Artifacts, Prompts, Tools, Memory, Trader Eval (accounts/payouts/violations/fraud tabs),
Approvals, Audit Log, Login

Auth flow: JWT in localStorage, AuthProvider context, AppShell route guard, ErrorBoundary.

### Business Logic (real, not stubbed)

- Task lifecycle: 11 statuses, enforced transitions, dependency blocking, completion cascading
- Approval gates: agent deletion, review-required task completion, sensitive-action tasks, payout decisions
- Trading rules: max drawdown breach fails account, daily loss limit, profit target passes account
- PnL: long and short calculation, account balance update, trading day counting
- Fraud: oversized position detection (>50% balance), rapid trading detection (>20/day)
- Handoffs: task reassignment, review send-back to source agent
- Artifact versioning: version bumps on content change

### AI Service

Real httpx client with timeout (60s), retry (2x with backoff), structured JSON output, explicit AIError type. Orchestrator uses it for goal decomposition. Tested with mocked AI (5 tests prove plan creation, dependency wiring, failure handling). Never tested with a real API key.

### Worker

Redis-backed queue, task pickup, AI execution, retry with backoff, failure logging, result storage. Enqueue API endpoint exists. Worker process at `python -m app.workers.task_worker`. Never executed against real Redis.

## 3. What Is Still Simplified or Not Fully Verified

| Item | Status |
|---|---|
| AI service | Real code, never called with real API key |
| Worker execution | Real code, never run as a process against real Redis |
| Prompt/Tool APIs | Working routes, zero test coverage |
| Admin stats endpoint | Working, zero direct test coverage |
| Orchestrator with real AI | Tested only with mocked responses |
| Trader eval daily loss rule | Implemented but only tested via drawdown path |
| Trader eval profit target pass | Implemented, no dedicated test |
| Fraud rapid trading alert | Implemented, no dedicated test (needs >20 trades) |
| Docker image builds | Dockerfiles exist, never built |
| Production compose | docker-compose.prod.yml exists, never run |
| JSONB payload validation | Accepts arbitrary dicts, no content schema |
| Agent-level permissions | AGENT_ROLE_PERMISSIONS defined, check_agent_permission() never called |
| Automated task enqueue | Nothing auto-enqueues after orchestrator creates tasks |

## 4. Known Gaps Before Real Launch

**Must fix:**
- No rate limiting on login (brute force possible)
- No token refresh (24h expiry, user must re-login)
- Hardcoded admin password in seed (admin123)
- No CI/CD pipeline
- No HTTPS/TLS
- Agent-level permissions defined but not enforced
- Worker never tested in real execution

**Should fix:**
- Only 3 trading rules (need position size limits, weekend hold rules, news restrictions)
- Rules are hardcoded, not configurable per plan
- No email notifications for violations/payouts/status changes
- No user management UI (admin-only via seed)
- No WebSocket for real-time updates
- No account expiry enforcement
- No payout processing integration

## 5. Exact Next Step for Tomorrow

1. Set a real AI_API_KEY in .env and test the orchestrator with a real API call
2. Start the worker process and verify it picks up and executes a queued task
3. Add tests for prompts and tools APIs (currently at zero coverage)
4. Add rate limiting to the login endpoint (install slowapi)
5. Add a token refresh endpoint

## 6. Commands to Restart Everything

```bash
# Start Docker (if Colima stopped)
colima start

# Start PostgreSQL + Redis
cd ~/agentic-company-builder
docker compose up -d

# Run migrations (idempotent)
./scripts/migrate.sh

# Seed database (idempotent)
./scripts/seed-db.sh

# Start backend (port 8000, hot reload)
./scripts/start-backend.sh

# Start frontend (port 3000, separate terminal)
./scripts/start-frontend.sh

# Start worker (separate terminal, requires Redis)
./scripts/start-worker.sh

# Run tests
cd backend && source .venv/bin/activate && python -m pytest tests/ -v

# Check status
docker ps
curl http://localhost:8000/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

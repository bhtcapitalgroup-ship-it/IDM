# Session Notes — 2026-03-24 (updated after audit pass)

## 1. Current Verified Status

**Verified against real running infrastructure on 2026-03-24.**

### Infrastructure (all verified running)
- Colima VM running (2 CPU, 4GB RAM, 20GB disk)
- PostgreSQL (pgvector:pg16) on :5432 — accepting connections
- Redis (7-alpine) on :6379 — PONG confirmed
- All 4 Alembic migrations applied (head = 004)
- Database seeded: 1 admin user (admin@agentic.dev), 8 agents, 16 tools
- Backend running on http://localhost:8000 (56 routes, hot reload)
- Frontend running on http://localhost:3000 (17 pages, Turbopack)
- Worker connects to Redis successfully (verified programmatically)

### Backend (verified via real HTTP calls against PostgreSQL)
- Login: returns JWT token (verified)
- Auth me: returns user profile (verified)
- Protected routes: return 401 without token (verified)
- Agents: create, list, get, update all work (verified)
- Agent deletion: returns 409 requiring approval (verified)
- Input validation: rejects invalid roles (422), empty names (422) (verified)
- Tasks: create, transition (assigned), invalid transition rejected (400) (verified)
- Dependency enforcement: blocked task cannot start (400) (verified)
- Completion cascading: completing dependency unblocks dependent task (verified)
- Review-required gate: completing review task returns 409 until approved (verified)
- Approvals: create, decide (verified)
- Memory: store, retrieve, scope filter (verified)
- Audit logs: captured for all mutations tested (verified)
- Trader eval: create account, open trade, close trade, PnL correct (verified)
  - Short trade PnL: (5000-4950)*5 = $250 (verified)
  - Balance update: $100,000 + $250 = $100,250 (verified)
- Collaboration: threads, messages, artifacts, handoffs, resolve, inbox (all verified)
- Prompts: create (verified)
- Tools: create (verified)
- Orchestrator: correctly returns 502 with explicit error when AI key is invalid (verified)
  - Confirms real OpenAI client is active, not a mock
- Worker enqueue: task queued via API, confirmed in Redis (verified)
- Redis queue: enqueue/dequeue cycle works (verified programmatically)

### Frontend (verified)
- All 17 pages return HTTP 200
- Dynamic pages (/agents/[id], /tasks/[id]) return 200
- All 35 frontend API paths match backend routes (zero mismatches)
- Production build: zero TypeScript errors, zero compile errors

### Tests
- 96 automated tests, all passing (21.7s)
- 0 failures, 0 errors, 0 warnings

### Deployment Safety (verified)
- Staging with default JWT secret: startup rejected with FATAL
- Production with default DB creds: startup rejected with FATAL
- Debug mode auto-disabled in non-local environments
- Seed endpoint returns 403 in non-local environments

## 2. What Was Fixed During This Audit

- Removed stale admin@agentic.local user from PostgreSQL (orphaned from pre-email-fix seed run)
- No code changes needed — all systems working correctly

## 3. What Is NOT Verified (honest)

| Item | Why |
|---|---|
| Frontend UI interactions | No browser/screenshot access in this environment. Pages load (200) and API paths match, but form submissions, dialog behavior, filter interactions not visually confirmed. |
| Orchestrator with real AI | AI_API_KEY is placeholder. Confirmed the real client fires and returns explicit 502 on invalid key. Never seen a successful AI-generated plan. |
| Worker task execution | Worker connects to Redis and queue operations work. But _process_one and run_worker never executed as a running process picking up real tasks. |
| Docker image builds | Dockerfiles exist. Never built. Never run. |
| Production docker-compose | docker-compose.prod.yml exists. Never run. |
| Prompts/Tools list endpoints | Create verified. List/update not explicitly tested via HTTP (covered by 96 unit tests). |

## 4. Known Gaps Before Real Launch

**Must fix:**
- Set a real AI_API_KEY and verify orchestrator produces usable plans
- Run the worker process and verify it picks up and executes a queued task end-to-end
- No rate limiting on login (brute force possible)
- No token refresh (24h expiry, user must re-login)
- Hardcoded admin password (admin123) in seed — acceptable for dev, not for shared environments
- No CI/CD pipeline
- No HTTPS/TLS
- Docker images never built or tested

**Should fix:**
- Agent-level permissions defined but not enforced (check_agent_permission never called)
- Only 3 trading rules, not configurable per plan
- No email notifications
- No WebSocket for real-time updates
- No user management UI

## 5. Exact Next Step

1. Get a real OpenAI API key, set AI_API_KEY in .env, restart backend, and POST to /api/orchestrator/decompose with a real goal
2. Start the worker (`./scripts/start-worker.sh`), enqueue a task, and watch it execute
3. Open the frontend in a browser and click through every page to verify UI behavior
4. Build the Docker images and verify they start correctly

## 6. Commands to Restart Everything

```bash
# If machine was rebooted — start Colima first
colima start

# Start databases
cd ~/agentic-company-builder
docker compose up -d

# Verify databases
docker exec agentic-company-builder-postgres-1 pg_isready -U postgres
docker exec agentic-company-builder-redis-1 redis-cli ping

# Run migrations (idempotent, safe to re-run)
./scripts/migrate.sh

# Seed database (idempotent, safe to re-run)
./scripts/seed-db.sh

# Start backend (port 8000, hot reload)
./scripts/start-backend.sh

# Start frontend (port 3000, separate terminal)
cd frontend && npm run dev

# Start worker (separate terminal)
./scripts/start-worker.sh

# Run tests
cd backend && source .venv/bin/activate && python -m pytest tests/ -v

# Quick health check
curl http://localhost:8000/api/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Login
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@agentic.dev","password":"admin123"}'
```

### Git status
```
Repository: https://github.com/bhtcapitalgroup-ship-it/IDM.git
Branch: main
Latest commit: ad0a465 (Add frontend, fix admin email to valid domain)
Working tree: clean
```

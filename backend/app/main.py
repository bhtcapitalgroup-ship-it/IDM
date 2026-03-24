from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import auth, agents, tasks, approvals, admin, orchestrator, prompts, tools, memory, trader_eval, collaboration

settings = get_settings()

app = FastAPI(
    title="Agentic Company Builder",
    description="A controlled multi-agent operating system for building and running companies",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS: lock down by environment
_cors_origins = {
    "local": ["http://localhost:3000"],
    "dev": ["http://localhost:3000"],
    "staging": [],  # Set via CORS_ORIGINS env var
    "production": [],  # Set via CORS_ORIGINS env var
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins.get(settings.environment, []),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(orchestrator.router, prefix="/api")
app.include_router(prompts.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(trader_eval.router, prefix="/api")
app.include_router(collaboration.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
    }

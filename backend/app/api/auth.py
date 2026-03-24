from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.config import get_settings
from app.core.auth import verify_password, create_access_token, get_current_user, hash_password
from app.core.logging import log_action
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

# Lazy dummy hash for constant-time comparison when user not found
_DUMMY_HASH: str | None = None


def _get_dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy-timing-pad")
    return _DUMMY_HASH


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Always run bcrypt to prevent timing-based user enumeration
    if user:
        password_valid = verify_password(body.password, user.hashed_password)
    else:
        verify_password(body.password, _get_dummy_hash())
        password_valid = False

    if not user or not password_valid:
        await log_action(
            db, actor=body.email, actor_type="anonymous", action="login_failed",
            resource_type="auth", resource_id="login",
            metadata={"email": body.email},
        )
        # Commit the failed login audit entry before raising
        # (raising causes get_db to rollback, which would lose the log)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await log_action(
        db, actor=str(user.id), actor_type="user", action="login_success",
        resource_type="auth", resource_id=str(user.id),
    )
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/seed", response_model=UserResponse)
async def seed_admin(db: AsyncSession = Depends(get_db)):
    """Create default admin user. Only available in local/dev environments."""
    settings = get_settings()
    if not settings.is_local:
        raise HTTPException(status_code=403, detail="Seed endpoint disabled in this environment")

    result = await db.execute(select(User).where(User.email == "admin@agentic.dev"))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    admin = User(
        id=uuid.uuid4(),
        email="admin@agentic.dev",
        hashed_password=hash_password("admin123"),
        full_name="System Admin",
        role="admin",
    )
    db.add(admin)
    await db.flush()
    return admin

"""Test fixtures: in-memory SQLite database, test client, auth helpers."""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import JSON, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from app.database import Base, get_db
from app.main import app
from app.core.auth import hash_password, create_access_token
from app.models.user import User
from app.models.agent import Agent

# Register JSONB and PG UUID as JSON/String for SQLite DDL compilation
sqlite_dialect.base.SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
sqlite_dialect.base.SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Enable FK enforcement in SQLite
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("testpass123"),
        full_name="Test Admin",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def viewer_user(db: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="viewer@test.com",
        hashed_password=hash_password("testpass123"),
        full_name="Test Viewer",
        role="viewer",
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user: User):
    return create_access_token(str(admin_user.id), admin_user.role)


@pytest_asyncio.fixture
async def viewer_token(viewer_user: User):
    return create_access_token(str(viewer_user.id), viewer_user.role)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def sample_agent(db: AsyncSession):
    agent = Agent(
        id=uuid.uuid4(),
        name="Test Agent",
        role="backend_builder",
        type="specialist",
        status="active",
    )
    db.add(agent)
    await db.commit()
    return agent

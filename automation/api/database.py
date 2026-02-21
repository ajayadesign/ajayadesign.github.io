"""
AjayaDesign Automation — Async SQLAlchemy database setup.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from api.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # pool settings only for postgres
    **(
        {}
        if "sqlite" in settings.database_url
        else {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,       # test connections before use (survives sleep/wake)
            "pool_recycle": 300,          # recycle connections every 5 min to avoid stale FDs
        }
    ),
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
async_session_factory = async_session  # alias used by outreach services


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async session."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create all tables (used in lifespan and tests)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()

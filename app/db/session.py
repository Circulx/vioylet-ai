# Database bootstrap code centralizes SQLAlchemy metadata and session lifecycle for repositories.
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


settings = get_settings()
engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    # Yields an async SQLAlchemy session to FastAPI and closes the request-scoped DB context afterward.
    async with AsyncSessionLocal() as session:
        yield session

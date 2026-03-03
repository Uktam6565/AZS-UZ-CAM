import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _db_url() -> str:
    # 1) Берём из переменных окружения/ .env
    # ожидаем формат вида:
    # postgresql+asyncpg://user:pass@localhost:5432/dbname
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url

    # 2) запасной вариант под твой docker-compose (gasq/gasq/gasq)
    return "postgresql+asyncpg://gasq:gasq@localhost:5432/gasq"


engine: AsyncEngine = create_async_engine(
    _db_url(),
    future=True,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

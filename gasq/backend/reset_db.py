import asyncio
from sqlalchemy import text

from app.db.engine import engine
from app.db.base_class import Base
import app.db.base  # важно: импортирует модели


async def main():
    print("METADATA TABLES:", list(Base.metadata.tables.keys()))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))

    print("DB RESET OK")


if __name__ == "__main__":
    asyncio.run(main())
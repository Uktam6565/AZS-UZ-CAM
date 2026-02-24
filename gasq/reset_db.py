import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://gasq:gasq@localhost:5432/gasq"

async def reset():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute("DROP SCHEMA public CASCADE;")
        await conn.execute("CREATE SCHEMA public;")
    await engine.dispose()

asyncio.run(reset())
print("DB RESET OK")
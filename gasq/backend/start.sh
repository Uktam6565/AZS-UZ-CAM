#!/usr/bin/env bash
set -e

echo "Starting GasQ backend..."

python - <<'PY'
import os, asyncio
import asyncpg

db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    print("DATABASE_URL is not set")
    raise SystemExit(1)

# asyncpg expects postgresql:// (SQLAlchemy async uses postgresql+asyncpg://)
db_url_asyncpg = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

async def wait_db():
    last_err = None
    for _ in range(60):
        try:
            conn = await asyncpg.connect(dsn=db_url_asyncpg, timeout=5)
            await conn.execute("SELECT 1")
            await conn.close()
            print("DB is up")
            return
        except Exception as e:
            last_err = e
            await asyncio.sleep(1)

    print("DB is not reachable after 60s")
    print("Last error:", repr(last_err))
    raise SystemExit(1)

asyncio.run(wait_db())
PY

echo "Running migrations..."
alembic upgrade head

echo "Launching gunicorn..."

exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120
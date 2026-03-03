#!/usr/bin/env bash
set -e

echo "Starting GasQ backend..."

python - <<'PY'
import os, time
import psycopg2
from urllib.parse import urlparse

db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    print("DATABASE_URL is not set")
    raise SystemExit(1)

db_url_sync = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
u = urlparse(db_url_sync)

host = u.hostname
port = u.port or 5432
user = u.username
password = u.password
dbname = u.path.lstrip("/")

for i in range(60):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
        conn.close()
        print("DB is up")
        break
    except Exception:
        time.sleep(1)
else:
    print("DB is not reachable after 60s")
    raise SystemExit(1)
PY

echo "Running migrations..."
alembic upgrade head

echo "Launching gunicorn..."
exec gunicorn \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  -b 0.0.0.0:8000 \
  app.main:app \
  --access-logfile - \
  --error-logfile -
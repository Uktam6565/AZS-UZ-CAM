from fastapi import FastAPI, Request
import logging
import sys
import time
import os
import sentry_sdk
from sqlalchemy import text
from app.core.config import settings
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
from app.core.lifespan import lifespan

from app.api.router import api_router
from app.db.engine import engine
from app.db.base import Base
from app.api.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("gasq")

# Sentry monitoring
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.2,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info("Sentry monitoring enabled")

# Prometheus HTTP metrics
HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

app = FastAPI(
    title="GasQ - Queue & Station Management",
    version="0.1.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    endpoint = request.url.path
    method = request.method
    status = response.status_code

    HTTP_REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
    HTTP_LATENCY.labels(method=method, endpoint=endpoint).observe(process_time)

    logger.info(
        f"{request.client.host} {method} {endpoint} "
        f"{status} {round(process_time * 1000, 2)}ms"
    )

    return response

# CORS — берём из .env (CORS_ORIGINS)
origins = settings.cors_origins_list()
# На всякий случай: если пусто — разрешим localhost:5500, чтобы не ломать фронт
if not origins:
    origins = ["http://localhost:5500"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["system"])
async def health_check():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "service": "gasq-backend",
            "database": "ok",
        }
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "service": "gasq-backend",
                "database": "unavailable",
            },
        )

@app.get("/", tags=["system"])
def root():
    return {"message": "GasQ API is running. Open /docs for Swagger UI."}

@app.get("/metrics", tags=["system"])
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

# Подключаем все API роуты
app.include_router(api_router, prefix="/api/v1")

# Глобальная обработка ошибок (чтобы не падало “молча”)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

@app.on_event("startup")
async def on_startup():
    logger.info("GasQ backend starting up")

    # Проверка БД
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("SELECT 1"))




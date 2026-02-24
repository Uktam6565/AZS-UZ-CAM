from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.db.engine import engine
from app.db.base import Base

app = FastAPI(
    title="GasQ - Queue & Station Management",
    version="0.1.0",
)

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
def health_check():
    return {"status": "ok", "service": "gasq-backend"}

@app.get("/", tags=["system"])
def root():
    return {"message": "GasQ API is running. Open /docs for Swagger UI."}

# Подключаем все API роуты
app.include_router(api_router, prefix="/api")

# Глобальная обработка ошибок (чтобы не падало “молча”)
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # optional ping
        await conn.execute(text("SELECT 1"))
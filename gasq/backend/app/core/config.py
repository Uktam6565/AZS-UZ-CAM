from __future__ import annotations

from typing import List, Optional

# Поддержка и Pydantic v2 (pydantic-settings), и Pydantic v1
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    PYDANTIC_V2 = True
except Exception:
    from pydantic import BaseSettings  # type: ignore
    PYDANTIC_V2 = False


def _parse_origins(value: str | List[str] | None) -> List[str]:
    """
    Поддерживаем:
    - "http://localhost:5500,http://127.0.0.1:5500"
    - "http://localhost:5500"
    - ["http://localhost:5500", ...]
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]


class Settings(BaseSettings):
    # -----------------
    # Database
    # -----------------
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/gasq"

    # -----------------
    # JWT / Auth
    # -----------------
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # -----------------
    # CORS
    # -----------------
    # в .env можно строкой через запятую: CORS_ORIGINS=http://localhost:5500
    CORS_ORIGINS: Optional[str] = "http://localhost:5500"

    def cors_origins_list(self) -> List[str]:
        return _parse_origins(self.CORS_ORIGINS)

    # -----------------
    # Stations / Search defaults
    # (чтобы не падало stations.py)
    # -----------------
    DEFAULT_SEARCH_RADIUS_KM: float = 5.0

    # Если где-то в проекте используются такие настройки — они тоже безопасны:
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    NO_SHOW_MINUTES: int = 3  # для теста. потом можно 5-7
    AVG_SERVICE_MINUTES: int = 5
    JOIN_COOLDOWN_SECONDS: int = 10

    if PYDANTIC_V2:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"


settings = Settings()

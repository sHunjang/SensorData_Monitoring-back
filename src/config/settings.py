"""
환경변수 로딩
- PG_DSN: 예) postgresql://postgres:postgres@localhost:5432/energydb
- CORS_ORIGINS: 콤마구분(옵션). 예) http://localhost:3000
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    pg_dsn: str
    cors_origins: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

settings = Settings()

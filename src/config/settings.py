"""
환경변서 / .env 파일에서 로드
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    pg_dsn: str
    allowed_origins: str  # .env에서 ALLOWED_ORIGINS 읽어옴

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

def get_allowed_origins() -> list[str]:
    """콤마 구분 문자열을 리스트로 변환"""
    return [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

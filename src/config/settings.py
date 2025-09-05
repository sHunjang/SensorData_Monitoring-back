from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class SerialConfig(BaseModel):
    port: str
    slave_id: int
    baudrate: int = 9600
    parity: str = "N"   # N/E/O
    stopbits: int = 1   # 1/2
    timeout_s: float = 1.0
    poll_seconds: int = 5

class Settings(BaseSettings):
    pg_dsn: str
    serial: SerialConfig

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_nested_delimiter="__")

# 환경변수 키 예시:
# PG_DSN=...
# SERIAL__PORT=COM3
# SERIAL__SLAVE_ID=11
# SERIAL__BAUDRATE=9600 ...
settings = Settings()  # import 해서 사용

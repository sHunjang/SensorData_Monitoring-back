"""
전역 설정 모듈.
사용법:
  from src.config.settings import settings
  settings.MODBUS_PORT, settings.MODBUS_3W_IDS, settings.ENV_PORT 등 사용
환경파일: .env 로 덮어쓰기 가능.
"""

import os
from dotenv import load_dotenv
from typing import List, Optional

load_dotenv()

def _parse_int(env_name: str, default: int) -> int:
    v = os.getenv(env_name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default

def _parse_list_int(env_name: str, default: List[int]) -> List[int]:
    v = os.getenv(env_name, "")
    if not v:
        return default
    parts = [p.strip() for p in v.split(",") if p.strip()]
    out = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            continue
    return out

class Settings:
    # 실행 모드
    MODE: str = os.getenv("MODE", "real").lower()

    # CORS 설정 문자열 (콤마 구분). 빈 값이면 개발용 기본 origin 허용.
    cors_origins: Optional[str] = os.getenv("CORS_ORIGINS", "").strip() or None

    # Postgres DSN
    PG_DSN: str = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")

    # 로깅 레벨
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # ---------------- Modbus (전력량계) 관련 ----------------
    # 전력량계가 연결된 COM 포트
    MODBUS_PORT: str = os.getenv("MODBUS_PORT", "COM7")
    MODBUS_BAUDRATE: int = _parse_int("MODBUS_BAUDRATE", 9600)
    MODBUS_PARITY: str = os.getenv("MODBUS_PARITY", "N")
    MODBUS_STOPBITS: int = _parse_int("MODBUS_STOPBITS", 1)
    MODBUS_BYTESIZE: int = _parse_int("MODBUS_BYTESIZE", 8)

    # 3상 3선 장비 ID (기본값: 11,12,13)
    MODBUS_3W_IDS: List[int] = _parse_list_int("MODBUS_3W_IDS", [11, 12, 13])
    # 3상 4선 장비 ID (기본값: 14,15)
    MODBUS_4W_IDS: List[int] = _parse_list_int("MODBUS_4W_IDS", [14, 15])
    # 전체 장비 리스트
    MODBUS_DEVICE_IDS: List[int] = MODBUS_3W_IDS + MODBUS_4W_IDS

    # 폴링 주기(초)
    MODBUS_POLL_INTERVAL: int = _parse_int("MODBUS_POLL_INTERVAL", 60)
    MODBUS_MAX_FAILS: int = _parse_int("MODBUS_MAX_FAILS", 3)

    # ---------------- Env (온/습도) 관련 ----------------
    ENV_PORT: str = os.getenv("ENV_PORT", "COM8")
    ENV_BAUDRATE: int = _parse_int("ENV_BAUDRATE", 9600)
    ENV_DEVICE_IDS: List[int] = _parse_list_int("ENV_DEVICE_IDS", [21,22,23])
    ENV_POLL_INTERVAL: int = _parse_int("ENV_POLL_INTERVAL", 60)

    # ---------------- Solar (일사량) 관련 ----------------
    SOLAR_PORT: str = os.getenv("SOLAR_PORT", "COM8")
    SOLAR_BAUDRATE: int = _parse_int("SOLAR_BAUDRATE", 9600)
    SOLAR_DEVICE_IDS: List[int] = _parse_list_int("SOLAR_DEVICE_IDS", [31])
    SOLAR_POLL_INTERVAL: int = _parse_int("SOLAR_POLL_INTERVAL", 60)

    # 빌드 디렉토리
    VITE_DIST_DIR: str = os.getenv("VITE_DIST_DIR", "dist")

    def get_cors_origins_list(self):
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

# 전역 인스턴스
settings = Settings()

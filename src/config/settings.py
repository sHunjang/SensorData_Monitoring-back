# src/config/settings.py

"""
전역 설정 모듈

주요 기능:
- 환경 변수(.env) 로드 및 파싱
- 센서별 디바이스 ID 및 통신 설정 관리
- 실행 모드(real/dummy) 설정
- bootstrap.py 스키마 기반 디바이스 구분

사용법:
  from src.config.settings import settings
  
  # Modbus 설정 접근
  settings.MODBUS_4W_IDS  # [11, 12, 13] (3상 4선식)
  settings.MODBUS_3W_IDS  # [14, 15] (3상 3선식)
  
  # 디바이스 타입 확인
  settings.is_4wire_device(11)  # True
  settings.is_3wire_device(14)  # True
  
  # 환경/태양광 설정
  settings.ENV_DEVICE_IDS    # [21, 22, 23]
  settings.SOLAR_DEVICE_IDS  # [31]

환경 변수 파일:
  .env 파일로 모든 설정 변경 가능
"""

import os
from dotenv import load_dotenv
from typing import List, Optional

# .env 파일 로드
load_dotenv()


def _parse_int(env_name: str, default: int) -> int:
    """
    환경 변수를 정수로 파싱
    
    Args:
        env_name: 환경 변수 이름
        default: 기본값
        
    Returns:
        파싱된 정수 또는 기본값
    """
    v = os.getenv(env_name)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _parse_list_int(env_name: str, default: List[int]) -> List[int]:
    """
    환경 변수를 정수 리스트로 파싱 (콤마 구분)
    
    Args:
        env_name: 환경 변수 이름
        default: 기본값 리스트
        
    Returns:
        파싱된 정수 리스트 또는 기본값
        
    Example:
        MODBUS_4W_IDS=11,12,13 -> [11, 12, 13]
    """
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
    """
    전역 설정 클래스
    
    모든 설정은 환경 변수 또는 기본값으로 초기화됨
    """
    
    # ============================================================
    # 공통 설정
    # ============================================================
    
    # 실행 모드: "real" (실제 센서) 또는 "dummy" (테스트용 더미 데이터)
    MODE: str = os.getenv("MODE", "real").lower()
    
    # CORS 설정 (콤마 구분 문자열)
    cors_origins: Optional[str] = os.getenv("CORS_ORIGINS", "").strip() or None
    
    # PostgreSQL 데이터베이스 연결 문자열
    PG_DSN: str = os.getenv(
        "PG_DSN", 
        "postgresql://postgres:1234@127.0.0.1:5432/energydb"
    )
    
    # 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # ============================================================
    # Modbus (전력량계 TAC4300) 설정
    # ============================================================
    
    # 시리얼 포트 설정
    MODBUS_PORT: str = os.getenv("MODBUS_PORT", "COM7")
    MODBUS_BAUDRATE: int = _parse_int("MODBUS_BAUDRATE", 9600)
    MODBUS_PARITY: str = os.getenv("MODBUS_PARITY", "N")  # N(None), E(Even), O(Odd)
    MODBUS_STOPBITS: int = _parse_int("MODBUS_STOPBITS", 1)  # 1 또는 2
    MODBUS_BYTESIZE: int = _parse_int("MODBUS_BYTESIZE", 8)  # 7 또는 8
    
    # 📌 3상 4선식 전력계 (Line-to-Line 전압 측정)
    # bootstrap.py 스키마: modbus_4wire_*
    # 기본값: [11, 12, 13]
    MODBUS_4W_IDS: List[int] = _parse_list_int("MODBUS_4W_IDS", [11, 12, 13])
    
    # 📌 3상 3선식 전력계 (Line-to-Neutral 전압 측정)
    # bootstrap.py 스키마: modbus_3wire_*
    # 기본값: [14, 15]
    MODBUS_3W_IDS: List[int] = _parse_list_int("MODBUS_3W_IDS", [14, 15])
    
    # 전체 Modbus 장비 ID 리스트 (자동 생성)
    @property
    def MODBUS_DEVICE_IDS(self) -> List[int]:
        """전체 Modbus 장비 ID 리스트 (4선식 + 3선식)"""
        return list(dict.fromkeys(self.MODBUS_4W_IDS + self.MODBUS_3W_IDS))
    
    # 데이터 수집 주기 (초)
    # 요구사항: 5초마다 수집 -> 1분/15분/1시간/1일/1년 집계
    MODBUS_POLL_INTERVAL: int = _parse_int("MODBUS_POLL_INTERVAL", 5)
    
    # 최대 연속 실패 횟수 (초과 시 에러 로깅)
    MODBUS_MAX_FAILS: int = _parse_int("MODBUS_MAX_FAILS", 3)
    
    # ============================================================
    # Env (온습도 센서) 설정
    # ============================================================
    
    ENV_PORT: str = os.getenv("ENV_PORT", "COM8")
    ENV_BAUDRATE: int = _parse_int("ENV_BAUDRATE", 9600)
    ENV_PARITY: str = os.getenv("ENV_PARITY", "N")
    ENV_STOPBITS: int = _parse_int("ENV_STOPBITS", 1)
    ENV_BYTESIZE: int = _parse_int("ENV_BYTESIZE", 8)
    
    # 온습도 센서 ID 리스트
    # bootstrap.py 스키마: env_*
    # 기본값: [21, 22, 23]
    ENV_DEVICE_IDS: List[int] = _parse_list_int("ENV_DEVICE_IDS", [21, 22, 23])
    
    # 데이터 수집 주기 (초)
    ENV_POLL_INTERVAL: int = _parse_int("ENV_POLL_INTERVAL", 5)
    
    # ============================================================
    # Solar (일사량 센서) 설정
    # ============================================================
    
    SOLAR_PORT: str = os.getenv("SOLAR_PORT", "COM8")
    SOLAR_BAUDRATE: int = _parse_int("SOLAR_BAUDRATE", 9600)
    SOLAR_PARITY: str = os.getenv("SOLAR_PARITY", "N")
    SOLAR_STOPBITS: int = _parse_int("SOLAR_STOPBITS", 1)
    SOLAR_BYTESIZE: int = _parse_int("SOLAR_BYTESIZE", 8)
    
    # 일사량 센서 ID 리스트
    # bootstrap.py 스키마: solar_*
    # 기본값: [31]
    SOLAR_DEVICE_IDS: List[int] = _parse_list_int("SOLAR_DEVICE_IDS", [31])
    
    # 데이터 수집 주기 (초)
    SOLAR_POLL_INTERVAL: int = _parse_int("SOLAR_POLL_INTERVAL", 5)
    
    # ============================================================
    # 프론트엔드 빌드 디렉토리
    # ============================================================
    
    VITE_DIST_DIR: str = os.getenv("VITE_DIST_DIR", "dist")
    
    # ============================================================
    # 헬퍼 메서드
    # ============================================================
    
    def get_cors_origins_list(self) -> List[str]:
        """
        CORS origin 문자열을 리스트로 변환
        
        Returns:
            origin URL 리스트
            
        Example:
            "http://localhost:3000,http://localhost:5173"
            -> ["http://localhost:3000", "http://localhost:5173"]
        """
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    def is_4wire_device(self, device_id: int) -> bool:
        """
        디바이스가 3상 4선식인지 확인
        
        Args:
            device_id: 디바이스 ID
            
        Returns:
            True if 4선식 (ID: 11,12,13), False otherwise
            
        Example:
            settings.is_4wire_device(11)  # True
            settings.is_4wire_device(14)  # False
        """
        return device_id in self.MODBUS_4W_IDS
    
    def is_3wire_device(self, device_id: int) -> bool:
        """
        디바이스가 3상 3선식인지 확인
        
        Args:
            device_id: 디바이스 ID
            
        Returns:
            True if 3선식 (ID: 14,15), False otherwise
            
        Example:
            settings.is_3wire_device(14)  # True
            settings.is_3wire_device(11)  # False
        """
        return device_id in self.MODBUS_3W_IDS
    
    def get_device_type_name(self, device_id: int) -> str:
        """
        디바이스 ID에 해당하는 타입명 반환
        
        Args:
            device_id: 디바이스 ID
            
        Returns:
            타입명 문자열
            
        Example:
            settings.get_device_type_name(11)  # "3상 4선식 전력계"
            settings.get_device_type_name(21)  # "환경센서"
            settings.get_device_type_name(31)  # "일사량센서"
        """
        if device_id in self.MODBUS_4W_IDS:
            return "3상 4선식 전력계"
        elif device_id in self.MODBUS_3W_IDS:
            return "3상 3선식 전력계"
        elif device_id in self.ENV_DEVICE_IDS:
            return "환경센서"
        elif device_id in self.SOLAR_DEVICE_IDS:
            return "일사량센서"
        else:
            return "알 수 없음"
    
    def validate_config(self) -> List[str]:
        """
        설정 검증 및 경고 메시지 반환
        
        Returns:
            경고 메시지 리스트 (없으면 빈 리스트)
        """
        warnings = []
        
        # Modbus 설정 검증
        if not self.MODBUS_4W_IDS and not self.MODBUS_3W_IDS:
            warnings.append("⚠️ MODBUS_4W_IDS, MODBUS_3W_IDS가 모두 비어있습니다.")
        
        if self.MODBUS_POLL_INTERVAL < 1:
            warnings.append(f"⚠️ MODBUS_POLL_INTERVAL이 너무 짧습니다: {self.MODBUS_POLL_INTERVAL}초")
        
        # 환경센서 설정 검증
        if not self.ENV_DEVICE_IDS:
            warnings.append("⚠️ ENV_DEVICE_IDS가 비어있습니다.")
        
        # 태양광센서 설정 검증
        if not self.SOLAR_DEVICE_IDS:
            warnings.append("⚠️ SOLAR_DEVICE_IDS가 비어있습니다.")
        
        # 모드 검증
        if self.MODE not in ["real", "dummy"]:
            warnings.append(f"⚠️ 알 수 없는 MODE: {self.MODE} (real 또는 dummy만 가능)")
        
        return warnings


# ============================================================
# 전역 인스턴스 생성
# ============================================================
settings = Settings()


# ============================================================
# 설정 검증 (모듈 로드 시 자동 실행)
# ============================================================
_warnings = settings.validate_config()
if _warnings:
    import logging
    log = logging.getLogger("settings")
    for w in _warnings:
        log.warning(w)

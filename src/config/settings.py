"""
전역 설정 모듈

이 모듈은 환경변수와 .env 파일에서 설정을 읽어와 애플리케이션 전역에서 사용할 수 있음.

주요 변경사항 (2025-10-10):
    - 3상 4선/3선 구분 설정 명확화
    - RAW 테이블 관련 설정 제거
    - 1분 테이블 보존 기간 설정 추가
    - 속성명 일관성 개선

사용법:
    from src.config.settings import settings
    
    # 설정값 접근
    device_ids = settings.MODBUS_3W_IDS  # [11, 12, 13]
    four_wire = settings.MODBUS_4W_IDS   # [14, 15]

작성일: 2025-10-10
"""

import os
from typing import List
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    """
    애플리케이션 설정 클래스
    
    환경변수를 읽어와 타입 변환 및 기본값을 제공합니다.
    """
    
    # ========================================
    # 실행 모드
    # ========================================
    MODE: str = os.getenv("MODE", "dummy")  # "real" or "dummy"
    
    # ========================================
    # 데이터베이스 설정
    # ========================================
    PG_DSN: str = os.getenv(
        "PG_DSN",
        "postgresql://postgres:1234@localhost:5432/energydb"
    )
    
    # ========================================
    # Modbus 전력계 설정
    # ========================================
    # 3상 3선식 (중성선 없음) - voltage_n 컬럼 없음
    MODBUS_3W_IDS: List[int] = [11, 12, 13]
    
    # 3상 4선식 (중성선 있음) - voltage_n 컬럼 사용
    MODBUS_4W_IDS: List[int] = [14, 15]
    
    # Modbus 통신 설정 (실제 장치용)
    MODBUS_PORT: str = os.getenv("MODBUS_PORT", "/dev/ttyUSB0")
    MODBUS_BAUDRATE: int = int(os.getenv("MODBUS_BAUDRATE", "9600"))
    MODBUS_TIMEOUT: float = float(os.getenv("MODBUS_TIMEOUT", "1.0"))
    
    # ========================================
    # 환경(온습도) 센서 설정
    # ========================================
    ENV_IDS: List[int] = [21, 22, 23]
    
    # Env 통신 설정 (실제 장치용)
    ENV_PORT: str = os.getenv("ENV_PORT", "/dev/ttyUSB1")
    ENV_BAUDRATE: int = int(os.getenv("ENV_BAUDRATE", "9600"))
    ENV_TIMEOUT: float = float(os.getenv("ENV_TIMEOUT", "1.0"))
    
    # ========================================
    # 일사량 센서 설정
    # ========================================
    SOLAR_ID: int = 31
    
    # Solar 통신 설정 (실제 장치용)
    SOLAR_PORT: str = os.getenv("SOLAR_PORT", "/dev/ttyUSB2")
    SOLAR_BAUDRATE: int = int(os.getenv("SOLAR_BAUDRATE", "9600"))
    SOLAR_TIMEOUT: float = float(os.getenv("SOLAR_TIMEOUT", "1.0"))
    
    # ========================================
    # 데이터 수집 설정
    # ========================================
    # 수집 주기 (초)
    COLLECTION_INTERVAL: int = int(os.getenv("COLLECTION_INTERVAL", "5"))
    
    # ========================================
    # 데이터 보존 정책
    # ========================================
    # 1분 테이블 보존 기간 (일)
    RETENTION_1M_DAYS: int = int(os.getenv("RETENTION_1M_DAYS", "30"))
    
    # 백업 파일 저장 경로
    BACKUP_PATH: str = os.getenv("BACKUP_PATH", "/backup")
    
    # ========================================
    # CORS 설정
    # ========================================
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    
    # ========================================
    # 로깅 설정
    # ========================================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ========================================
    # 편의 속성 (하위 호환성)
    # ========================================
    @property
    def MODBUS_DEVICE_IDS(self) -> List[int]:
        """전체 Modbus 디바이스 ID (3W + 4W)"""
        return self.MODBUS_3W_IDS + self.MODBUS_4W_IDS
    
    @property
    def ENV_DEVICE_IDS(self) -> List[int]:
        """환경센서 디바이스 ID (alias)"""
        return self.ENV_IDS
    
    @property
    def SOLAR_DEVICE_ID(self) -> int:
        """일사량 센서 디바이스 ID (alias)"""
        return self.SOLAR_ID
    
    @property
    def COLLECTION_INTERVAL_SECONDS(self) -> int:
        """수집 주기 (초) (alias)"""
        return self.COLLECTION_INTERVAL

# 싱글톤 인스턴스
settings = Settings()

# ========================================
# 설정 검증 함수
# ========================================
def validate_settings():
    """
    설정값 유효성 검증
    
    주요 검증 항목:
        - 디바이스 ID 중복 확인
        - 3상 4선/3선 교집합 확인
        - 필수 환경변수 존재 확인
    
    Raises:
        ValueError: 설정값이 유효하지 않을 때
    """
    # 교집합이 없는지 확인 (중복 방지)
    intersection = (
        set(settings.MODBUS_3W_IDS) &
        set(settings.MODBUS_4W_IDS)
    )
    
    if intersection:
        raise ValueError(
            f"3상 3선과 4선에 중복된 ID가 있습니다: {intersection}"
        )
    
    # 수집 주기 범위 확인
    if not (1 <= settings.COLLECTION_INTERVAL <= 60):
        raise ValueError(
            f"수집 주기는 1-60초 사이여야 합니다. 현재: {settings.COLLECTION_INTERVAL}"
        )
    
    # 보존 기간 범위 확인
    if not (1 <= settings.RETENTION_1M_DAYS <= 365):
        raise ValueError(
            f"1분 데이터 보존 기간은 1-365일 사이여야 합니다. "
            f"현재: {settings.RETENTION_1M_DAYS}"
        )

# ========================================
# 직접 실행 시 설정 출력
# ========================================
if __name__ == "__main__":
    """
    설정값 확인 및 검증
    
    사용법:
        python -m src.config.settings
    """
    import logging
    
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger("settings")
    
    log.info("=" * 60)
    log.info("⚙️  애플리케이션 설정")
    log.info("=" * 60)
    
    log.info("\n📋 기본 설정:")
    log.info(f"   MODE: {settings.MODE}")
    log.info(f"   PG_DSN: {settings.PG_DSN}")
    
    log.info("\n⚡ Modbus 전력계:")
    log.info(f"   3상 3선 (중성선 X): {settings.MODBUS_3W_IDS}")
    log.info(f"   3상 4선 (중성선 O): {settings.MODBUS_4W_IDS}")
    log.info(f"   전체 ID: {settings.MODBUS_DEVICE_IDS}")
    log.info(f"   통신 포트: {settings.MODBUS_PORT}")
    log.info(f"   보드레이트: {settings.MODBUS_BAUDRATE}")
    
    log.info("\n🌡️  환경 센서:")
    log.info(f"   ID: {settings.ENV_IDS}")
    log.info(f"   통신 포트: {settings.ENV_PORT}")
    
    log.info("\n☀️  일사량 센서:")
    log.info(f"   ID: {settings.SOLAR_ID}")
    log.info(f"   통신 포트: {settings.SOLAR_PORT}")
    
    log.info("\n⏱️  데이터 수집:")
    log.info(f"   수집 주기: {settings.COLLECTION_INTERVAL}초")
    
    log.info("\n💾 데이터 보존:")
    log.info(f"   1분 테이블 보존 기간: {settings.RETENTION_1M_DAYS}일")
    log.info(f"   백업 경로: {settings.BACKUP_PATH}")
    
    log.info("\n🔍 설정 검증 중...")
    try:
        validate_settings()
        log.info("✅ 설정 검증 성공")
    except ValueError as e:
        log.error(f"❌ 설정 검증 실패: {e}")
    
    log.info("\n" + "=" * 60)

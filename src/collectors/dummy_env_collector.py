"""
더미 환경 센서 수집기 - Device별 분리 테이블 지원

기능:
- 3개 Device (21~23)를 순환하며 더미 온습도 데이터 생성
- Device별 분리 테이블에 저장 (env_data_21 ~ env_data_23)
- 3초마다 랜덤 데이터 생성

작성일: 2025-10-02 (마이그레이션 대응)
"""

import os
import time
import random
import logging
from datetime import datetime, timezone
from src.db.client import get_cursor

log = logging.getLogger("dummy_env")

# Device ID 목록
ENV_DEVICE_IDS = [21, 22, 23]


def ensure_tables():
    """
    모든 Env Device별 분리 테이블 생성
    """
    log.info("🌡️ Env 분리 테이블 확인 중...")
    
    with get_cursor() as cur:
        for device_id in ENV_DEVICE_IDS:
            table_name = f"env_data_{device_id}"
            
            # 테이블 생성
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    time_stamp TIMESTAMPTZ NOT NULL,
                    temperature DOUBLE PRECISION,
                    humidity DOUBLE PRECISION
                )
            """)
            
            # 인덱스 생성
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
                ON {table_name}(time_stamp DESC)
            """)
            
            log.info(f"  ✅ {table_name} 준비 완료")


def generate_dummy_data(device_id: int) -> dict:
    """
    특정 Device ID에 대한 더미 환경 데이터 생성
    
    Args:
        device_id: 환경 센서 장치 ID (21~23)
        
    Returns:
        dict: 더미 온습도 데이터
    """
    # Device별로 약간 다른 온도/습도 범위 (실제처럼)
    base_temp = 20 + (device_id - 21) * 3      # 20, 23, 26
    base_humidity = 45 + (device_id - 21) * 5  # 45, 50, 55
    
    return {
        "time_stamp": datetime.now(timezone.utc),
        "temperature": round(random.uniform(base_temp - 5, base_temp + 5), 1),
        "humidity": round(random.uniform(base_humidity - 10, base_humidity + 10), 1),
    }


def save_data(device_id: int, data: dict):
    """
    Device별 분리 테이블에 데이터 저장
    
    Args:
        device_id: 환경 센서 장치 ID
        data: 저장할 데이터
    """
    table_name = f"env_data_{device_id}"
    
    with get_cursor() as cur:
        cur.execute(f"""
            INSERT INTO {table_name} (
                time_stamp,
                temperature,
                humidity
            ) VALUES (%s, %s, %s)
        """, (
            data["time_stamp"],
            data["temperature"],
            data["humidity"],
        ))


def run_collector(interval: int = 3):
    """
    더미 환경 센서 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초)
    """
    log.info("🌿 더미 Env 수집기 시작 (Device별 분리 테이블)")
    
    # 테이블 생성
    ensure_tables()
    
    # Device 순환 인덱스
    device_index = 0
    
    while True:
        try:
            # 현재 Device 선택 (순환)
            device_id = ENV_DEVICE_IDS[device_index]
            
            # 더미 데이터 생성
            data = generate_dummy_data(device_id)
            
            # 저장
            save_data(device_id, data)
            
            log.info(
                f"🌡️ Device {device_id}: "
                f"온도 {data['temperature']}°C, "
                f"습도 {data['humidity']}%"
            )
            
            # 다음 Device로 이동
            device_index = (device_index + 1) % len(ENV_DEVICE_IDS)
            
            # 대기
            time.sleep(interval)
            
        except KeyboardInterrupt:
            log.info("🛑 더미 Env 수집기 종료")
            break
        except Exception as e:
            log.error(f"❌ 더미 Env 수집 오류: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # 수집기 실행
    run_collector(interval=3)

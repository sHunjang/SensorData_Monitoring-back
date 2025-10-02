"""
더미 태양광 센서 수집기 - device_id 지원

기능:
- 단일 Device (31)에 대한 더미 일사량 데이터 생성
- solar_data 테이블에 device_id와 함께 저장
- 3초마다 랜덤 데이터 생성

작성일: 2025-10-02 (마이그레이션 대응)
"""

import os
import time
import random
import logging
from datetime import datetime, timezone
from src.db.client import get_cursor

log = logging.getLogger("dummy_solar")

# Solar Device ID (단일)
SOLAR_DEVICE_ID = 31


def ensure_table():
    """
    Solar 테이블 생성 (device_id 컬럼 포함)
    """
    log.info("☀️ Solar 테이블 확인 중...")
    
    with get_cursor() as cur:
        # 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL DEFAULT 31,
                irradiance DOUBLE PRECISION
            )
        """)
        
        # 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_solar_device_time 
            ON solar_data(device_id, time_stamp DESC)
        """)
        
        log.info("  ✅ solar_data 준비 완료")


def generate_dummy_data() -> dict:
    """
    더미 태양광 데이터 생성
    
    Returns:
        dict: 더미 일사량 데이터
    """
    # 시간대별로 다른 일사량 패턴 (실제처럼)
    current_hour = datetime.now().hour
    
    if 6 <= current_hour < 8:
        # 이른 아침: 낮은 일사량
        base_irradiance = 100
    elif 8 <= current_hour < 10:
        # 오전: 증가
        base_irradiance = 400
    elif 10 <= current_hour < 14:
        # 정오: 최대
        base_irradiance = 800
    elif 14 <= current_hour < 17:
        # 오후: 감소
        base_irradiance = 500
    elif 17 <= current_hour < 19:
        # 저녁: 낮음
        base_irradiance = 150
    else:
        # 밤: 0
        base_irradiance = 0
    
    return {
        "time_stamp": datetime.now(timezone.utc),
        "device_id": SOLAR_DEVICE_ID,
        "irradiance": round(random.uniform(
            max(0, base_irradiance - 100),
            base_irradiance + 100
        ), 2),
    }


def save_data(data: dict):
    """
    Solar 데이터 저장 (device_id 포함)
    
    Args:
        data: 저장할 데이터
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (
                time_stamp,
                device_id,
                irradiance
            ) VALUES (%s, %s, %s)
        """, (
            data["time_stamp"],
            data["device_id"],
            data["irradiance"],
        ))


def run_collector(interval: int = 3):
    """
    더미 태양광 센서 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초)
    """
    log.info("☀️ 더미 Solar 수집기 시작 (device_id 지원)")
    
    # 테이블 생성
    ensure_table()
    
    while True:
        try:
            # 더미 데이터 생성
            data = generate_dummy_data()
            
            # 저장
            save_data(data)
            
            log.info(
                f"☀️ Device {data['device_id']}: "
                f"일사량 {data['irradiance']} W/m²"
            )
            
            # 대기
            time.sleep(interval)
            
        except KeyboardInterrupt:
            log.info("🛑 더미 Solar 수집기 종료")
            break
        except Exception as e:
            log.error(f"❌ 더미 Solar 수집 오류: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # 수집기 실행
    run_collector(interval=3)

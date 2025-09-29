"""
더미 ENV 수집기 - 온습도 센서 시뮬레이션
"""
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional
from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_env")
KST = ZoneInfo("Asia/Seoul")

DEVICE_IDS: List[int] = getattr(settings, "ENV_DEVICE_IDS", [21, 22, 23]) or [21, 22, 23]
POLL_INTERVAL: int = getattr(settings, "ENV_POLL_INTERVAL", 3)

def ensure_table():
    """🎯 새 스키마에 맞춘 env_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            )
        """)

def insert_row(device_id: int, temperature: float, humidity: float):
    """🎯 새 스키마에 맞춘 DB 삽입"""
    now_kst = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
            VALUES (%s, %s, %s, %s)
        """, (now_kst, device_id, temperature, humidity))

def _make_sample():
    """온도(°C)와 습도(%RH) 샘플 생성"""
    temperature = round(random.uniform(15.0, 32.0), 2)
    humidity = round(random.uniform(25.0, 70.0), 2)
    return temperature, humidity

def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """더미 환경 수집기 메인 루프"""
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS
    
    ensure_table()
    log.info(f"🌿 Dummy Env started: interval={interval}s devices={devices}")
    
    idx = 0
    while True:
        try:
            did = devices[idx % len(devices)]
            temp, hum = _make_sample()
            insert_row(did, temp, hum)
            log.info(f"🌡️ dummy_env: id={did} T={temp:.1f}°C H={hum:.1f}%")
            idx += 1
        except Exception as e:
            log.exception(f"❌ dummy_env error: {e}")
        time.sleep(interval)

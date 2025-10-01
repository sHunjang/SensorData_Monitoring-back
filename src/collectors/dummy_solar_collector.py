"""
더미 Solar 수집기 - 태양광 일사량 센서 시뮬레이션
"""
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional
from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_solar")
KST = ZoneInfo("Asia/Seoul")

DEVICE_IDS: List[int] = getattr(settings, "SOLAR_DEVICE_IDS", [31]) or [31]
POLL_INTERVAL: int = getattr(settings, "SOLAR_POLL_INTERVAL", 3)
MAX_FAILS = getattr(settings, "MODBUS_MAX_FAILS", 5)

def ensure_table():
    """🎯 새 스키마에 맞춘 solar_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                solar DOUBLE PRECISION
            )
        """)

def insert_row(device_id: int, value: float):
    """🎯 새 스키마에 맞춘 DB 삽입"""
    now = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, solar)
            VALUES (%s, %s, %s)
        """, (now, device_id, value))

def sample_irradiance(prev: Optional[float]) -> float:
    """일사량 샘플 생성 (랜덤워크)"""
    if prev is None:
        base = random.choice([random.uniform(0, 20), random.uniform(200, 800)])
        return round(base + random.uniform(-10, 10), 2)
    
    change = random.uniform(-0.2, 0.2) * prev
    v = max(0.0, prev + change + random.uniform(-5, 5))
    return round(v, 2)

def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """더미 태양광 수집기 메인 루프"""
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS
    
    ensure_table()
    log.info(f"☀️ Dummy Solar started: interval={interval}s devices={devices}")
    
    last_vals = {sid: None for sid in devices}
    fail_counts = {sid: 0 for sid in devices}
    
    while True:
        for sid in devices:
            try:
                val = sample_irradiance(last_vals.get(sid))
                insert_row(sid, val)
                last_vals[sid] = val
                fail_counts[sid] = 0
                log.info(f"☀️ dummy_solar: id={sid} solar={val} W/m²")
            except Exception as e:
                fail_counts[sid] += 1
                log.exception(f"❌ dummy_solar: id={sid} insert failed ({fail_counts[sid]}/{MAX_FAILS}): {e}")
        time.sleep(interval)

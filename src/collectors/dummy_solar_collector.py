"""
src/collectors/dummy_solar_collector.py

테스트/개발용 더미 Collector.
- device_id 인자를 받아서 동일한 스키마로 저장.
- 시간은 KST tz-aware로 저장.
"""
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.db.client import get_cursor

log = logging.getLogger("dummy_solar")
KST = ZoneInfo("Asia/Seoul")

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT,
                solar DOUBLE PRECISION
            );
        """)
        cur.execute("ALTER TABLE solar_data ADD COLUMN IF NOT EXISTS device_id INT;")

def insert_row(device_id: int):
    now_kst = datetime.now(KST)
    val = round(random.uniform(0, 1000), 2)
    with get_cursor() as cur:
        cur.execute("INSERT INTO solar_data(time_stamp, device_id, solar) VALUES (%s,%s,%s)", (now_kst, device_id, val))

def run_collector(interval=10, device_ids=None):
    """
    device_ids: list of ints. 기본 [21] 사용.
    """
    if device_ids is None:
        device_ids = [21]
    ensure_table()
    log.info("Dummy Solar started interval=%s devices=%s", interval, device_ids)
    while True:
        for did in device_ids:
            try:
                insert_row(did)
            except Exception as e:
                log.exception("solar fail: %s", e)
        time.sleep(interval)

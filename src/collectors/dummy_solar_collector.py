"""
dummy_solar_collector.py
- 일사량(W/m²) 더미 데이터 생성기
- solar_data 테이블에 랜덤 값 삽입
"""

import time
import random
import datetime
import logging
from src.db.client import get_cursor

log = logging.getLogger("dummy_solar_collector")

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                value DOUBLE PRECISION
            );
        """)

def insert_dummy_row():
    row = {
        "time_stamp": datetime.datetime.utcnow(),
        "value": round(random.uniform(0.0, 1000.0), 2),  # 일사량(W/m²)
    }
    with get_cursor() as cur:
        cur.execute("INSERT INTO solar_data (time_stamp, value) VALUES (%s,%s)", (row["time_stamp"], row["value"]))
    log.info("Inserted solar dummy row: %s", row)

def run_collector(interval: int = 60):
    ensure_table()
    log.info("Dummy Solar collector started. Interval=%s sec", interval)
    while True:
        try:
            insert_dummy_row()
        except Exception as e:
            log.exception("Failed to insert solar dummy row: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    run_collector(interval=60)

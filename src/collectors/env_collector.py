"""
env_collector.py
- RS485 온습도 센서 → DB 적재
- Slave IDs: 21, 22, 23
"""

import time, logging
from src.sensors.env_reader import create_instrument, read_env
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("env_collector")

DEVICE_IDS = [21, 22, 23]  # 온습도 센서 ID
MAX_FAILS = 5  # 연속 실패 허용 횟수

def ensure_table():
    """env_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, row: dict):
    """DB에 한 줄 삽입"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
            VALUES (NOW(), %s, %s, %s)
        """, (
            device_id,
            row.get("temperature"),
            row.get("humidity"),
        ))

def main():
    setup_logging()
    ensure_table()
    log.info("Env collector started.")

    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning(f"sid={sid} disabled after {MAX_FAILS} fails")
                continue
            try:
                inst = create_instrument(port="COM8", slave_id=sid)
                row = read_env(inst)
                insert_row(sid, row)
                log.info(f"sid={sid} row={row}")
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning(f"sid={sid} fail {fail_counts[sid]}: {e}")
        time.sleep(60)

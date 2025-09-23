"""
src/collectors/solar_collector.py

실 센서에서 일사량을 읽고 DB에 저장하는 Collector.
- 시간은 한국표준시(KST, Asia/Seoul)로 tz-aware datetime 생성하여 DB에 저장.
- DB 삽입시 timestamptz 컬럼에 tz 정보가 포함되어 저장됨.
- 실패/재시도 로직 간단 포함.
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.sensors.solar_reader import create_instrument, read_solar
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("solar_collector")
KST = ZoneInfo("Asia/Seoul")

DEVICE_IDS = [31]  # 실제 장치 ID 목록, 필요한대로 수정
MAX_FAILS = 5

def ensure_table():
    """
    안전하게 테이블과 device_id 칼럼 확인/생성.
    - 기존 테이블에 device_id 칼럼이 없으면 추가(기본 NULL).
    - 이 함수는 파손가능성이 적게 동작하도록 IF NOT EXISTS 사용.
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT,
                solar DOUBLE PRECISION
            );
        """)
        # device_id 칼럼이 없으면 추가 (IF NOT EXISTS 사용)
        cur.execute("ALTER TABLE solar_data ADD COLUMN IF NOT EXISTS device_id INT;")

def insert_row(device_id: int, solar_val: float):
    """
    한국 시간 tz-aware로 NOW 생성하여 삽입.
    - now_kst: tz-aware datetime with ZoneInfo('Asia/Seoul')
    """
    now_kst = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, solar)
            VALUES (%s, %s, %s)
        """, (now_kst, device_id, solar_val))

def main(interval=10):
    """
    주 루프: 각 DEVICE_IDS에 대해 센서 읽고 DB에 저장.
    """
    setup_logging()
    ensure_table()
    log.info("Solar collector started. interval=%s", interval)

    fail_counts = {sid: 0 for sid in DEVICE_IDS}
    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning("sid=%s disabled after %s fails", sid, MAX_FAILS)
                continue
            try:
                inst = create_instrument(port="COM7", slave_id=sid)
                val = read_solar(inst)
                insert_row(sid, val)
                log.info("sid=%s solar=%.2f W/m² stored @KST", sid, val)
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning("sid=%s fail %s: %s", sid, fail_counts[sid], e)
        time.sleep(interval)

if __name__ == "__main__":
    main()

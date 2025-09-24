"""
solar_collector.py
- 일사량 센서 → DB 적재
- KST(Asia/Seoul) 타임스탬프 저장
- 실패 누적 차단, 1분 주기 수집(운영 권장)
"""
import time, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from src.sensors.solar_reader import create_instrument, read_solar
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("solar_collector")

DEVICE_IDS = [31]
MAX_FAILS = 5
INTERVAL_SEC = 1  # 수집 주기(초)

def ensure_table():
    """solar_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id  INT NOT NULL,
                solar      DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, solar: float):
    """
    tz-aware datetime으로 KST 저장.
    - timestamptz에 정확히 기록됨
    """
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, solar)
            VALUES (%s, %s, %s)
        """, (now_kst, device_id, solar))

def main():
    setup_logging()
    ensure_table()
    log.info("Solar collector started.")
    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning("sid=%s disabled after %d fails", sid, MAX_FAILS)
                continue
            try:
                inst = create_instrument(port="COM3", slave_id=sid)  # 포트는 환경에 맞게
                val = read_solar(inst)  # float W/m²
                insert_row(sid, val)
                log.info("sid=%s solar=%s W/m²", sid, val)
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning("sid=%s fail %d: %s", sid, fail_counts[sid], e)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()

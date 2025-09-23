"""
env_collector.py
- CWT-XYTH → RS485 → PostgreSQL(env_data)
- 60초 주기 수집, 한국시간(KST) tz-aware로 저장
- 실패 누적 차단(MAX_FAILS)
"""
import time, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from src.sensors.env_reader import create_instrument, read_env
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("env_collector")

DEVICE_IDS   = [21]   # 보유 센서 ID에 맞게 수정
SERIAL_PORT  = "COM3"         # RS485 포트
INTERVAL_SEC = 5             # 수집 주기(초)
MAX_FAILS    = 5              # 연속 실패 허용

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id  INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity    DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, row: dict):
    """
    timestamptz 컬럼에 tz-aware(datetime, Asia/Seoul)로 저장
    """
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
            VALUES (%s, %s, %s, %s)
        """, (now_kst, device_id, row.get("temperature"), row.get("humidity")))

def main():
    setup_logging()
    ensure_table()
    log.info("Env collector started.")
    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning("sid=%s disabled after %d fails", sid, MAX_FAILS)
                continue
            try:
                inst = create_instrument(port=SERIAL_PORT, slave_id=sid)
                row = read_env(inst)     # {"temperature": float, "humidity": float}
                insert_row(sid, row)
                log.info("sid=%s row=%s", sid, row)
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning("sid=%s fail %d: %s", sid, fail_counts[sid], e)
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()

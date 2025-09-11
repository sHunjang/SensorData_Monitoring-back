import time, logging
from src.sensors.solar_reader import create_instrument, read_solar
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("solar_collector")

DEVICE_IDS = [31]
MAX_FAILS = 5

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                solar DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int, solar: float):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, solar)
            VALUES (NOW(), %s, %s)
        """, (device_id, solar))

def main():
    setup_logging()
    ensure_table()
    log.info("Solar collector started.")

    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning(f"sid={sid} disabled after {MAX_FAILS} fails")
                continue
            try:
                inst = create_instrument(port="COM7", slave_id=sid)
                val = read_solar(inst)
                insert_row(sid, val)
                log.info(f"sid={sid} solar={val} W/m²")
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning(f"sid={sid} fail {fail_counts[sid]}: {e}")
        time.sleep(60)

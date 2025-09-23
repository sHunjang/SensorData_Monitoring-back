"""
src/collectors/dummy_modbus_collector.py

개발용 더미 모듈. KST tz-aware로 modbus_data에 저장.
"""
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.db.client import get_cursor

log = logging.getLogger("dummy_modbus")
KST = ZoneInfo("Asia/Seoul")

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION
            );
        """)
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS device_id INT;")

def insert_row(device_id: int):
    now_kst = datetime.now(KST)
    # 랜덤 더미 값
    avg_v_ll = round(random.uniform(380, 420), 2)
    avg_v_ln = round(avg_v_ll / 1.732, 2)
    sum_i = round(random.uniform(1, 20), 2)
    p_kw = round((avg_v_ln * sum_i) / 1000.0, 3)
    e_kwh = round(random.uniform(0, 50), 3)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data (
                time_stamp, device_id,
                avg_line_to_line_volts_v,
                avg_line_to_neutral_volts_v,
                sum_line_currents_a,
                total_active_power_kw,
                total_active_energy_kwh
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (now_kst, device_id, avg_v_ll, avg_v_ln, sum_i, p_kw, e_kwh))

def run_collector(interval=10, device_ids=None):
    if device_ids is None:
        device_ids = [11, 12, 13, 14, 15]
    ensure_table()
    log.info("Dummy Modbus started interval=%s devices=%s", interval, device_ids)
    while True:
        for did in device_ids:
            try:
                insert_row(did)
            except Exception as e:
                log.exception("modbus fail: %s", e)
        time.sleep(interval)

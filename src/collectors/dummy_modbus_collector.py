"""
dummy_modbus_collector.py
- TAC4300 전력량계 장치 더미 데이터 생성기
- 장치 ID 11~15 (3P3W, 3P4W) 각각에 대해 유효전력/전압/전류/에너지 값을 랜덤으로 생성해 DB에 삽입
"""

import time
import random
import datetime
import logging
from src.db.client import get_cursor

log = logging.getLogger("dummy_modbus_collector")

DEVICE_IDS = [11, 12, 13, 14, 15]

def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_current_A DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_kvar DOUBLE PRECISION,
                total_apparent_kVA DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            );
        """)

def insert_dummy_row(device_id: int):
    now = datetime.datetime.utcnow()
    row = {
        "time_stamp": now,
        "device_id": device_id,
        "p": round(random.uniform(5.0, 50.0), 2),   # kW
        "q": round(random.uniform(0.0, 20.0), 2),   # kvar
        "s": round(random.uniform(5.0, 60.0), 2),   # kVA
        "pf": round(random.uniform(0.7, 1.0), 3),   # power factor
        "i_sum": round(random.uniform(10.0, 100.0), 2), # A
        "v_ll": round(random.uniform(370.0, 400.0), 1), # V (3P3W)
        "v_ln": round(random.uniform(210.0, 230.0), 1), # V (3P4W)
        "kwh": round(random.uniform(1000.0, 5000.0), 2),
        "kvarh": round(random.uniform(500.0, 2000.0), 2),
        "kvah": round(random.uniform(1500.0, 6000.0), 2),
    }
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO modbus_data
            (time_stamp, device_id,
             avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
             sum_current_A,
             total_active_power_kw, total_reactive_kvar, total_apparent_kVA,
             total_power_factor,
             total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kvah)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
                row["time_stamp"], row["device_id"],
                row["p"], row["q"], row["s"],
                row["pf"], row["i_sum"],
                row["v_ll"], row["v_ln"],
                row["kwh"], row["kvarh"], row["kvah"]
            )
        )
    log.info("Inserted modbus dummy row: %s", row)

def run_collector(interval: int = 60):
    ensure_table()
    log.info("Dummy Modbus collector started. Interval=%s sec", interval)
    while True:
        for dev in DEVICE_IDS:
            try:
                insert_dummy_row(dev)
            except Exception as e:
                log.exception("Failed to insert modbus dummy row (device %s): %s", dev, e)
        time.sleep(interval)

if __name__ == "__main__":
    run_collector(interval=60)

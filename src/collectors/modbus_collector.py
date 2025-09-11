"""
modbus_collector.py
- TAC4300 전력량계 → RS485 → DB 적재
"""

import time, logging
from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("modbus_collector")

# 장치 ID
THREE_WIRE_IDS = [11, 12, 13]  # 3상 3선
FOUR_WIRE_IDS  = [14, 15]      # 3상 4선
DEVICE_IDS = THREE_WIRE_IDS + FOUR_WIRE_IDS

# 연속 실패 허용 횟수
MAX_FAILS = 3

def ensure_table():
    """modbus_data 테이블 생성"""
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

def insert_row(device_id: int, row: dict):
    """DB에 한 줄 삽입"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data
            (time_stamp, device_id,
             avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
             sum_current_A,
             total_active_kW, total_reactive_kvar, total_apparent_kVA,
             total_power_factor,
             total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kvah)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            device_id,
            # 전압은 선간/상전압 중 하나만 값, 나머지는 None
            row["avg_line_to_line_volts_v"] if device_id in THREE_WIRE_IDS else None,
            row["avg_line_to_neutral_volts_v"] if device_id in FOUR_WIRE_IDS else None,
            row["sum_current_A"],
            row["total_active_kW"], row["total_reactive_kvar"], row["total_apparent_kVA"],
            row["total_power_factor"],
            row["total_active_energy_kwh"], row["total_reactive_energy_kvarh"], row["total_apparent_energy_kvah"],
        ))

def main():
    setup_logging()
    ensure_table()
    log.info("Modbus collector started.")
    
    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning(f"sid={sid} disabled after {MAX_FAILS} fails")
                continue
            try:
                inst = create_instrument(slave_id=sid)
                row = read_summary(inst)
                insert_row(sid, row)
                log.info(f"sid={sid} row={row}")
                fail_counts[sid] = 0  # 정상 읽기 → 실패 카운터 초기화
            except Exception as e:
                fail_counts[sid] += 1
                log.warning(f"sid={sid} fail {fail_counts[sid]}: {e}")
        time.sleep(60)

if __name__ == "__main__":
    main()

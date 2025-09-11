"""
modbus_collector.py
- reader에서 읽은 데이터를 주기적으로 DB에 저장
"""

import time, logging
from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("modbus_collector")

DEVICE_IDS = [11, 12, 13, 14, 15]

def ensure_table():
    """modbus_data 테이블 생성"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                total_active_energy_kWh DOUBLE PRECISION,
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
             avg_voltage_V, sum_current_A,
             total_active_kW, total_reactive_kvar, total_apparent_kVA,
             total_power_factor,
             total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kvah)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            device_id,
            row["avg_voltage_V"], row["sum_current_A"],
            row["total_active_kW"], row["total_reactive_kvar"], row["total_apparent_kVA"],
            row["total_power_factor"],
            row["total_active_energy_kwh"], row["total_reactive_energy_kvarh"], row["total_apparent_energy_kvah"],
        ))

def main():
    setup_logging()
    ensure_table()
    log.info("Modbus collector started.")

    device_ids = [11, 12, 13, 14, 15]

    while True:
        for sid in device_ids:
            try:
                inst = create_instrument(slave_id=sid)
                row = read_summary(inst)
                insert_row(sid, row)
                log.info(f"sid={sid} row={row}")
            except Exception as e:
                # 장치 연결 실패 or 데이터 읽기 실패 -> 로그만 남기고 넘어감
                log.warning("sid=%d error: %s", sid, e)
        time.sleep(60)

if __name__ == "__main__":
    main()

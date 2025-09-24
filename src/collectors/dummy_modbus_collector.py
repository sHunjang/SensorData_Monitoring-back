# src/collectors/dummy_modbus_collector.py
"""
Dummy Modbus collector (테스트/개발용)

- modbus_data 테이블 스키마에 맞춰 랜덤한 더미값을 삽입합니다.
- 타임스탬프는 KST(tz-aware)로 생성하여 timestamptz 컬럼에 저장합니다.
- 항상 device_id를 포함하여 INSERT 하므로 NOT NULL 제약 위반이 발생하지 않습니다.
- 환경변수:
    DUMMY_MODBUS_DEVICES (예: "11,12,13") 기본: "11"
    DUMMY_MODBUS_INTERVAL (초) 기본: 3
"""

import os
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.db.client import get_cursor

log = logging.getLogger("dummy_modbus")
log.setLevel(logging.INFO)

# 환경 구성
DEVICES_ENV = os.getenv("DUMMY_MODBUS_DEVICES", "11")
DEVICE_IDS = [int(x.strip()) for x in DEVICES_ENV.split(",") if x.strip()]
if not DEVICE_IDS:
    DEVICE_IDS = [11]  # 최소 1개 보장

POLL_INTERVAL = int(os.getenv("DUMMY_MODBUS_INTERVAL", "3"))
KST = ZoneInfo("Asia/Seoul")

def ensure_table():
    """
    더미 수집기용 테이블 보장.
    실제 운영에서는 bootstrap.py에서 이미 생성되어 있어야 함.
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            );
        """)

def _make_row_for_device(device_id: int) -> dict:
    """
    device_id에 맞춰 랜덤 더미값을 생성.
    3선/4선 구분 같은 실제 로직이 없다면 모두 LL/LN 중 하나에 랜덤값 할당할 수 있음.
    여기서는 device_id가 짝수이면 4선(LN), 홀수이면 3선(LL)으로 간단 분기.
    """
    # 간단 시뮬: 홀수 -> 3선, 짝수 -> 4선
    is_three_wire = (device_id % 2 == 1)
    row = {
        "time_stamp": datetime.now(KST),
        "device_id": device_id,
        "avg_line_to_line_volts_v": round(random.uniform(200, 240), 2) if is_three_wire else None,
        "avg_line_to_neutral_volts_v": round(random.uniform(110, 140), 2) if not is_three_wire else None,
        "sum_line_currents_a": round(random.uniform(0, 50), 2),
        "total_active_power_kw": round(random.uniform(0, 10), 3),
        "total_reactive_power_kvar": round(random.uniform(-5, 5), 3),
        "total_apparent_power_kva": round(random.uniform(0, 12), 3),
        "total_power_factor": round(random.uniform(0.6, 1.0), 3),
        # 에너지 값은 누적형이므로 간단히 랜덤 누적처럼 보이도록 생성(테스트 목적)
        "total_active_energy_kwh": round(random.uniform(0, 1000), 3),
        "total_reactive_energy_kvarh": round(random.uniform(0, 500), 3),
        "total_apparent_energy_kvah": round(random.uniform(0, 1200), 3),
    }
    return row

def insert_row(row: dict):
    """
    modbus_data 스키마에 맞춰 INSERT. 항상 device_id 포함.
    """
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data (
                time_stamp, device_id,
                avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                sum_line_currents_a, total_active_power_kw, total_reactive_power_kvar,
                total_apparent_power_kva, total_power_factor,
                total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kvah
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            row["time_stamp"], row["device_id"],
            row.get("avg_line_to_line_volts_v"),
            row.get("avg_line_to_neutral_volts_v"),
            row.get("sum_line_currents_a"),
            row.get("total_active_power_kw"),
            row.get("total_reactive_power_kvar"),
            row.get("total_apparent_power_kva"),
            row.get("total_power_factor"),
            row.get("total_active_energy_kwh"),
            row.get("total_reactive_energy_kvarh"),
            row.get("total_apparent_energy_kvah"),
        ))

def run_collector(interval: int = POLL_INTERVAL):
    ensure_table()
    log.info("Dummy Modbus collector started. interval=%s devices=%s", interval, DEVICE_IDS)
    i = 0
    while True:
        try:
            dev = DEVICE_IDS[i % len(DEVICE_IDS)]
            row = _make_row_for_device(dev)
            insert_row(row)
            log.info("dummy_modbus: sid=%s row=%s", dev, {k: row[k] for k in ("total_active_power_kw","total_active_energy_kwh")})
        except Exception as e:
            log.exception("dummy_modbus insert failed: %s", e)
        i += 1
        time.sleep(interval)

if __name__ == "__main__":
    run_collector()

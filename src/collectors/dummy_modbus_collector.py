# src/collectors/dummy_modbus_collector.py
"""
Dummy Modbus Collector (업데이트)
- settings.MODBUS_DEVICE_IDS 및 settings.MODBUS_POLL_INTERVAL 사용
- modbus_data 스키마에 맞는 필드 삽입
- KST 타임스탬프 사용
"""

import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_modbus")
KST = ZoneInfo("Asia/Seoul")

DEVICE_IDS: List[int] = getattr(settings, "MODBUS_DEVICE_IDS", [11, 12, 13, 14, 15]) or [11,12,13,14,15]
POLL_INTERVAL: int = getattr(settings, "MODBUS_POLL_INTERVAL", 3)
MAX_FAILS: int = getattr(settings, "MODBUS_MAX_FAILS", 3)


def ensure_table():
    """modbus_data 테이블 및 컬럼 보장"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL
            );
        """)
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS avg_line_to_line_volts_v DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS avg_line_to_neutral_volts_v DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS sum_line_currents_a DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_active_power_kw DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_reactive_power_kvar DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_apparent_power_kva DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_power_factor DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_active_energy_kwh DOUBLE PRECISION;")


def _make_row_for_device(device_id: int) -> dict:
    """
    device_id 기준 간단 시뮬레이션:
    - id in settings.MODBUS_3W_IDS -> 3-wire (LL voltage)
    - id in settings.MODBUS_4W_IDS -> 4-wire (LN voltage)
    """
    ids_3w = getattr(settings, "MODBUS_3W_IDS", [11,12,13]) or [11,12,13]
    ids_4w = getattr(settings, "MODBUS_4W_IDS", [14,15]) or [14,15]
    is_3w = device_id in ids_3w

    row = {
        "time_stamp": datetime.now(KST),
        "device_id": device_id,
        "avg_line_to_line_volts_v": round(random.uniform(200, 240), 2) if is_3w else None,
        "avg_line_to_neutral_volts_v": round(random.uniform(110, 140), 2) if not is_3w else None,
        "sum_line_currents_a": round(random.uniform(0, 50), 2),
        "total_active_power_kw": round(random.uniform(0, 10), 3),
        "total_reactive_power_kvar": round(random.uniform(-5, 5), 3),
        "total_apparent_power_kva": round(random.uniform(0, 12), 3),
        "total_power_factor": round(random.uniform(0.6, 1.0), 3),
        "total_active_energy_kwh": round(random.uniform(0, 1000), 3),
    }
    return row


def insert_row(row: dict):
    """DB에 행 삽입 (modbus_data 스키마 준수)"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_data (
                time_stamp, device_id,
                avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                sum_line_currents_a, total_active_power_kw, total_reactive_power_kvar,
                total_apparent_power_kva, total_power_factor,
                total_active_energy_kwh
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        ))


def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS

    ensure_table()
    log.info("Dummy Modbus started interval=%s devices=%s", interval, devices)

    idx = 0
    while True:
        try:
            dev = devices[idx % len(devices)]
            row = _make_row_for_device(dev)
            insert_row(row)
            log.info("dummy_modbus: sid=%s p=%.3f e=%.3f", dev, row["total_active_power_kw"], row["total_active_energy_kwh"])
            idx += 1
        except Exception as e:
            log.exception("dummy_modbus insert failed: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collector()

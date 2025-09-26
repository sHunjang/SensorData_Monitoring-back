# src/collectors/dummy_solar_collector.py
"""
Dummy Solar Collector (업데이트)
- settings.SOLAR_DEVICE_IDS 및 settings.SOLAR_POLL_INTERVAL 사용
- 저장 컬럼: irradiance (solar_collector와 일관성)
- 간단 랜덤 워크로 시계열 생성
"""

import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_solar")
KST = ZoneInfo("Asia/Seoul")

DEVICE_IDS: List[int] = getattr(settings, "SOLAR_DEVICE_IDS", [31]) or [31]
POLL_INTERVAL: int = getattr(settings, "SOLAR_POLL_INTERVAL", 3)
MAX_FAILS = getattr(settings, "MODBUS_MAX_FAILS", 5)


def ensure_table():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL
            );
        """)
        cur.execute("ALTER TABLE solar_data ADD COLUMN IF NOT EXISTS irradiance DOUBLE PRECISION;")


def sample_irradiance(prev: Optional[float]) -> float:
    if prev is None:
        base = random.choice([random.uniform(0, 20), random.uniform(200, 800)])
        return round(base + random.uniform(-10, 10), 2)
    change = random.uniform(-0.2, 0.2) * prev
    v = max(0.0, prev + change + random.uniform(-5, 5))
    return round(v, 2)


def insert_row(device_id: int, value: float):
    now = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO solar_data(time_stamp, device_id, irradiance) VALUES (%s, %s, %s)",
            (now, device_id, value)
        )


def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS

    ensure_table()
    log.info("Dummy Solar started interval=%s devices=%s", interval, devices)

    last_vals = {sid: None for sid in devices}
    fail_counts = {sid: 0 for sid in devices}

    while True:
        for sid in devices:
            try:
                val = sample_irradiance(last_vals.get(sid))
                insert_row(sid, val)
                last_vals[sid] = val
                fail_counts[sid] = 0
                log.info("dummy_solar: sid=%s irradiance=%s W/m²", sid, val)
            except Exception as e:
                fail_counts[sid] += 1
                log.exception("dummy_solar: sid=%s insert failed (%d/%d): %s", sid, fail_counts[sid], MAX_FAILS, e)
                if fail_counts[sid] >= MAX_FAILS:
                    log.error("dummy_solar: sid=%s disabled after %d consecutive failures", sid, MAX_FAILS)
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collector()

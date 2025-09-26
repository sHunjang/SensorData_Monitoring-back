# src/collectors/dummy_env_collector.py
"""
Dummy Env Collector (업데이트)
- 설정(settings)에서 장치 목록 및 간격을 읽어 동작.
- 저장 컬럼: temperature, humidity (env_collector와 일관성)
- KST(tz-aware) 타임스탬프 사용
"""

import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_env")
KST = ZoneInfo("Asia/Seoul")

# settings 우선 사용, 없으면 기본값
DEVICE_IDS: List[int] = getattr(settings, "ENV_DEVICE_IDS", [21, 22, 23]) or [21, 22, 23]
POLL_INTERVAL: int = getattr(settings, "ENV_POLL_INTERVAL", 3)


def ensure_table():
    """env_data 테이블 및 컬럼 보장 (안전한 ALTER 사용)."""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL
            );
        """)
        cur.execute("ALTER TABLE env_data ADD COLUMN IF NOT EXISTS temperature DOUBLE PRECISION;")
        cur.execute("ALTER TABLE env_data ADD COLUMN IF NOT EXISTS humidity DOUBLE PRECISION;")
        cur.execute("ALTER TABLE env_data ALTER COLUMN device_id SET NOT NULL;")


def _make_sample():
    """온도(°C)와 습도(%RH) 샘플 생성"""
    temperature = round(random.uniform(15.0, 32.0), 2)
    humidity = round(random.uniform(25.0, 70.0), 2)
    return temperature, humidity


def insert_row(device_id: int, temperature: float, humidity: float):
    """DB에 행 삽입 (KST 타임스탬프)."""
    now_kst = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO env_data(time_stamp, device_id, temperature, humidity) VALUES (%s, %s, %s, %s)",
            (now_kst, device_id, temperature, humidity)
        )
    log.debug("dummy_env: inserted device=%s temp=%s hum=%s @%s", device_id, temperature, humidity, now_kst.isoformat())


def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """
    더미 수집기 실행
    - 기본값: settings에서 읽음
    """
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS

    ensure_table()
    log.info("Dummy Env started interval=%s devices=%s", interval, devices)

    idx = 0
    while True:
        try:
            did = devices[idx % len(devices)]
            temp, hum = _make_sample()
            insert_row(did, temp, hum)
            idx += 1
        except Exception as e:
            log.exception("dummy_env error: %s", e)
        time.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collector()

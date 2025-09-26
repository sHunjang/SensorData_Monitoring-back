# src/collectors/solar_collector.py
"""
일사량(Solar) 수집기

요약:
- settings에서 COM 포트, 장치 ID, 폴링 주기 등을 읽어 동작.
- 시리얼 리더 인터페이스는 src.sensors.solar_reader 모듈의
    create_instrument(port, slave_id, baudrate, ...) -> instrument
    read_solar_sensor(instrument) -> dict
  를 사용한다고 가정.
- read_solar_sensor는 최소 다음 키를 포함한 dict를 반환해야 :
    {"irradiance_w_m2": 812.3}  # 단위 W/m^2
- DB 적재는 방어적으로 수행. 컬럼이 없으면 추가.
- 연속 실패(max_fails) 초과 시 해당 장치를 스킵. 운영에서는 알람 연동 권장.
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
# reader 모듈의 함수명은 실제 구현에 맞게 조정.
from src.sensors.solar_reader import create_instrument, read_solar_sensor

log = logging.getLogger("solar_collector")
KST = ZoneInfo("Asia/Seoul")


def ensure_table():
    """
    solar_data 테이블 생성(없으면) 및 주요 컬럼 보장.
    운영에서는 마이그레이션 툴을 사용할 것을 권장.
    """
    with get_cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS solar_data (
            time_stamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL
        );
        """)
        # 안전하게 컬럼 추가
        cur.execute("ALTER TABLE solar_data ADD COLUMN IF NOT EXISTS irradiance DOUBLE PRECISION;")


def insert_row(device_id: int, payload: Dict[str, float]):
    """
    단일 행을 solar_data에 삽입.
    - payload는 read_solar_sensor가 반환한 dict.
    - 없는 값은 NULL로 삽입.
    - 시간은 KST로 저장.
    """
    now_kst = datetime.now(KST)
    irr = payload.get("irradiance_w_m2") or payload.get("irradiance") or None

    try:
        with get_cursor() as cur:
            cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, irradiance)
            VALUES (%s, %s, %s, %s)
            """, (now_kst, device_id, irr))
    except Exception:
        log.exception("solar DB insert failed for device=%s payload=%s", device_id, payload)


def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치에 대해 시리얼에서 읽고 DB에 저장.
    실패 발생 시 fail_counts를 증가시킵니다.
    """
    port = settings.SOLAR_PORT
    baud = settings.SOLAR_BAUDRATE

    try:
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        data = read_solar_sensor(inst)
        if not isinstance(data, dict):
            raise RuntimeError(f"read_solar_sensor returned non-dict: {data}")

        insert_row(device_id, data)
        log.info("solar: device=%s stored irradiance=%s", device_id, data.get("irradiance_w_m2"))
        fail_counts[device_id] = 0
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("solar read fail device=%s count=%s err=%s", device_id, fail_counts[device_id], e)


def main():
    """
    메인 루프:
    - settings.SOLAR_DEVICE_IDS 목록으로 동작.
    - 폴링 주기: settings.SOLAR_POLL_INTERVAL (초)
    - 연속 실패 허용: settings.MODBUS_MAX_FAILS 재사용 (설정 변경 가능)
    """
    ensure_table()

    device_ids = getattr(settings, "SOLAR_DEVICE_IDS", []) or []
    interval = getattr(settings, "SOLAR_POLL_INTERVAL", 5)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 3)  # 공통 실패 정책 재사용 가능

    log.info("solar_collector start. port=%s devices=%s interval=%s", settings.SOLAR_PORT, device_ids, interval)

    fail_counts = {sid: 0 for sid in device_ids}

    while True:
        for sid in device_ids:
            if fail_counts.get(sid, 0) >= max_fails:
                log.warning("solar device %s disabled after %s consecutive fails", sid, max_fails)
                continue
            run_once_for_device(sid, fail_counts)
        time.sleep(interval)

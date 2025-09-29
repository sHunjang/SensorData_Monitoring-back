# src/collectors/env_collector.py
"""
환경센서(온도·습도) 수집기

설명:
- settings 모듈에서 COM 포트, 장비 ID, 폴링 주기 등을 읽어 동작.
- 시리얼 리더 인터페이스는 src.sensors.env_reader 모듈의
  - create_instrument(port, slave_id, baudrate, ...) -> instrument
  - read_env_sensor(instrument) -> dict
  를 사용한다고 가정.
- read_env_sensor는 최소 다음 키를 포함한 dict를 반환해야 :
    {
        "temperature": 23.4,   # 섭씨
        "humidity": 55.2      # 상대습도 %
    }
- DB 적재는 방어적으로 값이 없을 경우 NULL로 넣습니다.
- 연속 실패(max_fails) 초과 시 해당 장치를 스킵. 운영에서는 알람 연동 권장.
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
# reader 모듈: 실제 함수명이 다르면 이 import를 사용자 reader에 맞춰 변경하세요.
from src.sensors.env_reader import create_instrument, read_env_sensor

log = logging.getLogger("env_collector")
KST = ZoneInfo("Asia/Seoul")


def ensure_table():
    """env_data 테이블 생성 - 새 스키마"""
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            )
        """)

def insert_row(device_id: int, payload: Dict[str, float]):
    """DB 삽입 - 새 스키마"""
    now_kst = datetime.now(KST)
    temp = payload.get("temperature") or payload.get("temp") or None
    hum = payload.get("humidity") or payload.get("humidity") or None
    
    try:
        with get_cursor() as cur:
            # 🔥 새 테이블명과 컬럼명
            cur.execute("""
                INSERT INTO env_data (time_stamp, device_id, temperature, humidity) 
                VALUES (%s, %s, %s, %s)
            """, (now_kst, device_id, temp, hum))
    except Exception:
        log.exception("env DB insert failed for device=%s payload=%s", device_id, payload)


def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치에 대해 시리얼에서 읽고 DB에 저장.
    실패 시 fail_counts를 증가시킴.
    """
    port = settings.ENV_PORT
    baud = settings.ENV_BAUDRATE
    try:
        # create_instrument 시그니처는 사용자 env_reader에 맞춰 조정할 것
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        data = read_env_sensor(inst)
        if not isinstance(data, dict):
            raise RuntimeError(f"read_env_sensor returned non-dict: {data}")

        insert_row(device_id, data)
        log.info("env: device=%s stored temp=%s hum=%s", device_id, data.get("temperature"), data.get("humidity"))
        fail_counts[device_id] = 0
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("env read fail device=%s count=%s err=%s", device_id, fail_counts[device_id], e)


def main():
    """
    메인 루프: settings.ENV_DEVICE_IDS 목록 순회하면서 주기적으로 읽음.
    환경설정:
      - 포트: settings.ENV_PORT (기본 COM8)
      - 장치 ID: settings.ENV_DEVICE_IDS (예: [21,22,23])
      - 간격: settings.ENV_POLL_INTERVAL (초)
      - 연속 실패 허용: settings.MODBUS_MAX_FAILS (재사용)
    """
    ensure_table()

    device_ids = getattr(settings, "ENV_DEVICE_IDS", []) or []
    interval = getattr(settings, "ENV_POLL_INTERVAL", 60)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 3)  # 공통 실패 정책 재사용 가능

    log.info("env_collector start. port=%s devices=%s interval=%s", settings.ENV_PORT, device_ids, interval)

    fail_counts = {sid: 0 for sid in device_ids}

    while True:
        for sid in device_ids:
            if fail_counts.get(sid, 0) >= max_fails:
                log.warning("env device %s disabled after %s consecutive fails", sid, max_fails)
                continue
            run_once_for_device(sid, fail_counts)
        time.sleep(interval)

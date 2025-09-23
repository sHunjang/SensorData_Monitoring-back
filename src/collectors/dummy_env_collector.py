# src/collectors/dummy_env_collector.py
"""
Dummy Env Collector
- 목적: 개발/테스트용 더미 온/습도 데이터 생성 및 DB 적재
- 변경점: time_stamp를 UTC가 아닌 KST(Asia/Seoul) tz-aware datetime으로 저장
- 사용법: run_collector(interval=10, device_ids=[21,22,23])
"""

import time
import random
import datetime
import logging
from zoneinfo import ZoneInfo

from src.db.client import get_cursor

log = logging.getLogger("dummy_env")

# 기본 장치 목록(라운드로빈)
DEVS = [21, 22, 23]
_i = 0  # 라운드로빈 인덱스 (모듈 레벨 상태)

# KST ZoneInfo 객체 (Python 3.9+)
KST = ZoneInfo("Asia/Seoul")


def next_dev(device_list=None):
    """
    라운드로빈으로 다음 device id 반환.
    - device_list를 전달하면 그 목록으로 순환.
    - 모듈 전역 DEVS는 기본값.
    """
    global _i
    devs = device_list if device_list is not None else DEVS
    if not devs:
        raise ValueError("device list is empty")
    d = devs[_i % len(devs)]
    _i += 1
    return d


def ensure_table():
    """
    env_data 테이블 존재 보장.
    - time_stamp는 TIMESTAMPTZ NOT NULL
    - device_id는 NOT NULL
    - 안전을 위해 ALTER TABLE로 필요한 컬럼 보장
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            );
        """)
        # 기존 테이블에 컬럼이 없을 경우를 대비한 보강
        cur.execute("ALTER TABLE env_data ADD COLUMN IF NOT EXISTS device_id INT;")
        cur.execute("ALTER TABLE env_data ALTER COLUMN device_id SET NOT NULL;")


def insert_row(device_id: int):
    """
    한 행을 DB에 삽입.
    - time_stamp는 KST tz-aware datetime으로 생성하여 timestamptz 컬럼에 저장.
    - temperature/humidity는 소수 둘째자리로 생성.
    """
    # KST 기준 현재 시각(tz-aware)
    now_kst = datetime.datetime.now(KST)

    temperature = round(random.uniform(15, 32), 2)
    humidity = round(random.uniform(25, 70), 2)

    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO env_data(time_stamp, device_id, temperature, humidity) VALUES (%s, %s, %s, %s)",
            (now_kst, device_id, temperature, humidity)
        )
    log.debug("Inserted env row device=%s temp=%s hum=%s @%s", device_id, temperature, humidity, now_kst.isoformat())


def run_collector(interval: int = 10, device_ids=None):
    """
    더미 수집기 실행 루프.
    - interval: 초 단위 주기
    - device_ids: None이면 모듈 DEVS 사용, 리스트 전달 가능
    - 내부에서 ensure_table을 호출해 테이블을 보장
    - 예외 발생 시 로깅 후 루프 계속 (개발용)
    """
    ensure_table()
    log.info("Dummy Env started interval=%s devices=%s", interval, device_ids or DEVS)

    # 로컬 장치 목록 사용 (인자로 넘어온 경우 우선)
    devices = device_ids if device_ids is not None else DEVS

    while True:
        try:
            did = next_dev(devices)
            insert_row(did)
        except Exception as e:
            log.exception("env fail: %s", e)
        time.sleep(interval)


# 모듈을 직접 실행하면 기본 동작(start with default interval)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_collector()

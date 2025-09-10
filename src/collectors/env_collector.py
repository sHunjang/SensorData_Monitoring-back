"""
env_collector.py
- 주기적으로 read_env()를 호출해서 DB에 데이터를 적재하는 모듈.
- 백그라운드 태스크, systemd 서비스, 혹은 별도 프로세스로 실행 가능.
"""

import time
import logging

from src.sensors.env_reader import read_env
from src.db.client import get_cursor

log = logging.getLogger("env_collector")

def ensure_table():
    """
    환경 데이터 테이블 생성 (존재하지 않으면).
    - time_stamp: 타임스탬프
    - temperature: 섭씨 온도
    - humidity: 상대 습도(%)
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXIStime_stamp env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            );
        """)

def insert_env_row(row: dict):
    """
    읽은 환경 데이터를 DB에 1행 삽입한다.
    Args:
        row (dict): {"time_stamp": datetime, "temperature": float, "humidity": float}
    """
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO env_data (time_stamp, temperature, humidity) VALUES (%s, %s, %s)",
            (row["time_stamp"], row["temperature"], row["humidity"])
        )

def run_collector(interval: int = 60):
    """
    주기적으로 read_env() 호출 → DB 적재
    Args:
        interval (int): 측정 주기 (초 단위)
    """
    ensure_table()
    log.info("Env collector started. Interval=%s sec", interval)
    while True:
        try:
            row = read_env()
            insert_env_row(row)
            log.debug("Inserted env_data row: %s", row)
        except Exception as e:
            log.exception("Failed to insert env_data: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    # 개발 환경에서 직접 실행 가능: python -m src.collectors.env_collector
    run_collector(interval=60)

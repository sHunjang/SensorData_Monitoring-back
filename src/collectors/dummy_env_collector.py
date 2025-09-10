"""
dummy_env_collector.py
- 실제 센서가 도착하기 전 테스트용.
- 온도(°C), 습도(%)를 랜덤으로 생성해서 env_data 테이블에 저장한다.
- Collector 실행 시, 일정 주기(interval 초)마다 한 행씩 INSERT한다.
"""

import time
import random
import datetime
import logging
from src.db.client import get_cursor

log = logging.getLogger("dummy_env_collector")

def ensure_table():
    """
    env_data 테이블 생성 (없으면).
    - time_stamp: 시각
    - temperature: °C
    - humidity: %
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            );
        """)

def insert_dummy_row():
    """
    더미 온습도 데이터를 생성해서 DB에 삽입한다.
    """
    row = {
        "time_stamp": datetime.datetime.utcnow(),
        "temperature": round(random.uniform(18.0, 30.0), 2),  # 18~30°C
        "humidity": round(random.uniform(30.0, 70.0), 2),     # 30~70%
    }
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO env_data (time_stamp, temperature, humidity) VALUES (%s, %s, %s)",
            (row["time_stamp"], row["temperature"], row["humidity"])
        )
    log.info("Inserted dummy row: %s", row)

def run_collector(interval: int = 60):
    """
    주기적으로 더미 데이터를 생성해서 env_data에 적재한다.
    Args:
        interval (int): 수집 주기(초)
    """
    ensure_table()
    log.info("Dummy Env collector started. Interval=%s sec", interval)
    while True:
        try:
            insert_dummy_row()
        except Exception as e:
            log.exception("Failed to insert dummy env_data: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    # 개발/테스트 환경에서 실행
    run_collector(interval=60)  # 1분 간격

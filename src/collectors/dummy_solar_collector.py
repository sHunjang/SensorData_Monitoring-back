# src/collectors/dummy_solar_collector.py
"""
Dummy solar collector
- 목적: 개발/테스트용 더미 일사량 데이터를 DB에 주기적으로 삽입
- 변경점:
  1) solar_data 테이블 스키마에 device_id(INT NOT NULL) 추가
  2) insert_row에서 device_id 인자를 받아 DB에 함께 저장
  3) DB 타임스탬프는 서버 측에서 KST로 생성: NOW() AT TIME ZONE 'Asia/Seoul'
  4) run_collector는 기본 device_id=31로 동작. 호출 시 다른 ID 전달 가능.
"""
import time
import random
import datetime
import logging
from src.db.client import get_cursor

log = logging.getLogger("dummy_solar")

# 기본 더미 장치 ID. 필요시 run_collector(..., device_id=XX)로 변경 가능.
DEFAULT_DEVICE_ID = 31

def ensure_table():
    """
    로컬 더미 테이블 보장 (bootstrap이 이미 처리했을 수 있음).
    bootstrap과 동일한 컬럼을 사용하여 충돌을 최소화.
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data(
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                solar DOUBLE PRECISION
            );
        """)

def insert_row(device_id: int = DEFAULT_DEVICE_ID):
    """
    한 행 삽입.
    - device_id: 삽입할 장치 ID (NOT NULL)
    - solar: 0..1000 범위의 랜덤 실수
    - time_stamp는 DB 측에서 KST(Asia/Seoul) 기준으로 생성
    """
    val = round(random.uniform(0, 1000), 2)
    with get_cursor() as cur:
        # DB에서 KST로 타임스탬프 생성. Python에서 시간대 변환을 신경쓰지 않아도 됨.
        cur.execute(
            "INSERT INTO solar_data (time_stamp, device_id, solar) VALUES (NOW() AT TIME ZONE 'Asia/Seoul', %s, %s)",
            (device_id, val),
        )
    # log.info("inserted dummy solar: device_id=%s solar=%s", device_id, val)

def run_collector(interval: int = 10, device_id: int = DEFAULT_DEVICE_ID):
    """
    더미 수집기 메인 루프
    - interval: 초 단위 폴링 주기
    - device_id: 삽입에 사용할 장치 ID
    """
    ensure_table()
    log.info("Dummy Solar started interval=%s device_id=%s", interval, device_id)
    while True:
        try:
            insert_row(device_id=device_id)
        except Exception as e:
            log.exception("solar fail: %s", e)
        time.sleep(interval)

if __name__ == "__main__":
    # 직접 실행용
    logging.basicConfig(level=logging.INFO)
    run_collector()

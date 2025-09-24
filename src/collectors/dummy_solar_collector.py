# src/collectors/dummy_solar_collector.py
"""
Dummy Solar Collector
- 목적: 개발환경에서 일사량 데이터를 DB에 주기적으로 넣어
  프론트에서 실시간 그래프로 확인할 수 있게 함.
- 특징:
  - device_id 리스트 지원 (기본 [1])
  - KST(Asia/Seoul) tz-aware timestamp 저장 (timestamptz 컬럼에 적합)
  - INSERT 시 device_id 필드 포함 (NOT NULL 제약 대응)
  - 값에 약간의 변동성(랜덤 노이즈) 추가하여 그래프 변화가 보이게 함
- 사용:
  - 백엔드가 실행될 때 main에서 스레드로 실행되거나,
    개발 중에는 별도 프로세스로 실행해서 데이터 주입 가능.
"""
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from src.db.client import get_cursor

log = logging.getLogger("dummy_solar")

# 테스트할 device id 목록. 실제 환경에 맞게 변경 가능.
DEVICE_IDS: List[int] = [1]

# 최대 실패 허용 횟수 (DB 접속 문제 등)
MAX_FAILS = 5

# 기본 삽입 간격(초) -- 개발/테스트용은 1~5초 권장
DEFAULT_INTERVAL = 1

_i = 0
def next_device() -> int:
    global _i
    d = DEVICE_IDS[_i % len(DEVICE_IDS)]
    _i += 1
    return d

def ensure_table():
    """
    안전 장치: 테이블이 없으면 생성.
    (프로덕션에서는 bootstrap에서 처리되므로 중복되어도 무해함)
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data(
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                solar DOUBLE PRECISION
            );
        """)

def sample_irradiance(prev: Optional[float]) -> float:
    """
    간단한 시계열 생성:
    - prev 값이 있으면 그 근처에서 랜덤 워크
    - 없으면 낮/밤 단순 분포로 초기값 생성
    """
    if prev is None:
        # 초기값: 낮(200~800) / 밤(0~20) 랜덤 선택 (간단)
        base = random.choice([random.uniform(0, 20), random.uniform(200, 800)])
        return round(base + random.uniform(-10, 10), 2)
    # 랜덤 워크: ±20% 범위 제한
    change = random.uniform(-0.2, 0.2) * prev
    v = max(0.0, prev + change + random.uniform(-5, 5))
    return round(v, 2)

def insert_row(device_id: int, value: float):
    """
    KST tz-aware timestamp로 저장.
    """
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO solar_data(time_stamp, device_id, solar) VALUES (%s, %s, %s)",
            (now, device_id, value)
        )

def run_collector(interval: int = DEFAULT_INTERVAL):
    """
    메인 루프: 지정한 interval(초)마다 데이터 삽입.
    - 예외 발생 시 로그를 남기고 재시도.
    """
    ensure_table()
    log.info("Dummy Solar collector started. interval=%s, devices=%s", interval, DEVICE_IDS)

    fail_counts = {sid: 0 for sid in DEVICE_IDS}
    last_vals = {sid: None for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            try:
                # generate next sample based on last value
                val = sample_irradiance(last_vals.get(sid))
                insert_row(sid, val)
                last_vals[sid] = val
                fail_counts[sid] = 0
                log.info("dummy_solar: sid=%s solar=%s W/m²", sid, val)
            except Exception as e:
                fail_counts[sid] += 1
                log.exception("dummy_solar: sid=%s insert failed (%d/%d): %s", sid, fail_counts[sid], MAX_FAILS, e)
                # if repeated failure, back off a bit
                if fail_counts[sid] >= MAX_FAILS:
                    log.error("dummy_solar: sid=%s disabled after %d consecutive failures", sid, MAX_FAILS)
        time.sleep(interval)

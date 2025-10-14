"""
더미 태양광 센서 수집기 모듈

주요 기능:
- 일사량(irradiance) 센서 시뮬레이션 (테스트용)
- 시간대별 현실적인 일사량 패턴 생성
- 실시간 DB 저장 (solar_data 원본 테이블)
- 주기적 데이터 수집 (기본 5초)

센서 정보:
- 디바이스 ID: 31 (1개 센서)
- 측정값: 일사량 (W/m²)
- 범위: 0~1200 W/m² (맑은 날 기준)
- 특징: 시간대별 변화 반영 (낮 높음, 밤 0)

사용법:
  python -m src.collectors.dummy_solar_collector
  
  또는 main.py에서 자동 실행 (MODE=dummy)
"""

import time
import random
import logging
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_solar")

# ============================================================
# 전역 설정
# ============================================================

KST = ZoneInfo("Asia/Seoul")

# 디바이스 ID 설정 (settings.py에서 로드)
DEVICE_IDS: List[int] = settings.SOLAR_DEVICE_IDS  # [31]
POLL_INTERVAL: int = settings.SOLAR_POLL_INTERVAL  # 5초

# 최대 연속 실패 횟수
MAX_FAILS: int = 3


# ============================================================
# 테이블 관리
# ============================================================

def ensure_table():
    """
    solar_data 원본 테이블 생성 확인
    
    ⚠️ 주의: bootstrap.py와 동일한 스키마 사용
    - 실제 운영에서는 bootstrap.py 실행 후 이 함수는 스킵됨 (IF NOT EXISTS)
    """
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                irradiance DOUBLE PRECISION
            );
        """)
        log.debug("✅ solar_data table ensured")


# ============================================================
# 더미 데이터 생성
# ============================================================

def get_time_based_irradiance() -> float:
    """
    현재 시간대를 기반으로 현실적인 일사량 생성
    
    Returns:
        일사량 (W/m²)
        
    패턴:
        - 00:00~06:00: 0 W/m² (밤)
        - 06:00~12:00: 0 → 1000 W/m² (일출~정오)
        - 12:00~18:00: 1000 → 0 W/m² (정오~일몰)
        - 18:00~24:00: 0 W/m² (밤)
        
    개선 가능:
        - 계절별 일출/일몰 시각 반영
        - 날씨 변화 시뮬레이션 (구름)
        - 실제 지역 위도/경도 기반 계산
    """
    now = datetime.now(KST)
    hour = now.hour
    minute = now.minute
    time_decimal = hour + minute / 60.0
    
    # 밤 시간 (0~6시, 18~24시)
    if time_decimal < 6.0 or time_decimal >= 18.0:
        return 0.0
    
    # 낮 시간 (6~18시): sin 곡선으로 자연스러운 변화
    # 06:00 -> 0°, 12:00 -> 90°, 18:00 -> 180°
    angle = (time_decimal - 6.0) / 12.0 * math.pi
    base_irradiance = math.sin(angle) * 1000.0  # 최대 1000 W/m²
    
    # 랜덤 변동 추가 (구름 등)
    variation = random.uniform(-50, 50)
    irradiance = max(0.0, base_irradiance + variation)
    
    return round(irradiance, 2)


def sample_irradiance(prev: Optional[float] = None) -> float:
    """
    일사량 샘플 생성 (시간대 기반 + 랜덤워크)
    
    Args:
        prev: 이전 측정값 (연속성 유지용)
        
    Returns:
        일사량 (W/m²)
        
    동작:
        - 시간대 기반 기본값 생성
        - 이전 값과의 연속성 유지 (급격한 변화 방지)
    """
    # 시간대 기반 기본값
    time_based = get_time_based_irradiance()
    
    # 이전 값이 없으면 시간대 기반값 사용
    if prev is None:
        return time_based
    
    # 이전 값과의 차이 제한 (급격한 변화 방지)
    max_change = 50.0  # 최대 50 W/m² 변화
    if abs(time_based - prev) > max_change:
        # 서서히 변화
        direction = 1 if time_based > prev else -1
        return round(prev + direction * max_change + random.uniform(-10, 10), 2)
    else:
        # 작은 랜덤 변동
        return round(time_based + random.uniform(-10, 10), 2)


# ============================================================
# 데이터베이스 저장
# ============================================================

def insert_row(device_id: int, irradiance: float):
    """
    solar_data 테이블에 원시 데이터 삽입
    
    Args:
        device_id: 디바이스 ID
        irradiance: 일사량 (W/m²)
        
    동작:
        - 5초마다 수집된 원시 데이터를 저장
        - 이후 별도 집계 프로세스가 이를 읽어 1분/15분/... 테이블로 집계
    """
    now = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, irradiance)
            VALUES (%s, %s, %s)
        """, (now, device_id, irradiance))


# ============================================================
# 수집기 메인 루프
# ============================================================

def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """
    더미 태양광 센서 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초), 기본값은 settings에서 로드 (5초)
        device_ids: 수집할 디바이스 ID 목록, 기본값은 settings에서 로드
        
    동작 흐름:
        1. 테이블 생성 확인
        2. 무한 루프 시작
        3. 각 디바이스별 일사량 생성 (시간대 반영)
        4. DB에 저장
        5. interval 초 대기
        6. 반복
        
    종료 조건:
        - Ctrl+C (KeyboardInterrupt)
        - 연속 실패 횟수 초과
        - 치명적 에러 발생
    """
    # 파라미터 기본값 설정
    interval = interval if interval is not None else POLL_INTERVAL
    devices = device_ids if device_ids is not None else DEVICE_IDS
    
    # 테이블 생성 확인
    try:
        ensure_table()
    except Exception as e:
        log.error(f"❌ Failed to ensure table: {e}")
        return
    
    log.info("=" * 70)
    log.info("☀️  Dummy Solar Sensor Collector Started")
    log.info(f"   Interval: {interval}s")
    log.info(f"   Devices: {devices}")
    log.info("=" * 70)
    
    # 디바이스별 이전 값 관리 (연속성 유지)
    last_vals = {sid: None for sid in devices}
    fail_counts = {sid: 0 for sid in devices}
    
    try:
        while True:
            for sid in devices:
                try:
                    # 일사량 샘플 생성 (시간대 반영)
                    val = sample_irradiance(last_vals.get(sid))
                    
                    # DB 저장
                    insert_row(sid, val)
                    
                    # 상태 업데이트
                    last_vals[sid] = val
                    fail_counts[sid] = 0
                    
                    # 성공 로깅 (시간 정보 추가)
                    now = datetime.now(KST)
                    log.info(
                        f"☀️  ID={sid:2d} | "
                        f"Time={now.strftime('%H:%M:%S')} | "
                        f"Irradiance={val:7.2f} W/m²"
                    )
                    
                except Exception as e:
                    fail_counts[sid] += 1
                    log.error(
                        f"❌ Insert failed for device {sid} "
                        f"(attempt {fail_counts[sid]}/{MAX_FAILS}): {e}"
                    )
                    
                    if fail_counts[sid] >= MAX_FAILS:
                        log.critical(
                            f"🔥 Max failures reached for device {sid} "
                            f"({MAX_FAILS}), stopping collector"
                        )
                        return
            
            # 수집 주기 대기
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("")
        log.info("=" * 70)
        log.info("🛑 Dummy Solar collector stopped by user (Ctrl+C)")
        log.info("=" * 70)
        
    except Exception as e:
        log.exception(f"❌ Dummy Solar collector fatal error: {e}")


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":
    # 직접 실행 시 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    run_collector()

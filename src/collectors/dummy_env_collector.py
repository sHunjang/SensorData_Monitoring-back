"""
더미 환경센서 수집기 모듈

주요 기능:
- 온습도 센서 시뮬레이션 (테스트용)
- 현실적인 온도/습도 데이터 생성
- 실시간 DB 저장 (env_data 원본 테이블)
- 주기적 데이터 수집 (기본 5초)

센서 정보:
- 디바이스 ID: 21, 22, 23 (3개 센서)
- 측정값: 온도(°C), 습도(%RH)
- 범위: 온도 15~32°C, 습도 25~70%

사용법:
  python -m src.collectors.dummy_env_collector
  
  또는 main.py에서 자동 실행 (MODE=dummy)
"""

import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Optional, Tuple

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_env")

# ============================================================
# 전역 설정
# ============================================================

KST = ZoneInfo("Asia/Seoul")

# 디바이스 ID 설정 (settings.py에서 로드)
DEVICE_IDS: List[int] = settings.ENV_DEVICE_IDS  # [21, 22, 23]
POLL_INTERVAL: int = settings.ENV_POLL_INTERVAL  # 5초

# 최대 연속 실패 횟수
MAX_FAILS: int = 3


# ============================================================
# 테이블 관리
# ============================================================

def ensure_table():
    """
    env_data 원본 테이블 생성 확인
    
    ⚠️ 주의: bootstrap.py와 동일한 스키마 사용
    - 실제 운영에서는 bootstrap.py 실행 후 이 함수는 스킵됨 (IF NOT EXISTS)
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
        log.debug("✅ env_data table ensured")


# ============================================================
# 더미 데이터 생성
# ============================================================

def make_sample(device_id: int) -> Tuple[float, float]:
    """
    디바이스별 현실적인 온습도 데이터 생성
    
    Args:
        device_id: 디바이스 ID (21~23)
        
    Returns:
        (temperature, humidity): 온도(°C), 습도(%RH)
        
    데이터 범위:
        - 온도: 15~32°C (실내 환경 기준)
        - 습도: 25~70%RH (쾌적 범위)
        
    개선 가능:
        - 시간대별 온도 변화 반영 (낮/밤)
        - 계절별 변화 반영
        - 센서별 위치 특성 반영
    """
    # 기본 랜덤 생성
    temperature = round(random.uniform(15.0, 32.0), 2)
    humidity = round(random.uniform(25.0, 70.0), 2)
    
    # 센서별 약간의 특성 부여 (선택적)
    # 예: ID 21은 약간 더 따뜻한 위치, ID 23은 습한 위치 등
    if device_id == 21:
        temperature += 1.0  # 약간 더 따뜻
    elif device_id == 23:
        humidity += 5.0  # 약간 더 습함
    
    # 범위 제한
    temperature = max(15.0, min(35.0, temperature))
    humidity = max(20.0, min(80.0, humidity))
    
    return round(temperature, 2), round(humidity, 2)


# ============================================================
# 데이터베이스 저장
# ============================================================

def insert_row(device_id: int, temperature: float, humidity: float):
    """
    env_data 테이블에 원시 데이터 삽입
    
    Args:
        device_id: 디바이스 ID
        temperature: 온도(°C)
        humidity: 습도(%RH)
        
    동작:
        - 5초마다 수집된 원시 데이터를 저장
        - 이후 별도 집계 프로세스가 이를 읽어 1분/15분/... 테이블로 집계
    """
    now_kst = datetime.now(KST)
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
            VALUES (%s, %s, %s, %s)
        """, (now_kst, device_id, temperature, humidity))


# ============================================================
# 수집기 메인 루프
# ============================================================

def run_collector(interval: Optional[int] = None, device_ids: Optional[List[int]] = None):
    """
    더미 환경센서 수집기 메인 루프
    
    Args:
        interval: 수집 주기 (초), 기본값은 settings에서 로드 (5초)
        device_ids: 수집할 디바이스 ID 목록, 기본값은 settings에서 로드
        
    동작 흐름:
        1. 테이블 생성 확인
        2. 무한 루프 시작
        3. 각 디바이스 순환하며 데이터 생성
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
    log.info("🌿 Dummy Environmental Sensor Collector Started")
    log.info(f"   Interval: {interval}s")
    log.info(f"   Devices: {devices}")
    log.info("=" * 70)
    
    # 디바이스 순환 인덱스
    idx = 0
    fail_count = 0
    
    try:
        while True:
            try:
                # 순환 방식으로 디바이스 선택
                # 예: [21,22,23] -> 21 -> 22 -> 23 -> 21 -> ...
                dev = devices[idx % len(devices)]
                
                # 더미 데이터 생성
                temp, hum = make_sample(dev)
                
                # DB 저장
                insert_row(dev, temp, hum)
                
                # 성공 로깅
                log.info(
                    f"🌡️  ID={dev:2d} | "
                    f"Temp={temp:5.2f}°C | "
                    f"Humidity={hum:5.2f}%RH"
                )
                
                # 실패 카운터 리셋
                fail_count = 0
                
                # 다음 디바이스로
                idx += 1
                
            except Exception as e:
                fail_count += 1
                log.error(f"❌ Insert failed (attempt {fail_count}/{MAX_FAILS}): {e}")
                
                if fail_count >= MAX_FAILS:
                    log.critical(f"🔥 Max failures reached ({MAX_FAILS}), stopping collector")
                    break
            
            # 수집 주기 대기
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("")
        log.info("=" * 70)
        log.info("🛑 Dummy Env collector stopped by user (Ctrl+C)")
        log.info("=" * 70)
        
    except Exception as e:
        log.exception(f"❌ Dummy Env collector fatal error: {e}")


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

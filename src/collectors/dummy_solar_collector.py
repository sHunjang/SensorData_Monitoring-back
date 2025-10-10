"""
더미 일사량(Solar) 센서 데이터 수집기

실제 하드웨어 없이 테스트/개발을 위한 더미 일사량 데이터를 생성합니다.

주요 변경사항 (2025-10-10):
    - RAW 테이블 제거: 5초 데이터는 메모리에만 보관
    - 1분마다 평균 계산하여 1분 테이블에 직접 저장

데이터 흐름:
    1. 5초마다 더미 데이터 생성 → 메모리 버퍼에 저장
    2. 실시간 API에서 메모리 버퍼 데이터 제공 (DB 저장 안함)
    3. 1분마다 버퍼 데이터 평균 계산 → 1분 테이블 INSERT
    4. 버퍼 클리어

테이블:
    - solar_data_31_1m (device_id: 31 고정)

실행:
    python -m src.collectors.dummy_solar_collector

작성일: 2025-10-10
"""

import time
import random
import logging
import statistics
import math
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_solar")

# ========================================
# 전역 변수
# ========================================
SOLAR_DEVICE = settings.SOLAR_ID  # 31
COLLECTION_INTERVAL = settings.COLLECTION_INTERVAL  # 5초

# 메모리 버퍼: 5초 데이터를 1분간 누적
data_buffer: List[dict] = []


# ========================================
# 테이블 존재 확인
# ========================================
def ensure_table():
    """
    Solar 1분 테이블 존재 여부 확인
    
    동작:
        solar_data_31_1m 테이블이 존재하는지 확인하고,
        없으면 에러 발생
    
    Raises:
        RuntimeError: 필요한 테이블이 존재하지 않을 때
    """
    log.info("📊 Solar 1분 테이블 확인 중...")
    
    table_name = f"solar_data_{SOLAR_DEVICE}_1m"
    
    with get_cursor() as cur:
        cur.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name='{table_name}'
            );
        """)
        
        if cur.fetchone()[0]:
            log.info(f"  ✅ {table_name} 존재")
        else:
            log.error(f"  ❌ {table_name} 없음! bootstrap.py 실행 필요")
            raise RuntimeError(
                f"{table_name} 테이블이 존재하지 않습니다. "
                "python -m src.db.bootstrap 를 먼저 실행하세요."
            )


# ========================================
# 더미 데이터 생성
# ========================================
def generate_dummy_data() -> dict:
    """
    더미 일사량 5초 데이터 생성
    
    현실적인 일사량 패턴을 시뮬레이션합니다.
    
    Returns:
        dict: 더미 일사량 데이터
              {
                  'device_id': int,
                  'timestamp': datetime,
                  'irradiance_w_per_m2': float  # 일사량 (W/m²)
              }
    
    패턴:
        - 야간(18:00-06:00): 0 W/m²
        - 일출/일몰 시간대: 점진적 증가/감소
        - 정오(12:00): 최대 약 1000 W/m² (맑은 날 기준)
        - 구름/날씨에 따른 변동 반영
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    
    # 시간을 소수점으로 변환 (예: 12:30 → 12.5)
    time_decimal = hour + minute / 60.0
    
    # ========================================
    # 일출/일몰 시간 (간단한 모델)
    # ========================================
    sunrise = 6.0   # 06:00
    sunset = 18.0   # 18:00
    solar_noon = 12.0  # 12:00 (태양 최고점)
    
    # ========================================
    # 야간: 일사량 0
    # ========================================
    if time_decimal < sunrise or time_decimal > sunset:
        irradiance = 0.0
    else:
        # ========================================
        # 주간: 정현파 패턴으로 일사량 계산
        # ========================================
        # 정오를 기준으로 대칭적인 곡선
        # sin 함수 사용: 일출에서 0, 정오에서 최대, 일몰에서 0
        
        # 일출부터 일몰까지의 시간 (시간 단위)
        day_length = sunset - sunrise  # 12시간
        
        # 현재 시각이 일출 이후 몇 시간인지
        hours_since_sunrise = time_decimal - sunrise
        
        # 0~π 범위로 정규화 (일출=0, 정오=π/2, 일몰=π)
        angle = (hours_since_sunrise / day_length) * math.pi
        
        # 정현파로 일사량 계산 (최대 1000 W/m²)
        max_irradiance = 1000.0  # 맑은 날 최대 일사량
        base_irradiance = max_irradiance * math.sin(angle)
        
        # ========================================
        # 날씨 효과 (구름 등)
        # ========================================
        # 80-100%의 랜덤 계수 (구름, 대기 조건)
        weather_factor = random.uniform(0.8, 1.0)
        
        irradiance = base_irradiance * weather_factor
        
        # 음수 방지 (일출/일몰 직전/직후)
        irradiance = max(0.0, irradiance)
    
    # 약간의 노이즈 추가 (센서 측정 오차)
    irradiance += random.uniform(-5, 5)
    irradiance = max(0.0, irradiance)  # 음수 방지
    
    return {
        'device_id': SOLAR_DEVICE,
        'timestamp': datetime.now(timezone.utc),
        'irradiance_w_per_m2': round(irradiance, 1)
    }


# ========================================
# 5초 데이터 수집 (메모리 버퍼)
# ========================================
def collect_5s_data():
    """
    Solar 디바이스의 5초 데이터를 생성하고 메모리 버퍼에 저장
    
    동작:
        1. 더미 데이터 생성
        2. 메모리 버퍼에 추가 (DB 저장 안함)
        3. 실시간 API에서 이 버퍼를 읽어서 제공
    """
    try:
        data = generate_dummy_data()
        data_buffer.append(data)
        
        log.debug(
            f"📥 Solar 버퍼 추가: "
            f"일사량={data['irradiance_w_per_m2']:.1f}W/m²"
        )
        
    except Exception as e:
        log.error(f"❌ Solar 데이터 생성 실패: {e}")


# ========================================
# 1분마다 평균 계산 및 DB 저장
# ========================================
def flush_1m_aggregation():
    """
    1분마다 버퍼의 5초 데이터를 평균 계산하여 1분 테이블에 저장
    """
    global data_buffer
    
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    try:
        if not data_buffer:
            log.warning(f"  ⚠️  Solar: 버퍼 데이터 없음")
            return
        
        # 집계 계산
        irradiances = [r['irradiance_w_per_m2'] for r in data_buffer]
        avg_irradiance = statistics.mean(irradiances)
        max_irradiance = max(irradiances)
        min_irradiance = min(irradiances)
        count = len(data_buffer)
        
        # ✅ 수정: device_id 추가!
        with get_cursor() as cur:
            cur.execute(f"""
                INSERT INTO solar_data_{SOLAR_DEVICE}_1m (
                    timestamp,
                    device_id,
                    avg_irradiance_w_per_m2,
                    max_irradiance_w_per_m2,
                    min_irradiance_w_per_m2,
                    count
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                );
            """, (
                now,
                SOLAR_DEVICE,  # ✅ 추가!
                avg_irradiance, max_irradiance, min_irradiance, count
            ))
        
        log.info(
            f"  ✅ Solar 1분 집계 저장: "
            f"평균={avg_irradiance:.1f}W/m²({min_irradiance:.1f}-{max_irradiance:.1f}), "
            f"samples={count}"
        )
        
    except Exception as e:
        log.error(f"  ❌ Solar 1분 집계 실패: {e}")
    
    # 버퍼 클리어
    data_buffer.clear()
    log.info("🧹 버퍼 클리어 완료\n")


# ========================================
# 메인 실행 루프
# ========================================
def run():
    """
    더미 Solar 수집기 메인 루프
    
    동작:
        1. 테이블 존재 확인
        2. 5초마다 데이터 수집 (메모리 버퍼)
        3. 1분마다 집계 및 DB 저장
        4. Ctrl+C로 종료 시 정상 종료
    """
    log.info("=" * 60)
    log.info("🎭 더미 Solar 수집기 시작 (신규 아키텍처)")
    log.info(f"   Device: {SOLAR_DEVICE}")
    log.info(f"   수집 주기: {COLLECTION_INTERVAL}초")
    log.info(f"   집계 주기: 1분")
    log.info("=" * 60)
    
    # 테이블 확인
    ensure_table()
    
    # 마지막 집계 시각
    last_flush_minute = datetime.now(timezone.utc).minute
    
    try:
        while True:
            # 5초 데이터 수집
            collect_5s_data()
            
            # 1분 경과 확인
            current_minute = datetime.now(timezone.utc).minute
            if current_minute != last_flush_minute:
                flush_1m_aggregation()
                last_flush_minute = current_minute
            
            # 5초 대기
            time.sleep(COLLECTION_INTERVAL)
            
    except KeyboardInterrupt:
        log.info("\n🛑 더미 Solar 수집기 종료 (사용자 요청)")
    except Exception as e:
        log.exception(f"❌ 더미 Solar 수집기 오류: {e}")
        raise


if __name__ == "__main__":
    """
    직접 실행 시 수집기 시작
    
    사용법:
        python -m src.collectors.dummy_solar_collector
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()

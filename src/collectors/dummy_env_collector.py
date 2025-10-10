"""
더미 환경(온습도) 센서 데이터 수집기

실제 하드웨어 없이 테스트/개발을 위한 더미 온습도 데이터를 생성합니다.

주요 변경사항 (2025-10-10):
    - RAW 테이블 제거: 5초 데이터는 메모리에만 보관
    - 1분마다 평균 계산하여 1분 테이블에 직접 저장

데이터 흐름:
    1. 5초마다 더미 데이터 생성 → 메모리 버퍼에 저장
    2. 실시간 API에서 메모리 버퍼 데이터 제공 (DB 저장 안함)
    3. 1분마다 버퍼 데이터 평균 계산 → 1분 테이블 INSERT
    4. 버퍼 클리어

테이블:
    - env_data_{device_id}_1m (device_id: 21-23)

실행:
    python -m src.collectors.dummy_env_collector

작성일: 2025-10-10
"""

import time
import random
import logging
import statistics
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("dummy_env")

# ========================================
# 전역 변수
# ========================================
ENV_DEVICES = settings.ENV_IDS
COLLECTION_INTERVAL = settings.COLLECTION_INTERVAL  # 5초

# 메모리 버퍼: device_id별로 5초 데이터를 1분간 누적
data_buffer: Dict[int, List[dict]] = defaultdict(list)


# ========================================
# 테이블 존재 확인
# ========================================
def ensure_tables():
    """
    Env 1분 테이블 존재 여부 확인
    
    동작:
        각 device_id에 대해 env_data_{device_id}_1m 테이블이
        존재하는지 확인하고, 없으면 에러 발생
    
    Raises:
        RuntimeError: 필요한 테이블이 존재하지 않을 때
    """
    log.info("📊 Env 1분 테이블 확인 중...")
    
    with get_cursor() as cur:
        for device_id in ENV_DEVICES:
            table_name = f"env_data_{device_id}_1m"
            
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
def generate_dummy_data(device_id: int) -> dict:
    """
    Device별 더미 환경(온습도) 5초 데이터 생성
    
    현실적인 온습도 패턴을 시뮬레이션합니다.
    
    Args:
        device_id: Env 디바이스 ID (21-23)
    
    Returns:
        dict: 더미 온습도 데이터
              {
                  'device_id': int,
                  'timestamp': datetime,
                  'temperature_c': float,    # 온도 (섭씨)
                  'humidity_percent': float  # 습도 (%)
              }
    
    패턴:
        - 온도: 20-30°C (계절/시간대별 변동)
        - 습도: 40-80% (온도와 역상관 관계)
    """
    current_hour = datetime.now().hour
    
    # ========================================
    # 시간대별 온도 패턴
    # ========================================
    if 6 <= current_hour < 12:
        # 오전: 온도 상승
        base_temp = random.uniform(20, 24)
    elif 12 <= current_hour < 18:
        # 오후: 최고 온도
        base_temp = random.uniform(24, 28)
    elif 18 <= current_hour < 22:
        # 저녁: 온도 하강
        base_temp = random.uniform(22, 26)
    else:
        # 밤/새벽: 최저 온도
        base_temp = random.uniform(18, 22)
    
    # Device별 위치에 따른 온도 차이
    device_offset = {
        21: 0.0,   # Device 21: 기준
        22: 1.5,   # Device 22: +1.5°C (햇빛이 잘 드는 위치)
        23: -1.0   # Device 23: -1.0°C (그늘진 위치)
    }.get(device_id, 0.0)
    
    temperature = base_temp + device_offset + random.uniform(-0.5, 0.5)
    
    # ========================================
    # 습도 계산 (온도와 역상관)
    # 온도가 높으면 습도 낮음
    # ========================================
    # 기준 습도: 60%
    base_humidity = 60.0
    # 온도 1도 증가당 습도 2% 감소
    temp_effect = (temperature - 24.0) * -2.0
    humidity = base_humidity + temp_effect + random.uniform(-5, 5)
    
    # 습도 범위 제한 (30-90%)
    humidity = max(30.0, min(90.0, humidity))
    
    return {
        'device_id': device_id,
        'timestamp': datetime.now(timezone.utc),
        'temperature_c': round(temperature, 1),
        'humidity_percent': round(humidity, 1)
    }


# ========================================
# 5초 데이터 수집 (메모리 버퍼)
# ========================================
def collect_5s_data():
    """
    모든 Env 디바이스의 5초 데이터를 생성하고 메모리 버퍼에 저장
    
    동작:
        1. 각 device_id에 대해 더미 데이터 생성
        2. 메모리 버퍼에 추가 (DB 저장 안함)
        3. 실시간 API에서 이 버퍼를 읽어서 제공
    """
    for device_id in ENV_DEVICES:
        try:
            data = generate_dummy_data(device_id)
            data_buffer[device_id].append(data)
            
            log.debug(
                f"📥 Device {device_id} 버퍼 추가: "
                f"온도={data['temperature_c']:.1f}°C, "
                f"습도={data['humidity_percent']:.1f}%"
            )
            
        except Exception as e:
            log.error(f"❌ Device {device_id} 데이터 생성 실패: {e}")


# ========================================
# 1분마다 평균 계산 및 DB 저장
# ========================================
def flush_1m_aggregation():
    """
    1분마다 버퍼의 5초 데이터를 평균 계산하여 1분 테이블에 저장
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    for device_id in ENV_DEVICES:
        try:
            rows = data_buffer[device_id]
            if not rows:
                log.warning(f"  ⚠️  Device {device_id}: 버퍼 데이터 없음")
                continue
            
            # 집계 계산
            temps = [r['temperature_c'] for r in rows]
            humids = [r['humidity_percent'] for r in rows]
            
            avg_temp = statistics.mean(temps)
            max_temp = max(temps)
            min_temp = min(temps)
            avg_humid = statistics.mean(humids)
            max_humid = max(humids)
            min_humid = min(humids)
            count = len(rows)
            
            # ✅ 수정: device_id 추가!
            with get_cursor() as cur:
                cur.execute(f"""
                    INSERT INTO env_data_{device_id}_1m (
                        timestamp,
                        device_id,
                        avg_temperature_c,
                        max_temperature_c,
                        min_temperature_c,
                        avg_humidity_percent,
                        max_humidity_percent,
                        min_humidity_percent,
                        count
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    );
                """, (
                    now,
                    device_id,  # ✅ 추가!
                    avg_temp, max_temp, min_temp,
                    avg_humid, max_humid, min_humid, count
                ))
            
            log.info(
                f"  ✅ Device {device_id} 1분 집계 저장: "
                f"온도={avg_temp:.1f}°C({min_temp:.1f}-{max_temp:.1f}), "
                f"습도={avg_humid:.1f}%({min_humid:.1f}-{max_humid:.1f}), "
                f"samples={count}"
            )
            
        except Exception as e:
            log.error(f"  ❌ Device {device_id} 1분 집계 실패: {e}")
    
    # 버퍼 클리어
    data_buffer.clear()
    log.info("🧹 버퍼 클리어 완료\n")



# ========================================
# 메인 실행 루프
# ========================================
def run():
    """
    더미 Env 수집기 메인 루프
    
    동작:
        1. 테이블 존재 확인
        2. 5초마다 데이터 수집 (메모리 버퍼)
        3. 1분마다 집계 및 DB 저장
        4. Ctrl+C로 종료 시 정상 종료
    """
    log.info("=" * 60)
    log.info("🎭 더미 Env 수집기 시작 (신규 아키텍처)")
    log.info(f"   Devices: {ENV_DEVICES}")
    log.info(f"   수집 주기: {COLLECTION_INTERVAL}초")
    log.info(f"   집계 주기: 1분")
    log.info("=" * 60)
    
    # 테이블 확인
    ensure_tables()
    
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
        log.info("\n🛑 더미 Env 수집기 종료 (사용자 요청)")
    except Exception as e:
        log.exception(f"❌ 더미 Env 수집기 오류: {e}")
        raise


if __name__ == "__main__":
    """
    직접 실행 시 수집기 시작
    
    사용법:
        python -m src.collectors.dummy_env_collector
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run()

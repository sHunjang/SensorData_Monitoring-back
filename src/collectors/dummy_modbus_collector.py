"""
더미 Modbus 데이터 수집기 (2025-10-10 최종 버전)

bootstrap.py와 100% 동기화된 칼럼명 사용
- 3상 4선식 (14, 15): 중성선 포함
- 3상 3선식 (11, 12, 13): 중성선 없음

데이터 흐름:
  5초마다 더미 데이터 생성 → 메모리 버퍼 저장
  → 1분마다 평균 계산 → 1분 테이블 INSERT
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

log = logging.getLogger("dummy_modbus")

# ========================================
# 전역 변수
# ========================================

MODBUS_DEVICES = settings.MODBUS_3W_IDS + settings.MODBUS_4W_IDS  # [11-15]
COLLECTION_INTERVAL = 5  # 5초
AGGREGATION_INTERVAL = 60  # 1분

# 메모리 버퍼
data_buffer = defaultdict(list)

# 에너지 누적 (device별)
energy_accumulator = {}


# ========================================
# 더미 데이터 생성
# ========================================

def generate_dummy_data(device_id: int) -> dict:
    """
    더미 Modbus 데이터 생성
    
    Returns:
        dict: 센서 데이터 (키 이름은 flush_1m_aggregation과 일치!)
    """
    base_voltage = random.uniform(220, 240)
    base_current = random.uniform(10, 50)
    base_power = base_voltage * base_current * 1.732 / 1000  # kW
    
    # 에너지 누적 초기화
    if device_id not in energy_accumulator:
        energy_accumulator[device_id] = random.uniform(1000, 5000)
    
    # 에너지 증가
    energy_accumulator[device_id] += random.uniform(0.001, 0.01)
    
    # 기본 데이터 (모든 device 공통)
    data = {
        # 전압 (선간)
        'voltage_ab': base_voltage + random.uniform(-5, 5),
        'voltage_bc': base_voltage + random.uniform(-5, 5),
        'voltage_ca': base_voltage + random.uniform(-5, 5),
        
        # 전류 (선)
        'current_a': base_current + random.uniform(-2, 2),
        'current_b': base_current + random.uniform(-2, 2),
        'current_c': base_current + random.uniform(-2, 2),
        
        # 전력
        'total_active_power_kw': base_power + random.uniform(-5, 5),
        
        # 역률
        'total_power_factor': random.uniform(0.85, 0.95),
        
        # 주파수
        'frequency_hz': 60.0 + random.uniform(-0.1, 0.1),
        
        # 누적 전력량
        'total_active_energy_kwh': energy_accumulator[device_id],
        
        # 타임스탬프
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # ✅ 3상 4선식 (14, 15): 중성선 데이터 추가
    if device_id in settings.MODBUS_4W_IDS:
        data['current_n'] = random.uniform(0, 5)
        data['voltage_an'] = base_voltage + random.uniform(-3, 3)
        data['voltage_bn'] = base_voltage + random.uniform(-3, 3)
        data['voltage_cn'] = base_voltage + random.uniform(-3, 3)
    
    return data


# ========================================
# 1분 집계
# ========================================

def flush_1m_aggregation():
    """
    1분마다 버퍼의 5초 데이터를 평균 계산하여 1분 테이블에 저장
    
    ✅ bootstrap.py와 100% 동일한 칼럼명 사용!
    """
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    log.info(f"\n⏰ 1분 집계 시작: {now.isoformat()}")
    
    for device_id in MODBUS_DEVICES:
        try:
            rows = data_buffer[device_id]
            if not rows:
                log.warning(f"  ⚠️  Device {device_id}: 버퍼 데이터 없음")
                continue
            
            # 집계 계산
            avg_kw = statistics.mean(r['total_active_power_kw'] for r in rows)
            max_kw = max(r['total_active_power_kw'] for r in rows)
            min_kw = min(r['total_active_power_kw'] for r in rows)
            
            avg_current_l1 = statistics.mean(r['current_a'] for r in rows)
            avg_current_l2 = statistics.mean(r['current_b'] for r in rows)
            avg_current_l3 = statistics.mean(r['current_c'] for r in rows)
            
            avg_voltage_l1l2 = statistics.mean(r['voltage_ab'] for r in rows)
            avg_voltage_l2l3 = statistics.mean(r['voltage_bc'] for r in rows)
            avg_voltage_l3l1 = statistics.mean(r['voltage_ca'] for r in rows)
            
            avg_pf = statistics.mean(r['total_power_factor'] for r in rows)
            avg_freq = statistics.mean(r['frequency_hz'] for r in rows)
            total_kwh = rows[-1]['total_active_energy_kwh']
            count = len(rows)
            
            # ✅ 3상 4선식 (14, 15) - 중성선 포함
            if device_id in settings.MODBUS_4W_IDS:
                avg_current_n = statistics.mean(r['current_n'] for r in rows)
                avg_voltage_l1n = statistics.mean(r['voltage_an'] for r in rows)
                avg_voltage_l2n = statistics.mean(r['voltage_bn'] for r in rows)
                avg_voltage_l3n = statistics.mean(r['voltage_cn'] for r in rows)
                
                with get_cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO modbus_data_{device_id}_1m (
                            timestamp, device_id,
                            avg_power_kw, max_power_kw, min_power_kw,
                            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a, avg_current_n_a,
                            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
                            avg_voltage_l1n_v, avg_voltage_l2n_v, avg_voltage_l3n_v,
                            avg_power_factor, avg_frequency_hz,
                            total_active_energy_kwh,
                            count
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """, (
                        now, device_id,
                        avg_kw, max_kw, min_kw,
                        avg_current_l1, avg_current_l2, avg_current_l3, avg_current_n,
                        avg_voltage_l1l2, avg_voltage_l2l3, avg_voltage_l3l1,
                        avg_voltage_l1n, avg_voltage_l2n, avg_voltage_l3n,
                        avg_pf, avg_freq,
                        total_kwh,
                        count
                    ))
            
            # ✅ 3상 3선식 (11, 12, 13) - 중성선 없음
            else:
                with get_cursor() as cur:
                    cur.execute(f"""
                        INSERT INTO modbus_data_{device_id}_1m (
                            timestamp, device_id,
                            avg_power_kw, max_power_kw, min_power_kw,
                            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a,
                            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
                            avg_power_factor, avg_frequency_hz,
                            total_active_energy_kwh,
                            count
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """, (
                        now, device_id,
                        avg_kw, max_kw, min_kw,
                        avg_current_l1, avg_current_l2, avg_current_l3,
                        avg_voltage_l1l2, avg_voltage_l2l3, avg_voltage_l3l1,
                        avg_pf, avg_freq,
                        total_kwh,
                        count
                    ))
            
            log.info(
                f"  ✅ Device {device_id} 1분 집계 저장: "
                f"avg={avg_kw:.2f}kW, max={max_kw:.2f}kW, samples={count}"
            )
            
        except Exception as e:
            log.error(f"  ❌ Device {device_id} 1분 집계 실패: {e}")
    
    # 버퍼 클리어
    data_buffer.clear()
    log.info("🧹 버퍼 클리어 완료\n")


# ========================================
# 테이블 확인
# ========================================

def check_tables():
    """1분 테이블 존재 확인"""
    log.info("📊 Modbus 1분 테이블 확인 중...")
    
    try:
        with get_cursor() as cur:
            for device_id in MODBUS_DEVICES:
                table_name = f"modbus_data_{device_id}_1m"
                cur.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table_name}'
                    );
                """)
                exists = cur.fetchone()[0]
                
                if exists:
                    log.info(f"  ✅ {table_name} 존재")
                else:
                    log.error(f"  ❌ {table_name} 없음!")
                    
    except Exception as e:
        log.error(f"❌ 테이블 확인 실패: {e}")


# ========================================
# 데이터 수집 루프
# ========================================

def collection_loop():
    """
    5초마다 더미 데이터 생성 → 메모리 버퍼 저장
    """
    last_aggregation = time.time()
    
    while True:
        try:
            # 5초마다 데이터 생성
            for device_id in MODBUS_DEVICES:
                try:
                    data = generate_dummy_data(device_id)
                    data_buffer[device_id].append(data)
                except Exception as e:
                    log.error(f"❌ Device {device_id} 데이터 생성 실패: {e}")
            
            # 1분마다 집계
            now = time.time()
            if now - last_aggregation >= AGGREGATION_INTERVAL:
                flush_1m_aggregation()
                last_aggregation = now
            
            # 5초 대기
            time.sleep(COLLECTION_INTERVAL)
            
        except KeyboardInterrupt:
            log.info("\n🛑 더미 Modbus 수집기 종료 (사용자 요청)")
            break
        except Exception as e:
            log.error(f"❌ 수집 루프 에러: {e}")
            time.sleep(5)


# ========================================
# 메모리 버퍼 API (FastAPI용)
# ========================================

def get_latest_data(device_id: int) -> dict:
    """
    실시간 API용: 메모리 버퍼에서 최신 데이터 반환
    
    Args:
        device_id: Modbus device ID
        
    Returns:
        dict: 최신 센서 데이터 (없으면 빈 dict)
    """
    rows = data_buffer.get(device_id, [])
    if rows:
        return rows[-1]
    return {}


def get_buffer_data(device_id: int, limit: int = 12) -> List[dict]:
    """
    실시간 API용: 메모리 버퍼에서 최근 N개 데이터 반환
    
    Args:
        device_id: Modbus device ID
        limit: 반환할 데이터 개수 (기본 12개 = 최근 1분)
        
    Returns:
        List[dict]: 최근 센서 데이터 리스트
    """
    rows = data_buffer.get(device_id, [])
    return rows[-limit:] if rows else []


# ========================================
# 메인 실행
# ========================================

def run():
    """더미 Modbus 수집기 시작"""
    log.info("=" * 60)
    log.info("🎭 더미 Modbus 수집기 시작 (신규 아키텍처)")
    log.info(f"   Devices: {MODBUS_DEVICES}")
    log.info(f"   3상 4선: {settings.MODBUS_4W_IDS}")
    log.info(f"   3상 3선: {settings.MODBUS_3W_IDS}")
    log.info(f"   수집 주기: {COLLECTION_INTERVAL}초")
    log.info(f"   집계 주기: {AGGREGATION_INTERVAL//60}분")
    log.info("=" * 60)
    
    # 테이블 확인
    check_tables()
    
    # 수집 시작
    collection_loop()


if __name__ == "__main__":
    """
    직접 실행 시 테스트
    
    Usage:
        python -m src.collectors.dummy_modbus_collector
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    run()

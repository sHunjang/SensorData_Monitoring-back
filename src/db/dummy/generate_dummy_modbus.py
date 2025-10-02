"""
Modbus 전력량계 더미 데이터 생성기 (Device 11-15)

생성 대상:
  - modbus_data_11 ~ modbus_data_15
  - 5초 간격, 지정 기간만큼 생성

사용법:
    python -m src.db.generate_dummy_modbus --days 7
    python -m src.db.generate_dummy_modbus --days 30
"""

import os
import sys
import logging
import random
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트 추가
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.db.client import get_cursor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("dummy_modbus")

# ============================================================================
# 설정
# ============================================================================
DEVICE_IDS = [11, 12, 13, 14, 15]
INTERVAL_SECONDS = 5

# ============================================================================
# 더미 데이터 생성
# ============================================================================

def generate_modbus_row(device_id: int, timestamp: datetime) -> dict:
    """
    Modbus 전력 데이터 1개 행 생성
    
    Args:
        device_id: 장치 ID (11-15)
        timestamp: 타임스탬프 (UTC)
    
    Returns:
        dict: 컬럼명-값 매핑
    """
    # 3상 (11,12,13) vs 4상 (14,15) 구분
    is_3phase = device_id in [11, 12, 13]
    
    # 전압
    if is_3phase:
        voltage_ll = round(random.uniform(200, 240), 2)
        voltage_ln = None
    else:
        voltage_ll = None
        voltage_ln = round(random.uniform(110, 140), 2)
    
    # 전류 (5~50A)
    current = round(random.uniform(5, 50), 2)
    
    # 유효전력 (1~30kW)
    active_power = round(random.uniform(1, 30), 3)
    
    # 무효전력 (0~10kVAr)
    reactive_power = round(random.uniform(0, 10), 3)
    
    # 피상전력
    apparent_power = round((active_power**2 + reactive_power**2)**0.5, 3)
    
    # 역률 (0.7~0.99)
    power_factor = round(random.uniform(0.7, 0.99), 3)
    
    # 에너지 누적값 (시간 기반 증가)
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    elapsed_hours = (timestamp - base_time).total_seconds() / 3600
    energy = round(elapsed_hours * active_power * random.uniform(0.8, 1.2), 2)
    
    return {
        'time_stamp': timestamp,
        'avg_line_to_line_volts_v': voltage_ll,
        'avg_line_to_neutral_volts_v': voltage_ln,
        'sum_line_currents_a': current,
        'total_active_power_kw': active_power,
        'total_reactive_power_kvar': reactive_power,
        'total_apparent_power_kva': apparent_power,
        'total_power_factor': power_factor,
        'total_active_energy_kwh': energy,
    }


# ============================================================================
# 배치 INSERT
# ============================================================================

def batch_insert(device_id: int, rows: list):
    """
    배치 INSERT (1000건씩)
    
    Args:
        device_id: 장치 ID
        rows: 삽입할 데이터 리스트
    """
    if not rows:
        return
    
    table_name = f'modbus_data_{device_id}'
    
    sql = f"""
    INSERT INTO {table_name} (
        time_stamp,
        avg_line_to_line_volts_v,
        avg_line_to_neutral_volts_v,
        sum_line_currents_a,
        total_active_power_kw,
        total_reactive_power_kvar,
        total_apparent_power_kva,
        total_power_factor,
        total_active_energy_kwh
    ) VALUES %s
    ON CONFLICT (time_stamp) DO NOTHING
    """
    
    values = [
        (
            r['time_stamp'],
            r['avg_line_to_line_volts_v'],
            r['avg_line_to_neutral_volts_v'],
            r['sum_line_currents_a'],
            r['total_active_power_kw'],
            r['total_reactive_power_kvar'],
            r['total_apparent_power_kva'],
            r['total_power_factor'],
            r['total_active_energy_kwh']
        )
        for r in rows
    ]
    
    try:
        with get_cursor() as cur:
            from psycopg2.extras import execute_values
            execute_values(cur, sql, values, page_size=1000)
        log.info(f"Device {device_id}: {len(rows)} rows inserted")
    except Exception as e:
        log.error(f"Device {device_id} insert failed: {e}")


# ============================================================================
# 메인 생성 로직
# ============================================================================

def generate_data(days: int = 7):
    """
    Modbus 더미 데이터 생성
    
    Args:
        days: 생성할 과거 일수 (기본 7일)
    """
    # 시간 범위 계산
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    log.info("=" * 70)
    log.info("Modbus Dummy Data Generator")
    log.info("=" * 70)
    log.info(f"Period: {start_time} ~ {end_time}")
    log.info(f"Interval: {INTERVAL_SECONDS} seconds")
    log.info(f"Devices: {DEVICE_IDS}")
    
    # 총 샘플 개수
    total_seconds = int((end_time - start_time).total_seconds())
    total_samples = total_seconds // INTERVAL_SECONDS
    log.info(f"Samples per device: {total_samples:,}")
    log.info(f"Total rows: {total_samples * len(DEVICE_IDS):,}")
    
    # 확인
    response = input("\nContinue? (y/N): ")
    if response.lower() != 'y':
        log.info("Cancelled")
        return
    
    # 각 장치별 생성
    batch_size = 1000
    
    for device_id in DEVICE_IDS:
        log.info(f"\n[Device {device_id}] Generating...")
        
        batch = []
        current_time = start_time
        
        for i in range(total_samples):
            row = generate_modbus_row(device_id, current_time)
            batch.append(row)
            
            # 배치 INSERT
            if len(batch) >= batch_size:
                batch_insert(device_id, batch)
                batch = []
            
            current_time += timedelta(seconds=INTERVAL_SECONDS)
            
            # 진행률 표시
            if (i + 1) % 10000 == 0:
                progress = (i + 1) / total_samples * 100
                log.info(f"  Progress: {progress:.1f}% ({i+1:,}/{total_samples:,})")
        
        # 남은 데이터 INSERT
        if batch:
            batch_insert(device_id, batch)
        
        log.info(f"[Device {device_id}] Complete!")
    
    log.info("\n" + "=" * 70)
    log.info("All Modbus data generation complete!")
    log.info("=" * 70)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Modbus Dummy Data Generator (Device 11-15)"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to generate (default: 7)'
    )
    
    args = parser.parse_args()
    
    # 경고
    total_samples = (args.days * 24 * 3600) // INTERVAL_SECONDS
    total_rows = total_samples * len(DEVICE_IDS)
    
    print(f"\nWarning: Will generate {total_rows:,} rows")
    print(f"Estimated time: {total_rows // 10000} ~ {total_rows // 5000} minutes\n")
    
    generate_data(days=args.days)


if __name__ == '__main__':
    main()

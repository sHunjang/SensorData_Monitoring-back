"""
Env 온습도 더미 데이터 생성기 (Device 21-23)

생성 대상:
  - env_data_21 ~ env_data_23
  - 5초 간격, 지정 기간만큼 생성

사용법:
    python -m src.db.generate_dummy_env --days 7
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
log = logging.getLogger("dummy_env")

# ============================================================================
# 설정
# ============================================================================
DEVICE_IDS = [21, 22, 23]
INTERVAL_SECONDS = 5

# ============================================================================
# 더미 데이터 생성
# ============================================================================

def generate_env_row(device_id: int, timestamp: datetime) -> dict:
    """
    온습도 데이터 1개 행 생성
    
    Args:
        device_id: 장치 ID (21-23)
        timestamp: 타임스탬프 (UTC)
    
    Returns:
        dict: 컬럼명-값 매핑
    """
    # UTC를 KST로 변환
    kst_hour = (timestamp.hour + 9) % 24
    
    # 시간대별 온도 변화
    base_temp = 25.0
    if 6 <= kst_hour < 18:
        temp_offset = random.uniform(0, 10)  # 낮: 25~35℃
    else:
        temp_offset = random.uniform(-10, 0)  # 밤: 15~25℃
    
    temperature = round(base_temp + temp_offset, 2)
    humidity = round(random.uniform(30, 80), 2)
    
    return {
        'time_stamp': timestamp,
        'temperature': temperature,
        'humidity': humidity,
    }


# ============================================================================
# 배치 INSERT
# ============================================================================

def batch_insert(device_id: int, rows: list):
    """
    배치 INSERT (1000건씩)
    """
    if not rows:
        return
    
    table_name = f'env_data_{device_id}'
    
    sql = f"""
    INSERT INTO {table_name} (time_stamp, temperature, humidity)
    VALUES %s
    ON CONFLICT (time_stamp) DO NOTHING
    """
    
    values = [
        (r['time_stamp'], r['temperature'], r['humidity'])
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
    Env 더미 데이터 생성
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    log.info("=" * 70)
    log.info("Env Dummy Data Generator")
    log.info("=" * 70)
    log.info(f"Period: {start_time} ~ {end_time}")
    log.info(f"Interval: {INTERVAL_SECONDS} seconds")
    log.info(f"Devices: {DEVICE_IDS}")
    
    total_seconds = int((end_time - start_time).total_seconds())
    total_samples = total_seconds // INTERVAL_SECONDS
    log.info(f"Samples per device: {total_samples:,}")
    log.info(f"Total rows: {total_samples * len(DEVICE_IDS):,}")
    
    response = input("\nContinue? (y/N): ")
    if response.lower() != 'y':
        log.info("Cancelled")
        return
    
    batch_size = 1000
    
    for device_id in DEVICE_IDS:
        log.info(f"\n[Device {device_id}] Generating...")
        
        batch = []
        current_time = start_time
        
        for i in range(total_samples):
            row = generate_env_row(device_id, current_time)
            batch.append(row)
            
            if len(batch) >= batch_size:
                batch_insert(device_id, batch)
                batch = []
            
            current_time += timedelta(seconds=INTERVAL_SECONDS)
            
            if (i + 1) % 10000 == 0:
                progress = (i + 1) / total_samples * 100
                log.info(f"  Progress: {progress:.1f}% ({i+1:,}/{total_samples:,})")
        
        if batch:
            batch_insert(device_id, batch)
        
        log.info(f"[Device {device_id}] Complete!")
    
    log.info("\n" + "=" * 70)
    log.info("All Env data generation complete!")
    log.info("=" * 70)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Env Dummy Data Generator (Device 21-23)"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to generate (default: 7)'
    )
    
    args = parser.parse_args()
    
    total_samples = (args.days * 24 * 3600) // INTERVAL_SECONDS
    total_rows = total_samples * len(DEVICE_IDS)
    
    print(f"\nWarning: Will generate {total_rows:,} rows")
    print(f"Estimated time: {total_rows // 10000} ~ {total_rows // 5000} minutes\n")
    
    generate_data(days=args.days)


if __name__ == '__main__':
    main()

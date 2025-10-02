"""
Solar 일사량 더미 데이터 생성기 (Device 31)

생성 대상:
  - solar_data
  - 5초 간격, 지정 기간만큼 생성

사용법:
    python -m src.db.generate_dummy_solar --days 7
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
log = logging.getLogger("dummy_solar")

# ============================================================================
# 설정
# ============================================================================
INTERVAL_SECONDS = 5

# ============================================================================
# 더미 데이터 생성
# ============================================================================

def generate_solar_row(timestamp: datetime) -> dict:
    """
    일사량 데이터 1개 행 생성
    
    Args:
        timestamp: 타임스탬프 (UTC)
    
    Returns:
        dict: 컬럼명-값 매핑
    """
    # UTC를 KST로 변환
    kst_hour = (timestamp.hour + 9) % 24
    
    # 일출 6시, 일몰 18시 가정
    if 6 <= kst_hour < 18:
        # 정오(12시)에 최대값
        peak_hour = 12
        distance = abs(kst_hour - peak_hour)
        max_irradiance = 1200 - (distance * 100)
        irradiance = round(random.uniform(max_irradiance * 0.7, max_irradiance), 2)
    else:
        irradiance = 0.0
    
    return {
        'time_stamp': timestamp,
        'irradiance': irradiance,
    }


# ============================================================================
# 배치 INSERT
# ============================================================================

def batch_insert(rows: list):
    """
    배치 INSERT (1000건씩)
    """
    if not rows:
        return
    
    sql = """
    INSERT INTO solar_data (time_stamp, irradiance)
    VALUES %s
    ON CONFLICT (time_stamp) DO NOTHING
    """
    
    values = [
        (r['time_stamp'], r['irradiance'])
        for r in rows
    ]
    
    try:
        with get_cursor() as cur:
            from psycopg2.extras import execute_values
            execute_values(cur, sql, values, page_size=1000)
        log.info(f"{len(rows)} rows inserted")
    except Exception as e:
        log.error(f"Insert failed: {e}")


# ============================================================================
# 메인 생성 로직
# ============================================================================

def generate_data(days: int = 7):
    """
    Solar 더미 데이터 생성
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    log.info("=" * 70)
    log.info("Solar Dummy Data Generator")
    log.info("=" * 70)
    log.info(f"Period: {start_time} ~ {end_time}")
    log.info(f"Interval: {INTERVAL_SECONDS} seconds")
    
    total_seconds = int((end_time - start_time).total_seconds())
    total_samples = total_seconds // INTERVAL_SECONDS
    log.info(f"Total samples: {total_samples:,}")
    
    response = input("\nContinue? (y/N): ")
    if response.lower() != 'y':
        log.info("Cancelled")
        return
    
    batch_size = 1000
    batch = []
    current_time = start_time
    
    log.info("\nGenerating...")
    
    for i in range(total_samples):
        row = generate_solar_row(current_time)
        batch.append(row)
        
        if len(batch) >= batch_size:
            batch_insert(batch)
            batch = []
        
        current_time += timedelta(seconds=INTERVAL_SECONDS)
        
        if (i + 1) % 10000 == 0:
            progress = (i + 1) / total_samples * 100
            log.info(f"Progress: {progress:.1f}% ({i+1:,}/{total_samples:,})")
    
    if batch:
        batch_insert(batch)
    
    log.info("\n" + "=" * 70)
    log.info("Solar data generation complete!")
    log.info("=" * 70)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Solar Dummy Data Generator (Device 31)"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to generate (default: 7)'
    )
    
    args = parser.parse_args()
    
    total_samples = (args.days * 24 * 3600) // INTERVAL_SECONDS
    
    print(f"\nWarning: Will generate {total_samples:,} rows")
    print(f"Estimated time: {total_samples // 10000} ~ {total_samples // 5000} minutes\n")
    
    generate_data(days=args.days)


if __name__ == '__main__':
    main()

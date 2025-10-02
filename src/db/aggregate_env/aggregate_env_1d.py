"""
Env 1-Day 집계 스크립트 (Device 21-23)

실행:
  python src/db/aggregate_env/aggregate_env_1d.py --days 7
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.db.client import get_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("agg_env_1d")

DEVICE_IDS = [21, 22, 23]

def get_aggregate_sql(device_id: int, start_time: datetime, end_time: datetime) -> str:
    return f"""
    INSERT INTO agg_env_{device_id}_1d (
        bucket, avg_temperature, max_temperature, min_temperature,
        avg_humidity, max_humidity, min_humidity, sample_count
    )
    SELECT
        time_bucket('1 day', bucket) AS bucket_1d,
        AVG(avg_temperature),
        MAX(max_temperature),
        MIN(min_temperature),
        AVG(avg_humidity),
        MAX(max_humidity),
        MIN(min_humidity),
        SUM(sample_count) AS sample_count
    FROM agg_env_{device_id}_1h
    WHERE bucket >= %s AND bucket < %s
    GROUP BY bucket_1d
    ON CONFLICT (bucket) DO UPDATE SET
        avg_temperature = EXCLUDED.avg_temperature,
        max_temperature = EXCLUDED.max_temperature,
        min_temperature = EXCLUDED.min_temperature,
        avg_humidity = EXCLUDED.avg_humidity,
        max_humidity = EXCLUDED.max_humidity,
        min_humidity = EXCLUDED.min_humidity,
        sample_count = EXCLUDED.sample_count;
    """

def aggregate_device(device_id: int, start_time: datetime, end_time: datetime) -> int:
    sql = get_aggregate_sql(device_id, start_time, end_time)
    try:
        with get_cursor() as cur:
            cur.execute(sql, (start_time, end_time))
            row_count = cur.rowcount
        log.info(f"Device {device_id}: {row_count} rows aggregated")
        return row_count
    except Exception as e:
        log.error(f"Device {device_id} aggregation failed: {e}")
        return 0

def aggregate_all(days: int = 7):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    log.info("=" * 70)
    log.info("Env 1-Day Aggregation")
    log.info("=" * 70)
    log.info(f"Period: {start_time} ~ {end_time}")
    log.info(f"Devices: {DEVICE_IDS}")
    log.info("")
    
    total_rows = 0
    for device_id in DEVICE_IDS:
        rows = aggregate_device(device_id, start_time, end_time)
        total_rows += rows
    
    log.info("")
    log.info("=" * 70)
    log.info(f"Total aggregated: {total_rows} rows")
    log.info("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Env 1-Day Aggregation")
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()
    aggregate_all(days=args.days)

if __name__ == '__main__':
    main()

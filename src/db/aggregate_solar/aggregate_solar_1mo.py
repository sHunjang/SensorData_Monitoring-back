"""
Solar 1-Month 집계 스크립트 (Device 31)

실행:
  python src/db/aggregate_solar/aggregate_solar_1mo.py --months 6
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
log = logging.getLogger("agg_solar_1mo")

def get_aggregate_sql(start_time: datetime, end_time: datetime) -> str:
    return f"""
    INSERT INTO agg_solar_1mo (
        bucket, avg_irradiance, max_irradiance, min_irradiance, sample_count
    )
    SELECT
        time_bucket('1 month', bucket) AS bucket_1mo,
        AVG(avg_irradiance),
        MAX(max_irradiance),
        MIN(min_irradiance),
        SUM(sample_count) AS sample_count
    FROM agg_solar_1d
    WHERE bucket >= %s AND bucket < %s
    GROUP BY bucket_1mo
    ON CONFLICT (bucket) DO UPDATE SET
        avg_irradiance = EXCLUDED.avg_irradiance,
        max_irradiance = EXCLUDED.max_irradiance,
        min_irradiance = EXCLUDED.min_irradiance,
        sample_count = EXCLUDED.sample_count;
    """

def aggregate(start_time: datetime, end_time: datetime) -> int:
    sql = get_aggregate_sql(start_time, end_time)
    try:
        with get_cursor() as cur:
            cur.execute(sql, (start_time, end_time))
            row_count = cur.rowcount
        log.info(f"Solar: {row_count} rows aggregated")
        return row_count
    except Exception as e:
        log.error(f"Solar aggregation failed: {e}")
        return 0

def aggregate_all(months: int = 6):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=months * 30)
    
    log.info("=" * 70)
    log.info("Solar 1-Month Aggregation")
    log.info("=" * 70)
    log.info(f"Period: {start_time} ~ {end_time}")
    log.info("")
    
    rows = aggregate(start_time, end_time)
    
    log.info("")
    log.info("=" * 70)
    log.info(f"Total aggregated: {rows} rows")
    log.info("=" * 70)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Solar 1-Month Aggregation")
    parser.add_argument('--months', type=int, default=6)
    args = parser.parse_args()
    aggregate_all(months=args.months)

if __name__ == '__main__':
    main()

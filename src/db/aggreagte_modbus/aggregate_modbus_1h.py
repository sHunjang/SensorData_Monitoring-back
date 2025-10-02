"""
Modbus 1시간 집계 스크립트 (Device 11-15)

목적:
  - agg_modbus_11~15_15m (15분 집계) → agg_modbus_11~15_1h (1시간 집계)
  
실행:
  python src/db/aggreagte_modbus/aggregate_modbus_1h.py --hours 168
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 프로젝트 루트 추가
if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.db.client import get_cursor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
log = logging.getLogger("agg_modbus_1h")

# ============================================================================
# 설정
# ============================================================================
DEVICE_IDS = [11, 12, 13, 14, 15]

# ============================================================================
# 집계 SQL
# ============================================================================

def get_aggregate_sql(device_id: int, start_time: datetime, end_time: datetime) -> str:
    """1시간 집계 SQL 생성"""
    return f"""
    INSERT INTO agg_modbus_{device_id}_1h (
        bucket,
        avg_avg_line_to_line_volts_v,
        max_avg_line_to_line_volts_v,
        min_avg_line_to_line_volts_v,
        avg_avg_line_to_neutral_volts_v,
        max_avg_line_to_neutral_volts_v,
        min_avg_line_to_neutral_volts_v,
        avg_sum_line_currents_a,
        max_sum_line_currents_a,
        min_sum_line_currents_a,
        avg_total_active_power_kw,
        max_total_active_power_kw,
        min_total_active_power_kw,
        sum_total_active_power_kw,
        avg_total_reactive_power_kvar,
        avg_total_apparent_power_kva,
        avg_total_power_factor,
        min_total_power_factor,
        min_total_active_energy_kwh,
        max_total_active_energy_kwh,
        delta_total_active_energy_kwh,
        sample_count
    )
    SELECT
        time_bucket('1 hour', bucket) AS bucket_1h,
        AVG(avg_avg_line_to_line_volts_v),
        MAX(max_avg_line_to_line_volts_v),
        MIN(min_avg_line_to_line_volts_v),
        AVG(avg_avg_line_to_neutral_volts_v),
        MAX(max_avg_line_to_neutral_volts_v),
        MIN(min_avg_line_to_neutral_volts_v),
        AVG(avg_sum_line_currents_a),
        MAX(max_sum_line_currents_a),
        MIN(min_sum_line_currents_a),
        AVG(avg_total_active_power_kw),
        MAX(max_total_active_power_kw),
        MIN(min_total_active_power_kw),
        SUM(sum_total_active_power_kw),
        AVG(avg_total_reactive_power_kvar),
        AVG(avg_total_apparent_power_kva),
        AVG(avg_total_power_factor),
        MIN(min_total_power_factor),
        MIN(min_total_active_energy_kwh),
        MAX(max_total_active_energy_kwh),
        MAX(max_total_active_energy_kwh) - MIN(min_total_active_energy_kwh) AS delta_energy,
        SUM(sample_count) AS sample_count
    FROM agg_modbus_{device_id}_15m
    WHERE bucket >= %s
      AND bucket < %s
    GROUP BY bucket_1h
    ON CONFLICT (bucket) DO UPDATE SET
        avg_avg_line_to_line_volts_v = EXCLUDED.avg_avg_line_to_line_volts_v,
        max_avg_line_to_line_volts_v = EXCLUDED.max_avg_line_to_line_volts_v,
        min_avg_line_to_line_volts_v = EXCLUDED.min_avg_line_to_line_volts_v,
        avg_avg_line_to_neutral_volts_v = EXCLUDED.avg_avg_line_to_neutral_volts_v,
        max_avg_line_to_neutral_volts_v = EXCLUDED.max_avg_line_to_neutral_volts_v,
        min_avg_line_to_neutral_volts_v = EXCLUDED.min_avg_line_to_neutral_volts_v,
        avg_sum_line_currents_a = EXCLUDED.avg_sum_line_currents_a,
        max_sum_line_currents_a = EXCLUDED.max_sum_line_currents_a,
        min_sum_line_currents_a = EXCLUDED.min_sum_line_currents_a,
        avg_total_active_power_kw = EXCLUDED.avg_total_active_power_kw,
        max_total_active_power_kw = EXCLUDED.max_total_active_power_kw,
        min_total_active_power_kw = EXCLUDED.min_total_active_power_kw,
        sum_total_active_power_kw = EXCLUDED.sum_total_active_power_kw,
        avg_total_reactive_power_kvar = EXCLUDED.avg_total_reactive_power_kvar,
        avg_total_apparent_power_kva = EXCLUDED.avg_total_apparent_power_kva,
        avg_total_power_factor = EXCLUDED.avg_total_power_factor,
        min_total_power_factor = EXCLUDED.min_total_power_factor,
        min_total_active_energy_kwh = EXCLUDED.min_total_active_energy_kwh,
        max_total_active_energy_kwh = EXCLUDED.max_total_active_energy_kwh,
        delta_total_active_energy_kwh = EXCLUDED.delta_total_active_energy_kwh,
        sample_count = EXCLUDED.sample_count;
    """

def aggregate_device(device_id: int, start_time: datetime, end_time: datetime) -> int:
    """특정 장치의 1시간 집계 실행"""
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

def aggregate_all(hours: int = 24):
    """모든 장치의 1시간 집계 실행"""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    log.info("=" * 70)
    log.info("Modbus 1-Hour Aggregation")
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
    parser = argparse.ArgumentParser(description="Modbus 1-Hour Aggregation")
    parser.add_argument('--hours', type=int, default=24, help='Hours to aggregate')
    args = parser.parse_args()
    aggregate_all(hours=args.hours)

if __name__ == '__main__':
    main()

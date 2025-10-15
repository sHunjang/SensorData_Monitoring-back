"""
기존 원시 데이터를 집계 테이블로 마이그레이션하는 스크립트

사용법:
    # 전체 데이터 마이그레이션
    python -m src.db.migrate_historical_data
    
    # 특정 기간만 마이그레이션
    python -m src.db.migrate_historical_data --start "2025-10-01" --end "2025-10-15"
    
    # 특정 센서만 마이그레이션
    python -m src.db.migrate_historical_data --sensor modbus
    python -m src.db.migrate_historical_data --sensor env
    python -m src.db.migrate_historical_data --sensor solar
"""

import logging
import argparse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from src.db.client import get_cursor
from src.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("migrate")

KST = ZoneInfo("Asia/Seoul")


def migrate_modbus_4wire(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    Modbus 3상 4선 데이터 마이그레이션 (ID: 11, 12, 13)
    
    흐름:
    1. modbus_data → modbus_4wire_1min
    2. modbus_4wire_1min → modbus_4wire_15min
    3. modbus_4wire_15min → modbus_4wire_1hour
    4. modbus_4wire_1hour → modbus_4wire_1day
    """
    log.info("=" * 70)
    log.info("📊 Modbus 3상 4선 데이터 마이그레이션 시작...")
    log.info("=" * 70)
    
    device_ids = settings.MODBUS_4W_IDS  # [11, 12, 13]
    
    # WHERE 절 생성
    where_clause = ""
    params = []
    
    if start_date or end_date:
        conditions = []
        if start_date:
            conditions.append("time_stamp >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("time_stamp < %s")
            params.append(end_date)
        where_clause = " AND " + " AND ".join(conditions)
    
    with get_cursor() as cur:
        # Step 1: 원본 → 1분 집계
        log.info("📌 Step 1: modbus_data → modbus_4wire_1min")
        sql = f"""
            INSERT INTO modbus_4wire_1min (
                bucket, device_id,
                avg_voltage_ll_v, min_voltage_ll_v, max_voltage_ll_v,
                avg_current_a, min_current_a, max_current_a,
                avg_active_power_kw, avg_reactive_power_kvar,
                avg_apparent_power_kva, avg_power_factor,
                energy_start_kwh, energy_end_kwh, energy_delta_kwh, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket,
                device_id,
                AVG(avg_line_to_line_volts_v),
                MIN(avg_line_to_line_volts_v),
                MAX(avg_line_to_line_volts_v),
                AVG(sum_line_currents_a),
                MIN(sum_line_currents_a),
                MAX(sum_line_currents_a),
                AVG(total_active_power_kw),
                AVG(total_reactive_power_kvar),
                AVG(total_apparent_power_kva),
                AVG(total_power_factor),
                MIN(total_active_energy_kwh),
                MAX(total_active_energy_kwh),
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh),
                COUNT(*)
            FROM modbus_data
            WHERE device_id IN %s{where_clause}
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        count_1min = cur.rowcount
        log.info(f"   ✅ {count_1min} rows → modbus_4wire_1min")
        
        # Step 2: 1분 → 15분 집계
        log.info("📌 Step 2: modbus_4wire_1min → modbus_4wire_15min")
        sql = f"""
            INSERT INTO modbus_4wire_15min (
                bucket, device_id,
                energy_start_kwh, energy_end_kwh, energy_delta_kwh,
                peak_power_kw, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id,
                MIN(energy_start_kwh),
                MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(avg_active_power_kw),
                SUM(data_points)
            FROM modbus_4wire_1min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY 
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15),
                device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        count_15min = cur.rowcount
        log.info(f"   ✅ {count_15min} rows → modbus_4wire_15min")
        
        # Step 3: 15분 → 1시간 집계
        log.info("📌 Step 3: modbus_4wire_15min → modbus_4wire_1hour")
        sql = f"""
            INSERT INTO modbus_4wire_1hour (
                bucket, device_id,
                energy_start_kwh, energy_end_kwh, energy_delta_kwh,
                peak_power_kw, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket,
                device_id,
                MIN(energy_start_kwh),
                MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(peak_power_kw),
                SUM(data_points)
            FROM modbus_4wire_15min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        count_1hour = cur.rowcount
        log.info(f"   ✅ {count_1hour} rows → modbus_4wire_1hour")
        
        # Step 4: 1시간 → 1일 집계
        log.info("📌 Step 4: modbus_4wire_1hour → modbus_4wire_1day")
        sql = f"""
            INSERT INTO modbus_4wire_1day (
                bucket, device_id,
                energy_start_kwh, energy_end_kwh, energy_delta_kwh,
                peak_power_kw, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket,
                device_id,
                MIN(energy_start_kwh),
                MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(peak_power_kw),
                SUM(data_points)
            FROM modbus_4wire_1hour
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        count_1day = cur.rowcount
        log.info(f"   ✅ {count_1day} rows → modbus_4wire_1day")
    
    log.info("✅ Modbus 4-wire 마이그레이션 완료")


def migrate_modbus_3wire(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """Modbus 3상 3선 데이터 마이그레이션 (ID: 14, 15)"""
    log.info("=" * 70)
    log.info("📊 Modbus 3상 3선 데이터 마이그레이션 시작...")
    log.info("=" * 70)
    
    device_ids = settings.MODBUS_3W_IDS  # [14, 15]
    
    where_clause = ""
    params = []
    
    if start_date or end_date:
        conditions = []
        if start_date:
            conditions.append("time_stamp >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("time_stamp < %s")
            params.append(end_date)
        where_clause = " AND " + " AND ".join(conditions)
    
    with get_cursor() as cur:
        # Step 1: 원본 → 1분 집계
        log.info("📌 Step 1: modbus_data → modbus_3wire_1min")
        sql = f"""
            INSERT INTO modbus_3wire_1min (
                bucket, device_id,
                avg_voltage_ln_v, min_voltage_ln_v, max_voltage_ln_v,
                avg_current_a, min_current_a, max_current_a,
                avg_active_power_kw, avg_reactive_power_kvar,
                avg_apparent_power_kva, avg_power_factor,
                energy_start_kwh, energy_end_kwh, energy_delta_kwh, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket,
                device_id,
                AVG(avg_line_to_neutral_volts_v),
                MIN(avg_line_to_neutral_volts_v),
                MAX(avg_line_to_neutral_volts_v),
                AVG(sum_line_currents_a),
                MIN(sum_line_currents_a),
                MAX(sum_line_currents_a),
                AVG(total_active_power_kw),
                AVG(total_reactive_power_kvar),
                AVG(total_apparent_power_kva),
                AVG(total_power_factor),
                MIN(total_active_energy_kwh),
                MAX(total_active_energy_kwh),
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh),
                COUNT(*)
            FROM modbus_data
            WHERE device_id IN %s{where_clause}
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        count_1min = cur.rowcount
        log.info(f"   ✅ {count_1min} rows → modbus_3wire_1min")
        
        # Step 2-4: 동일한 패턴으로 15분/1시간/1일 집계 (4선과 동일한 로직)
        # (코드 생략 - 위 4선과 동일하게 작성, 테이블명만 3wire로 변경)
        
        # 15분 집계
        log.info("📌 Step 2: modbus_3wire_1min → modbus_3wire_15min")
        sql = f"""
            INSERT INTO modbus_3wire_15min (
                bucket, device_id, energy_start_kwh, energy_end_kwh, 
                energy_delta_kwh, peak_power_kw, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id, MIN(energy_start_kwh), MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(avg_active_power_kw), SUM(data_points)
            FROM modbus_3wire_1min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → modbus_3wire_15min")
        
        # 1시간 집계
        log.info("📌 Step 3: modbus_3wire_15min → modbus_3wire_1hour")
        sql = f"""
            INSERT INTO modbus_3wire_1hour (
                bucket, device_id, energy_start_kwh, energy_end_kwh, 
                energy_delta_kwh, peak_power_kw, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket, device_id,
                MIN(energy_start_kwh), MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(peak_power_kw), SUM(data_points)
            FROM modbus_3wire_15min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → modbus_3wire_1hour")
        
        # 1일 집계
        log.info("📌 Step 4: modbus_3wire_1hour → modbus_3wire_1day")
        sql = f"""
            INSERT INTO modbus_3wire_1day (
                bucket, device_id, energy_start_kwh, energy_end_kwh, 
                energy_delta_kwh, peak_power_kw, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket, device_id,
                MIN(energy_start_kwh), MAX(energy_end_kwh),
                MAX(energy_end_kwh) - MIN(energy_start_kwh),
                MAX(peak_power_kw), SUM(data_points)
            FROM modbus_3wire_1hour
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → modbus_3wire_1day")
    
    log.info("✅ Modbus 3-wire 마이그레이션 완료")


def migrate_env(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """환경센서 데이터 마이그레이션 (ID: 21, 22, 23)"""
    log.info("=" * 70)
    log.info("🌿 환경센서 데이터 마이그레이션 시작...")
    log.info("=" * 70)
    
    device_ids = settings.ENV_DEVICE_IDS  # [21, 22, 23]
    
    where_clause = ""
    params = []
    
    if start_date or end_date:
        conditions = []
        if start_date:
            conditions.append("time_stamp >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("time_stamp < %s")
            params.append(end_date)
        where_clause = " AND " + " AND ".join(conditions)
    
    with get_cursor() as cur:
        # Step 1: 원본 → 1분 집계
        log.info("📌 Step 1: env_data → env_1min")
        sql = f"""
            INSERT INTO env_1min (
                bucket, device_id,
                avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket, device_id,
                AVG(temperature), MIN(temperature), MAX(temperature),
                AVG(humidity), MIN(humidity), MAX(humidity), COUNT(*)
            FROM env_data
            WHERE device_id IN %s{where_clause}
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → env_1min")
        
        # Step 2-4: 15분/1시간/1일 집계
        log.info("📌 Step 2: env_1min → env_15min")
        sql = f"""
            INSERT INTO env_15min (
                bucket, device_id, avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id, AVG(avg_temperature), MIN(min_temperature), MAX(max_temperature),
                AVG(avg_humidity), MIN(min_humidity), MAX(max_humidity), SUM(data_points)
            FROM env_1min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → env_15min")
        
        log.info("📌 Step 3: env_15min → env_1hour")
        sql = f"""
            INSERT INTO env_1hour (
                bucket, device_id, avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket, device_id,
                AVG(avg_temperature), MIN(min_temperature), MAX(max_temperature),
                AVG(avg_humidity), MIN(min_humidity), MAX(max_humidity), SUM(data_points)
            FROM env_15min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → env_1hour")
        
        log.info("📌 Step 4: env_1hour → env_1day")
        sql = f"""
            INSERT INTO env_1day (
                bucket, device_id, avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket, device_id,
                AVG(avg_temperature), MIN(min_temperature), MAX(max_temperature),
                AVG(avg_humidity), MIN(min_humidity), MAX(max_humidity), SUM(data_points)
            FROM env_1hour
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → env_1day")
    
    log.info("✅ 환경센서 마이그레이션 완료")


def migrate_solar(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """태양광 센서 데이터 마이그레이션 (ID: 31)"""
    log.info("=" * 70)
    log.info("☀️  태양광 센서 데이터 마이그레이션 시작...")
    log.info("=" * 70)
    
    device_ids = settings.SOLAR_DEVICE_IDS  # [31]
    
    where_clause = ""
    params = []
    
    if start_date or end_date:
        conditions = []
        if start_date:
            conditions.append("time_stamp >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("time_stamp < %s")
            params.append(end_date)
        where_clause = " AND " + " AND ".join(conditions)
    
    with get_cursor() as cur:
        # Step 1: 원본 → 1분 집계
        log.info("📌 Step 1: solar_data → solar_1min")
        sql = f"""
            INSERT INTO solar_1min (
                bucket, device_id,
                avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket, device_id,
                AVG(irradiance), MIN(irradiance), MAX(irradiance), COUNT(*)
            FROM solar_data
            WHERE device_id IN %s{where_clause}
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → solar_1min")
        
        # Step 2-4: 15분/1시간/1일 집계
        log.info("📌 Step 2: solar_1min → solar_15min")
        sql = f"""
            INSERT INTO solar_15min (
                bucket, device_id, avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id, AVG(avg_irradiance), MIN(min_irradiance), MAX(max_irradiance), SUM(data_points)
            FROM solar_1min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → solar_15min")
        
        log.info("📌 Step 3: solar_15min → solar_1hour")
        sql = f"""
            INSERT INTO solar_1hour (
                bucket, device_id, avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket, device_id,
                AVG(avg_irradiance), MIN(min_irradiance), MAX(max_irradiance), SUM(data_points)
            FROM solar_15min
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → solar_1hour")
        
        log.info("📌 Step 4: solar_1hour → solar_1day")
        sql = f"""
            INSERT INTO solar_1day (
                bucket, device_id, avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket, device_id,
                AVG(avg_irradiance), MIN(min_irradiance), MAX(max_irradiance), SUM(data_points)
            FROM solar_1hour
            WHERE device_id IN %s{where_clause.replace('time_stamp', 'bucket')}
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO NOTHING;
        """
        cur.execute(sql, (tuple(device_ids), *params))
        log.info(f"   ✅ {cur.rowcount} rows → solar_1day")
    
    log.info("✅ 태양광센서 마이그레이션 완료")


def main():
    parser = argparse.ArgumentParser(description="기존 데이터를 집계 테이블로 마이그레이션")
    parser.add_argument("--sensor", choices=["modbus", "env", "solar", "all"], default="all",
                        help="마이그레이션할 센서 타입")
    parser.add_argument("--start", type=str, help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="종료 날짜 (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # 날짜 파싱
    start_date = None
    end_date = None
    
    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=KST)
        log.info(f"📅 시작 날짜: {start_date}")
    
    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=KST)
        log.info(f"📅 종료 날짜: {end_date}")
    
    if not args.start and not args.end:
        log.info("📅 전체 기간 마이그레이션")
    
    log.info("")
    log.info("=" * 70)
    log.info("🚀 기존 데이터 마이그레이션 시작")
    log.info("=" * 70)
    
    try:
        if args.sensor in ["modbus", "all"]:
            migrate_modbus_4wire(start_date, end_date)
            migrate_modbus_3wire(start_date, end_date)
        
        if args.sensor in ["env", "all"]:
            migrate_env(start_date, end_date)
        
        if args.sensor in ["solar", "all"]:
            migrate_solar(start_date, end_date)
        
        log.info("")
        log.info("=" * 70)
        log.info("✅ 마이그레이션 완료!")
        log.info("=" * 70)
        
    except Exception as e:
        log.exception(f"❌ 마이그레이션 실패: {e}")


if __name__ == "__main__":
    main()

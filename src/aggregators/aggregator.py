"""
시계열 데이터 집계 모듈

주요 기능:
- 원시 데이터(5초 수집)를 다중 해상도로 자동 집계
- 1분 → 15분 → 1시간 → 1일 순차 집계
- 백그라운드 스레드로 주기적 실행
- ✅ 시작 시 과거 전체 데이터 집계 지원

집계 흐름:
  [원본 테이블 - 5초 수집]
    ↓ 1분마다 집계
  [1분 테이블] → 하루 단위 그래프용
    ↓ 15분마다 집계
  [15분 테이블] → 1주 단위 그래프용
    ↓ 1시간마다 집계
  [1시간 테이블] → 1달 단위 그래프용
    ↓ 1일마다 집계
  [1일 테이블] → 1년 단위 그래프용

사용법:
  # main.py에서 자동 실행
  aggregator = AggregatorManager()
  aggregator.start()
  
  # 또는 직접 실행
  python -m src.aggregators.aggregator
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("aggregator")
KST = ZoneInfo("Asia/Seoul")


# ============================================================
# Modbus 3상 4선식 집계 (ID: 11, 12, 13)
# ============================================================

def aggregate_modbus_4wire_to_1min():
    """
    modbus_data (4선식) → modbus_4wire_1min 집계
    
    ✅ 수정: 과거 30일치 데이터 모두 집계
    """
    with get_cursor() as cur:
        cur.execute("""
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
            WHERE device_id IN (11, 12, 13)
              AND time_stamp >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_voltage_ll_v = EXCLUDED.avg_voltage_ll_v,
                min_voltage_ll_v = EXCLUDED.min_voltage_ll_v,
                max_voltage_ll_v = EXCLUDED.max_voltage_ll_v,
                avg_current_a = EXCLUDED.avg_current_a,
                min_current_a = EXCLUDED.min_current_a,
                max_current_a = EXCLUDED.max_current_a,
                avg_active_power_kw = EXCLUDED.avg_active_power_kw,
                avg_reactive_power_kvar = EXCLUDED.avg_reactive_power_kvar,
                avg_apparent_power_kva = EXCLUDED.avg_apparent_power_kva,
                avg_power_factor = EXCLUDED.avg_power_factor,
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 4-wire 1min: {affected} rows aggregated")


def aggregate_modbus_4wire_to_15min():
    """
    modbus_4wire_1min → modbus_4wire_15min 집계
    
    ✅ 수정: 과거 30일치 데이터 모두 집계
    """
    with get_cursor() as cur:
        cur.execute("""
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
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY 
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15),
                device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 4-wire 15min: {affected} rows aggregated")


def aggregate_modbus_4wire_to_1hour():
    """
    modbus_4wire_15min → modbus_4wire_1hour 집계
    
    ✅ 수정: 과거 30일치 데이터 모두 집계
    """
    with get_cursor() as cur:
        cur.execute("""
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
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 4-wire 1hour: {affected} rows aggregated")


def aggregate_modbus_4wire_to_1day():
    """
    modbus_4wire_1hour → modbus_4wire_1day 집계
    
    ✅ 수정: 과거 30일치 데이터 모두 집계
    """
    with get_cursor() as cur:
        cur.execute("""
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
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 4-wire 1day: {affected} rows aggregated")


# ============================================================
# Modbus 3상 3선식 집계 (ID: 14, 15)
# ============================================================

def aggregate_modbus_3wire_to_1min():
    """modbus_data (3선식) → modbus_3wire_1min 집계"""
    with get_cursor() as cur:
        cur.execute("""
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
            WHERE device_id IN (14, 15)
              AND time_stamp >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_voltage_ln_v = EXCLUDED.avg_voltage_ln_v,
                min_voltage_ln_v = EXCLUDED.min_voltage_ln_v,
                max_voltage_ln_v = EXCLUDED.max_voltage_ln_v,
                avg_current_a = EXCLUDED.avg_current_a,
                min_current_a = EXCLUDED.min_current_a,
                max_current_a = EXCLUDED.max_current_a,
                avg_active_power_kw = EXCLUDED.avg_active_power_kw,
                avg_reactive_power_kvar = EXCLUDED.avg_reactive_power_kvar,
                avg_apparent_power_kva = EXCLUDED.avg_apparent_power_kva,
                avg_power_factor = EXCLUDED.avg_power_factor,
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 3-wire 1min: {affected} rows aggregated")


def aggregate_modbus_3wire_to_15min():
    """modbus_3wire_1min → modbus_3wire_15min 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_3wire_15min (
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
            FROM modbus_3wire_1min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY 
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15),
                device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 3-wire 15min: {affected} rows aggregated")


def aggregate_modbus_3wire_to_1hour():
    """modbus_3wire_15min → modbus_3wire_1hour 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_3wire_1hour (
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
            FROM modbus_3wire_15min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 3-wire 1hour: {affected} rows aggregated")


def aggregate_modbus_3wire_to_1day():
    """modbus_3wire_1hour → modbus_3wire_1day 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO modbus_3wire_1day (
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
            FROM modbus_3wire_1hour
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                energy_start_kwh = EXCLUDED.energy_start_kwh,
                energy_end_kwh = EXCLUDED.energy_end_kwh,
                energy_delta_kwh = EXCLUDED.energy_delta_kwh,
                peak_power_kw = EXCLUDED.peak_power_kw,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Modbus 3-wire 1day: {affected} rows aggregated")


# ============================================================
# 환경센서 집계 (ID: 21, 22, 23)
# ============================================================

def aggregate_env_to_1min():
    """env_data → env_1min 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_1min (
                bucket, device_id,
                avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket,
                device_id,
                AVG(temperature),
                MIN(temperature),
                MAX(temperature),
                AVG(humidity),
                MIN(humidity),
                MAX(humidity),
                COUNT(*)
            FROM env_data
            WHERE time_stamp >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_temperature = EXCLUDED.avg_temperature,
                min_temperature = EXCLUDED.min_temperature,
                max_temperature = EXCLUDED.max_temperature,
                avg_humidity = EXCLUDED.avg_humidity,
                min_humidity = EXCLUDED.min_humidity,
                max_humidity = EXCLUDED.max_humidity,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Env 1min: {affected} rows aggregated")


def aggregate_env_to_15min():
    """env_1min → env_15min 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_15min (
                bucket, device_id,
                avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id,
                AVG(avg_temperature),
                MIN(min_temperature),
                MAX(max_temperature),
                AVG(avg_humidity),
                MIN(min_humidity),
                MAX(max_humidity),
                SUM(data_points)
            FROM env_1min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY 
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15),
                device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_temperature = EXCLUDED.avg_temperature,
                min_temperature = EXCLUDED.min_temperature,
                max_temperature = EXCLUDED.max_temperature,
                avg_humidity = EXCLUDED.avg_humidity,
                min_humidity = EXCLUDED.min_humidity,
                max_humidity = EXCLUDED.max_humidity,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Env 15min: {affected} rows aggregated")


def aggregate_env_to_1hour():
    """env_15min → env_1hour 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_1hour (
                bucket, device_id,
                avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket,
                device_id,
                AVG(avg_temperature),
                MIN(min_temperature),
                MAX(max_temperature),
                AVG(avg_humidity),
                MIN(min_humidity),
                MAX(max_humidity),
                SUM(data_points)
            FROM env_15min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_temperature = EXCLUDED.avg_temperature,
                min_temperature = EXCLUDED.min_temperature,
                max_temperature = EXCLUDED.max_temperature,
                avg_humidity = EXCLUDED.avg_humidity,
                min_humidity = EXCLUDED.min_humidity,
                max_humidity = EXCLUDED.max_humidity,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Env 1hour: {affected} rows aggregated")


def aggregate_env_to_1day():
    """env_1hour → env_1day 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO env_1day (
                bucket, device_id,
                avg_temperature, min_temperature, max_temperature,
                avg_humidity, min_humidity, max_humidity, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket,
                device_id,
                AVG(avg_temperature),
                MIN(min_temperature),
                MAX(max_temperature),
                AVG(avg_humidity),
                MIN(min_humidity),
                MAX(max_humidity),
                SUM(data_points)
            FROM env_1hour
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_temperature = EXCLUDED.avg_temperature,
                min_temperature = EXCLUDED.min_temperature,
                max_temperature = EXCLUDED.max_temperature,
                avg_humidity = EXCLUDED.avg_humidity,
                min_humidity = EXCLUDED.min_humidity,
                max_humidity = EXCLUDED.max_humidity,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Env 1day: {affected} rows aggregated")


# ============================================================
# 태양광센서 집계 (ID: 31)
# ============================================================

def aggregate_solar_to_1min():
    """solar_data → solar_1min 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_1min (
                bucket, device_id,
                avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('minute', time_stamp) AS bucket,
                device_id,
                AVG(irradiance),
                MIN(irradiance),
                MAX(irradiance),
                COUNT(*)
            FROM solar_data
            WHERE time_stamp >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY bucket, device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_irradiance = EXCLUDED.avg_irradiance,
                min_irradiance = EXCLUDED.min_irradiance,
                max_irradiance = EXCLUDED.max_irradiance,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Solar 1min: {affected} rows aggregated")


def aggregate_solar_to_15min():
    """solar_1min → solar_15min 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_15min (
                bucket, device_id,
                avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15) AS bucket,
                device_id,
                AVG(avg_irradiance),
                MIN(min_irradiance),
                MAX(max_irradiance),
                SUM(data_points)
            FROM solar_1min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY 
                date_trunc('hour', bucket) + 
                    INTERVAL '15 min' * FLOOR(EXTRACT(MINUTE FROM bucket) / 15),
                device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_irradiance = EXCLUDED.avg_irradiance,
                min_irradiance = EXCLUDED.min_irradiance,
                max_irradiance = EXCLUDED.max_irradiance,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Solar 15min: {affected} rows aggregated")


def aggregate_solar_to_1hour():
    """solar_15min → solar_1hour 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_1hour (
                bucket, device_id,
                avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('hour', bucket) AS bucket,
                device_id,
                AVG(avg_irradiance),
                MIN(min_irradiance),
                MAX(max_irradiance),
                SUM(data_points)
            FROM solar_15min
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('hour', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_irradiance = EXCLUDED.avg_irradiance,
                min_irradiance = EXCLUDED.min_irradiance,
                max_irradiance = EXCLUDED.max_irradiance,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Solar 1hour: {affected} rows aggregated")


def aggregate_solar_to_1day():
    """solar_1hour → solar_1day 집계"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO solar_1day (
                bucket, device_id,
                avg_irradiance, min_irradiance, max_irradiance, data_points
            )
            SELECT
                date_trunc('day', bucket) AS bucket,
                device_id,
                AVG(avg_irradiance),
                MIN(min_irradiance),
                MAX(max_irradiance),
                SUM(data_points)
            FROM solar_1hour
            WHERE bucket >= NOW() - INTERVAL '30 days'  -- ✅ 30일로 확장
            GROUP BY date_trunc('day', bucket), device_id
            ON CONFLICT (bucket, device_id) DO UPDATE SET
                avg_irradiance = EXCLUDED.avg_irradiance,
                min_irradiance = EXCLUDED.min_irradiance,
                max_irradiance = EXCLUDED.max_irradiance,
                data_points = EXCLUDED.data_points;
        """)
        affected = cur.rowcount
        if affected > 0:
            log.debug(f"✅ Solar 1day: {affected} rows aggregated")


# ============================================================
# 집계 관리자
# ============================================================

class AggregatorManager:
    """
    집계 작업 스케줄러 및 관리자
    
    동작:
    - 1분마다: 1분 집계 (모든 센서)
    - 15분마다: 15분 집계
    - 1시간마다: 1시간 집계
    - 1일마다: 1일 집계
    - 백그라운드 스레드로 실행
    """
    
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """집계 스레드 시작"""
        if self._thread and self._thread.is_alive():
            log.warning("Aggregator already running")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        log.info("🔄 Aggregator Manager started")
    
    def stop(self):
        """집계 스레드 중지"""
        if not self._thread or not self._thread.is_alive():
            log.warning("Aggregator not running")
            return
        
        self._stop_event.set()
        self._thread.join(timeout=5)
        log.info("🛑 Aggregator Manager stopped")
    
    def _run_loop(self):
        """집계 메인 루프"""
        log.info("=" * 70)
        log.info("🔄 Aggregation Loop Started")
        log.info("   1min aggregation: every 60s")
        log.info("   15min aggregation: every 15min")
        log.info("   1hour aggregation: every 1hour")
        log.info("   1day aggregation: every 1day")
        log.info("=" * 70)
        
        now_kst = datetime.now(KST)
        last_1min = now_kst - timedelta(days=365)
        last_15min = now_kst - timedelta(days=365)
        last_1hour = now_kst - timedelta(days=365)
        last_1day = now_kst - timedelta(days=365)
        
        while not self._stop_event.is_set():
            try:
                now = datetime.now(KST)
                
                # 1분 집계 (60초마다)
                if (now - last_1min).total_seconds() >= 60:
                    log.info("🔄 Running 1min aggregation...")
                    aggregate_modbus_4wire_to_1min()
                    aggregate_modbus_3wire_to_1min()
                    aggregate_env_to_1min()
                    aggregate_solar_to_1min()
                    last_1min = now
                    log.info("✅ 1min aggregation completed")
                
                # 15분 집계 (15분마다)
                if (now - last_15min).total_seconds() >= 900:
                    log.info("🔄 Running 15min aggregation...")
                    aggregate_modbus_4wire_to_15min()
                    aggregate_modbus_3wire_to_15min()
                    aggregate_env_to_15min()
                    aggregate_solar_to_15min()
                    last_15min = now
                    log.info("✅ 15min aggregation completed")
                
                # 1시간 집계 (1시간마다)
                if (now - last_1hour).total_seconds() >= 3600:
                    log.info("🔄 Running 1hour aggregation...")
                    aggregate_modbus_4wire_to_1hour()
                    aggregate_modbus_3wire_to_1hour()
                    aggregate_env_to_1hour()
                    aggregate_solar_to_1hour()
                    last_1hour = now
                    log.info("✅ 1hour aggregation completed")
                
                # 1일 집계 (1일마다)
                if (now - last_1day).total_seconds() >= 86400:
                    log.info("🔄 Running 1day aggregation...")
                    aggregate_modbus_4wire_to_1day()
                    aggregate_modbus_3wire_to_1day()
                    aggregate_env_to_1day()
                    aggregate_solar_to_1day()
                    last_1day = now
                    log.info("✅ 1day aggregation completed")
                
            except Exception as e:
                log.exception(f"❌ Aggregation error: {e}")
            
            # 10초마다 체크
            time.sleep(10)
        
        log.info("🛑 Aggregation loop terminated")


# ============================================================
# 직접 실행
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    manager = AggregatorManager()
    manager.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\nStopping aggregator...")
        manager.stop()

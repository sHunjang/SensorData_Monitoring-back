"""
계층적 데이터 집계 스케줄러

주요 기능:
    1. 계층적 집계 자동 실행 (1m → 15m → 1h → 1d → 1w → 1mo)
    2. 스케줄링 (APScheduler 크론 잡)

작성일: 2025-10-10
"""

import logging
import subprocess
import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("aggregator")


# ========================================
# Device ID 정의
# ========================================

MODBUS_DEVICES = settings.MODBUS_3W_IDS + settings.MODBUS_4W_IDS  # [11-15]
ENV_DEVICES = settings.ENV_IDS  # [21-23]
SOLAR_DEVICE = settings.SOLAR_ID  # 31


# ========================================
# 전역 스케줄러 인스턴스
# ========================================

_scheduler_instance = None
_scheduler_running = False


# ========================================
# Modbus 집계 함수
# ========================================

def aggregate_modbus_1m_to_15m(device_id: int):
    """1분 → 15분 집계"""
    log.info(f"📊 [Modbus {device_id}] 1분 → 15분 집계 시작")
    
    now = datetime.now(timezone.utc)
    bucket_time = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    
    end_time = bucket_time
    start_time = end_time - timedelta(minutes=15)
    
    # ✅ 3상 4선식 (14, 15) - 중성선 포함
    if device_id in settings.MODBUS_4W_IDS:
        sql = f"""
        INSERT INTO modbus_data_{device_id}_15m (
            timestamp, device_id,
            avg_power_kw, max_power_kw, min_power_kw,
            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a, avg_current_n_a,
            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
            avg_voltage_l1n_v, avg_voltage_l2n_v, avg_voltage_l3n_v,
            avg_power_factor, avg_frequency_hz,
            total_active_energy_kwh,
            count
        )
        SELECT
            %s AS timestamp,
            device_id,
            AVG(avg_power_kw), MAX(max_power_kw), MIN(min_power_kw),
            AVG(avg_current_l1_a), AVG(avg_current_l2_a), AVG(avg_current_l3_a), AVG(avg_current_n_a),
            AVG(avg_voltage_l1l2_v), AVG(avg_voltage_l2l3_v), AVG(avg_voltage_l3l1_v),
            AVG(avg_voltage_l1n_v), AVG(avg_voltage_l2n_v), AVG(avg_voltage_l3n_v),
            AVG(avg_power_factor), AVG(avg_frequency_hz),
            MAX(total_active_energy_kwh),
            SUM(count)
        FROM modbus_data_{device_id}_1m
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY device_id;
        """
    
    # ✅ 3상 3선식 (11, 12, 13) - 중성선 없음
    else:
        sql = f"""
        INSERT INTO modbus_data_{device_id}_15m (
            timestamp, device_id,
            avg_power_kw, max_power_kw, min_power_kw,
            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a,
            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
            avg_power_factor, avg_frequency_hz,
            total_active_energy_kwh,
            count
        )
        SELECT
            %s AS timestamp,
            device_id,
            AVG(avg_power_kw), MAX(max_power_kw), MIN(min_power_kw),
            AVG(avg_current_l1_a), AVG(avg_current_l2_a), AVG(avg_current_l3_a),
            AVG(avg_voltage_l1l2_v), AVG(avg_voltage_l2l3_v), AVG(avg_voltage_l3l1_v),
            AVG(avg_power_factor), AVG(avg_frequency_hz),
            MAX(total_active_energy_kwh),
            SUM(count)
        FROM modbus_data_{device_id}_1m
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY device_id;
        """
    
    try:
        with get_cursor() as cur:
            cur.execute(sql, (bucket_time, start_time, end_time))
            log.info(f"✅ [Modbus {device_id}] 15분 집계 완료: {bucket_time}")
    except Exception as e:
        log.error(f"❌ [Modbus {device_id}] 15분 집계 실패: {e}")


def aggregate_modbus_15m_to_1h(device_id: int):
    """15분 → 1시간 집계"""
    log.info(f"📊 [Modbus {device_id}] 15분 → 1시간 집계 시작")
    
    now = datetime.now(timezone.utc)
    bucket_time = now.replace(minute=0, second=0, microsecond=0)
    
    end_time = bucket_time
    start_time = end_time - timedelta(hours=1)
    
    # ✅ 동일한 칼럼명 사용 (15m → 1h도 동일!)
    if device_id in settings.MODBUS_4W_IDS:
        sql = f"""
        INSERT INTO modbus_data_{device_id}_1h (
            timestamp, device_id,
            avg_power_kw, max_power_kw, min_power_kw,
            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a, avg_current_n_a,
            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
            avg_voltage_l1n_v, avg_voltage_l2n_v, avg_voltage_l3n_v,
            avg_power_factor, avg_frequency_hz,
            total_active_energy_kwh,
            count
        )
        SELECT
            %s AS timestamp,
            device_id,
            AVG(avg_power_kw), MAX(max_power_kw), MIN(min_power_kw),
            AVG(avg_current_l1_a), AVG(avg_current_l2_a), AVG(avg_current_l3_a), AVG(avg_current_n_a),
            AVG(avg_voltage_l1l2_v), AVG(avg_voltage_l2l3_v), AVG(avg_voltage_l3l1_v),
            AVG(avg_voltage_l1n_v), AVG(avg_voltage_l2n_v), AVG(avg_voltage_l3n_v),
            AVG(avg_power_factor), AVG(avg_frequency_hz),
            MAX(total_active_energy_kwh),
            SUM(count)
        FROM modbus_data_{device_id}_15m
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY device_id;
        """
    else:
        sql = f"""
        INSERT INTO modbus_data_{device_id}_1h (
            timestamp, device_id,
            avg_power_kw, max_power_kw, min_power_kw,
            avg_current_l1_a, avg_current_l2_a, avg_current_l3_a,
            avg_voltage_l1l2_v, avg_voltage_l2l3_v, avg_voltage_l3l1_v,
            avg_power_factor, avg_frequency_hz,
            total_active_energy_kwh,
            count
        )
        SELECT
            %s AS timestamp,
            device_id,
            AVG(avg_power_kw), MAX(max_power_kw), MIN(min_power_kw),
            AVG(avg_current_l1_a), AVG(avg_current_l2_a), AVG(avg_current_l3_a),
            AVG(avg_voltage_l1l2_v), AVG(avg_voltage_l2l3_v), AVG(avg_voltage_l3l1_v),
            AVG(avg_power_factor), AVG(avg_frequency_hz),
            MAX(total_active_energy_kwh),
            SUM(count)
        FROM modbus_data_{device_id}_15m
        WHERE timestamp >= %s AND timestamp < %s
        GROUP BY device_id;
        """
    
    try:
        with get_cursor() as cur:
            cur.execute(sql, (bucket_time, start_time, end_time))
            log.info(f"✅ [Modbus {device_id}] 1시간 집계 완료: {bucket_time}")
    except Exception as e:
        log.error(f"❌ [Modbus {device_id}] 1시간 집계 실패: {e}")


# ========================================
# Env 집계 함수
# ========================================

def aggregate_env_1m_to_15m(device_id: int):
    """환경 센서: 1분 → 15분 집계"""
    log.info(f"🌡️  [Env {device_id}] 1분 → 15분 집계 시작")
    
    now = datetime.now(timezone.utc)
    bucket_time = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    
    end_time = bucket_time
    start_time = end_time - timedelta(minutes=15)
    
    sql = f"""
    INSERT INTO env_data_{device_id}_15m (
        timestamp, device_id,
        avg_temperature_c, max_temperature_c, min_temperature_c,
        avg_humidity_percent, max_humidity_percent, min_humidity_percent,
        count
    )
    SELECT
        %s AS timestamp,
        device_id,
        AVG(avg_temperature_c), MAX(max_temperature_c), MIN(min_temperature_c),
        AVG(avg_humidity_percent), MAX(max_humidity_percent), MIN(min_humidity_percent),
        SUM(count)
    FROM env_data_{device_id}_1m
    WHERE timestamp >= %s AND timestamp < %s
    GROUP BY device_id;
    """
    
    try:
        with get_cursor() as cur:
            cur.execute(sql, (bucket_time, start_time, end_time))
            log.info(f"✅ [Env {device_id}] 15분 집계 완료: {bucket_time}")
    except Exception as e:
        log.error(f"❌ [Env {device_id}] 15분 집계 실패: {e}")


# ========================================
# Solar 집계 함수
# ========================================

def aggregate_solar_1m_to_15m():
    """일사량 센서: 1분 → 15분 집계"""
    log.info(f"☀️  [Solar {SOLAR_DEVICE}] 1분 → 15분 집계 시작")
    
    now = datetime.now(timezone.utc)
    bucket_time = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    
    end_time = bucket_time
    start_time = end_time - timedelta(minutes=15)
    
    sql = f"""
    INSERT INTO solar_data_{SOLAR_DEVICE}_15m (
        timestamp, device_id,
        avg_irradiance_w_per_m2, max_irradiance_w_per_m2, min_irradiance_w_per_m2,
        count
    )
    SELECT
        %s AS timestamp,
        device_id,
        AVG(avg_irradiance_w_per_m2), MAX(max_irradiance_w_per_m2), MIN(min_irradiance_w_per_m2),
        SUM(count)
    FROM solar_data_{SOLAR_DEVICE}_1m
    WHERE timestamp >= %s AND timestamp < %s
    GROUP BY device_id;
    """
    
    try:
        with get_cursor() as cur:
            cur.execute(sql, (bucket_time, start_time, end_time))
            log.info(f"✅ [Solar {SOLAR_DEVICE}] 15분 집계 완료: {bucket_time}")
    except Exception as e:
        log.error(f"❌ [Solar {SOLAR_DEVICE}] 15분 집계 실패: {e}")


# ========================================
# 스케줄러 시작
# ========================================

def start_scheduler():
    """백그라운드 스케줄러 시작"""
    global _scheduler_instance, _scheduler_running
    
    if _scheduler_running:
        log.warning("⚠️  스케줄러가 이미 실행 중입니다.")
        return
    
    _scheduler_running = True
    
    log.info("=" * 60)
    log.info("🚀 집계 스케줄러 시작")
    log.info("=" * 60)
    
    _scheduler_instance = BackgroundScheduler(timezone="UTC")
    scheduler = _scheduler_instance
    
    # Modbus 집계 (device별 루프)
    for device_id in MODBUS_DEVICES:
        # 1분 → 15분: 매 15분마다
        scheduler.add_job(
            aggregate_modbus_1m_to_15m,
            CronTrigger(minute="*/15"),
            args=[device_id],
            id=f"modbus_1m_to_15m_{device_id}",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
        
        # 15분 → 1시간: 매 시간 0분
        scheduler.add_job(
            aggregate_modbus_15m_to_1h,
            CronTrigger(minute="0"),
            args=[device_id],
            id=f"modbus_15m_to_1h_{device_id}",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
    
    # Env 집계
    for device_id in ENV_DEVICES:
        scheduler.add_job(
            aggregate_env_1m_to_15m,
            CronTrigger(minute="*/15"),
            args=[device_id],
            id=f"env_1m_to_15m_{device_id}",
            replace_existing=True,
            coalesce=True,
            max_instances=1
        )
    
    # Solar 집계
    scheduler.add_job(
        aggregate_solar_1m_to_15m,
        CronTrigger(minute="*/15"),
        id="solar_1m_to_15m",
        replace_existing=True,
        coalesce=True,
        max_instances=1
    )
    
    # 등록된 작업 출력
    log.info("\n📋 등록된 작업:")
    for job in scheduler.get_jobs():
        log.info(f"   - {job.id}: {job.trigger}")
    
    scheduler.start()
    log.info("\n✅ 스케줄러 준비 완료. 백그라운드 실행 중...\n")


# ========================================
# 메인 실행
# ========================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )
    
    start_scheduler()
    
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("🛑 스케줄러 종료")
        if _scheduler_instance:
            _scheduler_instance.shutdown()

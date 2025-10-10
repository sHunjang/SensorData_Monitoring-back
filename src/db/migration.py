"""
데이터베이스 마이그레이션 유틸리티

이 모듈은 기존 RAW 테이블 데이터를 새로운 1분 집계 테이블로 마이그레이션합니다.

주요 변경사항 (2025-10-10):
    - RAW 테이블 → 1분 테이블로 데이터 이전
    - 3상 4선/3선 구분 처리
    - 기존 RAW 테이블 백업 후 삭제

마이그레이션 절차:
    1. 기존 RAW 테이블 존재 확인
    2. RAW 데이터를 1분 단위로 집계
    3. 1분 테이블에 INSERT
    4. RAW 테이블 백업 (CSV)
    5. RAW 테이블 삭제

사용법:
    python -m src.db.migration

작성일: 2025-10-10
"""

import logging
import os
from datetime import datetime, timezone
from typing import List

from src.db.client import get_cursor
from src.config.settings import settings

log = logging.getLogger("migration")


# ========================================
# Modbus RAW → 1분 마이그레이션
# ========================================
def migrate_modbus_raw_to_1m(device_id: int):
    """
    Modbus RAW 테이블 데이터를 1분 테이블로 마이그레이션
    
    Args:
        device_id: Modbus 디바이스 ID (11-15)
    
    동작:
        1. modbus_data_{id}_raw 테이블 존재 확인
        2. RAW 데이터를 1분 단위로 GROUP BY 집계
        3. modbus_data_{id}_1m 테이블에 INSERT
        4. RAW 테이블 백업 (CSV)
        5. RAW 테이블 DROP
    
    주의:
        - 데이터 손실 방지를 위해 백업 필수
        - 3상 4선/3선 구분 처리
    """
    raw_table = f"modbus_data_{device_id}_raw"
    target_table = f"modbus_data_{device_id}_1m"
    
    log.info(f"\n{'='*60}")
    log.info(f"🔄 Modbus {device_id} 마이그레이션 시작")
    log.info(f"   RAW: {raw_table}")
    log.info(f"   Target: {target_table}")
    log.info(f"{'='*60}")
    
    try:
        with get_cursor() as cur:
            # ========================================
            # 1. RAW 테이블 존재 확인
            # ========================================
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name='{raw_table}'
                );
            """)
            
            if not cur.fetchone()[0]:
                log.info(f"  ⏭️  {raw_table} 테이블 없음. 건너뜀.")
                return
            
            # ========================================
            # 2. RAW 데이터 개수 확인
            # ========================================
            cur.execute(f"SELECT COUNT(*) FROM {raw_table};")
            raw_count = cur.fetchone()[0]
            log.info(f"  📊 RAW 데이터: {raw_count:,}행")
            
            if raw_count == 0:
                log.info(f"  ⏭️  데이터 없음. RAW 테이블 삭제만 수행.")
                cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
                log.info(f"  ✅ {raw_table} 삭제 완료")
                return
            
            # ========================================
            # 3. 1분 집계 INSERT
            # ========================================
            log.info(f"  🔄 1분 집계 중...")
            
            if device_id in settings.THREE_PHASE_FOUR_WIRE_IDS:
                # 3상 4선: voltage_n 포함
                cur.execute(f"""
                    INSERT INTO {target_table} (
                        time_bucket,
                        avg_line_to_line_volts_v,
                        avg_line_to_neutral_volts_v,
                        sum_line_currents_a,
                        avg_active_power_kw,
                        max_active_power_kw,
                        min_active_power_kw,
                        avg_reactive_power_kvar,
                        avg_apparent_power_kva,
                        avg_power_factor,
                        total_active_energy_kwh,
                        count
                    )
                    SELECT
                        date_trunc('minute', timestamp) AS time_bucket,
                        AVG(avg_line_to_line_volts_v),
                        AVG(avg_line_to_neutral_volts_v),
                        AVG(sum_line_currents_a),
                        AVG(total_active_power_kw),
                        MAX(total_active_power_kw),
                        MIN(total_active_power_kw),
                        AVG(total_reactive_power_kvar),
                        AVG(total_apparent_power_kva),
                        AVG(total_power_factor),
                        MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh),
                        COUNT(*)
                    FROM {raw_table}
                    GROUP BY time_bucket
                    ON CONFLICT (time_bucket) DO NOTHING;
                """)
            elif device_id in settings.THREE_PHASE_THREE_WIRE_IDS:
                # 3상 3선: voltage_n 없음
                cur.execute(f"""
                    INSERT INTO {target_table} (
                        time_bucket,
                        avg_line_to_line_volts_v,
                        sum_line_currents_a,
                        avg_active_power_kw,
                        max_active_power_kw,
                        min_active_power_kw,
                        avg_reactive_power_kvar,
                        avg_apparent_power_kva,
                        avg_power_factor,
                        total_active_energy_kwh,
                        count
                    )
                    SELECT
                        date_trunc('minute', timestamp) AS time_bucket,
                        AVG(avg_line_to_line_volts_v),
                        AVG(sum_line_currents_a),
                        AVG(total_active_power_kw),
                        MAX(total_active_power_kw),
                        MIN(total_active_power_kw),
                        AVG(total_reactive_power_kvar),
                        AVG(total_apparent_power_kva),
                        AVG(total_power_factor),
                        MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh),
                        COUNT(*)
                    FROM {raw_table}
                    GROUP BY time_bucket
                    ON CONFLICT (time_bucket) DO NOTHING;
                """)
            
            migrated_count = cur.rowcount
            log.info(f"  ✅ 1분 집계 완료: {migrated_count:,}행 INSERT")
            
            # ========================================
            # 4. RAW 테이블 백업 (CSV)
            # ========================================
            backup_dir = settings.BACKUP_PATH
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(
                backup_dir,
                f"{raw_table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            log.info(f"  💾 백업 중: {backup_file}")
            cur.execute(f"""
                COPY {raw_table} TO '{backup_file}' WITH CSV HEADER;
            """)
            log.info(f"  ✅ 백업 완료")
            
            # ========================================
            # 5. RAW 테이블 삭제
            # ========================================
            log.info(f"  🗑️  RAW 테이블 삭제 중...")
            cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
            log.info(f"  ✅ {raw_table} 삭제 완료")
            
        log.info(f"{'='*60}")
        log.info(f"✅ Modbus {device_id} 마이그레이션 완료")
        log.info(f"{'='*60}\n")
        
    except Exception as e:
        log.exception(f"❌ Modbus {device_id} 마이그레이션 실패: {e}")


# ========================================
# Env RAW → 1분 마이그레이션
# ========================================
def migrate_env_raw_to_1m(device_id: int):
    """
    Env RAW 테이블 데이터를 1분 테이블로 마이그레이션
    
    Args:
        device_id: Env 디바이스 ID (21-23)
    """
    raw_table = f"env_data_{device_id}_raw"
    target_table = f"env_data_{device_id}_1m"
    
    log.info(f"\n{'='*60}")
    log.info(f"🔄 Env {device_id} 마이그레이션 시작")
    log.info(f"   RAW: {raw_table}")
    log.info(f"   Target: {target_table}")
    log.info(f"{'='*60}")
    
    try:
        with get_cursor() as cur:
            # RAW 테이블 존재 확인
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name='{raw_table}'
                );
            """)
            
            if not cur.fetchone()[0]:
                log.info(f"  ⏭️  {raw_table} 테이블 없음. 건너뜀.")
                return
            
            # RAW 데이터 개수 확인
            cur.execute(f"SELECT COUNT(*) FROM {raw_table};")
            raw_count = cur.fetchone()[0]
            log.info(f"  📊 RAW 데이터: {raw_count:,}행")
            
            if raw_count == 0:
                log.info(f"  ⏭️  데이터 없음. RAW 테이블 삭제만 수행.")
                cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
                log.info(f"  ✅ {raw_table} 삭제 완료")
                return
            
            # 1분 집계 INSERT
            log.info(f"  🔄 1분 집계 중...")
            cur.execute(f"""
                INSERT INTO {target_table} (
                    time_bucket,
                    avg_temperature_c,
                    max_temperature_c,
                    min_temperature_c,
                    avg_humidity_percent,
                    max_humidity_percent,
                    min_humidity_percent,
                    count
                )
                SELECT
                    date_trunc('minute', timestamp) AS time_bucket,
                    AVG(temperature_c),
                    MAX(temperature_c),
                    MIN(temperature_c),
                    AVG(humidity_percent),
                    MAX(humidity_percent),
                    MIN(humidity_percent),
                    COUNT(*)
                FROM {raw_table}
                GROUP BY time_bucket
                ON CONFLICT (time_bucket) DO NOTHING;
            """)
            
            migrated_count = cur.rowcount
            log.info(f"  ✅ 1분 집계 완료: {migrated_count:,}행 INSERT")
            
            # 백업
            backup_dir = settings.BACKUP_PATH
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(
                backup_dir,
                f"{raw_table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            log.info(f"  💾 백업 중: {backup_file}")
            cur.execute(f"COPY {raw_table} TO '{backup_file}' WITH CSV HEADER;")
            log.info(f"  ✅ 백업 완료")
            
            # RAW 테이블 삭제
            log.info(f"  🗑️  RAW 테이블 삭제 중...")
            cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
            log.info(f"  ✅ {raw_table} 삭제 완료")
            
        log.info(f"{'='*60}")
        log.info(f"✅ Env {device_id} 마이그레이션 완료")
        log.info(f"{'='*60}\n")
        
    except Exception as e:
        log.exception(f"❌ Env {device_id} 마이그레이션 실패: {e}")


# ========================================
# Solar RAW → 1분 마이그레이션
# ========================================
def migrate_solar_raw_to_1m():
    """
    Solar RAW 테이블 데이터를 1분 테이블로 마이그레이션
    """
    device_id = settings.SOLAR_ID
    raw_table = f"solar_data_{device_id}_raw"
    target_table = f"solar_data_{device_id}_1m"
    
    log.info(f"\n{'='*60}")
    log.info(f"🔄 Solar {device_id} 마이그레이션 시작")
    log.info(f"   RAW: {raw_table}")
    log.info(f"   Target: {target_table}")
    log.info(f"{'='*60}")
    
    try:
        with get_cursor() as cur:
            # RAW 테이블 존재 확인
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name='{raw_table}'
                );
            """)
            
            if not cur.fetchone()[0]:
                log.info(f"  ⏭️  {raw_table} 테이블 없음. 건너뜀.")
                return
            
            # RAW 데이터 개수 확인
            cur.execute(f"SELECT COUNT(*) FROM {raw_table};")
            raw_count = cur.fetchone()[0]
            log.info(f"  📊 RAW 데이터: {raw_count:,}행")
            
            if raw_count == 0:
                log.info(f"  ⏭️  데이터 없음. RAW 테이블 삭제만 수행.")
                cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
                log.info(f"  ✅ {raw_table} 삭제 완료")
                return
            
            # 1분 집계 INSERT
            log.info(f"  🔄 1분 집계 중...")
            cur.execute(f"""
                INSERT INTO {target_table} (
                    time_bucket,
                    avg_irradiance_w_per_m2,
                    max_irradiance_w_per_m2,
                    min_irradiance_w_per_m2,
                    count
                )
                SELECT
                    date_trunc('minute', timestamp) AS time_bucket,
                    AVG(irradiance_w_per_m2),
                    MAX(irradiance_w_per_m2),
                    MIN(irradiance_w_per_m2),
                    COUNT(*)
                FROM {raw_table}
                GROUP BY time_bucket
                ON CONFLICT (time_bucket) DO NOTHING;
            """)
            
            migrated_count = cur.rowcount
            log.info(f"  ✅ 1분 집계 완료: {migrated_count:,}행 INSERT")
            
            # 백업
            backup_dir = settings.BACKUP_PATH
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_file = os.path.join(
                backup_dir,
                f"{raw_table}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            log.info(f"  💾 백업 중: {backup_file}")
            cur.execute(f"COPY {raw_table} TO '{backup_file}' WITH CSV HEADER;")
            log.info(f"  ✅ 백업 완료")
            
            # RAW 테이블 삭제
            log.info(f"  🗑️  RAW 테이블 삭제 중...")
            cur.execute(f"DROP TABLE IF EXISTS {raw_table};")
            log.info(f"  ✅ {raw_table} 삭제 완료")
            
        log.info(f"{'='*60}")
        log.info(f"✅ Solar {device_id} 마이그레이션 완료")
        log.info(f"{'='*60}\n")
        
    except Exception as e:
        log.exception(f"❌ Solar {device_id} 마이그레이션 실패: {e}")


# ========================================
# 전체 마이그레이션 실행
# ========================================
def auto_migrate(dsn: str):
    """
    모든 센서의 RAW → 1분 마이그레이션 자동 실행
    
    Args:
        dsn: PostgreSQL 연결 문자열
    
    실행 순서:
        1. Modbus (11-15)
        2. Env (21-23)
        3. Solar (31)
    """
    log.info("\n" + "=" * 60)
    log.info("🚀 자동 마이그레이션 시작")
    log.info("=" * 60)
    
    # Modbus 마이그레이션
    log.info("\n📊 Modbus 마이그레이션...")
    for device_id in settings.MODBUS_3W_IDS:
        migrate_modbus_raw_to_1m(device_id)
    
    # Env 마이그레이션
    log.info("\n🌡️  Env 마이그레이션...")
    for device_id in settings.ENV_IDS:
        migrate_env_raw_to_1m(device_id)
    
    # Solar 마이그레이션
    log.info("\n☀️  Solar 마이그레이션...")
    migrate_solar_raw_to_1m()
    
    log.info("\n" + "=" * 60)
    log.info("✅ 자동 마이그레이션 완료")
    log.info("=" * 60)


# ========================================
# 직접 실행
# ========================================
if __name__ == "__main__":
    """
    마이그레이션 직접 실행
    
    사용법:
        python -m src.db.migration
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    auto_migrate(settings.PG_DSN)

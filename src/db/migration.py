"""
자동 데이터 마이그레이션 모듈

기능:
1. 기존 통합 테이블 감지
2. Device별 분리 테이블로 자동 마이그레이션
3. 기존 데이터 보존
4. 서버 시작시 자동 실행

작성일: 2025-10-02
"""

import os
import logging
import psycopg2
from typing import List, Tuple

log = logging.getLogger("migration")

# Device ID 목록
MODBUS_DEVICE_IDS = [11, 12, 13, 14, 15]
ENV_DEVICE_IDS = [21, 22, 23]


def check_legacy_tables(cur) -> Tuple[bool, bool, bool]:
    """
    기존 통합 테이블 존재 여부 확인
    
    Returns:
        (modbus_exists, env_exists, solar_needs_migration)
    """
    # Modbus 통합 테이블 확인
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'modbus_data'
        )
    """)
    modbus_exists = cur.fetchone()[0]
    
    # Env 통합 테이블 확인
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'env_data'
        )
    """)
    env_exists = cur.fetchone()[0]
    
    # Solar device_id 컬럼 존재 확인
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'solar_data' 
            AND column_name = 'device_id'
        )
    """)
    solar_has_device_id = cur.fetchone()[0]
    
    return modbus_exists, env_exists, not solar_has_device_id


def migrate_modbus_data(cur, device_ids: List[int]) -> int:
    """
    Modbus 통합 테이블 → Device별 분리 테이블 마이그레이션
    """
    log.info("🔄 Modbus 데이터 마이그레이션 시작...")
    total_migrated = 0
    
    for device_id in device_ids:
        try:
            # 1. 분리 테이블 생성
            log.info(f"  📊 modbus_data_{device_id} 테이블 생성 중...")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS modbus_data_{device_id} (
                    time_stamp TIMESTAMPTZ NOT NULL,
                    avg_line_to_line_volts_v DOUBLE PRECISION,
                    avg_line_to_neutral_volts_v DOUBLE PRECISION,
                    sum_line_currents_a DOUBLE PRECISION,
                    total_active_power_kw DOUBLE PRECISION,
                    total_reactive_power_kvar DOUBLE PRECISION,
                    total_apparent_power_kva DOUBLE PRECISION,
                    total_power_factor DOUBLE PRECISION,
                    total_active_energy_kwh DOUBLE PRECISION,
                    total_reactive_energy_kvarh DOUBLE PRECISION,
                    total_apparent_energy_kvah DOUBLE PRECISION
                )
            """)
            
            # 2. 인덱스 생성
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_modbus_{device_id}_time 
                ON modbus_data_{device_id}(time_stamp DESC)
            """)
            
            # 3. 데이터 이동 (device_id 기준 필터링)
            cur.execute(f"""
                INSERT INTO modbus_data_{device_id} 
                SELECT 
                    time_stamp,
                    avg_line_to_line_volts_v,
                    avg_line_to_neutral_volts_v,
                    sum_line_currents_a,
                    total_active_power_kw,
                    total_reactive_power_kvar,
                    total_apparent_power_kva,
                    total_power_factor,
                    total_active_energy_kwh,
                    total_reactive_energy_kvarh,
                    total_apparent_energy_kvah
                FROM modbus_data
                WHERE device_id = %s
                ON CONFLICT DO NOTHING
            """, (device_id,))
            
            migrated = cur.rowcount
            total_migrated += migrated
            log.info(f"  ✅ Device {device_id}: {migrated}건 마이그레이션 완료")
            
        except Exception as e:
            log.error(f"  ❌ Device {device_id} 마이그레이션 실패: {e}")
            raise
    
    # 4. 원본 테이블 백업 (이미 있으면 건너뛰기)
    log.info("  💾 원본 테이블 백업 중...")
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'modbus_data_backup_legacy'
            )
        """)
        backup_exists = cur.fetchone()[0]
        
        if backup_exists:
            log.warning("  ⚠️  백업 테이블이 이미 존재합니다. 기존 통합 테이블을 삭제합니다.")
            cur.execute("DROP TABLE modbus_data CASCADE")
        else:
            cur.execute("ALTER TABLE modbus_data RENAME TO modbus_data_backup_legacy")
            log.info("  ✅ 백업 테이블 생성 완료")
    except Exception as e:
        log.error(f"  ❌ 백업 처리 실패: {e}")
        raise
    
    log.info(f"✅ Modbus 마이그레이션 완료: 총 {total_migrated}건")
    return total_migrated


def migrate_env_data(cur, device_ids: List[int]) -> int:
    """
    Env 통합 테이블 → Device별 분리 테이블 마이그레이션
    """
    log.info("🔄 Env 데이터 마이그레이션 시작...")
    total_migrated = 0
    
    for device_id in device_ids:
        try:
            # 1. 분리 테이블 생성
            log.info(f"  🌡️ env_data_{device_id} 테이블 생성 중...")
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS env_data_{device_id} (
                    time_stamp TIMESTAMPTZ NOT NULL,
                    temperature DOUBLE PRECISION,
                    humidity DOUBLE PRECISION
                )
            """)
            
            # 2. 인덱스 생성
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_env_{device_id}_time 
                ON env_data_{device_id}(time_stamp DESC)
            """)
            
            # 3. 데이터 이동
            cur.execute(f"""
                INSERT INTO env_data_{device_id} 
                SELECT time_stamp, temperature, humidity
                FROM env_data
                WHERE device_id = %s
                ON CONFLICT DO NOTHING
            """, (device_id,))
            
            migrated = cur.rowcount
            total_migrated += migrated
            log.info(f"  ✅ Device {device_id}: {migrated}건 마이그레이션 완료")
            
        except Exception as e:
            log.error(f"  ❌ Device {device_id} 마이그레이션 실패: {e}")
            raise
    
    # 4. 원본 테이블 백업 (이미 있으면 건너뛰기)
    log.info("  💾 원본 테이블 백업 중...")
    try:
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'env_data_backup_legacy'
            )
        """)
        backup_exists = cur.fetchone()[0]
        
        if backup_exists:
            log.warning("  ⚠️  백업 테이블이 이미 존재합니다. 기존 통합 테이블을 삭제합니다.")
            cur.execute("DROP TABLE env_data CASCADE")
        else:
            cur.execute("ALTER TABLE env_data RENAME TO env_data_backup_legacy")
            log.info("  ✅ 백업 테이블 생성 완료")
    except Exception as e:
        log.error(f"  ❌ 백업 처리 실패: {e}")
        raise
    
    log.info(f"✅ Env 마이그레이션 완료: 총 {total_migrated}건")
    return total_migrated



def migrate_solar_data(cur) -> int:
    """
    Solar 테이블에 device_id 컬럼 추가 및 기본값 설정
    
    Returns:
        업데이트된 레코드 수
    """
    log.info("🔄 Solar 데이터 마이그레이션 시작...")
    
    try:
        # 1. device_id 컬럼 추가 (기본값 31)
        log.info("  ☀️ device_id 컬럼 추가 중...")
        cur.execute("""
            ALTER TABLE solar_data 
            ADD COLUMN IF NOT EXISTS device_id INT DEFAULT 31
        """)
        
        # 2. NULL 값 처리
        cur.execute("""
            UPDATE solar_data 
            SET device_id = 31 
            WHERE device_id IS NULL
        """)
        updated = cur.rowcount
        
        # 3. NOT NULL 제약 추가
        cur.execute("""
            ALTER TABLE solar_data 
            ALTER COLUMN device_id SET NOT NULL
        """)
        
        # 4. 인덱스 재생성
        log.info("  📊 인덱스 재생성 중...")
        cur.execute("DROP INDEX IF EXISTS idx_solar_device_time")
        cur.execute("""
            CREATE INDEX idx_solar_device_time 
            ON solar_data(device_id, time_stamp DESC)
        """)
        
        log.info(f"✅ Solar 마이그레이션 완료: {updated}건 업데이트")
        return updated
        
    except Exception as e:
        log.error(f"  ❌ Solar 마이그레이션 실패: {e}")
        raise


def auto_migrate():
    """
    자동 마이그레이션 실행
    
    서버 시작시 호출되어 기존 데이터를 자동으로 마이그레이션
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    
    log.info("🔍 데이터베이스 마이그레이션 상태 확인 중...")
    
    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False  # 트랜잭션 사용
        
        with conn.cursor() as cur:
            # 기존 테이블 확인
            modbus_legacy, env_legacy, solar_needs_migration = check_legacy_tables(cur)
            
            migration_needed = modbus_legacy or env_legacy or solar_needs_migration
            
            if not migration_needed:
                log.info("✅ 마이그레이션 불필요 - 최신 스키마 사용 중")
                conn.close()
                return
            
            log.warning("⚠️  기존 통합 테이블 발견!")
            log.info("🔄 자동 마이그레이션 시작...")
            
            # 마이그레이션 실행
            total_migrated = 0
            
            if modbus_legacy:
                total_migrated += migrate_modbus_data(cur, MODBUS_DEVICE_IDS)
            
            if env_legacy:
                total_migrated += migrate_env_data(cur, ENV_DEVICE_IDS)
            
            if solar_needs_migration:
                total_migrated += migrate_solar_data(cur)
            
            # 커밋
            conn.commit()
            
            log.info(f"🎉 자동 마이그레이션 완료! 총 {total_migrated}건 처리됨")
            log.info("💾 백업 테이블: modbus_data_backup_legacy, env_data_backup_legacy")
            
        conn.close()
        
    except Exception as e:
        log.error(f"❌ 자동 마이그레이션 실패: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # 마이그레이션 실행
    auto_migrate()

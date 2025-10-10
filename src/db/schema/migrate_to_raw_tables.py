"""
기존 데이터를 RAW 테이블로 마이그레이션

기능:
- 기존 테이블 → _raw 테이블로 데이터 이동
- 기존 테이블 백업 (선택적)
- 마이그레이션 후 검증

실행:
    python -m src.db.schema.migrate_to_raw_tables

작성일: 2025-10-10
"""

import logging
from src.db.client import get_cursor

log = logging.getLogger(__name__)

# Device 정의
MODBUS_DEVICES = [11, 12, 13, 14, 15]
ENV_DEVICES = [21, 22, 23]
SOLAR_DEVICES = [31]


def migrate_modbus_data(device_id: int, backup: bool = True):
    """
    Modbus 데이터 마이그레이션
    
    Args:
        device_id: Device ID (11-15)
        backup: 기존 테이블 백업 여부
    """
    old_table = f"modbus_data_{device_id}"
    new_table = f"modbus_data_{device_id}_raw"
    backup_table = f"modbus_data_{device_id}_backup_before_raw"
    
    with get_cursor() as cur:
        # 1. 기존 테이블 존재 확인
        cur.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema='public' 
                AND table_name='{old_table}'
            );
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            log.warning(f"⚠️ {old_table} 테이블이 존재하지 않습니다. 스킵.")
            return
        
        # 2. 데이터 개수 확인
        cur.execute(f"SELECT COUNT(*) FROM {old_table}")
        old_count = cur.fetchone()[0]
        
        if old_count == 0:
            log.info(f"ℹ️ {old_table} 테이블이 비어있습니다. 스킵.")
            return
        
        # 3. 백업 생성 (선택)
        if backup:
            log.info(f"📦 백업 생성: {backup_table}")
            cur.execute(f"""
                DROP TABLE IF EXISTS {backup_table};
                CREATE TABLE {backup_table} AS 
                SELECT * FROM {old_table};
            """)
        
        # 4. 데이터 복사 (RAW 테이블로)
        log.info(f"📋 데이터 복사: {old_table} → {new_table} ({old_count}건)")
        cur.execute(f"""
            INSERT INTO {new_table} (
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
            )
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
            FROM {old_table}
            ON CONFLICT DO NOTHING;
        """)
        
        # 5. 복사 검증
        cur.execute(f"SELECT COUNT(*) FROM {new_table}")
        new_count = cur.fetchone()[0]
        
        if new_count == old_count:
            log.info(f"✅ {new_table} 마이그레이션 완료 ({new_count}건)")
        else:
            log.warning(f"⚠️ {new_table} 데이터 개수 불일치! (원본: {old_count}, 새: {new_count})")


def migrate_env_data(device_id: int, backup: bool = True):
    """
    Env 데이터 마이그레이션
    
    Args:
        device_id: Device ID (21-23)
        backup: 기존 테이블 백업 여부
    """
    old_table = f"env_data_{device_id}"
    new_table = f"env_data_{device_id}_raw"
    backup_table = f"env_data_{device_id}_backup_before_raw"
    
    with get_cursor() as cur:
        # 1. 기존 테이블 존재 확인
        cur.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema='public' 
                AND table_name='{old_table}'
            );
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            log.warning(f"⚠️ {old_table} 테이블이 존재하지 않습니다. 스킵.")
            return
        
        # 2. 데이터 개수 확인
        cur.execute(f"SELECT COUNT(*) FROM {old_table}")
        old_count = cur.fetchone()[0]
        
        if old_count == 0:
            log.info(f"ℹ️ {old_table} 테이블이 비어있습니다. 스킵.")
            return
        
        # 3. 백업 생성 (선택)
        if backup:
            log.info(f"📦 백업 생성: {backup_table}")
            cur.execute(f"""
                DROP TABLE IF EXISTS {backup_table};
                CREATE TABLE {backup_table} AS 
                SELECT * FROM {old_table};
            """)
        
        # 4. 데이터 복사 (RAW 테이블로)
        log.info(f"📋 데이터 복사: {old_table} → {new_table} ({old_count}건)")
        cur.execute(f"""
            INSERT INTO {new_table} (
                time_stamp,
                temperature,
                humidity
            )
            SELECT 
                time_stamp,
                temperature,
                humidity
            FROM {old_table}
            ON CONFLICT DO NOTHING;
        """)
        
        # 5. 복사 검증
        cur.execute(f"SELECT COUNT(*) FROM {new_table}")
        new_count = cur.fetchone()[0]
        
        if new_count == old_count:
            log.info(f"✅ {new_table} 마이그레이션 완료 ({new_count}건)")
        else:
            log.warning(f"⚠️ {new_table} 데이터 개수 불일치! (원본: {old_count}, 새: {new_count})")


def migrate_solar_data(device_id: int, backup: bool = True):
    """
    Solar 데이터 마이그레이션
    
    Args:
        device_id: Device ID (31)
        backup: 기존 테이블 백업 여부
    """
    old_table = "solar_data"
    new_table = f"solar_data_{device_id}_raw"
    backup_table = "solar_data_backup_before_raw"
    
    with get_cursor() as cur:
        # 1. 기존 테이블 존재 확인
        cur.execute(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema='public' 
                AND table_name='{old_table}'
            );
        """)
        exists = cur.fetchone()[0]
        
        if not exists:
            log.warning(f"⚠️ {old_table} 테이블이 존재하지 않습니다. 스킵.")
            return
        
        # 2. 데이터 개수 확인 (device_id 필터링)
        cur.execute(f"""
            SELECT COUNT(*) FROM {old_table} 
            WHERE device_id={device_id}
        """)
        old_count = cur.fetchone()[0]
        
        if old_count == 0:
            log.info(f"ℹ️ {old_table} (device_id={device_id}) 데이터가 없습니다. 스킵.")
            return
        
        # 3. 백업 생성 (선택, 전체 solar_data 백업)
        if backup and device_id == SOLAR_DEVICES[0]:  # 첫 번째 device만 백업
            log.info(f"📦 백업 생성: {backup_table}")
            cur.execute(f"""
                DROP TABLE IF EXISTS {backup_table};
                CREATE TABLE {backup_table} AS 
                SELECT * FROM {old_table};
            """)
        
        # 4. 데이터 복사 (RAW 테이블로)
        log.info(f"📋 데이터 복사: {old_table} (device_id={device_id}) → {new_table} ({old_count}건)")
        cur.execute(f"""
            INSERT INTO {new_table} (
                time_stamp,
                irradiance
            )
            SELECT 
                time_stamp,
                irradiance
            FROM {old_table}
            WHERE device_id={device_id}
            ON CONFLICT DO NOTHING;
        """)
        
        # 5. 복사 검증
        cur.execute(f"SELECT COUNT(*) FROM {new_table}")
        new_count = cur.fetchone()[0]
        
        if new_count == old_count:
            log.info(f"✅ {new_table} 마이그레이션 완료 ({new_count}건)")
        else:
            log.warning(f"⚠️ {new_table} 데이터 개수 불일치! (원본: {old_count}, 새: {new_count})")


def migrate_all_data(backup: bool = True):
    """
    모든 데이터 마이그레이션
    
    Args:
        backup: 기존 테이블 백업 여부
    """
    log.info("🚀 Starting data migration to _raw tables...")
    
    # 1. Modbus 마이그레이션
    log.info("\n📊 Migrating Modbus data...")
    for device_id in MODBUS_DEVICES:
        migrate_modbus_data(device_id, backup)
    
    # 2. Env 마이그레이션
    log.info("\n🌡️ Migrating Env data...")
    for device_id in ENV_DEVICES:
        migrate_env_data(device_id, backup)
    
    # 3. Solar 마이그레이션
    log.info("\n☀️ Migrating Solar data...")
    for device_id in SOLAR_DEVICES:
        migrate_solar_data(device_id, backup)
    
    log.info("\n✅ All data migration completed!")


def verify_migration():
    """
    마이그레이션 검증
    """
    log.info("\n🔍 Verifying migration...")
    
    with get_cursor() as cur:
        # Modbus 검증
        for device_id in MODBUS_DEVICES:
            old_table = f"modbus_data_{device_id}"
            new_table = f"modbus_data_{device_id}_raw"
            
            # 기존 테이블 확인
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema='public' AND table_name='{old_table}'
                );
            """)
            if cur.fetchone()[0]:
                cur.execute(f"SELECT COUNT(*) FROM {old_table}")
                old_count = cur.fetchone()[0]
            else:
                old_count = 0
            
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            new_count = cur.fetchone()[0]
            
            status = "✅" if old_count == new_count else "⚠️"
            log.info(f"{status} {old_table}: {old_count} → {new_table}: {new_count}")
        
        # Env 검증
        for device_id in ENV_DEVICES:
            old_table = f"env_data_{device_id}"
            new_table = f"env_data_{device_id}_raw"
            
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema='public' AND table_name='{old_table}'
                );
            """)
            if cur.fetchone()[0]:
                cur.execute(f"SELECT COUNT(*) FROM {old_table}")
                old_count = cur.fetchone()[0]
            else:
                old_count = 0
            
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            new_count = cur.fetchone()[0]
            
            status = "✅" if old_count == new_count else "⚠️"
            log.info(f"{status} {old_table}: {old_count} → {new_table}: {new_count}")
        
        # Solar 검증
        for device_id in SOLAR_DEVICES:
            old_table = "solar_data"
            new_table = f"solar_data_{device_id}_raw"
            
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema='public' AND table_name='{old_table}'
                );
            """)
            if cur.fetchone()[0]:
                cur.execute(f"SELECT COUNT(*) FROM {old_table} WHERE device_id={device_id}")
                old_count = cur.fetchone()[0]
            else:
                old_count = 0
            
            cur.execute(f"SELECT COUNT(*) FROM {new_table}")
            new_count = cur.fetchone()[0]
            
            status = "✅" if old_count == new_count else "⚠️"
            log.info(f"{status} {old_table} (device_id={device_id}): {old_count} → {new_table}: {new_count}")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # 데이터 마이그레이션 실행
    migrate_all_data(backup=True)
    
    # 검증
    verify_migration()

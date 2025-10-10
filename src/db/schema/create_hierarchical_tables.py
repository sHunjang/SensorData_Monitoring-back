"""
계층적 테이블 생성 스크립트

기능:
- 9단계 시간 계층 테이블 자동 생성
- Device별로 독립적인 테이블 구조
- Modbus, Env, Solar 모두 지원

실행:
    python -m src.db.schema.create_hierarchical_tables

작성일: 2025-10-10
"""

import logging
from src.db.client import get_cursor

log = logging.getLogger(__name__)

# Device 정의
MODBUS_DEVICES = [11, 12, 13, 14, 15]
ENV_DEVICES = [21, 22, 23]
SOLAR_DEVICES = [31]

# 시간 계층 정의
TIME_LEVELS = ['raw', '1m', '15m', '1h', '1d', '1w', '1mo', '6mo', '1y']


def create_modbus_raw_table(device_id: int):
    """
    Modbus RAW 테이블 생성 (원본 데이터)
    
    Args:
        device_id: Device ID (11-15)
    """
    table_name = f"modbus_data_{device_id}_raw"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
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
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_stamp DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_modbus_aggregated_table(device_id: int, level: str):
    """
    Modbus 집계 테이블 생성 (1m ~ 1y)
    
    Args:
        device_id: Device ID (11-15)
        level: 시간 레벨 (1m, 15m, 1h, 1d, 1w, 1mo, 6mo, 1y)
    """
    table_name = f"modbus_data_{device_id}_{level}"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time_bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
        avg_volts_ll DOUBLE PRECISION,
        avg_volts_ln DOUBLE PRECISION,
        avg_current DOUBLE PRECISION,
        avg_kw DOUBLE PRECISION,
        max_kw DOUBLE PRECISION,
        min_kw DOUBLE PRECISION,
        avg_kvar DOUBLE PRECISION,
        avg_kva DOUBLE PRECISION,
        avg_pf DOUBLE PRECISION,
        total_kwh DOUBLE PRECISION,
        data_points INTEGER DEFAULT 0
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_bucket DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_env_raw_table(device_id: int):
    """
    Env RAW 테이블 생성 (원본 데이터)
    
    Args:
        device_id: Device ID (21-23)
    """
    table_name = f"env_data_{device_id}_raw"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time_stamp TIMESTAMPTZ NOT NULL,
        temperature DOUBLE PRECISION,
        humidity DOUBLE PRECISION
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_stamp DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_env_aggregated_table(device_id: int, level: str):
    """
    Env 집계 테이블 생성 (1m ~ 1y)
    
    Args:
        device_id: Device ID (21-23)
        level: 시간 레벨 (1m, 15m, 1h, 1d, 1w, 1mo, 6mo, 1y)
    """
    table_name = f"env_data_{device_id}_{level}"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time_bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
        avg_temperature DOUBLE PRECISION,
        max_temperature DOUBLE PRECISION,
        min_temperature DOUBLE PRECISION,
        avg_humidity DOUBLE PRECISION,
        max_humidity DOUBLE PRECISION,
        min_humidity DOUBLE PRECISION,
        data_points INTEGER DEFAULT 0
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_bucket DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_solar_raw_table(device_id: int):
    """
    Solar RAW 테이블 생성 (원본 데이터)
    
    Args:
        device_id: Device ID (31)
    """
    table_name = f"solar_data_{device_id}_raw"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time_stamp TIMESTAMPTZ NOT NULL,
        irradiance DOUBLE PRECISION
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_stamp DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_solar_aggregated_table(device_id: int, level: str):
    """
    Solar 집계 테이블 생성 (1m ~ 1y)
    
    Args:
        device_id: Device ID (31)
        level: 시간 레벨 (1m, 15m, 1h, 1d, 1w, 1mo, 6mo, 1y)
    """
    table_name = f"solar_data_{device_id}_{level}"
    
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        time_bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
        avg_irradiance DOUBLE PRECISION,
        max_irradiance DOUBLE PRECISION,
        min_irradiance DOUBLE PRECISION,
        data_points INTEGER DEFAULT 0
    );
    
    -- 인덱스 생성
    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
    ON {table_name}(time_bucket DESC);
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
    
    log.info(f"✅ Created: {table_name}")


def create_all_tables():
    """
    모든 계층적 테이블 생성
    
    총 81개 테이블:
    - Modbus: 5 devices × 9 levels = 45 tables
    - Env: 3 devices × 9 levels = 27 tables
    - Solar: 1 device × 9 levels = 9 tables
    """
    log.info("🚀 Starting hierarchical table creation...")
    
    # 1. Modbus 테이블 (45개)
    log.info("\n📊 Creating Modbus tables (45 tables)...")
    for device_id in MODBUS_DEVICES:
        # RAW 테이블
        create_modbus_raw_table(device_id)
        
        # 집계 테이블들
        for level in TIME_LEVELS[1:]:  # raw 제외
            create_modbus_aggregated_table(device_id, level)
    
    # 2. Env 테이블 (27개)
    log.info("\n🌡️ Creating Env tables (27 tables)...")
    for device_id in ENV_DEVICES:
        # RAW 테이블
        create_env_raw_table(device_id)
        
        # 집계 테이블들
        for level in TIME_LEVELS[1:]:  # raw 제외
            create_env_aggregated_table(device_id, level)
    
    # 3. Solar 테이블 (9개)
    log.info("\n☀️ Creating Solar tables (9 tables)...")
    for device_id in SOLAR_DEVICES:
        # RAW 테이블
        create_solar_raw_table(device_id)
        
        # 집계 테이블들
        for level in TIME_LEVELS[1:]:  # raw 제외
            create_solar_aggregated_table(device_id, level)
    
    log.info("\n✅ All 81 hierarchical tables created successfully!")
    log.info("   - Modbus: 45 tables")
    log.info("   - Env: 27 tables")
    log.info("   - Solar: 9 tables")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    # 테이블 생성 실행
    create_all_tables()

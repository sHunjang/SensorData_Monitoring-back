"""
Database Schema Bootstrap

데이터베이스 스키마 초기화:
    1. 1m 테이블 생성 (hypertable) - RAW 테이블은 제거됨
    2. 집계 테이블 생성 (15m, 1h, 1d, 1w, 1mo, 6mo, 1y)
    3. Retention Policy 적용

작성일: 2025-10-10
"""

import logging
from src.db.client import get_cursor
from src.config.settings import settings

logger = logging.getLogger(__name__)


# ============================================================
# Helper Functions
# ============================================================

def add_retention_policy(cur, table_name: str, interval: str):
    """
    Retention Policy 추가
    
    Args:
        cur: DB cursor
        table_name: 테이블 이름
        interval: 보관 기간 (예: "30 days", "90 days")
    """
    try:
        # 기존 policy 제거
        cur.execute(f"""
            SELECT remove_retention_policy('{table_name}', if_exists => true);
        """)
        
        # 새 policy 추가
        cur.execute(f"""
            SELECT add_retention_policy('{table_name}', INTERVAL '{interval}');
        """)
        logger.info(f"    ✅ Retention policy: {table_name} ({interval})")
    except Exception as e:
        logger.warning(f"    ⚠️  Retention policy 스킵: {table_name} - {e}")


# ============================================================
# Modbus Tables
# ============================================================

def create_modbus_table_4wire(cur, device_id: int, bucket: str):
    """3상 4선식 Modbus 집계 테이블 생성"""
    table_name = f"modbus_data_{device_id}_{bucket}"
    
    logger.info(f"  ✅ CREATE TABLE IF NOT EXISTS {table_name} (...)")
    
    # 테이블 생성
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL,
            
            -- 전력 (평균/최대/최소)
            avg_power_kw REAL,
            max_power_kw REAL,
            min_power_kw REAL,
            
            -- 전류 (평균)
            avg_current_l1_a REAL,
            avg_current_l2_a REAL,
            avg_current_l3_a REAL,
            avg_current_n_a REAL,
            
            -- 전압 선간 (평균)
            avg_voltage_l1l2_v REAL,
            avg_voltage_l2l3_v REAL,
            avg_voltage_l3l1_v REAL,
            
            -- 전압 상-중성선 (평균)
            avg_voltage_l1n_v REAL,
            avg_voltage_l2n_v REAL,
            avg_voltage_l3n_v REAL,
            
            -- 역률 / 주파수
            avg_power_factor REAL,
            avg_frequency_hz REAL,
            
            -- 누적 전력량
            total_active_energy_kwh REAL,
            
            -- 데이터 개수
            count INT,
            
            PRIMARY KEY (timestamp)
        );
    """)
    
    # Hypertable 변환
    try:
        cur.execute(f"""
            SELECT create_hypertable(
                '{table_name}', 
                'timestamp',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        pass
    
    # 인덱스
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_timestamp_idx 
        ON {table_name} (timestamp DESC);
    """)
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_device_id_idx 
        ON {table_name} (device_id);
    """)


def create_modbus_table_3wire(cur, device_id: int, bucket: str):
    """3상 3선식 Modbus 집계 테이블 생성 (중성선 없음)"""
    table_name = f"modbus_data_{device_id}_{bucket}"
    
    logger.info(f"  ✅ CREATE TABLE IF NOT EXISTS {table_name} (...)")
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL,
            avg_power_kw REAL,
            max_power_kw REAL,
            min_power_kw REAL,
            avg_current_l1_a REAL,
            avg_current_l2_a REAL,
            avg_current_l3_a REAL,
            avg_voltage_l1l2_v REAL,
            avg_voltage_l2l3_v REAL,
            avg_voltage_l3l1_v REAL,
            avg_power_factor REAL,
            avg_frequency_hz REAL,
            total_active_energy_kwh REAL,
            count INT,
            PRIMARY KEY (timestamp)
        );
    """)
    
    try:
        cur.execute(f"""
            SELECT create_hypertable(
                '{table_name}', 
                'timestamp',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        pass
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_timestamp_idx 
        ON {table_name} (timestamp DESC);
    """)
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_device_id_idx 
        ON {table_name} (device_id);
    """)


# ============================================================
# Env Tables
# ============================================================

def create_env_table(cur, device_id: int, bucket: str):
    """환경센서 집계 테이블 생성"""
    table_name = f"env_data_{device_id}_{bucket}"
    
    logger.info(f"  ✅ CREATE TABLE IF NOT EXISTS {table_name} (...)")
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL,
            avg_temperature_c REAL,
            max_temperature_c REAL,
            min_temperature_c REAL,
            avg_humidity_percent REAL,
            max_humidity_percent REAL,
            min_humidity_percent REAL,
            count INT,
            PRIMARY KEY (timestamp)
        );
    """)
    
    try:
        cur.execute(f"""
            SELECT create_hypertable(
                '{table_name}', 
                'timestamp',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        pass
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_timestamp_idx 
        ON {table_name} (timestamp DESC);
    """)
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_device_id_idx 
        ON {table_name} (device_id);
    """)


# ============================================================
# Solar Tables
# ============================================================

def create_solar_table(cur, device_id: int, bucket: str):
    """일사량 센서 집계 테이블 생성"""
    table_name = f"solar_data_{device_id}_{bucket}"
    
    logger.info(f"  ✅ CREATE TABLE IF NOT EXISTS {table_name} (...)")
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp TIMESTAMPTZ NOT NULL,
            device_id INT NOT NULL,
            avg_irradiance_w_per_m2 REAL,
            max_irradiance_w_per_m2 REAL,
            min_irradiance_w_per_m2 REAL,
            count INT,
            PRIMARY KEY (timestamp)
        );
    """)
    
    try:
        cur.execute(f"""
            SELECT create_hypertable(
                '{table_name}', 
                'timestamp',
                if_not_exists => TRUE
            );
        """)
    except Exception:
        pass
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_timestamp_idx 
        ON {table_name} (timestamp DESC);
    """)
    
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {table_name}_device_id_idx 
        ON {table_name} (device_id);
    """)


# ============================================================
# Main Bootstrap Function
# ============================================================

def init_db_schema():
    """데이터베이스 스키마 초기화"""
    logger.info("=" * 60)
    logger.info("🚀 데이터베이스 스키마 초기화 시작")
    logger.info("=" * 60)
    
    try:
        with get_cursor() as cur:
            # =====================================
            # 1. Modbus 테이블 생성
            # =====================================
            logger.info("\n📊 Modbus 테이블 생성 중...")
            logger.info(f"  3상 4선 (중성선 포함): {settings.MODBUS_4W_IDS}")
            logger.info(f"  3상 3선 (중성선 없음): {settings.MODBUS_3W_IDS}")
            
            # 1m 테이블부터 시작 (RAW 테이블 없음)
            buckets = ["1m", "15m", "1h", "1d", "1w", "1mo", "6mo", "1y"]
            
            # 3상 4선식 (14, 15)
            for device_id in settings.MODBUS_4W_IDS:
                for bucket in buckets:
                    create_modbus_table_4wire(cur, device_id, bucket)
            
            # 3상 3선식 (11, 12, 13)
            for device_id in settings.MODBUS_3W_IDS:
                for bucket in buckets:
                    create_modbus_table_3wire(cur, device_id, bucket)
            
            # =====================================
            # 2. Env 테이블 생성
            # =====================================
            logger.info("\n🌡️  Env 테이블 생성 중...")
            logger.info(f"  Env Devices: {settings.ENV_IDS}")
            
            for device_id in settings.ENV_IDS:
                for bucket in buckets:
                    create_env_table(cur, device_id, bucket)
            
            # =====================================
            # 3. Solar 테이블 생성
            # =====================================
            logger.info("\n☀️  Solar 테이블 생성 중...")
            logger.info(f"  Solar Device: {settings.SOLAR_ID}")
            
            device_id = settings.SOLAR_ID
            for bucket in buckets:
                create_solar_table(cur, device_id, bucket)
            
            # =====================================
            # 4. Retention Policy 적용
            # =====================================
            logger.info("\n📅 Retention Policy 적용 중...")
            
            # 전체 Modbus device IDs
            all_modbus_ids = settings.MODBUS_4W_IDS + settings.MODBUS_3W_IDS
            
            # 1분 테이블: 30일 보관
            logger.info("  📅 1분 테이블 Retention Policy 적용 (30일)...")
            for device_id in all_modbus_ids:
                add_retention_policy(cur, f"modbus_data_{device_id}_1m", "30 days")
            
            for device_id in settings.ENV_IDS:
                add_retention_policy(cur, f"env_data_{device_id}_1m", "30 days")
            
            add_retention_policy(cur, f"solar_data_{settings.SOLAR_ID}_1m", "30 days")
            
            # 15분 테이블: 1년 보관
            logger.info("  📅 15분 테이블 Retention Policy 적용 (365일)...")
            for device_id in all_modbus_ids:
                add_retention_policy(cur, f"modbus_data_{device_id}_15m", "365 days")
            
            for device_id in settings.ENV_IDS:
                add_retention_policy(cur, f"env_data_{device_id}_15m", "365 days")
            
            add_retention_policy(cur, f"solar_data_{settings.SOLAR_ID}_15m", "365 days")
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ 데이터베이스 스키마 초기화 완료")
            logger.info("=" * 60)
            
    except Exception as e:
        logger.error(f"❌ 스키마 초기화 실패: {e}")
        logger.exception(e)
        raise


# ============================================================
# CLI Entry Point
# ============================================================

if __name__ == "__main__":
    """
    직접 실행 시 스키마 초기화
    
    Usage:
        python src/db/bootstrap.py
    """
    from src.common.logging_config import setup_logging
    setup_logging()
    
    init_db_schema()

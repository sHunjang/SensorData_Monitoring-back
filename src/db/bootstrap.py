"""
데이터베이스 스키마 초기화 모듈

주요 기능:
1. 자동 마이그레이션 실행 (기존 데이터 보존)
2. Device별 분리 테이블 생성
3. TimescaleDB 지원 (선택적)

작성일: 2025-10-02
"""

import os
import logging
import psycopg2
from typing import List

# 마이그레이션 모듈 임포트
try:
    from src.db.migration import auto_migrate
    MIGRATION_AVAILABLE = True
except ImportError:
    MIGRATION_AVAILABLE = False

log = logging.getLogger("bootstrap")

# Device ID 목록
MODBUS_DEVICE_IDS = [11, 12, 13, 14, 15]
ENV_DEVICE_IDS = [21, 22, 23]


def get_modbus_ddl(device_id: int) -> str:
    """Modbus device별 테이블 DDL"""
    return f"""
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
);

CREATE INDEX IF NOT EXISTS idx_modbus_{device_id}_time 
ON modbus_data_{device_id}(time_stamp DESC);
"""


def get_env_ddl(device_id: int) -> str:
    """Env device별 테이블 DDL"""
    return f"""
CREATE TABLE IF NOT EXISTS env_data_{device_id} (
    time_stamp TIMESTAMPTZ NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_env_{device_id}_time 
ON env_data_{device_id}(time_stamp DESC);
"""


DDL_SOLAR = """
CREATE TABLE IF NOT EXISTS solar_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL DEFAULT 31,
    irradiance DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_solar_device_time 
ON solar_data(device_id, time_stamp DESC);
"""


def ensure_schema():
    """
    스키마 초기화
    
    1. 자동 마이그레이션 실행 (기존 데이터 보존)
    2. Device별 분리 테이블 생성
    3. TimescaleDB hypertable 설정
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    
    log.info("🔌 스키마 초기화 시작...")
    
    try:
        # ============================================
        # Step 1: 자동 마이그레이션 실행
        # ============================================
        if MIGRATION_AVAILABLE:
            try:
                log.info("🔄 자동 마이그레이션 실행 중...")
                auto_migrate()
            except Exception as e:
                log.warning(f"⚠️  자동 마이그레이션 실패 (계속 진행): {e}")
        else:
            log.warning("⚠️  마이그레이션 모듈 없음 - 기존 데이터 보존 불가")
        
        # ============================================
        # Step 2: 분리 테이블 생성
        # ============================================
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        
        log.info("✅ Device별 분리 테이블 생성 중...")
        
        with conn.cursor() as cur:
            # Modbus 장치별 테이블
            for device_id in MODBUS_DEVICE_IDS:
                log.info(f"  📊 modbus_data_{device_id}")
                cur.execute(get_modbus_ddl(device_id))
            
            # Env 장치별 테이블
            for device_id in ENV_DEVICE_IDS:
                log.info(f"  🌡️ env_data_{device_id}")
                cur.execute(get_env_ddl(device_id))
            
            # Solar 단일 테이블
            log.info("  ☀️ solar_data")
            cur.execute(DDL_SOLAR)
        
        log.info("✅ 기본 테이블 생성 완료")
        
        # ============================================
        # Step 3: TimescaleDB Hypertable 설정
        # ============================================
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
                if cur.fetchone():
                    log.info("📊 TimescaleDB 감지 - Hypertable 생성 중...")
                    
                    # Modbus hypertables
                    for device_id in MODBUS_DEVICE_IDS:
                        try:
                            cur.execute(f"""
                                SELECT create_hypertable(
                                    'modbus_data_{device_id}', 
                                    'time_stamp', 
                                    if_not_exists => TRUE
                                )
                            """)
                        except Exception as e:
                            log.debug(f"Hypertable modbus_data_{device_id} already exists or error: {e}")
                    
                    # Env hypertables
                    for device_id in ENV_DEVICE_IDS:
                        try:
                            cur.execute(f"""
                                SELECT create_hypertable(
                                    'env_data_{device_id}', 
                                    'time_stamp', 
                                    if_not_exists => TRUE
                                )
                            """)
                        except Exception as e:
                            log.debug(f"Hypertable env_data_{device_id} already exists or error: {e}")
                    
                    # Solar hypertable
                    try:
                        cur.execute("""
                            SELECT create_hypertable(
                                'solar_data', 
                                'time_stamp', 
                                if_not_exists => TRUE
                            )
                        """)
                    except Exception as e:
                        log.debug(f"Hypertable solar_data already exists or error: {e}")
                    
                    log.info("✅ TimescaleDB Hypertable 생성 완료")
        except Exception as e:
            log.warning(f"⚠️  TimescaleDB 설정 생략: {e}")
        
        # ============================================
        # Step 4: 테이블 목록 확인
        # ============================================
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
        
        log.info(f"✅ 스키마 초기화 완료! 테이블 수: {len(tables)}")
        
        # 주요 테이블만 로그 출력
        main_tables = [t for t in tables if 'data' in t and 'backup' not in t][:10]
        log.info(f"📋 주요 테이블: {', '.join(main_tables)}...")
        
        conn.close()
        
    except Exception as e:
        log.exception("❌ 스키마 초기화 실패")
        raise


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    ensure_schema()

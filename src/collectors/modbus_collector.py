"""
데이터베이스 스키마 초기화 모듈

주요 기능:
- PostgreSQL 데이터베이스 스키마 생성
- 모든 테이블과 인덱스 초기화
- TimescaleDB 지원 (선택적)
- Idempotent 실행 (중복 실행 안전)
- ✅ 기존 데이터 보존 (migrate_data => TRUE)

테이블 구조:
- modbus_data: 전력 데이터 (TAC4300)
- env_data: 환경 데이터 (온도, 습도)
- solar_data: 태양광 데이터 (일사량) - irradiance 컬럼 사용

사용법:
python -m src.db.bootstrap
"""

import os
import logging
import psycopg2

# 로깅 설정
log = logging.getLogger("bootstrap")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
log.addHandler(handler)


# 🎯 통일된 스키마 DDL - irradiance 컬럼 사용
DDL_BASE = r"""
-- modbus_data 테이블 (전력 데이터)
CREATE TABLE IF NOT EXISTS modbus_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
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

-- modbus_data 인덱스
CREATE INDEX IF NOT EXISTS idx_modbus_device_time ON modbus_data(device_id, time_stamp DESC);

-- env_data 테이블 (환경 데이터)
CREATE TABLE IF NOT EXISTS env_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

-- env_data 인덱스
CREATE INDEX IF NOT EXISTS idx_env_device_time ON env_data(device_id, time_stamp DESC);

-- ✅ solar_data 테이블 (일사량 데이터) - irradiance 컬럼 통일
CREATE TABLE IF NOT EXISTS solar_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    irradiance DOUBLE PRECISION  -- 일사량 (W/m²)
);

-- solar_data 인덱스
CREATE INDEX IF NOT EXISTS idx_solar_device_time ON solar_data(device_id, time_stamp DESC);
"""


# ✅ TimescaleDB hypertable 설정 (migrate_data => TRUE 추가)
DDL_TIMESCALEDB = r"""
-- ✅ TimescaleDB hypertable 생성 (기존 데이터 보존)
SELECT create_hypertable('modbus_data', 'time_stamp', 
    if_not_exists => TRUE, 
    migrate_data => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

SELECT create_hypertable('env_data', 'time_stamp', 
    if_not_exists => TRUE, 
    migrate_data => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

SELECT create_hypertable('solar_data', 'time_stamp', 
    if_not_exists => TRUE, 
    migrate_data => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);
"""


def ensure_schema():
    """스키마 초기화 - 모든 테이블과 인덱스 생성 (기존 데이터 보존)"""
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    log.info("🔌 ensure_schema: connecting to DB")
    
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        
        log.info("✅ ensure_schema: creating base tables and indexes (if not exists)")
        with conn.cursor() as cur:
            cur.execute(DDL_BASE)
        log.info("✅ Base tables created successfully")
        
        # TimescaleDB 확장 확인 및 hypertable 생성
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
                if cur.fetchone():
                    log.info("📊 ensure_schema: timescaledb installed, ensuring hypertables (migrate_data=TRUE)")
                    cur.execute(DDL_TIMESCALEDB)
                    log.info("✅ TimescaleDB hypertables created successfully (기존 데이터 보존)")
                else:
                    log.warning("⚠️ TimescaleDB extension not found. Run: CREATE EXTENSION timescaledb;")
        except Exception as e:
            log.warning("⚠️ TimescaleDB setup skipped: %s", e)
        
        # 테이블 목록 확인
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            log.info("✅ Schema initialization complete! Tables: %s", tables)
        
        conn.close()
        
    except Exception as e:
        log.exception("❌ Schema initialization failed")
        raise


if __name__ == "__main__":
    ensure_schema()

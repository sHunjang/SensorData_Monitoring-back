"""
데이터베이스 스키마 초기화 모듈

주요 기능:
- PostgreSQL 데이터베이스 스키마 생성
- 모든 테이블과 인덱스 초기화
- TimescaleDB 지원 (선택적)
- Idempotent 실행 (중복 실행 안전)

테이블 구조:
- modbus_data: 전력 데이터 (TAC4300)
- env_data: 환경 데이터 (온도, 습도)
- solar_data: 태양광 데이터 (일사량)

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

# 🎯 통일된 스키마 DDL (언더스코어 포함)
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

-- solar_data 테이블 (태양광 데이터)
CREATE TABLE IF NOT EXISTS solar_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    irradiance DOUBLE PRECISION
);

-- solar_data 인덱스
CREATE INDEX IF NOT EXISTS idx_solar_device_time ON solar_data(device_id, time_stamp DESC);
"""

# TimescaleDB 하이퍼테이블 생성 (선택적)
DDL_TIMESCALE = r"""
-- TimescaleDB 하이퍼테이블 생성 (시계열 데이터 최적화)
SELECT create_hypertable('modbus_data', 'time_stamp', if_not_exists => TRUE);
SELECT create_hypertable('env_data', 'time_stamp', if_not_exists => TRUE);
SELECT create_hypertable('solar_data', 'time_stamp', if_not_exists => TRUE);
"""


def ensure_schema():
    """
    데이터베이스 스키마 초기화
    
    - PG_DSN 환경변수에서 연결 정보 읽기
    - 모든 테이블과 인덱스 생성
    - TimescaleDB 확장 감지 및 하이퍼테이블 생성
    - 멱등성 보장 (중복 실행 안전)
    """
    # 1. 환경변수에서 DSN 읽기
    dsn = os.getenv("PG_DSN", "postgresql://postgres:postgres@127.0.0.1:5432/energydb")
    log.info(f"ensure_schema: connecting to DB")
    log.debug(f"DSN: {dsn}")
    
    try:
        # 2. PostgreSQL 연결
        with psycopg2.connect(dsn) as conn:
            conn.autocommit = True
            
            with conn.cursor() as cur:
                # 3. 기본 테이블과 인덱스 생성
                log.info("ensure_schema: creating base tables and indexes (if not exists)")
                cur.execute(DDL_BASE)
                log.info("✅ Base tables created successfully")
                
                # 4. TimescaleDB 확장 확인
                try:
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_available_extensions 
                            WHERE name='timescaledb' AND installed_version IS NOT NULL
                        )
                    """)
                    has_ts = cur.fetchone()[0]
                    
                except Exception as e:
                    log.warning(f"Could not check timescaledb availability: {e}")
                    has_ts = False
                
                # 5. TimescaleDB 하이퍼테이블 생성 (선택적)
                if has_ts:
                    log.info("ensure_schema: timescaledb installed, ensuring hypertables")
                    try:
                        cur.execute(DDL_TIMESCALE)
                        log.info("✅ TimescaleDB hypertables created successfully")
                        
                    except Exception as e:
                        log.error(f"Failed to create hypertables: {e}")
                        log.info("Continuing without TimescaleDB optimization...")
                else:
                    log.info("ensure_schema: timescaledb not installed, skipping hypertable creation")
                
                # 6. 테이블 생성 확인
                cur.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    ORDER BY tablename
                """)
                tables = [row[0] for row in cur.fetchall()]
                log.info(f"✅ Schema initialization complete! Tables: {tables}")
                
    except psycopg2.OperationalError as e:
        log.error(f"❌ Database connection failed: {e}")
        log.error(f"   DSN: {dsn}")
        log.error("Please ensure PostgreSQL is running and accessible")
        raise
        
    except Exception as e:
        log.error(f"❌ Schema initialization failed: {e}")
        raise


def drop_schema():
    """
    개발용: 모든 테이블 삭제
    
    주의: 운영 환경에서는 사용 금지!
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    log.warning("⚠️  drop_schema: DROPPING ALL TABLES!")
    
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS modbus_data CASCADE")
            cur.execute("DROP TABLE IF EXISTS env_data CASCADE")
            cur.execute("DROP TABLE IF EXISTS solar_data CASCADE")
            log.warning("🗑️  All tables dropped!")


def verify_schema():
    """
    스키마 검증: 모든 테이블과 컬럼이 올바른지 확인
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            # 테이블 존재 확인
            required_tables = ["modbus_data", "env_data", "solar_data"]
            
            for table in required_tables:
                cur.execute(f"""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '{table}' AND table_schema = 'public'
                """)
                exists = cur.fetchone()[0] > 0
                
                if exists:
                    log.info(f"✅ Table '{table}' exists")
                    
                    # 컬럼 정보 확인
                    cur.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """)
                    columns = cur.fetchall()
                    log.info(f"   Columns: {[f'{col[0]}({col[1]})' for col in columns]}")
                else:
                    log.error(f"❌ Table '{table}' missing!")
            
            # 인덱스 확인
            cur.execute("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname
            """)
            indexes = cur.fetchall()
            log.info(f"✅ Indexes: {[f'{idx[1]}.{idx[0]}' for idx in indexes]}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "drop":
            drop_schema()
        elif sys.argv[1] == "verify":
            verify_schema()
        else:
            print("Usage: python bootstrap.py [drop|verify]")
    else:
        ensure_schema()

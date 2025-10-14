"""
데이터베이스 스키마 초기화 및 마이그레이션 모듈

주요 기능:
- 기존 테이블(modbus_data, env_data, solar_data) 보존
- 센서 타입별 집계 테이블 생성
- 기존 데이터를 새 집계 테이블로 마이그레이션
- TimescaleDB 지원 (선택적)
- Idempotent 실행 (중복 실행 안전)

테이블 구조:
[원본 테이블 - 5초 수집 데이터]
- modbus_data: 전력 원시 데이터 (3상 4선 + 3상 3선 혼재)
- env_data: 환경 원시 데이터 (온도, 습도)
- solar_data: 태양광 원시 데이터 (일사량)

[집계 테이블 - 센서 타입별 분리]
📌 Modbus 3상 4선식 (ID: 11, 12, 13)
  - modbus_4wire_1min, modbus_4wire_15min, modbus_4wire_1hour, modbus_4wire_1day, modbus_4wire_1year

📌 Modbus 3상 3선식 (ID: 14, 15)
  - modbus_3wire_1min, modbus_3wire_15min, modbus_3wire_1hour, modbus_3wire_1day, modbus_3wire_1year

📌 환경센서 (ID: 21, 22, 23)
  - env_1min, env_15min, env_1hour, env_1day, env_1year

📌 태양광센서 (ID: 31)
  - solar_1min, solar_15min, solar_1hour, solar_1day, solar_1year

사용법:
  python -m src.db.bootstrap              # 스키마만 생성
  python -m src.db.bootstrap --migrate    # 스키마 생성 + 기존 데이터 마이그레이션
"""

import os
import logging
import psycopg2
from datetime import datetime

# 로깅 설정
log = logging.getLogger("bootstrap")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
log.addHandler(handler)


# ==================== 원본 테이블 DDL (기존 유지) ====================
# 5초마다 수집되는 원시 데이터 저장
DDL_BASE_TABLES = r"""
-- ============================================================
-- 원본 테이블 (5초 수집 데이터)
-- ⚠️ 기존 데이터 보존: IF NOT EXISTS 사용
-- ============================================================

-- modbus_data 테이블 (전력 원시 데이터 - 5초 수집)
-- 3상 4선식(11,12,13)과 3상 3선식(14,15) 혼재
CREATE TABLE IF NOT EXISTS modbus_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    -- 3상 4선식 전용 (Line-to-Line): ID 11,12,13
    avg_line_to_line_volts_v DOUBLE PRECISION,
    -- 3상 3선식 전용 (Line-to-Neutral): ID 14,15
    avg_line_to_neutral_volts_v DOUBLE PRECISION,
    -- 공통 컬럼
    sum_line_currents_a DOUBLE PRECISION,
    total_active_power_kw DOUBLE PRECISION,
    total_reactive_power_kvar DOUBLE PRECISION,
    total_apparent_power_kva DOUBLE PRECISION,
    total_power_factor DOUBLE PRECISION,
    total_active_energy_kwh DOUBLE PRECISION,
    total_reactive_energy_kvarh DOUBLE PRECISION,
    total_apparent_energy_kvah DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_modbus_device_time ON modbus_data(device_id, time_stamp DESC);

-- env_data 테이블 (환경 원시 데이터 - 5초 수집)
CREATE TABLE IF NOT EXISTS env_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_env_device_time ON env_data(device_id, time_stamp DESC);

-- solar_data 테이블 (일사량 원시 데이터 - 5초 수집)
CREATE TABLE IF NOT EXISTS solar_data (
    time_stamp TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    irradiance DOUBLE PRECISION  -- 일사량 (W/m²)
);
CREATE INDEX IF NOT EXISTS idx_solar_device_time ON solar_data(device_id, time_stamp DESC);
"""


# ==================== Modbus 3상 4선식 집계 테이블 ====================
# ID: 11, 12, 13 (Line-to-Line 전압 측정)
DDL_MODBUS_4WIRE_AGG = r"""
-- ============================================================
-- Modbus 3상 4선식 집계 테이블 (ID: 11, 12, 13)
-- 특징: Line-to-Line 전압 (200-240V)
-- ============================================================

-- ============ 1분 집계 테이블 ============
-- 용도: 하루 단위 그래프 (00:00~23:59, 최대 1440개 포인트)
CREATE TABLE IF NOT EXISTS modbus_4wire_1min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    -- 전압 (Line-to-Line)
    avg_voltage_ll_v DOUBLE PRECISION,
    min_voltage_ll_v DOUBLE PRECISION,
    max_voltage_ll_v DOUBLE PRECISION,
    -- 전류
    avg_current_a DOUBLE PRECISION,
    min_current_a DOUBLE PRECISION,
    max_current_a DOUBLE PRECISION,
    -- 전력
    avg_active_power_kw DOUBLE PRECISION,
    avg_reactive_power_kvar DOUBLE PRECISION,
    avg_apparent_power_kva DOUBLE PRECISION,
    avg_power_factor DOUBLE PRECISION,
    -- 에너지 (delta 계산용)
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    -- 통계
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_4wire_1min_device ON modbus_4wire_1min(device_id, bucket DESC);

-- ============ 15분 집계 테이블 ============
-- 용도: 1주 단위 그래프 (7일간, 약 672개 포인트)
-- 📌 15분 이후부터는 에너지(kWh) 데이터만 저장
CREATE TABLE IF NOT EXISTS modbus_4wire_15min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    -- 에너지 데이터 (주력 데이터)
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    -- 피크 전력 (15분 구간 최대값)
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_4wire_15min_device ON modbus_4wire_15min(device_id, bucket DESC);

-- ============ 1시간 집계 테이블 ============
-- 용도: 1달 단위 그래프 (30~31일간, 약 720~744개 포인트)
CREATE TABLE IF NOT EXISTS modbus_4wire_1hour (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_4wire_1hour_device ON modbus_4wire_1hour(device_id, bucket DESC);

-- ============ 1일 집계 테이블 ============
-- 용도: 1년 단위 그래프 (365일간, 365개 포인트)
CREATE TABLE IF NOT EXISTS modbus_4wire_1day (
    bucket TIMESTAMPTZ NOT NULL,  -- 일자 (KST 00:00 기준)
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_4wire_1day_device ON modbus_4wire_1day(device_id, bucket DESC);

-- ============ 1년 집계 테이블 ============
-- 용도: 장기 통계 및 추세 분석
CREATE TABLE IF NOT EXISTS modbus_4wire_1year (
    bucket TIMESTAMPTZ NOT NULL,  -- 년도 (KST 1월 1일 00:00 기준)
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_4wire_1year_device ON modbus_4wire_1year(device_id, bucket DESC);
"""


# ==================== Modbus 3상 3선식 집계 테이블 ====================
# ID: 14, 15 (Line-to-Neutral 전압 측정)
DDL_MODBUS_3WIRE_AGG = r"""
-- ============================================================
-- Modbus 3상 3선식 집계 테이블 (ID: 14, 15)
-- 특징: Line-to-Neutral 전압 (110-140V)
-- ============================================================

-- ============ 1분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS modbus_3wire_1min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    -- 전압 (Line-to-Neutral)
    avg_voltage_ln_v DOUBLE PRECISION,
    min_voltage_ln_v DOUBLE PRECISION,
    max_voltage_ln_v DOUBLE PRECISION,
    -- 전류
    avg_current_a DOUBLE PRECISION,
    min_current_a DOUBLE PRECISION,
    max_current_a DOUBLE PRECISION,
    -- 전력
    avg_active_power_kw DOUBLE PRECISION,
    avg_reactive_power_kvar DOUBLE PRECISION,
    avg_apparent_power_kva DOUBLE PRECISION,
    avg_power_factor DOUBLE PRECISION,
    -- 에너지
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    -- 통계
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_3wire_1min_device ON modbus_3wire_1min(device_id, bucket DESC);

-- ============ 15분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS modbus_3wire_15min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_3wire_15min_device ON modbus_3wire_15min(device_id, bucket DESC);

-- ============ 1시간 집계 테이블 ============
CREATE TABLE IF NOT EXISTS modbus_3wire_1hour (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_3wire_1hour_device ON modbus_3wire_1hour(device_id, bucket DESC);

-- ============ 1일 집계 테이블 ============
CREATE TABLE IF NOT EXISTS modbus_3wire_1day (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_3wire_1day_device ON modbus_3wire_1day(device_id, bucket DESC);

-- ============ 1년 집계 테이블 ============
CREATE TABLE IF NOT EXISTS modbus_3wire_1year (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    energy_start_kwh DOUBLE PRECISION,
    energy_end_kwh DOUBLE PRECISION,
    energy_delta_kwh DOUBLE PRECISION,
    peak_power_kw DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_3wire_1year_device ON modbus_3wire_1year(device_id, bucket DESC);
"""


# ==================== 환경센서 집계 테이블 ====================
# ID: 21, 22, 23 (온도, 습도)
DDL_ENV_AGG = r"""
-- ============================================================
-- 환경센서 집계 테이블 (ID: 21, 22, 23)
-- 특징: 온도/습도 측정
-- ============================================================

-- ============ 1분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS env_1min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    -- 온도 통계
    avg_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    -- 습도 통계
    avg_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_env_1min_device ON env_1min(device_id, bucket DESC);

-- ============ 15분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS env_15min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_env_15min_device ON env_15min(device_id, bucket DESC);

-- ============ 1시간 집계 테이블 ============
CREATE TABLE IF NOT EXISTS env_1hour (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_env_1hour_device ON env_1hour(device_id, bucket DESC);

-- ============ 1일 집계 테이블 ============
CREATE TABLE IF NOT EXISTS env_1day (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_env_1day_device ON env_1day(device_id, bucket DESC);

-- ============ 1년 집계 테이블 ============
CREATE TABLE IF NOT EXISTS env_1year (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_env_1year_device ON env_1year(device_id, bucket DESC);
"""


# ==================== 태양광센서 집계 테이블 ====================
# ID: 31 (일사량)
DDL_SOLAR_AGG = r"""
-- ============================================================
-- 태양광센서 집계 테이블 (ID: 31)
-- 특징: 일사량 측정 (W/m²)
-- ============================================================

-- ============ 1분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS solar_1min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_solar_1min_device ON solar_1min(device_id, bucket DESC);

-- ============ 15분 집계 테이블 ============
CREATE TABLE IF NOT EXISTS solar_15min (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_solar_15min_device ON solar_15min(device_id, bucket DESC);

-- ============ 1시간 집계 테이블 ============
CREATE TABLE IF NOT EXISTS solar_1hour (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_solar_1hour_device ON solar_1hour(device_id, bucket DESC);

-- ============ 1일 집계 테이블 ============
CREATE TABLE IF NOT EXISTS solar_1day (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_solar_1day_device ON solar_1day(device_id, bucket DESC);

-- ============ 1년 집계 테이블 ============
CREATE TABLE IF NOT EXISTS solar_1year (
    bucket TIMESTAMPTZ NOT NULL,
    device_id INT NOT NULL,
    avg_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    data_points INT,
    PRIMARY KEY (bucket, device_id)
);
CREATE INDEX IF NOT EXISTS idx_solar_1year_device ON solar_1year(device_id, bucket DESC);
"""


# ==================== TimescaleDB 설정 ====================
DDL_TIMESCALEDB = r"""
-- TimescaleDB hypertable 생성 (선택적)
-- 원본 테이블
SELECT create_hypertable('modbus_data', 'time_stamp', if_not_exists => TRUE);
SELECT create_hypertable('env_data', 'time_stamp', if_not_exists => TRUE);
SELECT create_hypertable('solar_data', 'time_stamp', if_not_exists => TRUE);

-- Modbus 3상 4선식 집계 테이블
SELECT create_hypertable('modbus_4wire_1min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_4wire_15min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_4wire_1hour', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_4wire_1day', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_4wire_1year', 'bucket', if_not_exists => TRUE);

-- Modbus 3상 3선식 집계 테이블
SELECT create_hypertable('modbus_3wire_1min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_3wire_15min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_3wire_1hour', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_3wire_1day', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('modbus_3wire_1year', 'bucket', if_not_exists => TRUE);

-- 환경센서 집계 테이블
SELECT create_hypertable('env_1min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('env_15min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('env_1hour', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('env_1day', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('env_1year', 'bucket', if_not_exists => TRUE);

-- 태양광센서 집계 테이블
SELECT create_hypertable('solar_1min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('solar_15min', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('solar_1hour', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('solar_1day', 'bucket', if_not_exists => TRUE);
SELECT create_hypertable('solar_1year', 'bucket', if_not_exists => TRUE);
"""


def ensure_schema():
    """
    스키마 초기화 - 기존 테이블 보존 + 집계 테이블 생성
    
    동작 순서:
    1. 기존 원본 테이블 확인 (modbus_data, env_data, solar_data)
    2. 새 집계 테이블 생성 (타입별 분리)
       - Modbus 3상 4선식 (ID: 11,12,13)
       - Modbus 3상 3선식 (ID: 14,15)
       - 환경센서 (ID: 21,22,23)
       - 태양광센서 (ID: 31)
    3. TimescaleDB 확장 확인 및 hypertable 생성 (선택적)
    4. 생성된 테이블 목록 출력
    
    ⚠️ 주의: 기존 데이터는 삭제되지 않음 (DROP 명령 없음)
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    log.info("🔌 Connecting to PostgreSQL...")
    
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        
        # 1단계: 기존 원본 테이블 생성/확인
        log.info("=" * 70)
        log.info("✅ Step 1: Ensuring base tables (modbus_data, env_data, solar_data)...")
        log.info("=" * 70)
        with conn.cursor() as cur:
            cur.execute(DDL_BASE_TABLES)
        log.info("✅ Base tables verified (existing data preserved)")
        
        # 2단계: 집계 테이블 생성
        log.info("")
        log.info("=" * 70)
        log.info("✅ Step 2: Creating aggregation tables (by sensor type)...")
        log.info("=" * 70)
        
        with conn.cursor() as cur:
            # Modbus 3상 4선식
            log.info("📊 Creating Modbus 3-Phase 4-Wire tables (ID: 11,12,13)...")
            cur.execute(DDL_MODBUS_4WIRE_AGG)
            log.info("  ✅ modbus_4wire_1min, modbus_4wire_15min, modbus_4wire_1hour,")
            log.info("     modbus_4wire_1day, modbus_4wire_1year")
            
            # Modbus 3상 3선식
            log.info("📊 Creating Modbus 3-Phase 3-Wire tables (ID: 14,15)...")
            cur.execute(DDL_MODBUS_3WIRE_AGG)
            log.info("  ✅ modbus_3wire_1min, modbus_3wire_15min, modbus_3wire_1hour,")
            log.info("     modbus_3wire_1day, modbus_3wire_1year")
            
            # 환경센서
            log.info("📊 Creating Environmental sensor tables (ID: 21,22,23)...")
            cur.execute(DDL_ENV_AGG)
            log.info("  ✅ env_1min, env_15min, env_1hour, env_1day, env_1year")
            
            # 태양광센서
            log.info("📊 Creating Solar sensor tables (ID: 31)...")
            cur.execute(DDL_SOLAR_AGG)
            log.info("  ✅ solar_1min, solar_15min, solar_1hour, solar_1day, solar_1year")
        
        # 3단계: TimescaleDB 확장 확인 및 hypertable 생성
        log.info("")
        log.info("=" * 70)
        log.info("📊 Step 3: Checking TimescaleDB extension...")
        log.info("=" * 70)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'timescaledb'")
                if cur.fetchone():
                    log.info("✅ TimescaleDB detected, creating hypertables...")
                    cur.execute(DDL_TIMESCALEDB)
                    log.info("✅ TimescaleDB hypertables created for all tables")
                else:
                    log.info("⚠️  TimescaleDB not installed, skipping hypertables")
                    log.info("   (Regular PostgreSQL tables created successfully)")
        except Exception as e:
            log.warning(f"⚠️  TimescaleDB setup skipped: {e}")
        
        # 4단계: 생성된 테이블 목록 확인
        log.info("")
        log.info("=" * 70)
        log.info("📋 Step 4: Verifying created tables...")
        log.info("=" * 70)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            # 테이블 분류
            base_tables = [t for t in tables if t in ['modbus_data', 'env_data', 'solar_data']]
            modbus_4w = [t for t in tables if t.startswith('modbus_4wire_')]
            modbus_3w = [t for t in tables if t.startswith('modbus_3wire_')]
            env_tables = [t for t in tables if t.startswith('env_')]
            solar_tables = [t for t in tables if t.startswith('solar_')]
            
            log.info(f"✅ Total tables: {len(tables)}")
            log.info(f"   📁 Base tables: {len(base_tables)} - {', '.join(base_tables)}")
            log.info(f"   🔌 Modbus 4-wire: {len(modbus_4w)} tables")
            log.info(f"   🔌 Modbus 3-wire: {len(modbus_3w)} tables")
            log.info(f"   🌡️  Environment: {len(env_tables)} tables")
            log.info(f"   ☀️  Solar: {len(solar_tables)} tables")
        
        conn.close()
        log.info("")
        log.info("=" * 70)
        log.info("✅ Schema initialization completed successfully!")
        log.info("=" * 70)
        
    except Exception as e:
        log.exception("❌ Schema initialization failed")
        raise


def migrate_existing_data():
    """
    기존 데이터를 집계 테이블로 마이그레이션
    
    동작:
    1. modbus_data (ID 11,12,13) -> modbus_4wire_1min
    2. modbus_data (ID 14,15) -> modbus_3wire_1min
    3. env_data -> env_1min
    4. solar_data -> solar_1min
    
    ⚠️ 주의: 
    - 중복 실행 시 ON CONFLICT DO NOTHING으로 중복 방지
    - 대량 데이터의 경우 시간이 오래 걸릴 수 있음
    """
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@127.0.0.1:5432/energydb")
    log.info("")
    log.info("=" * 70)
    log.info("🔄 Starting data migration from raw tables to aggregated tables...")
    log.info("=" * 70)
    
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False  # 트랜잭션 사용
        
        # ========== Modbus 3상 4선식 마이그레이션 (ID: 11,12,13) ==========
        log.info("")
        log.info("📊 [1/4] Migrating Modbus 4-Wire data (ID: 11,12,13)...")
        with conn.cursor() as cur:
            # 데이터 개수 확인
            cur.execute("SELECT COUNT(*) FROM modbus_data WHERE device_id IN (11, 12, 13)")
            total_count = cur.fetchone()[0]
            log.info(f"  📥 Source data: {total_count:,} rows")
            
            if total_count > 0:
                # 1분 단위로 집계
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
                    GROUP BY bucket, device_id
                    ON CONFLICT (bucket, device_id) DO NOTHING;
                """)
                migrated = cur.rowcount
                log.info(f"  ✅ Migrated {migrated:,} aggregated rows to modbus_4wire_1min")
        
        # ========== Modbus 3상 3선식 마이그레이션 (ID: 14,15) ==========
        log.info("")
        log.info("📊 [2/4] Migrating Modbus 3-Wire data (ID: 14,15)...")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM modbus_data WHERE device_id IN (14, 15)")
            total_count = cur.fetchone()[0]
            log.info(f"  📥 Source data: {total_count:,} rows")
            
            if total_count > 0:
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
                    GROUP BY bucket, device_id
                    ON CONFLICT (bucket, device_id) DO NOTHING;
                """)
                migrated = cur.rowcount
                log.info(f"  ✅ Migrated {migrated:,} aggregated rows to modbus_3wire_1min")
        
        # ========== 환경센서 마이그레이션 ==========
        log.info("")
        log.info("📊 [3/4] Migrating Environmental sensor data (ID: 21,22,23)...")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM env_data")
            total_count = cur.fetchone()[0]
            log.info(f"  📥 Source data: {total_count:,} rows")
            
            if total_count > 0:
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
                    GROUP BY bucket, device_id
                    ON CONFLICT (bucket, device_id) DO NOTHING;
                """)
                migrated = cur.rowcount
                log.info(f"  ✅ Migrated {migrated:,} aggregated rows to env_1min")
        
        # ========== 태양광센서 마이그레이션 ==========
        log.info("")
        log.info("📊 [4/4] Migrating Solar sensor data (ID: 31)...")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM solar_data")
            total_count = cur.fetchone()[0]
            log.info(f"  📥 Source data: {total_count:,} rows")
            
            if total_count > 0:
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
                    GROUP BY bucket, device_id
                    ON CONFLICT (bucket, device_id) DO NOTHING;
                """)
                migrated = cur.rowcount
                log.info(f"  ✅ Migrated {migrated:,} aggregated rows to solar_1min")
        
        # 트랜잭션 커밋
        conn.commit()
        log.info("")
        log.info("=" * 70)
        log.info("✅ Data migration completed successfully!")
        log.info("=" * 70)
        conn.close()
        
    except Exception as e:
        log.exception("❌ Data migration failed")
        if conn:
            conn.rollback()
            conn.close()
        raise


if __name__ == "__main__":
    log.info("")
    log.info("=" * 70)
    log.info("🚀 Database Bootstrap & Migration Tool")
    log.info("   Real-time IoT Monitoring System - Multi-Resolution Schema")
    log.info("=" * 70)
    
    # 1단계: 스키마 생성
    ensure_schema()
    
    # 2단계: 기존 데이터 마이그레이션 (선택적)
    import sys
    if "--migrate" in sys.argv:
        migrate_existing_data()
    else:
        log.info("")
        log.info("=" * 70)
        log.info("💡 Tip: Run with --migrate flag to migrate existing data")
        log.info("   Example: python -m src.db.bootstrap --migrate")
        log.info("=" * 70)
    
    log.info("")
    log.info("🎉 Bootstrap completed successfully!")
    log.info("")

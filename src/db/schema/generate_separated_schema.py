"""
장치별 분리 스키마 자동 생성 스크립트

생성 대상:
  - 전력량계 5개: modbus_data_11~15 + 각 8단계 집계 (45개)
  - 온습도 3개: env_data_21~23 + 각 8단계 집계 (27개)
  - 일사량 1개: solar_data + 8단계 집계 (9개)
  총: 81개 테이블

사용법:
    python -m src.db.generate_separated_schema

출력:
    src/db/schema_all_separated.sql
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ============================================================================
# 설정
# ============================================================================
MODBUS_DEVICES = [11, 12, 13, 14, 15]
ENV_DEVICES = [21, 22, 23]
AGG_STAGES = ['1m', '15m', '1h', '1d', '1w', '1mo', '6mo', '1y']

# Chunk 간격 (TimescaleDB)
CHUNK_INTERVALS = {
    '1m': '30 days',
    '15m': '90 days',
    '1h': '180 days',
    '1d': '1 year',
    '1w': '2 years',
    '1mo': '5 years',
    '6mo': '10 years',
    '1y': '10 years',
}

# ============================================================================
# SQL 템플릿 함수
# ============================================================================

def generate_modbus_raw(device_id: int) -> str:
    """전력량계 원천 테이블 SQL 생성"""
    return f"""
-- Modbus Device {device_id} 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_{device_id} (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_line_to_line_volts_v DOUBLE PRECISION,
    avg_line_to_neutral_volts_v DOUBLE PRECISION,
    sum_line_currents_a DOUBLE PRECISION,
    total_active_power_kw DOUBLE PRECISION,
    total_reactive_power_kvar DOUBLE PRECISION,
    total_apparent_power_kva DOUBLE PRECISION,
    total_power_factor DOUBLE PRECISION,
    total_active_energy_kwh DOUBLE PRECISION
);

SELECT create_hypertable('modbus_data_{device_id}', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_{device_id}_time 
    ON modbus_data_{device_id} (time_stamp DESC);
"""


def generate_modbus_agg(device_id: int, stage: str) -> str:
    """전력량계 집계 테이블 SQL 생성"""
    return f"""
-- Device {device_id} - {stage} 집계
CREATE TABLE IF NOT EXISTS agg_modbus_{device_id}_{stage} (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_avg_line_to_line_volts_v DOUBLE PRECISION,
    max_avg_line_to_line_volts_v DOUBLE PRECISION,
    min_avg_line_to_line_volts_v DOUBLE PRECISION,
    avg_avg_line_to_neutral_volts_v DOUBLE PRECISION,
    max_avg_line_to_neutral_volts_v DOUBLE PRECISION,
    min_avg_line_to_neutral_volts_v DOUBLE PRECISION,
    avg_sum_line_currents_a DOUBLE PRECISION,
    max_sum_line_currents_a DOUBLE PRECISION,
    min_sum_line_currents_a DOUBLE PRECISION,
    avg_total_active_power_kw DOUBLE PRECISION,
    max_total_active_power_kw DOUBLE PRECISION,
    min_total_active_power_kw DOUBLE PRECISION,
    sum_total_active_power_kw DOUBLE PRECISION,
    avg_total_reactive_power_kvar DOUBLE PRECISION,
    avg_total_apparent_power_kva DOUBLE PRECISION,
    avg_total_power_factor DOUBLE PRECISION,
    min_total_power_factor DOUBLE PRECISION,
    min_total_active_energy_kwh DOUBLE PRECISION,
    max_total_active_energy_kwh DOUBLE PRECISION,
    delta_total_active_energy_kwh DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_modbus_{device_id}_{stage}', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '{CHUNK_INTERVALS[stage]}'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_{device_id}_{stage} 
    ON agg_modbus_{device_id}_{stage} (bucket DESC);
"""


def generate_env_raw(device_id: int) -> str:
    """온습도 원천 테이블 SQL 생성"""
    return f"""
-- Env Device {device_id} 원천 테이블
CREATE TABLE IF NOT EXISTS env_data_{device_id} (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

SELECT create_hypertable('env_data_{device_id}', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_env_{device_id}_time 
    ON env_data_{device_id} (time_stamp DESC);
"""


def generate_env_agg(device_id: int, stage: str) -> str:
    """온습도 집계 테이블 SQL 생성"""
    return f"""
-- Device {device_id} - {stage} 집계
CREATE TABLE IF NOT EXISTS agg_env_{device_id}_{stage} (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_{device_id}_{stage}', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '{CHUNK_INTERVALS[stage]}'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_{device_id}_{stage} 
    ON agg_env_{device_id}_{stage} (bucket DESC);
"""


def generate_solar_raw() -> str:
    """일사량 원천 테이블 SQL 생성"""
    return """
-- Solar 원천 테이블
CREATE TABLE IF NOT EXISTS solar_data (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    irradiance DOUBLE PRECISION
);

SELECT create_hypertable('solar_data', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_solar_time 
    ON solar_data (time_stamp DESC);
"""


def generate_solar_agg(stage: str) -> str:
    """일사량 집계 테이블 SQL 생성"""
    return f"""
-- Solar - {stage} 집계
CREATE TABLE IF NOT EXISTS agg_solar_{stage} (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_{stage}', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '{CHUNK_INTERVALS[stage]}'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_{stage} 
    ON agg_solar_{stage} (bucket DESC);
"""


# ============================================================================
# 전체 스키마 생성
# ============================================================================

def generate_full_schema() -> str:
    """전체 통합 스키마 생성"""
    sql = """-- ============================================================================
-- RS485 장치별 분리 스키마 (PostgreSQL 16 + TimescaleDB)
-- 자동 생성: generate_separated_schema.py
-- 
-- 구조:
--   전력량계: modbus_data_11~15 (5개) + 집계 40개 = 45개
--   온습도: env_data_21~23 (3개) + 집계 24개 = 27개
--   일사량: solar_data (1개) + 집계 8개 = 9개
--   총: 81개 테이블
-- 
-- 실행:
--   psql -U postgres -d energydb -f src/db/schema_all_separated.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

"""
    
    # 1. 전력량계 원천 테이블
    sql += """-- ============================================================================
-- 1. 전력량계 원천 테이블 (5개)
-- ============================================================================
"""
    for device_id in MODBUS_DEVICES:
        sql += generate_modbus_raw(device_id)
    
    # 2. 전력량계 집계 테이블
    for device_id in MODBUS_DEVICES:
        sql += f"""
-- ============================================================================
-- 2. Modbus Device {device_id} 집계 테이블 (8단계)
-- ============================================================================
"""
        for stage in AGG_STAGES:
            sql += generate_modbus_agg(device_id, stage)
    
    # 3. 온습도 원천 테이블
    sql += """
-- ============================================================================
-- 3. 온습도 원천 테이블 (3개)
-- ============================================================================
"""
    for device_id in ENV_DEVICES:
        sql += generate_env_raw(device_id)
    
    # 4. 온습도 집계 테이블
    for device_id in ENV_DEVICES:
        sql += f"""
-- ============================================================================
-- 4. Env Device {device_id} 집계 테이블 (8단계)
-- ============================================================================
"""
        for stage in AGG_STAGES:
            sql += generate_env_agg(device_id, stage)
    
    # 5. 일사량 테이블
    sql += """
-- ============================================================================
-- 5. 일사량 테이블 (1개 + 집계 8개)
-- ============================================================================
"""
    sql += generate_solar_raw()
    for stage in AGG_STAGES:
        sql += generate_solar_agg(stage)
    
    # 6. 압축 정책
    sql += """
-- ============================================================================
-- 6. 압축 정책 (7일 후 자동 압축)
-- ============================================================================
"""
    for device_id in MODBUS_DEVICES:
        sql += f"ALTER TABLE modbus_data_{device_id} SET (timescaledb.compress);\n"
        sql += f"SELECT add_compression_policy('modbus_data_{device_id}', INTERVAL '7 days', if_not_exists => TRUE);\n"
    
    for device_id in ENV_DEVICES:
        sql += f"ALTER TABLE env_data_{device_id} SET (timescaledb.compress);\n"
        sql += f"SELECT add_compression_policy('env_data_{device_id}', INTERVAL '7 days', if_not_exists => TRUE);\n"
    
    sql += "ALTER TABLE solar_data SET (timescaledb.compress);\n"
    sql += "SELECT add_compression_policy('solar_data', INTERVAL '7 days', if_not_exists => TRUE);\n"
    
    # 7. 보존 정책
    sql += """
-- ============================================================================
-- 7. 보존 정책 (30일 후 자동 삭제)
-- ============================================================================
"""
    for device_id in MODBUS_DEVICES:
        sql += f"SELECT add_retention_policy('modbus_data_{device_id}', INTERVAL '30 days', if_not_exists => TRUE);\n"
    
    for device_id in ENV_DEVICES:
        sql += f"SELECT add_retention_policy('env_data_{device_id}', INTERVAL '30 days', if_not_exists => TRUE);\n"
    
    sql += "SELECT add_retention_policy('solar_data', INTERVAL '30 days', if_not_exists => TRUE);\n"
    
    # 8. 완료 메시지
    sql += """
-- ============================================================================
-- 8. 스키마 생성 완료
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'Schema creation complete: 81 tables';
    RAISE NOTICE '  - Modbus: 45 tables (5 raw + 40 agg)';
    RAISE NOTICE '  - Env: 27 tables (3 raw + 24 agg)';
    RAISE NOTICE '  - Solar: 9 tables (1 raw + 8 agg)';
END $$;
"""
    
    return sql


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("Schema Generator - Device Separated Tables")
    print("=" * 80)
    print()
    
    # SQL 생성
    print("Generating SQL schema...")
    sql_content = generate_full_schema()
    
    # 파일 저장
    output_dir = Path(__file__).parent
    output_file = output_dir / "schema_all_separated.sql"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print(f"OK: Saved to {output_file}")
    print()
    print("Summary:")
    print(f"  - Modbus devices: {len(MODBUS_DEVICES)} (IDs: {MODBUS_DEVICES})")
    print(f"  - Env devices: {len(ENV_DEVICES)} (IDs: {ENV_DEVICES})")
    print(f"  - Solar device: 1 (ID: 31)")
    print(f"  - Aggregation stages: {len(AGG_STAGES)} (1m to 1y)")
    print(f"  - Total tables: {len(MODBUS_DEVICES) * 9 + len(ENV_DEVICES) * 9 + 9} = 81")
    print()
    print("Next step:")
    print(f"  psql -U postgres -d energydb -f {output_file}")
    print()


if __name__ == '__main__':
    main()

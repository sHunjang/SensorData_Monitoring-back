"""
온습도 전용 스키마 생성기 (Device 21-23)

생성 대상:
  - env_data_21 ~ env_data_23 (3개 원천)
  - 각 장치별 8단계 집계 (총 24개)
  
사용법:
    python -m src.db.generate_env_schema
    
출력:
    src/db/schema_env.sql
"""

from pathlib import Path

DEVICE_IDS = [21, 22, 23]
AGG_STAGES = ['1m', '15m', '1h', '1d', '1w', '1mo', '6mo', '1y']

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

def generate_raw_table(device_id: int) -> str:
    """원천 테이블 SQL"""
    return f"""
-- Env Device {device_id} 원천
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

def generate_agg_table(device_id: int, stage: str) -> str:
    """집계 테이블 SQL"""
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

def generate_schema() -> str:
    """전체 스키마 생성"""
    sql = """-- ============================================================================
-- Env 온습도 스키마 (Device 21-23)
-- 자동 생성: generate_env_schema.py
-- 총: 3개 원천 + 24개 집계 = 27개 테이블
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 원천 테이블 (3개)
-- ============================================================================
"""
    
    for device_id in DEVICE_IDS:
        sql += generate_raw_table(device_id)
    
    # 각 장치별 집계 테이블
    for device_id in DEVICE_IDS:
        sql += f"""
-- ============================================================================
-- 2. Device {device_id} 집계 (8단계)
-- ============================================================================
"""
        for stage in AGG_STAGES:
            sql += generate_agg_table(device_id, stage)
    
    # 압축 정책
    sql += """
-- ============================================================================
-- 3. 압축 정책
-- ============================================================================
"""
    for device_id in DEVICE_IDS:
        sql += f"ALTER TABLE env_data_{device_id} SET (timescaledb.compress);\n"
        sql += f"SELECT add_compression_policy('env_data_{device_id}', INTERVAL '7 days', if_not_exists => TRUE);\n"
    
    # 보존 정책
    sql += """
-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- ============================================================================
"""
    for device_id in DEVICE_IDS:
        sql += f"SELECT add_retention_policy('env_data_{device_id}', INTERVAL '1 year', if_not_exists => TRUE);\n"
    
    sql += """
DO $$
BEGIN
    RAISE NOTICE 'Env schema complete: 27 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;
"""
    
    return sql

def main():
    print("=" * 70)
    print("Env Schema Generator (Device 21-23)")
    print("=" * 70)
    
    sql = generate_schema()
    
    output_file = Path(__file__).parent / "schema_env.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql)
    
    print(f"\nOK: {output_file}")
    print(f"Tables: {len(DEVICE_IDS)} raw + {len(DEVICE_IDS) * len(AGG_STAGES)} agg = 27")
    print(f"\nNext: psql -U postgres -d energydb -f {output_file}")

if __name__ == '__main__':
    main()

"""
일사량 전용 스키마 생성기 (Device 31)

생성 대상:
  - solar_data (1개 원천)
  - 8단계 집계 (총 8개)
  
사용법:
    python -m src.db.generate_solar_schema
    
출력:
    src/db/schema_solar.sql
"""

from pathlib import Path

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

def generate_schema() -> str:
    """전체 스키마 생성"""
    sql = """-- ============================================================================
-- Solar 일사량 스키마 (Device 31)
-- 자동 생성: generate_solar_schema.py
-- 총: 1개 원천 + 8개 집계 = 9개 테이블
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 원천 테이블
-- ============================================================================

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

-- ============================================================================
-- 2. 집계 테이블 (8단계)
-- ============================================================================
"""
    
    for stage in AGG_STAGES:
        sql += f"""
-- {stage} 집계
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
    
    # 압축 정책
    sql += """
-- ============================================================================
-- 3. 압축 정책
-- ============================================================================
ALTER TABLE solar_data SET (timescaledb.compress);
SELECT add_compression_policy('solar_data', INTERVAL '7 days', if_not_exists => TRUE);
"""
    
    # 보존 정책
    sql += """
-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- ============================================================================
SELECT add_retention_policy('solar_data', INTERVAL '1 year', if_not_exists => TRUE);
"""
    
    sql += """
DO $$
BEGIN
    RAISE NOTICE 'Solar schema complete: 9 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;
"""
    
    return sql

def main():
    print("=" * 70)
    print("Solar Schema Generator (Device 31)")
    print("=" * 70)
    
    sql = generate_schema()
    
    output_file = Path(__file__).parent / "schema_solar.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql)
    
    print(f"\nOK: {output_file}")
    print(f"Tables: 1 raw + {len(AGG_STAGES)} agg = 9")
    print(f"\nNext: psql -U postgres -d energydb -f {output_file}")

if __name__ == '__main__':
    main()

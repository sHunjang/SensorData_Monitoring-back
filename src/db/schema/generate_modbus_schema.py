"""
전력량계 전용 스키마 생성기 (Device 11-15)

생성 대상:
  - modbus_data_11 ~ modbus_data_15 (5개 원천)
  - 각 장치별 8단계 집계 (총 40개)
  
사용법:
    python -m src.db.generate_modbus_schema
    
출력:
    src/db/schema_modbus.sql
"""

from pathlib import Path

DEVICE_IDS = [11, 12, 13, 14, 15]
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
-- Modbus Device {device_id} 원천
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

def generate_agg_table(device_id: int, stage: str) -> str:
    """집계 테이블 SQL"""
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

def generate_schema() -> str:
    """전체 스키마 생성"""
    sql = """-- ============================================================================
-- Modbus 전력량계 스키마 (Device 11-15)
-- 자동 생성: generate_modbus_schema.py
-- 총: 5개 원천 + 40개 집계 = 45개 테이블
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 원천 테이블 (5개)
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
-- 3. 압축 정책 (7일 후 압축)
-- ============================================================================
"""
    for device_id in DEVICE_IDS:
        sql += f"ALTER TABLE modbus_data_{device_id} SET (timescaledb.compress);\n"
        sql += f"SELECT add_compression_policy('modbus_data_{device_id}', INTERVAL '7 days', if_not_exists => TRUE);\n"
    
    # 보존 정책 (1년으로 수정)
    sql += """
-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- 
-- 설명:
--   - 원천 데이터는 1년 보관 (365일)
--   - 집계 데이터는 삭제 안 함 (영구 보관)
--   - 필요시 아래 주석 해제하여 개별 정책 설정 가능
-- ============================================================================
"""
    for device_id in DEVICE_IDS:
        sql += f"SELECT add_retention_policy('modbus_data_{device_id}', INTERVAL '1 year', if_not_exists => TRUE);\n"
    
    sql += """
-- 집계 테이블 보존 정책 (선택 사항, 기본: 삭제 안 함)
-- SELECT add_retention_policy('agg_modbus_11_1m', INTERVAL '2 years');
-- SELECT add_retention_policy('agg_modbus_11_15m', INTERVAL '3 years');
"""
    
    sql += """
DO $$
BEGIN
    RAISE NOTICE 'Modbus schema complete: 45 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;
"""
    
    return sql

def main():
    print("=" * 70)
    print("Modbus Schema Generator (Device 11-15)")
    print("=" * 70)
    
    sql = generate_schema()
    
    output_file = Path(__file__).parent / "schema_modbus.sql"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(sql)
    
    print(f"\nOK: {output_file}")
    print(f"Tables: {len(DEVICE_IDS)} raw + {len(DEVICE_IDS) * len(AGG_STAGES)} agg = 45")
    print(f"\nNext: psql -U postgres -d energydb -f {output_file}")

if __name__ == '__main__':
    main()

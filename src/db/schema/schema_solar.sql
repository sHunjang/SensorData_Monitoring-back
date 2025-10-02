-- ============================================================================
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

-- 1m 집계
CREATE TABLE IF NOT EXISTS agg_solar_1m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1m 
    ON agg_solar_1m (bucket DESC);

-- 15m 집계
CREATE TABLE IF NOT EXISTS agg_solar_15m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_15m 
    ON agg_solar_15m (bucket DESC);

-- 1h 집계
CREATE TABLE IF NOT EXISTS agg_solar_1h (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1h 
    ON agg_solar_1h (bucket DESC);

-- 1d 집계
CREATE TABLE IF NOT EXISTS agg_solar_1d (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1d 
    ON agg_solar_1d (bucket DESC);

-- 1w 집계
CREATE TABLE IF NOT EXISTS agg_solar_1w (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1w 
    ON agg_solar_1w (bucket DESC);

-- 1mo 집계
CREATE TABLE IF NOT EXISTS agg_solar_1mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1mo 
    ON agg_solar_1mo (bucket DESC);

-- 6mo 집계
CREATE TABLE IF NOT EXISTS agg_solar_6mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_6mo 
    ON agg_solar_6mo (bucket DESC);

-- 1y 집계
CREATE TABLE IF NOT EXISTS agg_solar_1y (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_irradiance DOUBLE PRECISION,
    max_irradiance DOUBLE PRECISION,
    min_irradiance DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_solar_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_solar_1y 
    ON agg_solar_1y (bucket DESC);

-- ============================================================================
-- 3. 압축 정책
-- ============================================================================
ALTER TABLE solar_data SET (timescaledb.compress);
SELECT add_compression_policy('solar_data', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- ============================================================================
SELECT add_retention_policy('solar_data', INTERVAL '1 year', if_not_exists => TRUE);

DO $$
BEGIN
    RAISE NOTICE 'Solar schema complete: 9 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;

-- ============================================================================
-- Env 온습도 스키마 (Device 21-23)
-- 자동 생성: generate_env_schema.py
-- 총: 3개 원천 + 24개 집계 = 27개 테이블
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 원천 테이블 (3개)
-- ============================================================================

-- Env Device 21 원천
CREATE TABLE IF NOT EXISTS env_data_21 (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

SELECT create_hypertable('env_data_21', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_env_21_time 
    ON env_data_21 (time_stamp DESC);

-- Env Device 22 원천
CREATE TABLE IF NOT EXISTS env_data_22 (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

SELECT create_hypertable('env_data_22', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_env_22_time 
    ON env_data_22 (time_stamp DESC);

-- Env Device 23 원천
CREATE TABLE IF NOT EXISTS env_data_23 (
    time_stamp TIMESTAMPTZ NOT NULL PRIMARY KEY,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

SELECT create_hypertable('env_data_23', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_env_23_time 
    ON env_data_23 (time_stamp DESC);

-- ============================================================================
-- 2. Device 21 집계 (8단계)
-- ============================================================================

-- Device 21 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1m 
    ON agg_env_21_1m (bucket DESC);

-- Device 21 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_env_21_15m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_15m 
    ON agg_env_21_15m (bucket DESC);

-- Device 21 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1h (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1h 
    ON agg_env_21_1h (bucket DESC);

-- Device 21 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1d (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1d 
    ON agg_env_21_1d (bucket DESC);

-- Device 21 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1w (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1w 
    ON agg_env_21_1w (bucket DESC);

-- Device 21 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1mo 
    ON agg_env_21_1mo (bucket DESC);

-- Device 21 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_env_21_6mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_6mo 
    ON agg_env_21_6mo (bucket DESC);

-- Device 21 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_env_21_1y (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_21_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_21_1y 
    ON agg_env_21_1y (bucket DESC);

-- ============================================================================
-- 2. Device 22 집계 (8단계)
-- ============================================================================

-- Device 22 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1m 
    ON agg_env_22_1m (bucket DESC);

-- Device 22 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_env_22_15m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_15m 
    ON agg_env_22_15m (bucket DESC);

-- Device 22 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1h (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1h 
    ON agg_env_22_1h (bucket DESC);

-- Device 22 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1d (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1d 
    ON agg_env_22_1d (bucket DESC);

-- Device 22 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1w (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1w 
    ON agg_env_22_1w (bucket DESC);

-- Device 22 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1mo 
    ON agg_env_22_1mo (bucket DESC);

-- Device 22 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_env_22_6mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_6mo 
    ON agg_env_22_6mo (bucket DESC);

-- Device 22 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_env_22_1y (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_22_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_22_1y 
    ON agg_env_22_1y (bucket DESC);

-- ============================================================================
-- 2. Device 23 집계 (8단계)
-- ============================================================================

-- Device 23 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1m 
    ON agg_env_23_1m (bucket DESC);

-- Device 23 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_env_23_15m (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_15m 
    ON agg_env_23_15m (bucket DESC);

-- Device 23 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1h (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1h 
    ON agg_env_23_1h (bucket DESC);

-- Device 23 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1d (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1d 
    ON agg_env_23_1d (bucket DESC);

-- Device 23 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1w (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1w 
    ON agg_env_23_1w (bucket DESC);

-- Device 23 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1mo 
    ON agg_env_23_1mo (bucket DESC);

-- Device 23 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_env_23_6mo (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_6mo 
    ON agg_env_23_6mo (bucket DESC);

-- Device 23 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_env_23_1y (
    bucket TIMESTAMPTZ NOT NULL PRIMARY KEY,
    avg_temperature DOUBLE PRECISION,
    max_temperature DOUBLE PRECISION,
    min_temperature DOUBLE PRECISION,
    avg_humidity DOUBLE PRECISION,
    max_humidity DOUBLE PRECISION,
    min_humidity DOUBLE PRECISION,
    sample_count INT
);

SELECT create_hypertable('agg_env_23_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_env_23_1y 
    ON agg_env_23_1y (bucket DESC);

-- ============================================================================
-- 3. 압축 정책
-- ============================================================================
ALTER TABLE env_data_21 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_21', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE env_data_22 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_22', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE env_data_23 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_23', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- ============================================================================
SELECT add_retention_policy('env_data_21', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('env_data_22', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('env_data_23', INTERVAL '1 year', if_not_exists => TRUE);

DO $$
BEGIN
    RAISE NOTICE 'Env schema complete: 27 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;

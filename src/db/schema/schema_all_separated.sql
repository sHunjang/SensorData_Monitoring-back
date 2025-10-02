-- ============================================================================
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

-- ============================================================================
-- 1. 전력량계 원천 테이블 (5개)
-- ============================================================================

-- Modbus Device 11 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_11 (
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

SELECT create_hypertable('modbus_data_11', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_11_time 
    ON modbus_data_11 (time_stamp DESC);

-- Modbus Device 12 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_12 (
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

SELECT create_hypertable('modbus_data_12', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_12_time 
    ON modbus_data_12 (time_stamp DESC);

-- Modbus Device 13 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_13 (
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

SELECT create_hypertable('modbus_data_13', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_13_time 
    ON modbus_data_13 (time_stamp DESC);

-- Modbus Device 14 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_14 (
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

SELECT create_hypertable('modbus_data_14', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_14_time 
    ON modbus_data_14 (time_stamp DESC);

-- Modbus Device 15 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data_15 (
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

SELECT create_hypertable('modbus_data_15', 'time_stamp', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS idx_modbus_15_time 
    ON modbus_data_15 (time_stamp DESC);

-- ============================================================================
-- 2. Modbus Device 11 집계 테이블 (8단계)
-- ============================================================================

-- Device 11 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1m (
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

SELECT create_hypertable('agg_modbus_11_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1m 
    ON agg_modbus_11_1m (bucket DESC);

-- Device 11 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_15m (
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

SELECT create_hypertable('agg_modbus_11_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_15m 
    ON agg_modbus_11_15m (bucket DESC);

-- Device 11 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1h (
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

SELECT create_hypertable('agg_modbus_11_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1h 
    ON agg_modbus_11_1h (bucket DESC);

-- Device 11 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1d (
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

SELECT create_hypertable('agg_modbus_11_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1d 
    ON agg_modbus_11_1d (bucket DESC);

-- Device 11 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1w (
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

SELECT create_hypertable('agg_modbus_11_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1w 
    ON agg_modbus_11_1w (bucket DESC);

-- Device 11 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1mo (
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

SELECT create_hypertable('agg_modbus_11_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1mo 
    ON agg_modbus_11_1mo (bucket DESC);

-- Device 11 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_6mo (
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

SELECT create_hypertable('agg_modbus_11_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_6mo 
    ON agg_modbus_11_6mo (bucket DESC);

-- Device 11 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_modbus_11_1y (
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

SELECT create_hypertable('agg_modbus_11_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_11_1y 
    ON agg_modbus_11_1y (bucket DESC);

-- ============================================================================
-- 2. Modbus Device 12 집계 테이블 (8단계)
-- ============================================================================

-- Device 12 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1m (
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

SELECT create_hypertable('agg_modbus_12_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1m 
    ON agg_modbus_12_1m (bucket DESC);

-- Device 12 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_15m (
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

SELECT create_hypertable('agg_modbus_12_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_15m 
    ON agg_modbus_12_15m (bucket DESC);

-- Device 12 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1h (
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

SELECT create_hypertable('agg_modbus_12_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1h 
    ON agg_modbus_12_1h (bucket DESC);

-- Device 12 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1d (
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

SELECT create_hypertable('agg_modbus_12_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1d 
    ON agg_modbus_12_1d (bucket DESC);

-- Device 12 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1w (
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

SELECT create_hypertable('agg_modbus_12_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1w 
    ON agg_modbus_12_1w (bucket DESC);

-- Device 12 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1mo (
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

SELECT create_hypertable('agg_modbus_12_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1mo 
    ON agg_modbus_12_1mo (bucket DESC);

-- Device 12 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_6mo (
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

SELECT create_hypertable('agg_modbus_12_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_6mo 
    ON agg_modbus_12_6mo (bucket DESC);

-- Device 12 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_modbus_12_1y (
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

SELECT create_hypertable('agg_modbus_12_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_12_1y 
    ON agg_modbus_12_1y (bucket DESC);

-- ============================================================================
-- 2. Modbus Device 13 집계 테이블 (8단계)
-- ============================================================================

-- Device 13 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1m (
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

SELECT create_hypertable('agg_modbus_13_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1m 
    ON agg_modbus_13_1m (bucket DESC);

-- Device 13 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_15m (
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

SELECT create_hypertable('agg_modbus_13_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_15m 
    ON agg_modbus_13_15m (bucket DESC);

-- Device 13 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1h (
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

SELECT create_hypertable('agg_modbus_13_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1h 
    ON agg_modbus_13_1h (bucket DESC);

-- Device 13 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1d (
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

SELECT create_hypertable('agg_modbus_13_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1d 
    ON agg_modbus_13_1d (bucket DESC);

-- Device 13 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1w (
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

SELECT create_hypertable('agg_modbus_13_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1w 
    ON agg_modbus_13_1w (bucket DESC);

-- Device 13 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1mo (
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

SELECT create_hypertable('agg_modbus_13_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1mo 
    ON agg_modbus_13_1mo (bucket DESC);

-- Device 13 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_6mo (
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

SELECT create_hypertable('agg_modbus_13_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_6mo 
    ON agg_modbus_13_6mo (bucket DESC);

-- Device 13 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_modbus_13_1y (
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

SELECT create_hypertable('agg_modbus_13_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_13_1y 
    ON agg_modbus_13_1y (bucket DESC);

-- ============================================================================
-- 2. Modbus Device 14 집계 테이블 (8단계)
-- ============================================================================

-- Device 14 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1m (
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

SELECT create_hypertable('agg_modbus_14_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1m 
    ON agg_modbus_14_1m (bucket DESC);

-- Device 14 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_15m (
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

SELECT create_hypertable('agg_modbus_14_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_15m 
    ON agg_modbus_14_15m (bucket DESC);

-- Device 14 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1h (
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

SELECT create_hypertable('agg_modbus_14_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1h 
    ON agg_modbus_14_1h (bucket DESC);

-- Device 14 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1d (
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

SELECT create_hypertable('agg_modbus_14_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1d 
    ON agg_modbus_14_1d (bucket DESC);

-- Device 14 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1w (
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

SELECT create_hypertable('agg_modbus_14_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1w 
    ON agg_modbus_14_1w (bucket DESC);

-- Device 14 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1mo (
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

SELECT create_hypertable('agg_modbus_14_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1mo 
    ON agg_modbus_14_1mo (bucket DESC);

-- Device 14 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_6mo (
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

SELECT create_hypertable('agg_modbus_14_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_6mo 
    ON agg_modbus_14_6mo (bucket DESC);

-- Device 14 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_modbus_14_1y (
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

SELECT create_hypertable('agg_modbus_14_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_14_1y 
    ON agg_modbus_14_1y (bucket DESC);

-- ============================================================================
-- 2. Modbus Device 15 집계 테이블 (8단계)
-- ============================================================================

-- Device 15 - 1m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1m (
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

SELECT create_hypertable('agg_modbus_15_1m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1m 
    ON agg_modbus_15_1m (bucket DESC);

-- Device 15 - 15m 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_15m (
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

SELECT create_hypertable('agg_modbus_15_15m', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '90 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_15m 
    ON agg_modbus_15_15m (bucket DESC);

-- Device 15 - 1h 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1h (
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

SELECT create_hypertable('agg_modbus_15_1h', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '180 days'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1h 
    ON agg_modbus_15_1h (bucket DESC);

-- Device 15 - 1d 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1d (
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

SELECT create_hypertable('agg_modbus_15_1d', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '1 year'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1d 
    ON agg_modbus_15_1d (bucket DESC);

-- Device 15 - 1w 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1w (
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

SELECT create_hypertable('agg_modbus_15_1w', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '2 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1w 
    ON agg_modbus_15_1w (bucket DESC);

-- Device 15 - 1mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1mo (
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

SELECT create_hypertable('agg_modbus_15_1mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '5 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1mo 
    ON agg_modbus_15_1mo (bucket DESC);

-- Device 15 - 6mo 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_6mo (
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

SELECT create_hypertable('agg_modbus_15_6mo', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_6mo 
    ON agg_modbus_15_6mo (bucket DESC);

-- Device 15 - 1y 집계
CREATE TABLE IF NOT EXISTS agg_modbus_15_1y (
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

SELECT create_hypertable('agg_modbus_15_1y', 'bucket', 
    if_not_exists => TRUE, 
    chunk_time_interval => INTERVAL '10 years'
);

CREATE INDEX IF NOT EXISTS idx_agg_modbus_15_1y 
    ON agg_modbus_15_1y (bucket DESC);

-- ============================================================================
-- 3. 온습도 원천 테이블 (3개)
-- ============================================================================

-- Env Device 21 원천 테이블
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

-- Env Device 22 원천 테이블
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

-- Env Device 23 원천 테이블
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
-- 4. Env Device 21 집계 테이블 (8단계)
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
-- 4. Env Device 22 집계 테이블 (8단계)
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
-- 4. Env Device 23 집계 테이블 (8단계)
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
-- 5. 일사량 테이블 (1개 + 집계 8개)
-- ============================================================================

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

-- Solar - 1m 집계
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

-- Solar - 15m 집계
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

-- Solar - 1h 집계
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

-- Solar - 1d 집계
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

-- Solar - 1w 집계
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

-- Solar - 1mo 집계
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

-- Solar - 6mo 집계
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

-- Solar - 1y 집계
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
-- 6. 압축 정책 (7일 후 자동 압축)
-- ============================================================================
ALTER TABLE modbus_data_11 SET (timescaledb.compress);
SELECT add_compression_policy('modbus_data_11', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE modbus_data_12 SET (timescaledb.compress);
SELECT add_compression_policy('modbus_data_12', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE modbus_data_13 SET (timescaledb.compress);
SELECT add_compression_policy('modbus_data_13', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE modbus_data_14 SET (timescaledb.compress);
SELECT add_compression_policy('modbus_data_14', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE modbus_data_15 SET (timescaledb.compress);
SELECT add_compression_policy('modbus_data_15', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE env_data_21 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_21', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE env_data_22 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_22', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE env_data_23 SET (timescaledb.compress);
SELECT add_compression_policy('env_data_23', INTERVAL '7 days', if_not_exists => TRUE);
ALTER TABLE solar_data SET (timescaledb.compress);
SELECT add_compression_policy('solar_data', INTERVAL '7 days', if_not_exists => TRUE);

-- ============================================================================
-- 7. 보존 정책 (30일 후 자동 삭제)
-- ============================================================================
SELECT add_retention_policy('modbus_data_11', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_12', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_13', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_14', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_15', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('env_data_21', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('env_data_22', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('env_data_23', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('solar_data', INTERVAL '30 days', if_not_exists => TRUE);

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

-- ============================================================================
-- Modbus 전력량계 스키마 (Device 11-15)
-- 자동 생성: generate_modbus_schema.py
-- 총: 5개 원천 + 40개 집계 = 45개 테이블
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- 1. 원천 테이블 (5개)
-- ============================================================================

-- Modbus Device 11 원천
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

-- Modbus Device 12 원천
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

-- Modbus Device 13 원천
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

-- Modbus Device 14 원천
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

-- Modbus Device 15 원천
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
-- 2. Device 11 집계 (8단계)
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
-- 2. Device 12 집계 (8단계)
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
-- 2. Device 13 집계 (8단계)
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
-- 2. Device 14 집계 (8단계)
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
-- 2. Device 15 집계 (8단계)
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
-- 3. 압축 정책 (7일 후 압축)
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

-- ============================================================================
-- 4. 보존 정책 (1년 후 자동 삭제)
-- 
-- 설명:
--   - 원천 데이터는 1년 보관 (365일)
--   - 집계 데이터는 삭제 안 함 (영구 보관)
--   - 필요시 아래 주석 해제하여 개별 정책 설정 가능
-- ============================================================================
SELECT add_retention_policy('modbus_data_11', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_12', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_13', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_14', INTERVAL '1 year', if_not_exists => TRUE);
SELECT add_retention_policy('modbus_data_15', INTERVAL '1 year', if_not_exists => TRUE);

-- 집계 테이블 보존 정책 (선택 사항, 기본: 삭제 안 함)
-- SELECT add_retention_policy('agg_modbus_11_1m', INTERVAL '2 years');
-- SELECT add_retention_policy('agg_modbus_11_15m', INTERVAL '3 years');

DO $$
BEGIN
    RAISE NOTICE 'Modbus schema complete: 45 tables';
    RAISE NOTICE 'Retention: Raw data 1 year, Aggregates unlimited';
END $$;

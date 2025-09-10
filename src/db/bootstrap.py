"""
TimescaleDB 스키마 부트스트랩
- 확장/테이블/하이퍼테이블/인덱스/연속집계뷰/정책을 idempotent하게 생성
- PG_DSN 환경변수 사용 (예: postgresql://user:pass@host:5432/db)
"""
import os
import psycopg2

DDL = r"""
-- 1) 확장
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2) 원천 테이블
CREATE TABLE IF NOT EXISTS modbus_data(
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id  INT NOT NULL,
  total_active_power_kw        DOUBLE PRECISION,
  total_reactive_power_kvar    DOUBLE PRECISION,
  total_apparent_power_kva     DOUBLE PRECISION,
  sum_line_currents_a          DOUBLE PRECISION,
  avg_line_to_neutral_volts_v  DOUBLE PRECISION,
  avg_line_to_line_volts_v     DOUBLE PRECISION,
  total_active_energy_kwh      DOUBLE PRECISION,
  total_reactive_energy_kvarh  DOUBLE PRECISION,
  total_apparent_energy_kvah   DOUBLE PRECISION
);
SELECT create_hypertable('modbus_data','time_stamp', if_not_exists=>TRUE);
CREATE INDEX IF NOT EXISTS idx_modbus_device_time ON modbus_data(device_id, time_stamp DESC);

-- 3) 연속집계 뷰들
CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_agg_15m WITH (timescaledb.continuous) AS
SELECT time_bucket('15 minutes', time_stamp) AS bucket, device_id,
  AVG(total_active_power_kw) AS avg_p,
  AVG(total_reactive_power_kvar) AS avg_q,
  AVG(total_apparent_power_kva) AS avg_s,
  AVG(sum_line_currents_a) AS avg_sum_i,
  AVG(avg_line_to_neutral_volts_v) AS avg_v_ln,
  AVG(avg_line_to_line_volts_v) AS avg_v_ll,
  MAX(total_active_energy_kwh)-MIN(total_active_energy_kwh) AS delta_e_active,
  MAX(total_reactive_energy_kvarh)-MIN(total_reactive_energy_kvarh) AS delta_e_reactive,
  MAX(total_apparent_energy_kvah)-MIN(total_apparent_energy_kvah) AS delta_e_apparent,
  COUNT(*) AS n_samples
FROM modbus_data GROUP BY bucket, device_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_agg_1h WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time_stamp) AS bucket, device_id,
  AVG(total_active_power_kw) AS avg_p,
  AVG(total_reactive_power_kvar) AS avg_q,
  AVG(total_apparent_power_kva) AS avg_s,
  AVG(sum_line_currents_a) AS avg_sum_i,
  AVG(avg_line_to_neutral_volts_v) AS avg_v_ln,
  AVG(avg_line_to_line_volts_v) AS avg_v_ll,
  MAX(total_active_energy_kwh)-MIN(total_active_energy_kwh) AS delta_e_active,
  MAX(total_reactive_energy_kvarh)-MIN(total_reactive_energy_kvarh) AS delta_e_reactive,
  MAX(total_apparent_energy_kvah)-MIN(total_apparent_energy_kvah) AS delta_e_apparent,
  COUNT(*) AS n_samples
FROM modbus_data GROUP BY bucket, device_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_agg_1d WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time_stamp) AS bucket, device_id,
  AVG(total_active_power_kw) AS avg_p,
  AVG(total_reactive_power_kvar) AS avg_q,
  AVG(total_apparent_power_kva) AS avg_s,
  AVG(sum_line_currents_a) AS avg_sum_i,
  AVG(avg_line_to_neutral_volts_v) AS avg_v_ln,
  AVG(avg_line_to_line_volts_v) AS avg_v_ll,
  MAX(total_active_energy_kwh)-MIN(total_active_energy_kwh) AS delta_e_active,
  MAX(total_reactive_energy_kvarh)-MIN(total_reactive_energy_kvarh) AS delta_e_reactive,
  MAX(total_apparent_energy_kvah)-MIN(total_apparent_energy_kvah) AS delta_e_apparent,
  COUNT(*) AS n_samples
FROM modbus_data GROUP BY bucket, device_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_agg_1w WITH (timescaledb.continuous) AS
SELECT time_bucket('1 week', time_stamp) AS bucket, device_id,
  AVG(total_active_power_kw) AS avg_p,
  AVG(total_reactive_power_kvar) AS avg_q,
  AVG(total_apparent_power_kva) AS avg_s,
  AVG(sum_line_currents_a) AS avg_sum_i,
  AVG(avg_line_to_neutral_volts_v) AS avg_v_ln,
  AVG(avg_line_to_line_volts_v) AS avg_v_ll,
  MAX(total_active_energy_kwh)-MIN(total_active_energy_kwh) AS delta_e_active,
  MAX(total_reactive_energy_kvarh)-MIN(total_reactive_energy_kvarh) AS delta_e_reactive,
  MAX(total_apparent_energy_kvah)-MIN(total_apparent_energy_kvah) AS delta_e_apparent,
  COUNT(*) AS n_samples
FROM modbus_data GROUP BY bucket, device_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_agg_1mo WITH (timescaledb.continuous) AS
SELECT time_bucket('1 month', time_stamp) AS bucket, device_id,
  AVG(total_active_power_kw) AS avg_p,
  AVG(total_reactive_power_kvar) AS avg_q,
  AVG(total_apparent_power_kva) AS avg_s,
  AVG(sum_line_currents_a) AS avg_sum_i,
  AVG(avg_line_to_neutral_volts_v) AS avg_v_ln,
  AVG(avg_line_to_line_volts_v) AS avg_v_ll,
  MAX(total_active_energy_kwh)-MIN(total_active_energy_kwh) AS delta_e_active,
  MAX(total_reactive_energy_kvarh)-MIN(total_reactive_energy_kvarh) AS delta_e_reactive,
  MAX(total_apparent_energy_kvah)-MIN(total_apparent_energy_kvah) AS delta_e_apparent,
  COUNT(*) AS n_samples
FROM modbus_data GROUP BY bucket, device_id;

-- 4) 자동 갱신 정책(있으면 무시)
SELECT add_continuous_aggregate_policy('modbus_agg_15m', INTERVAL '2 hours',  INTERVAL '15 minutes', INTERVAL '15 minutes')
ON CONFLICT DO NOTHING;
SELECT add_continuous_aggregate_policy('modbus_agg_1h',  INTERVAL '1 day',    INTERVAL '1 hour',     INTERVAL '15 minutes')
ON CONFLICT DO NOTHING;
SELECT add_continuous_aggregate_policy('modbus_agg_1d',  INTERVAL '14 days',  INTERVAL '1 day',      INTERVAL '1 hour')
ON CONFLICT DO NOTHING;
SELECT add_continuous_aggregate_policy('modbus_agg_1w',  INTERVAL '90 days',  INTERVAL '1 week',     INTERVAL '1 day')
ON CONFLICT DO NOTHING;
SELECT add_continuous_aggregate_policy('modbus_agg_1mo', INTERVAL '365 days', INTERVAL '1 month',    INTERVAL '1 day')
ON CONFLICT DO NOTHING;
"""

def ensure_schema():
    """PG_DSN로 접속해 DDL을 실행한다. 예외는 즉시 raise."""
    dsn = os.getenv("PG_DSN", "postgresql://postgres:1234@localhost:5432/energydb")
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(DDL)

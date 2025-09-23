"""
TimescaleDB 스키마 부트스트랩
- idempotent 하게 테이블/인덱스/하이퍼테이블을 생성
- solar_data는 device_id INT NOT NULL 포함
- 환경변수: PG_DSN
"""
import os
import logging
import psycopg2

log = logging.getLogger("bootstrap")

DDL_BASE = r"""
CREATE TABLE IF NOT EXISTS modbus_data(
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id  INT NOT NULL,
  avg_line_to_line_volts_v    DOUBLE PRECISION,
  avg_line_to_neutral_volts_v DOUBLE PRECISION,
  sum_line_currents_a         DOUBLE PRECISION,
  total_active_power_kw       DOUBLE PRECISION,
  total_reactive_power_kvar   DOUBLE PRECISION,
  total_apparent_power_kva    DOUBLE PRECISION,
  total_power_factor          DOUBLE PRECISION,
  total_active_energy_kwh     DOUBLE PRECISION,
  total_reactive_energy_kvarh DOUBLE PRECISION,
  total_apparent_energy_kvah  DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_modbus_device_time ON modbus_data(device_id, time_stamp DESC);

CREATE TABLE IF NOT EXISTS env_data(
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id  INT NOT NULL,
  temperature DOUBLE PRECISION,
  humidity   DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_env_device_time ON env_data(device_id, time_stamp DESC);

CREATE TABLE IF NOT EXISTS solar_data(
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id INT NOT NULL,
  solar DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_solar_device_time ON solar_data(device_id, time_stamp DESC);
"""

DDL_TS = r"""
SELECT create_hypertable('modbus_data','time_stamp', if_not_exists=>TRUE);
SELECT create_hypertable('env_data','time_stamp', if_not_exists=>TRUE);
SELECT create_hypertable('solar_data','time_stamp', if_not_exists=>TRUE);
"""

def ensure_schema():
    dsn = os.getenv("PG_DSN", "postgresql://postgres:postgres@localhost:5432/energydb")
    log.info("ensure_schema: connecting to DB")
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            log.info("ensure_schema: creating base tables and indexes if not exists")
            cur.execute(DDL_BASE)
            try:
                cur.execute("""
                    SELECT EXISTS (
                      SELECT 1 FROM pg_available_extensions
                      WHERE name='timescaledb' AND installed_version IS NOT NULL
                    )
                """)
                (has_ts,) = cur.fetchone()
            except Exception as e:
                log.warning("ensure_schema: failed to check timescaledb availability: %s", e)
                has_ts = False
            if has_ts:
                log.info("ensure_schema: timescaledb installed, ensuring hypertables")
                try:
                    cur.execute(DDL_TS)
                except Exception as e:
                    log.warning("ensure_schema: create_hypertable failed: %s", e)
            else:
                log.info("ensure_schema: timescaledb not installed or not available, skipping hypertable creation")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_schema()
    log.info("schema ensured")

# src/db/bootstrap.py
"""
TimescaleDB 스키마 부트스트랩

- 목적: 확장 / 테이블 / 인덱스 / 하이퍼테이블을 idempotent하게 보장
- 환경변수:
    PG_DSN (예: postgresql://user:pass@host:5432/db)
- 동작:
    1) 기본 테이블들을 CREATE TABLE IF NOT EXISTS 로 생성
    2) 필요한 인덱스 생성
    3) timescaledb 확장이 사용 가능하면 create_hypertable 호출 (if_not_exists=>TRUE)
       - 확장 설치 권한이 없거나 확장이 없으면 하이퍼테이블 생성 단계는 건너뜀
- 주의: 운영 DB에 적용 시 스키마(컬럼명/타입)가 기존 코드와 일치하는지 확인하세요.
"""

import os
import logging
import psycopg2

log = logging.getLogger("bootstrap")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
log.addHandler(handler)

DDL_BASE = r"""
-- modbus_data: 전력량계 원시 수집 테이블
CREATE TABLE IF NOT EXISTS modbus_data (
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

-- env_data: 온/습도 수집
CREATE TABLE IF NOT EXISTS env_data (
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id  INT NOT NULL,
  temperature DOUBLE PRECISION,
  humidity    DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_env_device_time ON env_data(device_id, time_stamp DESC);

-- solar_data: 일사량 수집
CREATE TABLE IF NOT EXISTS solar_data (
  time_stamp TIMESTAMPTZ NOT NULL,
  device_id INT NOT NULL,
  irradiance DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_solar_device_time ON solar_data(device_id, time_stamp DESC);
"""

DDL_TS = r"""
-- timescaledb 가 설치되어 있는 환경에서 하이퍼테이블을 보장
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

            # timescaledb 설치 여부 확인
            try:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_available_extensions
                        WHERE name='timescaledb' AND installed_version IS NOT NULL
                    );
                """)
                (has_ts,) = cur.fetchone()
            except Exception as e:
                log.warning("Could not check timescaledb availability: %s", e)
                has_ts = False

            if has_ts:
                log.info("ensure_schema: timescaledb installed, ensuring hypertables")
                try:
                    cur.execute(DDL_TS)
                except Exception as e:
                    log.error("Failed to create hypertables: %s", e)
            else:
                # 권한이 있으면 확장 설치 시도해볼 수 있지만 운영 DB에서는 권한 문제/정책이 있으므로 생략
                log.info("ensure_schema: timescaledb not installed or not available; skipping hypertable creation")

if __name__ == "__main__":
    ensure_schema()

# src/collectors/solar_collector.py

"""
일사량(Solar) 수집기 - TimescaleDB 연동
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.solar_reader import create_instrument, read_solar_sensor

log = logging.getLogger("solar_collector")
KST = ZoneInfo("Asia/Seoul")


def ensure_table():
    """
    TimescaleDB 하이퍼테이블 및 연속 집계 생성
    """
    with get_cursor() as cur:
        # 1. 원본 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS solar_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                irradiance DOUBLE PRECISION
            );
        """)
        
        # 2. 하이퍼테이블
        cur.execute("""
            SELECT create_hypertable(
                'solar_data', 
                'time_stamp',
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '7 days'
            );
        """)
        
        # 3. 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_solar_device_time 
            ON solar_data (device_id, time_stamp DESC);
        """)
        
        # 4-7. 연속 집계
        for interval_name, interval_str in [
            ('1min', '1 minute'),
            ('15min', '15 minutes'),
            ('1hour', '1 hour'),
            ('1day', '1 day')
        ]:
            cur.execute(f"""
                CREATE MATERIALIZED VIEW IF NOT EXISTS solar_data_{interval_name}
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('{interval_str}', time_stamp) AS bucket,
                    device_id,
                    AVG(irradiance) AS irradiance
                FROM solar_data
                GROUP BY bucket, device_id
                WITH NO DATA;
            """)
            
            try:
                cur.execute(f"""
                    SELECT add_continuous_aggregate_policy('solar_data_{interval_name}',
                        start_offset => INTERVAL '3 hours',
                        end_offset => INTERVAL '1 minute',
                        schedule_interval => INTERVAL '1 minute',
                        if_not_exists => TRUE
                    );
                """)
            except Exception as e:
                log.warning(f"⚠️ Policy for solar_data_{interval_name}: {e}")
        
        log.info("✅ TimescaleDB 하이퍼테이블 및 연속 집계 준비 완료 (solar)")


def insert_row(device_id: int, payload: Dict[str, float]):
    """DB 삽입"""
    now_kst = datetime.now(KST)
    irr = payload.get("irradiance_w_m2")
    
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO solar_data (time_stamp, device_id, irradiance)
                VALUES (%s, %s, %s)
            """, (now_kst, device_id, irr))
            
            log.debug("☀️ solar: device=%s irradiance=%.1f W/m²", device_id, irr or 0)
    except Exception:
        log.exception("❌ DB insert failed for device=%s", device_id)


def run_once_for_device(device_id: int, fail_counts: dict):
    """단일 장치 읽기"""
    port = settings.SOLAR_PORT
    baud = settings.SOLAR_BAUDRATE
    
    try:
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        data = read_solar_sensor(inst)
        
        if not isinstance(data, dict):
            raise RuntimeError(f"read_solar_sensor returned non-dict: {data}")
        
        insert_row(device_id, data)
        fail_counts[device_id] = 0
        
        if hasattr(inst, 'serial') and inst.serial:
            inst.serial.close()
            
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("⚠️ solar read fail device=%s count=%s err=%s", 
                   device_id, fail_counts[device_id], e)


def main():
    """메인 루프"""
    log.info("☀️ solar_collector starting...")
    ensure_table()
    
    device_ids = getattr(settings, "SOLAR_DEVICE_IDS", [])
    interval = getattr(settings, "SOLAR_POLL_INTERVAL", 5)
    max_fails = 5
    
    if not device_ids:
        log.warning("⚠️ SOLAR_DEVICE_IDS가 비어있음")
        return
    
    log.info("📡 solar config: port=%s devices=%s interval=%ss",
            settings.SOLAR_PORT, device_ids, interval)
    
    fail_counts = {sid: 0 for sid in device_ids}
    
    while True:
        for sid in device_ids:
            if fail_counts.get(sid, 0) >= max_fails:
                if fail_counts.get(sid, 0) == max_fails:
                    log.error("🚫 device %s disabled", sid)
                    fail_counts[sid] = max_fails + 1
                continue
            
            run_once_for_device(sid, fail_counts)
        
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("🛑 solar_collector stopped")
    except Exception as e:
        log.exception("❌ solar_collector crashed: %s", e)

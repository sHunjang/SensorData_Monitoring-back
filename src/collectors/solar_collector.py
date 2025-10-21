# src/collectors/solar_collector.py
"""
일사량(Solar) 수집기 - TimescaleDB 연동 (기존 데이터 보존)
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.solar_reader import create_instrument, read_solar_sensor
from src.collectors.serial_manager import SerialPortManager  # ✅ 추가

log = logging.getLogger("solar_collector")
KST = ZoneInfo("Asia/Seoul")

def ensure_table():
    """
    TimescaleDB 하이퍼테이블 및 연속 집계 생성 (기존 데이터 보존)
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
        
        # 2. 하이퍼테이블 변환 (✅ migrate_data => TRUE 추가)
        try:
            cur.execute("""
                SELECT create_hypertable(
                    'solar_data',
                    'time_stamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE,
                    chunk_time_interval => INTERVAL '7 days'
                );
            """)
            log.info("✅ solar_data 하이퍼테이블 변환 완료 (기존 데이터 보존)")
        except Exception as e:
            log.info("✅ solar_data 이미 하이퍼테이블로 존재함")
        
        # 3. 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_solar_device_time
            ON solar_data (device_id, time_stamp DESC);
        """)
        
        # 4-7. 연속 집계 (1분/15분/1시간/1일)
        for interval_name, interval_str in [
            ('1min', '1 minute'),
            ('15min', '15 minutes'),
            ('1hour', '1 hour'),
            ('1day', '1 day')
        ]:
            try:
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
                log.info(f"✅ solar_data_{interval_name} 연속 집계 생성 완료")
            except Exception as e:
                log.debug(f"solar_data_{interval_name} 이미 존재: {e}")
            
            # 자동 갱신 정책
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
                log.debug(f"⚠️ Policy for solar_data_{interval_name}: {e}")
    
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

def run_once_for_device(device_id: int, fail_counts: dict, serial_mgr: SerialPortManager):
    """단일 장치 읽기 - Thread-safe"""
    port = settings.SOLAR_PORT
    baud = settings.SOLAR_BAUDRATE
    
    def read_operation():
        """시리얼 포트 작업"""
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        try:
            data = read_solar_sensor(inst)
            if not isinstance(data, dict):
                raise RuntimeError(f"read_solar_sensor returned non-dict: {data}")
            insert_row(device_id, data)
            return True
        finally:
            if hasattr(inst, 'serial') and inst.serial:
                inst.serial.close()
    
    try:
        result = serial_mgr.execute(read_operation)
        if result:
            fail_counts[device_id] = 0
        else:
            raise RuntimeError("Read operation returned None")
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
    
    port = settings.SOLAR_PORT
    log.info("📡 solar config: port=%s devices=%s interval=%ss",
             port, device_ids, interval)
    
    # ✅ Serial Manager 가져오기 (env_collector와 같은 포트면 같은 인스턴스)
    serial_mgr = SerialPortManager.get_instance(port)
    fail_counts = {sid: 0 for sid in device_ids}
    
    while True:
        for sid in device_ids:
            if fail_counts.get(sid, 0) >= max_fails:
                if fail_counts.get(sid, 0) == max_fails:
                    log.error("🚫 device %s disabled", sid)
                    fail_counts[sid] = max_fails + 1
                continue
            
            run_once_for_device(sid, fail_counts, serial_mgr)  # ✅ serial_mgr 전달
        
        time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("🛑 solar_collector stopped")
    except Exception as e:
        log.exception("❌ solar_collector crashed: %s", e)

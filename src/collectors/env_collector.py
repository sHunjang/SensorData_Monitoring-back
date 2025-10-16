# src/collectors/env_collector.py


"""
환경센서(온도·습도) 수집기 - TimescaleDB 연동
"""


import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict


from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.env_reader import create_instrument, read_env_sensor


log = logging.getLogger("env_collector")
KST = ZoneInfo("Asia/Seoul")



def ensure_table():
    """
    TimescaleDB 하이퍼테이블 및 연속 집계 생성 (기존 데이터 보존)
    """
    with get_cursor() as cur:
        # 1. 원본 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS env_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                temperature DOUBLE PRECISION,
                humidity DOUBLE PRECISION
            );
        """)
        
        # 2. 하이퍼테이블 변환 (✅ migrate_data => TRUE 추가)
        try:
            cur.execute("""
                SELECT create_hypertable(
                    'env_data', 
                    'time_stamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE,
                    chunk_time_interval => INTERVAL '7 days'
                );
            """)
            log.info("✅ env_data 하이퍼테이블 변환 완료 (기존 데이터 보존)")
        except Exception as e:
            log.info(f"✅ env_data 이미 하이퍼테이블로 존재함")
        
        # 3. 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_env_device_time 
            ON env_data (device_id, time_stamp DESC);
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
                    CREATE MATERIALIZED VIEW IF NOT EXISTS env_data_{interval_name}
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('{interval_str}', time_stamp) AS bucket,
                        device_id,
                        AVG(temperature) AS temperature,
                        AVG(humidity) AS humidity
                    FROM env_data
                    GROUP BY bucket, device_id
                    WITH NO DATA;
                """)
                log.info(f"✅ env_data_{interval_name} 연속 집계 생성 완료")
            except Exception as e:
                log.debug(f"env_data_{interval_name} 이미 존재: {e}")
            
            # 자동 갱신 정책
            try:
                cur.execute(f"""
                    SELECT add_continuous_aggregate_policy('env_data_{interval_name}',
                        start_offset => INTERVAL '3 hours',
                        end_offset => INTERVAL '1 minute',
                        schedule_interval => INTERVAL '1 minute',
                        if_not_exists => TRUE
                    );
                """)
            except Exception as e:
                log.debug(f"⚠️ Policy for env_data_{interval_name}: {e}")
        
        log.info("✅ TimescaleDB 하이퍼테이블 및 연속 집계 준비 완료 (env)")



def insert_row(device_id: int, payload: Dict[str, float]):
    """DB 삽입"""
    now_kst = datetime.now(KST)
    temp = payload.get("temperature")
    humi = payload.get("humidity")
    
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO env_data (time_stamp, device_id, temperature, humidity)
                VALUES (%s, %s, %s, %s)
            """, (now_kst, device_id, temp, humi))
            
            log.debug("🌡️ env: device=%s temp=%.1f°C humi=%.1f%%", 
                     device_id, temp or 0, humi or 0)
    except Exception:
        log.exception("❌ DB insert failed for device=%s", device_id)



def run_once_for_device(device_id: int, fail_counts: dict):
    """단일 장치 읽기"""
    port = settings.ENV_PORT
    baud = settings.ENV_BAUDRATE
    
    try:
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        data = read_env_sensor(inst)
        
        if not isinstance(data, dict):
            raise RuntimeError(f"read_env_sensor returned non-dict: {data}")
        
        insert_row(device_id, data)
        fail_counts[device_id] = 0
        
        if hasattr(inst, 'serial') and inst.serial:
            inst.serial.close()
            
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("⚠️ env read fail device=%s count=%s err=%s", 
                   device_id, fail_counts[device_id], e)



def main():
    """메인 루프"""
    log.info("🌡️ env_collector starting...")
    ensure_table()
    
    device_ids = getattr(settings, "ENV_DEVICE_IDS", [])
    interval = getattr(settings, "ENV_POLL_INTERVAL", 5)
    max_fails = 5
    
    if not device_ids:
        log.warning("⚠️ ENV_DEVICE_IDS가 비어있음")
        return
    
    log.info("📡 env config: port=%s devices=%s interval=%ss",
            settings.ENV_PORT, device_ids, interval)
    
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
        log.info("🛑 env_collector stopped")
    except Exception as e:
        log.exception("❌ env_collector crashed: %s", e)

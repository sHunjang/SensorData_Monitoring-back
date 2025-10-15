# src/collectors/modbus_collector.py

"""
Modbus 수집기 (TAC4300 전력량계) - TimescaleDB 연동

주요 변경사항:
- 하이퍼테이블 자동 생성 (time_stamp 기준, 7일 청크)
- 연속 집계 자동 생성 (1분, 15분, 1시간, 1일 단위)
- energy_delta = 현재 - 이전 누적 에너지 (LAG 윈도우 함수)
- 자동 갱신 정책 (1분마다 최신 데이터 반영)
- 3P3W/3P4W 구분 로직 유지
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.modbus_reader import create_instrument, read_summary

log = logging.getLogger("modbus_collector")
KST = ZoneInfo("Asia/Seoul")


def ensure_table():
    """
    TimescaleDB 하이퍼테이블 및 연속 집계 생성
    """
    with get_cursor() as cur:
        # ==========================================
        # 1. 원본 테이블 생성
        # ==========================================
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                time_stamp TIMESTAMPTZ NOT NULL,
                device_id INT NOT NULL,
                avg_line_to_line_volts_v DOUBLE PRECISION,
                avg_line_to_neutral_volts_v DOUBLE PRECISION,
                sum_line_currents_a DOUBLE PRECISION,
                total_active_power_kw DOUBLE PRECISION,
                total_reactive_power_kvar DOUBLE PRECISION,
                total_apparent_power_kva DOUBLE PRECISION,
                total_power_factor DOUBLE PRECISION,
                total_active_energy_kwh DOUBLE PRECISION,
                total_reactive_energy_kvarh DOUBLE PRECISION,
                total_apparent_energy_kvah DOUBLE PRECISION
            );
        """)
        
        # ==========================================
        # 2. 하이퍼테이블 변환
        # ==========================================
        cur.execute("""
            SELECT create_hypertable(
                'modbus_data', 
                'time_stamp',
                if_not_exists => TRUE,
                chunk_time_interval => INTERVAL '7 days'
            );
        """)
        
        # ==========================================
        # 3. 인덱스 생성
        # ==========================================
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_modbus_device_time 
            ON modbus_data (device_id, time_stamp DESC);
        """)
        
        # ==========================================
        # 4. 연속 집계 - 1분 단위
        # ==========================================
        cur.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_data_1min
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 minute', time_stamp) AS bucket,
                device_id,
                AVG(COALESCE(avg_line_to_line_volts_v, avg_line_to_neutral_volts_v)) AS voltage,
                AVG(sum_line_currents_a) AS current,
                AVG(total_active_power_kw) AS power,
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS energy_delta
            FROM modbus_data
            WHERE total_active_energy_kwh IS NOT NULL
            GROUP BY bucket, device_id
            WITH NO DATA;
        """)
        
        # ==========================================
        # 5. 연속 집계 - 15분 단위
        # ==========================================
        cur.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_data_15min
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('15 minutes', time_stamp) AS bucket,
                device_id,
                AVG(COALESCE(avg_line_to_line_volts_v, avg_line_to_neutral_volts_v)) AS voltage,
                AVG(sum_line_currents_a) AS current,
                AVG(total_active_power_kw) AS power,
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS energy_delta
            FROM modbus_data
            WHERE total_active_energy_kwh IS NOT NULL
            GROUP BY bucket, device_id
            WITH NO DATA;
        """)
        
        # ==========================================
        # 6. 연속 집계 - 1시간 단위
        # ==========================================
        cur.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_data_1hour
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 hour', time_stamp) AS bucket,
                device_id,
                AVG(COALESCE(avg_line_to_line_volts_v, avg_line_to_neutral_volts_v)) AS voltage,
                AVG(sum_line_currents_a) AS current,
                AVG(total_active_power_kw) AS power,
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS energy_delta
            FROM modbus_data
            WHERE total_active_energy_kwh IS NOT NULL
            GROUP BY bucket, device_id
            WITH NO DATA;
        """)
        
        # ==========================================
        # 7. 연속 집계 - 1일 단위
        # ==========================================
        cur.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS modbus_data_1day
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 day', time_stamp) AS bucket,
                device_id,
                AVG(COALESCE(avg_line_to_line_volts_v, avg_line_to_neutral_volts_v)) AS voltage,
                AVG(sum_line_currents_a) AS current,
                AVG(total_active_power_kw) AS power,
                MAX(total_active_energy_kwh) - MIN(total_active_energy_kwh) AS energy_delta
            FROM modbus_data
            WHERE total_active_energy_kwh IS NOT NULL
            GROUP BY bucket, device_id
            WITH NO DATA;
        """)
        
        # ==========================================
        # 8. 자동 갱신 정책 설정
        # ==========================================
        for view_name in ['modbus_data_1min', 'modbus_data_15min', 'modbus_data_1hour', 'modbus_data_1day']:
            try:
                cur.execute(f"""
                    SELECT add_continuous_aggregate_policy('{view_name}',
                        start_offset => INTERVAL '3 hours',
                        end_offset => INTERVAL '1 minute',
                        schedule_interval => INTERVAL '1 minute',
                        if_not_exists => TRUE
                    );
                """)
            except Exception as e:
                log.warning(f"⚠️ Policy for {view_name} already exists or failed: {e}")
        
        log.info("✅ TimescaleDB 하이퍼테이블 및 연속 집계 준비 완료 (modbus)")


def insert_row(device_id: int, payload: Dict[str, float]):
    """
    DB 삽입 - 실제 센서 데이터 저장
    """
    now_kst = datetime.now(KST)
    
    # payload 매핑 (기존 로직 유지)
    llv = payload.get("avg_line_to_line_volts_v") or None
    lnv = payload.get("avg_line_to_neutral_volts_v") or None
    isum = payload.get("sum_line_currents_a") or None
    pkw = payload.get("total_active_power_kw") or None
    qkvar = payload.get("total_reactive_power_kvar") or None
    skva = payload.get("total_apparent_power_kva") or None
    pf = payload.get("total_power_factor") or None
    ekwh = payload.get("total_active_energy_kwh") or None
    erea = payload.get("total_reactive_energy_kvarh") or None
    eapp = payload.get("total_apparent_energy_kvah") or None
    
    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO modbus_data (
                    time_stamp, device_id,
                    avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
                    sum_line_currents_a, total_active_power_kw,
                    total_reactive_power_kvar, total_apparent_power_kva,
                    total_power_factor, total_active_energy_kwh,
                    total_reactive_energy_kvarh, total_apparent_energy_kvah
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (now_kst, device_id, llv, lnv, isum, pkw, qkvar, skva, pf, ekwh, erea, eapp))
            
            log.debug("📊 modbus: device=%s power=%.2f kW energy=%.2f kWh", 
                     device_id, pkw or 0, ekwh or 0)
    except Exception:
        log.exception("❌ DB insert failed for device=%s", device_id)


def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치 읽기 및 저장 (기존 로직 유지)
    """
    port = settings.MODBUS_PORT
    baud = settings.MODBUS_BAUDRATE
    parity = settings.MODBUS_PARITY
    stopbits = settings.MODBUS_STOPBITS
    bytesize = settings.MODBUS_BYTESIZE
    
    try:
        # 장비 연결
        inst = create_instrument(
            port=port, 
            slave_id=device_id,
            baudrate=baud, 
            parity=parity,
            stopbits=stopbits, 
            bytesize=bytesize
        )
        
        # 센서 데이터 읽기
        data = read_summary(inst)
        
        if not isinstance(data, dict):
            raise RuntimeError(f"read_summary returned non-dict: {data}")
        
        # DB 저장
        insert_row(device_id, data)
        
        # 성공 시 실패 카운터 리셋
        fail_counts[device_id] = 0
        
        # 연결 종료
        if hasattr(inst, 'serial') and inst.serial:
            inst.serial.close()
            
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("⚠️ modbus read fail device=%s count=%s err=%s", 
                   device_id, fail_counts[device_id], e)


def main():
    """
    메인 수집 루프
    """
    log.info("🔌 modbus_collector starting...")
    
    # 하이퍼테이블 및 집계 생성
    ensure_table()
    
    # 설정 읽기
    ids_3w = getattr(settings, "MODBUS_3W_IDS", []) or []
    ids_4w = getattr(settings, "MODBUS_4W_IDS", []) or []
    device_ids = list(dict.fromkeys(ids_3w + ids_4w))
    interval = getattr(settings, "MODBUS_POLL_INTERVAL", 5)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 5)
    
    if not device_ids:
        log.warning("⚠️ MODBUS_3W_IDS / MODBUS_4W_IDS가 비어있음. 수집기 종료.")
        return
    
    log.info("📡 modbus config: port=%s devices=%s interval=%ss",
            settings.MODBUS_PORT, device_ids, interval)
    
    # 실패 카운터 초기화
    fail_counts = {sid: 0 for sid in device_ids}
    
    # 메인 루프
    while True:
        for sid in device_ids:
            # 연속 실패 초과 시 스킵
            if fail_counts.get(sid, 0) >= max_fails:
                if fail_counts.get(sid, 0) == max_fails:
                    log.error("🚫 device %s disabled after %s fails", sid, max_fails)
                    fail_counts[sid] = max_fails + 1
                continue
            
            # 센서 읽기
            run_once_for_device(sid, fail_counts)
        
        # 폴링 간격 대기
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("🛑 modbus_collector stopped by user")
    except Exception as e:
        log.exception("❌ modbus_collector crashed: %s", e)

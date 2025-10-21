# src/collectors/modbus_collector.py
"""
Modbus(전력량계) 수집기 - TAC4300 통신
"""

import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from src.config.settings import settings
from src.db.client import get_cursor
from src.sensors.modbus_reader import create_instrument, read_modbus_sensor
from src.collectors.serial_manager import SerialPortManager

log = logging.getLogger("modbus_collector")
KST = ZoneInfo("Asia/Seoul")

def ensure_table():
    """
    TimescaleDB 하이퍼테이블 생성 (기존 데이터 보존)
    """
    with get_cursor() as cur:
        # 1. 원본 테이블
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
        
        # 2. 하이퍼테이블 변환
        try:
            cur.execute("""
                SELECT create_hypertable(
                    'modbus_data',
                    'time_stamp',
                    if_not_exists => TRUE,
                    migrate_data => TRUE,
                    chunk_time_interval => INTERVAL '7 days'
                );
            """)
            log.info("✅ modbus_data 하이퍼테이블 변환 완료 (기존 데이터 보존)")
        except Exception as e:
            log.info(f"✅ modbus_data 이미 하이퍼테이블로 존재함")
        
        # 3. 인덱스
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_modbus_device_time
            ON modbus_data (device_id, time_stamp DESC);
        """)
    
    log.info("✅ TimescaleDB 하이퍼테이블 준비 완료 (modbus)")

def insert_row(device_id: int, payload: Dict[str, float]):
    """DB 삽입"""
    now_kst = datetime.now(KST)
    
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
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                now_kst, device_id,
                payload.get("avg_line_to_line_volts_v"),
                payload.get("avg_line_to_neutral_volts_v"),
                payload.get("sum_line_currents_a"),
                payload.get("total_active_power_kw"),
                payload.get("total_reactive_power_kvar"),
                payload.get("total_apparent_power_kva"),
                payload.get("total_power_factor"),
                payload.get("total_active_energy_kwh"),
                payload.get("total_reactive_energy_kvarh"),
                payload.get("total_apparent_energy_kvah")
            ))
            log.debug("⚡ modbus: device=%s power=%.2f kW",
                      device_id, payload.get("total_active_power_kw", 0))
    except Exception:
        log.exception("❌ DB insert failed for device=%s", device_id)

def run_once_for_device(device_id: int, fail_counts: dict, serial_mgr: SerialPortManager):
    """단일 장치 읽기 - Thread-safe"""
    port = settings.MODBUS_PORT
    baud = settings.MODBUS_BAUDRATE
    
    def read_operation():
        """시리얼 포트 작업"""
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        try:
            data = read_modbus_sensor(inst)
            if not isinstance(data, dict):
                raise RuntimeError(f"read_modbus_sensor returned non-dict: {data}")
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
        log.warning("⚠️ modbus read fail device=%s count=%s err=%s",
                    device_id, fail_counts[device_id], e)

def main():
    """메인 루프"""
    log.info("⚡ modbus_collector starting...")
    ensure_table()
    
    device_ids = getattr(settings, "MODBUS_DEVICE_IDS", [11, 12, 13, 14, 15])
    interval = getattr(settings, "MODBUS_POLL_INTERVAL", 5)
    max_fails = 5
    
    if not device_ids:
        log.warning("⚠️ MODBUS_DEVICE_IDS가 비어있음")
        return
    
    port = settings.MODBUS_PORT
    log.info("📡 modbus config: port=%s devices=%s interval=%ss",
             port, device_ids, interval)
    
    # ✅ Serial Manager 가져오기
    serial_mgr = SerialPortManager.get_instance(port)
    fail_counts = {mid: 0 for mid in device_ids}
    
    while True:
        for mid in device_ids:
            if fail_counts.get(mid, 0) >= max_fails:
                if fail_counts.get(mid, 0) == max_fails:
                    log.error("🚫 device %s disabled", mid)
                    fail_counts[mid] = max_fails + 1
                continue
            
            run_once_for_device(mid, fail_counts, serial_mgr)
        
        time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("🛑 modbus_collector stopped")
    except Exception as e:
        log.exception("❌ modbus_collector crashed: %s", e)

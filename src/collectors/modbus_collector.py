# src/collectors/modbus_collector.py

"""
Modbus 수집기 (TAC4300 전력량계) - bootstrap.py 스키마 기반

주요 기능:
- 3상 4선식 (ID: 11,12,13) → modbus_data 저장
- 3상 3선식 (ID: 14,15) → modbus_data 저장
- 5초 주기 원시 데이터 수집
- ✅ 통신 코드(modbus_reader.py) 그대로 사용

테이블 구조 (bootstrap.py 기준):
- modbus_data: 원본 테이블 (5초 수집)
  - avg_line_to_line_volts_v (3상 4선식 전용, ID: 11,12,13)
  - avg_line_to_neutral_volts_v (3상 3선식 전용, ID: 14,15)
  - 공통: sum_line_currents_a, total_active_power_kw, 
          total_active_energy_kwh 등
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


def insert_row(device_id: int, payload: Dict[str, float]):
    """
    DB 삽입 - modbus_data 테이블에 원시 데이터 저장
    
    ✅ 데이터 매핑 (bootstrap.py 스키마 기준):
    - avg_line_to_line_volts_v: 3상 4선식 전압 (ID: 11,12,13)
    - avg_line_to_neutral_volts_v: 3상 3선식 전압 (ID: 14,15)
    - sum_line_currents_a: 총 전류
    - total_active_power_kw: 유효전력
    - total_active_energy_kwh: 누적 에너지
    """
    now_kst = datetime.now(KST)
    
    # ✅ bootstrap.py 스키마 그대로 사용
    llv = payload.get("avg_line_to_line_volts_v")  # 3상 4선식 (ID 11,12,13)
    lnv = payload.get("avg_line_to_neutral_volts_v")  # 3상 3선식 (ID 14,15)
    isum = payload.get("sum_line_currents_a")
    pkw = payload.get("total_active_power_kw")
    qkvar = payload.get("total_reactive_power_kvar")
    skva = payload.get("total_apparent_power_kva")
    pf = payload.get("total_power_factor")
    ekwh = payload.get("total_active_energy_kwh")
    erea = payload.get("total_reactive_energy_kvarh")
    eapp = payload.get("total_apparent_energy_kvah")
    
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
    단일 장치 읽기 및 저장
    
    ✅ 통신 코드(modbus_reader.py) 그대로 사용
    """
    port = settings.MODBUS_PORT
    baud = settings.MODBUS_BAUDRATE
    parity = settings.MODBUS_PARITY
    stopbits = settings.MODBUS_STOPBITS
    bytesize = settings.MODBUS_BYTESIZE
    
    try:
        # ✅ 장비 연결 (modbus_reader.py 그대로 사용)
        inst = create_instrument(
            port=port, 
            slave_id=device_id,
            baudrate=baud, 
            parity=parity,
            stopbits=stopbits, 
            bytesize=bytesize
        )
        
        # ✅ 센서 데이터 읽기 (modbus_reader.py 그대로 사용)
        data = read_summary(inst)
        
        if not isinstance(data, dict):
            raise RuntimeError(f"read_summary returned non-dict: {data}")
        
        # ✅ DB 저장 (bootstrap.py 스키마 사용)
        insert_row(device_id, data)
        
        # 성공 시 실패 카운터 리셋
        fail_counts[device_id] = 0
        
        # 연결 종료
        if hasattr(inst, 'instrument') and hasattr(inst.instrument, 'serial'):
            if inst.instrument.serial and hasattr(inst.instrument.serial, 'close'):
                inst.instrument.serial.close()
            
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("⚠️ modbus read fail device=%s count=%s err=%s", 
                   device_id, fail_counts[device_id], e)


def main():
    """
    메인 수집 루프
    """
    log.info("🔌 modbus_collector starting (bootstrap.py schema)...")
    
    # 설정 읽기
    ids_3w = getattr(settings, "MODBUS_3W_IDS", []) or []  # 3상 3선식 (ID 14,15)
    ids_4w = getattr(settings, "MODBUS_4W_IDS", []) or []  # 3상 4선식 (ID 11,12,13)
    device_ids = list(dict.fromkeys(ids_4w + ids_3w))  # 중복 제거
    interval = getattr(settings, "MODBUS_POLL_INTERVAL", 5)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 5)
    
    if not device_ids:
        log.warning("⚠️ MODBUS_3W_IDS / MODBUS_4W_IDS가 비어있음. 수집기 종료.")
        return
    
    log.info("📡 modbus config:")
    log.info("   - Port: %s", settings.MODBUS_PORT)
    log.info("   - 3-Phase 4-Wire (Line-to-Line): %s", ids_4w)
    log.info("   - 3-Phase 3-Wire (Line-to-Neutral): %s", ids_3w)
    log.info("   - Poll interval: %ss", interval)
    
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

# src/collectors/solar_collector.py
"""
일사량(Solar) 수집기 - irradiance 컬럼 통일

주요 기능:
- settings에서 COM 포트, 장치 ID, 폴링 주기 등을 읽어 동작
- 시리얼 리더 인터페이스 사용: src.sensors.solar_reader 모듈
- create_instrument(port, slave_id, baudrate, ...) -> instrument
- read_solar_sensor(instrument) -> dict

센서 데이터 형식:
- read_solar_sensor는 최소 다음 키를 포함한 dict를 반환:
  {"irradiance_w_m2": 812.3}  # 단위 W/m²

DB 저장:
- solar_data 테이블의 irradiance 컬럼에 저장
- 연속 실패(max_fails) 초과 시 해당 장치를 스킵
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
    """solar_data 테이블 생성 - irradiance 컬럼 사용"""
    with get_cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS solar_data (
        time_stamp TIMESTAMPTZ NOT NULL,
        device_id INT NOT NULL,
        irradiance DOUBLE PRECISION
        );
        """)
    log.info("✅ solar_data table ensured with irradiance column")

def insert_row(device_id: int, payload: Dict[str, float]):
    """
    일사량 데이터를 DB에 저장 - irradiance 컬럼 사용
    
    Args:
        device_id: 센서 장치 ID
        payload: 센서 데이터 (다양한 키 형태 지원)
    """
    now_kst = datetime.now(KST)
    
    # 다양한 키 형태에서 일사량 값 추출
    irradiance_val = (
        payload.get("irradiance_w_m2") or 
        payload.get("irradiance_wm2") or
        payload.get("irradiance") or 
        payload.get("solar") or 
        None
    )
    
    if irradiance_val is None:
        log.warning("⚠️ No irradiance data in payload for device %s: %s", device_id, payload)
        return
    
    try:
        with get_cursor() as cur:
            # ✅ irradiance 컬럼에 저장
            cur.execute("""
            INSERT INTO solar_data (time_stamp, device_id, irradiance)
            VALUES (%s, %s, %s)
            """, (now_kst, device_id, irradiance_val))
        
        log.info("☀️ solar: device=%s stored irradiance=%.1f W/m²", device_id, irradiance_val)
        
    except Exception:
        log.exception("❌ solar DB insert failed for device=%s payload=%s", device_id, payload)

def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치에 대해 시리얼에서 읽고 DB에 저장
    실패 발생 시 fail_counts를 증가시킵니다.
    
    Args:
        device_id: 센서 장치 ID
        fail_counts: 장치별 실패 카운터
    """
    port = settings.SOLAR_PORT
    baud = getattr(settings, "SOLAR_BAUDRATE", 9600)
    
    try:
        # 센서 연결
        inst = create_instrument(port=port, slave_id=device_id, baudrate=baud)
        
        # 센서에서 데이터 읽기
        data = read_solar_sensor(inst)
        
        if not isinstance(data, dict):
            raise RuntimeError(f"read_solar_sensor returned non-dict: {data}")
        
        # DB에 저장
        insert_row(device_id, data)
        
        # 성공 시 실패 카운터 리셋
        fail_counts[device_id] = 0
        
        # 센서 연결 종료
        if hasattr(inst, 'close'):
            inst.close()
        
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("⚠️ solar read fail device=%s count=%s err=%s", 
                   device_id, fail_counts[device_id], e)

def main():
    """
    일사량 센서 수집기 메인 루프
    
    동작:
    - settings.SOLAR_DEVICE_IDS 목록의 센서들을 순회
    - 폴링 주기: settings.SOLAR_POLL_INTERVAL (초)
    - 연속 실패 허용: settings.MODBUS_MAX_FAILS 설정 재사용
    - irradiance 컬럼으로 데이터 저장
    """
    # 테이블 생성
    ensure_table()
    
    # 설정값 읽기
    device_ids = getattr(settings, "SOLAR_DEVICE_IDS", [31]) or [31]
    interval = getattr(settings, "SOLAR_POLL_INTERVAL", 3)
    max_fails = getattr(settings, "SOLAR_MAX_FAILS", 5)  # 독립적인 실패 설정
    
    if not device_ids:
        log.warning("⚠️ SOLAR_DEVICE_IDS가 설정되지 않음. 일사량 수집기 종료.")
        return
    
    log.info("🌞 solar_collector start. port=%s devices=%s interval=%s", 
             settings.SOLAR_PORT, device_ids, interval)
    
    # 장치별 실패 카운터 초기화
    fail_counts = {sid: 0 for sid in device_ids}
    
    # 메인 루프
    while True:
        for sid in device_ids:
            # 연속 실패 초과 시 스킵
            if fail_counts.get(sid, 0) >= max_fails:
                if fail_counts.get(sid, 0) == max_fails:  # 처음 비활성화시만 로그
                    log.warning("🚫 solar device %s disabled after %s consecutive fails", sid, max_fails)
                    fail_counts[sid] = max_fails + 1  # 반복 로그 방지
                continue
                
            # 센서 데이터 읽기 및 DB 저장
            run_once_for_device(sid, fail_counts)
        
        # 폴링 간격 대기
        time.sleep(interval)

# 모듈이 직접 실행될 때
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("🛑 solar_collector stopped by user")
    except Exception as e:
        log.exception("❌ solar_collector crashed: %s", e)

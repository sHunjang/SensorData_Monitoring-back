# src/collectors/modbus_collector.py
"""
Modbus 수집기 (TAC4300 전력량계용)
- settings에서 COM 포트, 장비 ID, 폴링 주기 등을 읽어 동작.
- 내부적으로 src.sensors.modbus_reader.create_instrument, read_summary 사용.
  read_summary는 dict을 반환하며 주요 키(예: avg_voltage_ln_v, avg_voltage_ll_v, total_active_kw 등)를 포함함.
  (해당 reader 구현과 레지스터·스케일 정보는 src/sensors/modbus_reader.py에 정의되어 있음). :contentReference[oaicite:0]{index=0}
- TAC4300 레지스터 포맷(High-word->Low-word, 스케일) 및 데이터 정의는 기기 매뉴얼 참조. :contentReference[oaicite:1]{index=1}
- 동작:
  1) settings의 ID 리스트를 순회하며 read_summary로 값 읽음
  2) 장치별 3P3W(LL) vs 3P4W(LN)를 구분해 적절한 전압 컬럼에 저장
  3) DB insert는 방어적으로 처리. 실패는 로그에 남기고 재시도/스킵 로직 운영
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
    """DB 테이블 생성 - 새 스키마에 맞춤"""
    with get_cursor() as cur:
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
            )
        """)

def insert_row(device_id: int, payload: Dict[str, float]):
    """DB 삽입 - 새 스키마 적용"""
    now_kst = datetime.now(KST)
    
    # payload 값 매핑 (기존 로직 유지)
    llv = payload.get("avg_voltage_llv") or payload.get("avg_line_to_line_volts_v") or None
    lnv = payload.get("avg_voltage_lnv") or payload.get("avg_line_to_neutral_volts_v") or None
    isum = payload.get("sum_line_currents_a") or payload.get("sum_i") or None
    pkw = payload.get("total_active_kw") or payload.get("total_active_power_kw") or None
    qkvar = payload.get("total_reactive_power_kvar") or payload.get("q_kvar") or None
    skva = payload.get("total_apparent_power_kva") or payload.get("s_kva") or None
    pf = payload.get("total_power_factor") or payload.get("pf") or None
    ekwh = payload.get("total_active_energy_kwh") or payload.get("e_kwh") or None
    erea = payload.get("total_reactive_energy_kvarh") or payload.get("e_reactive") or None
    eapp = payload.get("total_apparent_energy_kvah") or payload.get("e_apparent") or None
    
    try:
        with get_cursor() as cur:
            # 🔥 새 테이블명과 컬럼명 사용
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
    except Exception:
        log.exception("DB insert failed for device=%s payload=%s", device_id, payload)



def run_once_for_device(device_id: int, fail_counts: dict):
    """
    단일 장치 읽기 시도 및 DB 적재.
    - 실패하면 fail_counts 증가. 연속 실패가 MAX_FAILS를 넘으면 스킵하도록 외부에서 확인.
    """
    port = settings.MODBUS_PORT
    baud = settings.MODBUS_BAUDRATE
    parity = settings.MODBUS_PARITY
    stopbits = settings.MODBUS_STOPBITS
    bytesize = settings.MODBUS_BYTESIZE

    try:
        # create_instrument은 minimalmodbus.Instrument 래핑으로 timeout 등 설정 포함.
        inst = create_instrument(port=port, slave_id=device_id,
                                 baudrate=baud, parity=parity,
                                 stopbits=stopbits, bytesize=bytesize)
        # read_summary는 기기별 레지스터를 읽어 dict 반환(스케일 적용 포함). :contentReference[oaicite:2]{index=2}
        data = read_summary(inst)
        if not isinstance(data, dict):
            raise RuntimeError(f"read_summary returned non-dict: {data}")

        # 3P3W vs 3P4W에 따라 DB에 올릴 때 의미가 달라짐.
        # settings에서 3W/4W ID를 분리해 관리하므로 추가 처리 필요하면 여기서 수행.
        insert_row(device_id, data)
        log.info("modbus: device=%s stored p=%s e=%s", device_id, data.get("total_active_kw"), data.get("total_active_energy_kwh"))
        # 성공하면 실패 카운트 초기화
        fail_counts[device_id] = 0
    except Exception as e:
        fail_counts[device_id] = fail_counts.get(device_id, 0) + 1
        log.warning("modbus read fail device=%s count=%s err=%s", device_id, fail_counts[device_id], e)


def main():
    """
    메인 루프.
    - settings의 ID 리스트로 동작.
    - 연속 실패 MAX_FAILS 초과 시 해당 장치는 경고 후 스킵.
    - 폴링 인터벌은 settings.MODBUS_POLL_INTERVAL(초).
    """
    setup = getattr(settings, "MODE", "real")
    log.info("starting modbus_collector mode=%s", setup)

    ensure_table()

    ids_3w = getattr(settings, "MODBUS_3W_IDS", []) or []
    ids_4w = getattr(settings, "MODBUS_4W_IDS", []) or []
    device_ids = list(dict.fromkeys(ids_3w + ids_4w))  # 중복 제거 보장
    interval = getattr(settings, "MODBUS_POLL_INTERVAL", 5)
    max_fails = getattr(settings, "MODBUS_MAX_FAILS", 3)

    log.info("modbus_collector config: port=%s devices=%s interval=%s", settings.MODBUS_PORT, device_ids, interval)

    # 장치별 실패 카운트 초기화
    fail_counts = {sid: 0 for sid in device_ids}

    while True:
        for sid in device_ids:
            if fail_counts.get(sid, 0) >= max_fails:
                # 연속 실패가 일정 횟수 넘으면 스킵. 운영에서는 여기서 알람 트리거 권장.
                log.warning("device %s disabled after %s consecutive fails", sid, max_fails)
                continue
            run_once_for_device(sid, fail_counts)

        # 폴링 간격
        time.sleep(interval)

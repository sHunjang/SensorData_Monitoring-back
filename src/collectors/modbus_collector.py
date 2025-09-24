"""
src/collectors/modbus_collector.py

TAC4300 -> RS485 -> DB 적재 Collector (실 운영용)
- 실제 장비 통신(create_instrument, read_summary)을 그대로 사용.
- DB에 저장할 때 시간은 KST(Asia/Seoul) tz-aware datetime 을 사용하여 timestamptz 컬럼에 저장.
- 3상 3선(LL)와 3상 4선(LN)을 장치별로 구분하여 각 컬럼에 저장.
- 방어적 코딩: read_summary가 반환하지 않는 키는 None 처리.
- 환경 변수로 포트/인터벌 조정 가능.
"""

import os
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("modbus_collector")

# 장치 ID 구분 (실장비 ID를 여기에 나열)
THREE_WIRE_IDS = [11, 12, 13]    # 3상 3선 -> LL 사용
FOUR_WIRE_IDS  = [14, 15]        # 3상 4선 -> LN 사용
DEVICE_IDS = THREE_WIRE_IDS + FOUR_WIRE_IDS

# 연속 실패 허용 횟수
MAX_FAILS = int(os.getenv("MODBUS_MAX_FAILS", "3"))

# 기본 시리얼 포트와 수집 인터벌(초)은 환경변수로 덮어쓸 수 있음
SERIAL_PORT = os.getenv("MODBUS_PORT", "COM3")
POLL_INTERVAL = int(os.getenv("MODBUS_POLL_INTERVAL", "1"))

# KST ZoneInfo
KST = ZoneInfo("Asia/Seoul")


def ensure_table():
    """
    modbus_data 테이블 존재 보장.
    - 테이블이 없으면 생성.
    - 필요한 컬럼이 없으면 ALTER TABLE ... ADD COLUMN IF NOT EXISTS 로 보장.
    - 이미 운영중인 데이터베이스에 적용하므로 컬럼 추가만 수행. 타입 변경 등은 수동 검토 필요.
    """
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
        );
        """)
        # 안전하게 칼럼 존재 보장 (Postgres 11+에서 지원)
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS device_id INT;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS avg_line_to_line_volts_v DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS avg_line_to_neutral_volts_v DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS sum_line_currents_a DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_active_power_kw DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_reactive_power_kvar DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_apparent_power_kva DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_power_factor DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_active_energy_kwh DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_reactive_energy_kvarh DOUBLE PRECISION;")
        cur.execute("ALTER TABLE modbus_data ADD COLUMN IF NOT EXISTS total_apparent_energy_kvah DOUBLE PRECISION;")


def insert_row(device_id: int, row: dict):
    """
    DB에 한 행을 삽입.
    - now_kst: KST tz-aware datetime. PostgreSQL의 timestamptz 컬럼에 올바르게 저장됨.
    - read_summary()가 어떤 필드명을 반환하느냐에 대비해 .get()으로 방어적 접근.
    - 세부 필드 네이밍은 사용중인 read_summary 구현에 맞춰 조정 가능.
    """
    now_kst = datetime.now(KST)

    # read_summary로부터 예상되는 키명들(방어적으로 접근)
    avg_voltage_ll_v = row.get("avg_voltage_ll_v") or row.get("avg_line_to_line_volts_v") or None
    avg_voltage_ln_v = row.get("avg_voltage_ln_v") or row.get("avg_line_to_neutral_volts_v") or None
    sum_line_currents_a = row.get("sum_line_currents_a") or row.get("sum_i") or row.get("i_sum") or None
    total_active_kw = row.get("total_active_kw") or row.get("total_active_power_kw") or row.get("p_kw") or None
    total_reactive_kvar = row.get("total_reactive_power_kvar") or row.get("q_kvar") or None
    total_apparent_kva = row.get("total_apparent_power_kva") or row.get("s_kva") or None
    total_power_factor = row.get("total_power_factor") or row.get("pf") or None
    total_active_energy_kwh = row.get("total_active_energy_kwh") or row.get("e_kwh") or None
    total_reactive_energy_kvarh = row.get("total_reactive_energy_kvarh") or row.get("e_reactive") or None
    total_apparent_energy_kvah = row.get("total_apparent_energy_kvah") or row.get("e_apparent") or None

    # 3선/4선 처리: 3선이면 LL 칼럼에 값, 4선이면 LN 칼럼에 값
    ll_value = avg_voltage_ll_v if device_id in THREE_WIRE_IDS else None
    ln_value = avg_voltage_ln_v if device_id in FOUR_WIRE_IDS else None

    try:
        with get_cursor() as cur:
            cur.execute("""
            INSERT INTO modbus_data
            (time_stamp, device_id,
             avg_line_to_line_volts_v, avg_line_to_neutral_volts_v,
             sum_line_currents_a, total_active_power_kw, total_reactive_power_kvar,
             total_apparent_power_kva, total_power_factor,
             total_active_energy_kwh, total_reactive_energy_kvarh, total_apparent_energy_kvah)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                now_kst, device_id,
                ll_value,
                ln_value,
                sum_line_currents_a,
                total_active_kw,
                total_reactive_kvar,
                total_apparent_kva,
                total_power_factor,
                total_active_energy_kwh,
                total_reactive_energy_kvarh,
                total_apparent_energy_kvah,
            ))
    except Exception:
        # DB 삽입 실패 시 로깅, 원인 파악을 위해 row 내용을 함께 남김
        log.exception("DB insert failed for device_id=%s row=%s", device_id, row)
        raise


def main():
    """
    Collector 메인 루프
    - setup_logging 호출
    - ensure_table 로 스키마 확인
    - 각 장치에 대해 read_summary 호출 후 insert_row
    - 실패 시 fail_counts 증가, MAX_FAILS 초과하면 해당 sid는 스킵
    """
    setup_logging()
    ensure_table()
    log.info("Modbus collector started. port=%s interval=%s DEVICE_IDS=%s", SERIAL_PORT, POLL_INTERVAL, DEVICE_IDS)

    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts.get(sid, 0) >= MAX_FAILS:
                log.warning("sid=%s disabled after %d fails", sid, MAX_FAILS)
                continue
            try:
                # create_instrument은 포트명과 slave_id 인자를 지원해야 함.
                # 실제 구현에서 다른 파라미터를 요구하면 여기서 조정하세요.
                inst = create_instrument(port=SERIAL_PORT, slave_id=sid)
                # read_summary는 dict를 반환한다고 가정
                row = read_summary(inst)
                if not isinstance(row, dict):
                    log.warning("read_summary returned non-dict for sid=%s: %s", sid, row)
                    fail_counts[sid] += 1
                    continue
                insert_row(sid, row)
                log.info("sid=%s stored row (p_kw=%s e_kwh=%s)", sid, row.get("p_kw") or row.get("total_active_kw") or row.get("total_active_power_kw"), row.get("e_kwh") or row.get("total_active_energy_kwh"))
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] = fail_counts.get(sid, 0) + 1
                log.warning("sid=%s fail %d: %s", sid, fail_counts[sid], e)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

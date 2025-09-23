"""
modbus_collector.py
- TAC4300 → RS485 → DB 적재
- KST(Asia/Seoul) 타임스탬프 저장
- LL/LN 전압 분리 컬럼 설계
"""
import time, logging
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+
from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import get_cursor
from src.common.logging_config import setup_logging

log = logging.getLogger("modbus_collector")

# 장치 ID 구분
FOUR_WIRE_IDS  = [14, 15]        # 3상 4선 → LN 사용
THREE_WIRE_IDS = [11, 12, 13]    # 3상 3선 → LL 사용
DEVICE_IDS = THREE_WIRE_IDS + FOUR_WIRE_IDS

# 연속 실패 허용 횟수
MAX_FAILS = 3

def ensure_table():
    """
    수집 테이블 보장.
    - avg_line_to_line_volts_v: 3상 3선에서 주로 사용
    - avg_line_to_neutral_volts_v: 3상 4선에서 주로 사용
    - 컬럼명: 서비스 쿼리와 1:1 매칭되도록 소문자 스네이크로 통일
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

def insert_row(device_id: int, row: dict):
    """
    KST로 저장.
    - timestamptz 컬럼에 tz-aware datetime을 전달하면 PostgreSQL이 정확히 저장.
    - 3선은 LL, 4선은 LN에 값을 채우고 반대쪽은 NULL.
    """
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
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
            row["avg_voltage_ll_v"] if device_id in THREE_WIRE_IDS else None,
            row["avg_voltage_ln_v"] if device_id in FOUR_WIRE_IDS  else None,
            row["sum_line_currents_a"],
            row["total_active_kw"],
            row["total_reactive_power_kvar"],
            row["total_apparent_power_kva"],
            row["total_power_factor"],
            row["total_active_energy_kwh"],
            row["total_reactive_energy_kvarh"],
            row["total_apparent_energy_kvah"],
        ))

def main():
    setup_logging()
    ensure_table()
    log.info("Modbus collector started.")

    fail_counts = {sid: 0 for sid in DEVICE_IDS}

    while True:
        for sid in DEVICE_IDS:
            if fail_counts[sid] >= MAX_FAILS:
                log.warning("sid=%s disabled after %d fails", sid, MAX_FAILS)
                continue
            try:
                inst = create_instrument(slave_id=sid)
                row = read_summary(inst)   # LL/LN, 전류, 유효/무효/피상, PF, 에너지
                insert_row(sid, row)
                log.info("sid=%s row=%s", sid, row)
                fail_counts[sid] = 0
            except Exception as e:
                fail_counts[sid] += 1
                log.warning("sid=%s fail %d: %s", sid, fail_counts[sid], e)
        time.sleep(60)  # 1분 주기 적재(운영권장)

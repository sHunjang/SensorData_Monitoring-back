"""
전력 데이터 수집 루프
- 1분 주기 실행
- Modbus 전력계에서 데이터 읽어 DB에 저장
- 테이블 없으면 자동 생성
"""
import time, logging
from minimalmodbus import NoResponseError, InvalidResponseError
from src.common.logging_config import setup_logging
from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import get_cursor

def insert_modbus_row(row: dict):
    with get_cursor() as cur:
        # 테이블 없으면 자동 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modbus_data (
                ts TIMESTAMPTZ NOT NULL,
                avg_voltage DOUBLE PRECISION,
                sum_current DOUBLE PRECISION,
                p_total DOUBLE PRECISION,
                q_total DOUBLE PRECISION,
                s_total DOUBLE PRECISION,
                pf_total DOUBLE PRECISION,
                e_active DOUBLE PRECISION,
                e_reactive DOUBLE PRECISION,
                e_apparent DOUBLE PRECISION
            );
        """)
        # 데이터 삽입
        cur.execute("""
            INSERT INTO modbus_data
            (ts, avg_voltage, sum_current, p_total, q_total, s_total,
             pf_total, e_active, e_reactive, e_apparent)
            VALUES (NOW(), %s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            row["avg_voltage_V"], row["sum_current_A"], row["total_active_kW"],
            row["total_reactive_kvar"], row["total_apparent_kVA"], row["total_power_factor"],
            row["total_active_energy_kWh"], row["total_reactive_energy_kvarh"], row["total_apparent_energy_kVAh"]
        ))

def main():
    setup_logging()
    log = logging.getLogger("collector")
    inst = create_instrument()

    while True:
        try:
            row = read_summary(inst)
            insert_modbus_row(row)
            log.info("전력: V=%.2f I=%.2f P=%.2f kW", row["avg_voltage_V"], row["sum_current_A"], row["total_active_kW"])
        except (NoResponseError, InvalidResponseError) as e:
            log.warning("Modbus 오류: %s", e)
        except Exception as e:
            log.exception("collector error: %s", e)
        time.sleep(60)  # 1분 주기

if __name__ == "__main__":
    main()

"""
1분 주기 수집 루프.
- 테이블 없으면 자동 생성 (CREATE TABLE IF NOT EXISTS).
- Modbus 읽기 실패 시 로그만 남기고 다음 주기로 진행.
- DB 연결은 호출마다 열고 닫아 간단하게 유지.
- 값은 소수점 둘째 자리까지 반올림해서 저장.
"""

import time
import logging
from minimalmodbus import NoResponseError, InvalidResponseError

from src.common.logging_config import setup_logging
from src.config.settings import settings
from src.sensors.modbus_reader import create_instrument, read_summary
from src.db.client import insert_modbus_row, ensure_tables_exist


def main():
    setup_logging()
    log = logging.getLogger("collector")

    # 테이블 자동 생성
    ensure_tables_exist()
    log.info("ensured modbus_data table exists")

    inst = create_instrument()

    poll = max(5, int(settings.serial.poll_seconds))  # 최소 5초 안전장치
    log.info(
        "collector start: port=%s slave=%d interval=%ds",
        settings.serial.port,
        settings.serial.slave_id,
        poll,
    )

    while True:
        t0 = time.time()
        try:
            row = read_summary(inst)
            
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 2)
            
            
            insert_modbus_row(row)
            log.info(
                "ok v=%.2fV i=%.3fA p=%.3fkW pf=%.3f",
                row["avg_voltage_V"],
                row["sum_current_A"],
                row["total_active_kW"],
                row["total_power_factor"],
            )
        except (NoResponseError, InvalidResponseError) as e:
            log.warning("modbus error: %s", e)
        except Exception as e:
            log.exception("unexpected error: %s", e)

        dt = time.time() - t0
        sleep_s = max(0, poll - dt)
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()

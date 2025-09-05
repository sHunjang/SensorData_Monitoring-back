"""
실시간 전력량 계산 루프.
- DB에서 최근 2개 누적 에너지 값(e_active) 조회
- ΔE / Δt 로 순간 전력(kW) 계산
- 5초마다 갱신
"""

import time, logging, psycopg2
from src.config.settings import settings
from src.common.logging_config import setup_logging

def get_realtime_power():
    conn = psycopg2.connect(settings.pg_dsn)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, e_active
        FROM modbus_data
        ORDER BY ts DESC
        LIMIT 2;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if len(rows) < 2:
        return None

    (t1, e1), (t0, e0) = rows[0], rows[1]  # 최신, 이전
    dt_hours = (t1 - t0).total_seconds() / 3600.0
    if dt_hours <= 0:
        return None

    delta_e = e1 - e0  # kWh 차이
    realtime_kw = delta_e / dt_hours  # kW
    return round(realtime_kw, 2)

def main():
    setup_logging()
    log = logging.getLogger("realtime_monitor")

    log.info("realtime monitor started (every 5s)")
    while True:
        try:
            power = get_realtime_power()
            if power is not None:
                log.info("realtime power = %.2f kW", power)
            else:
                log.warning("데이터 부족 → 계산 불가")
        except Exception as e:
            log.exception("error in realtime monitor: %s", e)

        time.sleep(5)

if __name__ == "__main__":
    main()

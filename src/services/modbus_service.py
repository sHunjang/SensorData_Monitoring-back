"""
Modbus 데이터 관련 로직
- 시간별 집계 조회
- 실시간 전력 계산
"""

from typing import Optional, List, Dict
from src.db.client import get_cursor

def get_modbus_data(interval: str = "1h", start: Optional[str] = None, end: Optional[str] = None):
    """
    주어진 시간 구간으로 버킷 집계된 데이터 조회
    : interval -> time_bucket 간격 (ex: '15 minutes', '1h', '1d')
    : start -> 조회 시작 시간 (YYYY-MM-DD HH:MM:SS)
    : end -> 조회 종료 시간 (YYYY-MM-DD HH:MM:SS)
    """
    
    sql = f"""
        SELECT time_bucket(%s, ts) AS bucket,
               avg(avg_voltage), avg(sum_current),
               avg(p_total), avg(q_total), avg(s_total),
               avg(pf_total),
               max(e_active)-min(e_active),
               max(e_reactive)-min(e_reactive),
               max(e_apparent)-min(e_apparent)
        FROM modbus_data
        WHERE (%s IS NULL OR ts >= %s)
          AND (%s IS NULL OR ts <= %s)
        GROUP BY bucket
        ORDER BY bucket;
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (interval, start, start, end, end))
        rows = cur.fetchall()
    
    return [
        {
            "bucket": r[0],
            "avg_voltage": round(r[1], 2) if r[1] else None,
            "sum_current": round(r[2], 2) if r[2] else None,
            "p_total": round(r[3], 2) if r[3] else None,
            "q_total": round(r[4], 2) if r[4] else None,
            "s_total": round(r[5], 2) if r[5] else None,
            "pf_total": round(r[6], 3) if r[6] else None,
            "delta_e_active": round(r[7], 2) if r[7] else None,
            "delta_e_reactive": round(r[8], 2) if r[8] else None,
            "delta_e_apparent": round(r[9], 2) if r[9] else None,
        }
        for r in rows
    ]


def get_realtime_power() -> Optional[float]:
    """
    실시간 전력(kW) 계산
    최근 두 개 누적 에너지(e_active) 차이 / 시간 간격
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT ts, e_active
            FROM modbus_data
            ORDER BY ts DESC
            LIMIT 2;
        """)
        rows = cur.fetchall()

    if len(rows) < 2:
        return None

    (t1, e1), (t0, e0) = rows[0], rows[1]
    dt_hours = (t1 - t0).total_seconds() / 3600.0
    if dt_hours <= 0:
        return None

    delta_e = e1 - e0
    realtime_kw = delta_e / dt_hours
    return round(realtime_kw, 2)
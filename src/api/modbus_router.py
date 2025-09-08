"""
전력 데이터 API
- /data/modbus → 집계 데이터 조회
- /data/modbus/realtime → 실시간 전력 계산
"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.client import get_cursor

router = APIRouter()

@router.get("/modbus")
def get_modbus(interval: str = "1h", start: Optional[str] = None, end: Optional[str] = None):
    """
    시간 버킷(interval) 단위로 집계된 전력 데이터 반환
    예: /data/modbus?interval=1h&start=2025-09-01&end=2025-09-03
    """
    sql = f"""
        SELECT time_bucket(%s, ts) AS bucket,
               avg(avg_voltage), avg(sum_current),
               avg(p_total), avg(q_total), avg(s_total),
               avg(pf_total)
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
        {"bucket": r[0], "voltage": r[1], "current": r[2], "p_total": r[3]}
        for r in rows
    ]

@router.get("/modbus/realtime")
def modbus_realtime():
    """
    최근 2개 누적 에너지(e_active) 값으로 순간 전력(kW) 계산
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT ts, e_active FROM modbus_data
            ORDER BY ts DESC LIMIT 2;
        """)
        rows = cur.fetchall()
    if len(rows) < 2:
        return {"realtime_power_kW": None}
    (t1, e1), (t0, e0) = rows[0], rows[1]
    dt_hours = (t1 - t0).total_seconds()/3600
    val = (e1 - e0)/dt_hours if dt_hours > 0 else None
    return {"realtime_power_kW": round(val,2) if val else None}

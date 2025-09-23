"""
/data/modbus routes
- /realtime?device_id=...
- /query?device_id=...&series=power,voltage,...
- /today?device_id=...

목적:
- modbus 관련 시계열 데이터와 스냅샷을 일관된 JSON 스펙으로 제공.
- DB에서 time_stamp를 UTC로 정규화하여 읽고, 응답에서는 KST ISO 문자열을 사용.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.db.client import get_cursor
from src.api._utils import make_query_response, make_realtime_response

router = APIRouter(prefix="/data/modbus", tags=["modbus"])

@router.get("/realtime")
def realtime(device_id: int = Query(...)):
    """
    가장 최근 한 행을 가져와서 snapshot 반환.
    반환 예: {"device_id": 11, "time_stamp": "2025-09-23T13:00:00+09:00", "metrics": {"p_kw": 1.23, "e_kwh": 4.56}}
    """
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT time_stamp AT TIME ZONE 'UTC' AS ts_utc,
                       device_id,
                       total_active_power_kw, total_active_energy_kwh,
                       avg_line_to_line_volts_v, sum_line_currents_a, total_power_factor
                FROM modbus_data
                WHERE device_id = %s
                ORDER BY time_stamp DESC
                LIMIT 1
            """, (device_id,))
            r = cur.fetchone()
            if not r:
                return make_realtime_response(device_id, None, {"p_kw": None, "e_kwh": None})
            ts, dev, p_kw, e_kwh, v_avg, i_sum, pf = r
            metrics = {"p_kw": p_kw, "e_kwh": e_kwh, "v_avg": v_avg, "i_sum": i_sum, "pf": pf}
            return make_realtime_response(dev, ts, metrics, raw=r)
    except Exception as ex:
        return {"error": str(ex)}

@router.get("/query")
def query(device_id: int = Query(...), series: Optional[str] = Query(None), preset: Optional[str] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), max_points: int = Query(500)):
    """
    시계열 쿼리:
    - series는 comma separated string. 가능한 값: power,energy,voltage,current,pf
    - 반환: make_query_response 형태
    """
    from datetime import datetime
    def resolve_window(preset, start, end):
        now = datetime.now(timezone.utc)
        if preset and not (start or end):
            if preset == "15m": return now - timedelta(minutes=15), now, "1 minute"
            if preset == "1h": return now - timedelta(hours=1), now, "5 minutes"
            if preset == "1d": return now - timedelta(days=1), now, "1 hour"
            if preset == "1w": return now - timedelta(weeks=1), now, "6 hours"
            if preset == "1mo": return now - timedelta(days=30), now, "1 day"
        s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
        e = datetime.fromisoformat(end) if end else now
        if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
        return s, e, "1 hour"

    s, e, bucket = resolve_window(preset, start, end)
    sel_series = (series or "power").split(",")
    col_map = {
        "power": "total_active_power_kw",
        "energy": "total_active_energy_kwh",
        "voltage": "avg_line_to_line_volts_v",
        "current": "sum_line_currents_a",
        "pf": "total_power_factor"
    }
    # build SQL select columns robustly
    select_cols = ["time_stamp AT TIME ZONE 'UTC' as ts_utc", "device_id"] + [f"{col_map.get(s, 'NULL')} AS {s}" for s in sel_series]
    sql_select = ", ".join(select_cols)
    try:
        with get_cursor() as cur:
            cur.execute(f"""
                SELECT {sql_select}
                FROM modbus_data
                WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC
                LIMIT %s
            """, (device_id, s, e, max_points))
            rows = []
            for r in cur.fetchall():
                ts = r[0]
                dev = r[1]
                vals = r[2:]
                row = {"bucket": ts.isoformat() if ts else None, "device_id": dev}
                for i, k in enumerate(sel_series):
                    row[k] = vals[i]
                rows.append(row)
        # stats
        stats = {}
        for k in sel_series:
            vals = [r[k] for r in rows if r.get(k) is not None]
            stats[k] = {"avg": sum(vals)/len(vals) if vals else None, "max": max(vals) if vals else None, "min": min(vals) if vals else None, "count": len(vals)}
        return make_query_response(s, e, bucket, sel_series, rows, stats)
    except Exception as ex:
        return make_query_response(None, None, bucket, [], [], {}, error=str(ex))

@router.get("/today")
def today(device_id: int = Query(...)):
    """
    오늘(서버 KST 00:00)부터 현재까지 누적 전력량 조회(간단 구현).
    - 반환: { device_id, kwh }
    """
    try:
        with get_cursor() as cur:
            # date_trunc('day', NOW() AT TIME ZONE 'Asia/Seoul')는 KST의 오늘 00:00을 반환.
            cur.execute("""
                SELECT SUM(total_active_energy_kwh) FROM modbus_data
                WHERE device_id=%s AND time_stamp >= date_trunc('day', NOW() AT TIME ZONE 'Asia/Seoul') AT TIME ZONE 'UTC'
            """, (device_id,))
            v = cur.fetchone()[0]
            return {"device_id": device_id, "kwh": v}
    except Exception as ex:
        return {"device_id": device_id, "kwh": None, "error": str(ex)}

"""
src/services/solar_service.py

- DB에서 device_id로 필터링 가능하도록 구현
- 반환 데이터의 bucket은 KST tz-aware ISO 문자열
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.api._utils import iso_kst, make_query_response

KST = ZoneInfo("Asia/Seoul")

def query_solar_window(preset: Optional[str] = None,
                       start: Optional[str] = None,
                       end: Optional[str] = None,
                       max_points: int = 500,
                       device_id: Optional[int] = None) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m": s, e, bucket = now - timedelta(minutes=15), now, "1 minute"
        elif preset == "1h": s, e, bucket = now - timedelta(hours=1), now, "5 minutes"
        elif preset == "1d": s, e, bucket = now - timedelta(days=1), now, "1 hour"
        elif preset == "1w": s, e, bucket = now - timedelta(weeks=1), now, "6 hours"
        else: s, e, bucket = now - timedelta(days=30), now, "1 day"
    else:
        s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
        e = datetime.fromisoformat(end) if end else now
        if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
        if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
        bucket = "1 hour"

    try:
        with get_cursor() as cur:
            if device_id is None:
                cur.execute("""
                    SELECT time_stamp, device_id, solar
                    FROM solar_data
                    WHERE time_stamp >= %s AND time_stamp <= %s
                    ORDER BY time_stamp DESC
                    LIMIT %s;
                """, (s, e, max_points))
            else:
                cur.execute("""
                    SELECT time_stamp, device_id, solar
                    FROM solar_data
                    WHERE device_id = %s AND time_stamp >= %s AND time_stamp <= %s
                    ORDER BY time_stamp DESC
                    LIMIT %s;
                """, (device_id, s, e, max_points))

            rows_raw = cur.fetchall()

        rows: List[Dict[str, Any]] = []
        for ts, did, solar in rows_raw:
            if ts is not None and ts.tzinfo is None:
                ts = ts.replace(tzinfo=KST)
            rows.append({
                "bucket": iso_kst(ts),
                "device_id": did,
                "solar": round(float(solar), 2) if solar is not None else None
            })

        sols = [r["solar"] for r in rows if r["solar"] is not None]
        stats = {
            "solar": {
                "avg": round(sum(sols) / len(sols), 2) if sols else None,
                "max": max(sols) if sols else None,
                "min": min(sols) if sols else None,
                "count": len(sols)
            }
        }

        return make_query_response(s, e, bucket, ["solar"], rows, stats)
    except Exception as ex:
        return make_query_response(None, None, "1 hour", ["solar"], [], {}, error=str(ex))

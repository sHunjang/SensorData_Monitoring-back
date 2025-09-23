"""
/data/solar/query
- 목적: 일사량(또는 다른 solar 센서 값) 시계열 조회
- 반환 포맷: make_query_response
- 주의: DB의 solar_data 테이블은 device_id NOT NULL 을 가진다(bootstrap과 수집기 일치)
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.db.client import get_cursor
from src.api._utils import make_query_response

router = APIRouter(prefix="/data/solar", tags=["solar"])

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
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

@router.get("/query")
def query_solar(preset: Optional[str] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), max_points: int = Query(500)):
    s, e, bucket = resolve_window(preset, start, end)
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT time_stamp AT TIME ZONE 'UTC' AS ts_utc, device_id, solar
                FROM solar_data
                WHERE time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC
                LIMIT %s
            """, (s, e, max_points))
            rows = []
            for ts, device_id, solar in cur.fetchall():
                rows.append({
                    "bucket": ts.isoformat() if ts else None,
                    "device_id": device_id,
                    "solar": solar
                })

        sols = [r["solar"] for r in rows if r["solar"] is not None]
        stats = {"solar": {"avg": sum(sols)/len(sols) if sols else None, "max": max(sols) if sols else None, "min": min(sols) if sols else None, "count": len(sols)}}

        return make_query_response(s, e, bucket, ["solar"], rows, stats)
    except Exception as ex:
        return make_query_response(None, None, bucket, ["solar"], [], {}, error=str(ex))

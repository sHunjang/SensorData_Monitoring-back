# src/api/env_router.py
"""
/data/env/query
- 목적:
    온도/습도 시계열 조회. solar_router.py에서 적용한 개선사항들을 동일하게 적용.
- 특징:
    - start/end ISO 문자열에 'Z' 포함되어도 안전하게 파싱.
    - device_id 또는 deviceId 둘 다 수용.
    - max_points 서버측 cap 적용.
    - 반환: make_query_response 형식. bucket 값은 KST tz-aware ISO.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/env", tags=["env"])

SERVER_MAX_POINTS = 5000
DEFAULT_POINTS = 500

def parse_iso_flexible(s: str) -> datetime:
    if s is None:
        raise ValueError("empty")
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m": return now - timedelta(minutes=15), now, "1 minute"
        if preset == "1h":  return now - timedelta(hours=1), now, "5 minutes"
        if preset == "1d":  return now - timedelta(days=1), now, "1 hour"
        if preset == "1w":  return now - timedelta(weeks=1), now, "6 hours"
        if preset == "1mo": return now - timedelta(days=30), now, "1 day"

    try:
        s = parse_iso_flexible(start) if start else (now - timedelta(hours=1))
        e = parse_iso_flexible(end) if end else now
    except Exception as ex:
        raise ValueError(f"invalid start/end datetime: {ex}")

    if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
    return s.astimezone(timezone.utc), e.astimezone(timezone.utc), "1 hour"

@router.get("/query")
def query_env(
    preset: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    max_points: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    deviceId: Optional[int] = Query(None),
):
    """
    안전한 온/습도 시계열 조회.
    - device_id/deviceId 지원
    - max_points 서버 cap 적용
    """
    dev_id = device_id if device_id is not None else deviceId

    if max_points is None:
        max_points = DEFAULT_POINTS
    try:
        max_points = int(max_points)
    except Exception:
        max_points = DEFAULT_POINTS
    if max_points < 1:
        max_points = DEFAULT_POINTS
    if max_points > SERVER_MAX_POINTS:
        max_points = SERVER_MAX_POINTS

    try:
        s, e, bucket = resolve_window(preset, start, end)
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    try:
        with get_cursor() as cur:
            sql = """
                SELECT time_stamp, device_id, temperature, humidity
                FROM env_data
                WHERE time_stamp >= %s AND time_stamp <= %s
            """
            params: List[Any] = [s, e]
            if dev_id is not None:
                sql += " AND device_id = %s"
                params.append(dev_id)
            sql += " ORDER BY time_stamp DESC LIMIT %s"
            params.append(max_points)

            cur.execute(sql, tuple(params))
            rows: List[Dict[str, Any]] = []
            for ts, dev, temp, hum in cur.fetchall():
                rows.append({
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev,
                    "temperature": temp,
                    "humidity": hum,
                })

        # stats for temperature & humidity
        def make_stat(key: str):
            vals = [r[key] for r in rows if r.get(key) is not None]
            return {
                "avg": (sum(vals) / len(vals)) if vals else None,
                "max": max(vals) if vals else None,
                "min": min(vals) if vals else None,
                "count": len(vals),
            }

        stats = {"temperature": make_stat("temperature"), "humidity": make_stat("humidity")}

        return make_query_response(s, e, bucket, ["temperature", "humidity"], rows, stats)

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

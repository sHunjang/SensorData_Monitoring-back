"""
일사량(solar) API 업그레이드
- /data/solar/query : time_bucket 집계 + 통계(평균/최대/최소/개수)
- 성능 제어: max_points 기반 버킷 자동 확대
"""
from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime
from src.db.client import get_cursor
from src.services.modbus_service import resolve_window, choose_bucket_seconds, seconds_to_interval_str

router = APIRouter(prefix="/data/solar", tags=["solar"])

def _query_solar(bucket: str, s: datetime, e: datetime) -> List[Dict]:
    sql = """
        SELECT time_bucket(%s, ts) AS bucket, avg(value) AS solar
        FROM solar_data
        WHERE ts >= %s AND ts <= %s
        GROUP BY bucket
        ORDER BY bucket
    """
    with get_cursor() as cur:
        cur.execute(sql, (bucket, s, e))
        rows = cur.fetchall()
    out = []
    for bucket_dt, val in rows:
        out.append({"bucket": bucket_dt.isoformat(), "solar": round(float(val), 2) if val is not None else None})
    return out

def _compute_stats(rows: List[Dict]) -> Dict[str, Dict]:
    vals = [float(r["solar"]) for r in rows if r.get("solar") is not None]
    if not vals:
        return {"solar": {"avg": None, "max": None, "min": None, "count": 0}}
    return {
        "solar": {
            "avg": round(sum(vals)/len(vals), 2),
            "max": round(max(vals), 2),
            "min": round(min(vals), 2),
            "count": len(vals),
        }
    }

@router.get("/query")
def solar_query(
    preset: Optional[str] = Query(default="1d", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: Optional[int] = Query(default=500, ge=50, le=5000),
):
    """
    일사량 집계 조회 API
    응답: { window, bucket_seconds, limited, series:['solar'], data[], stats{} }
    """
    s, e = resolve_window(preset, start, end)
    bucket_secs = choose_bucket_seconds(s, e, max_points or 500)
    bucket_str = seconds_to_interval_str(bucket_secs)

    data = _query_solar(bucket_str, s, e)
    stats = _compute_stats(data)

    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket_seconds": bucket_secs,
        "limited": False,
        "series": ["solar"],
        "data": data,
        "stats": stats,
    }

"""
환경(온도+습도) 통합 API
- /data/env/query : 동일 time_bucket으로 온도/습도 병합 + 통계(평균/최대/최소/개수)
- 성능 제어: max_points 기반 버킷 자동 확대
"""
from fastapi import APIRouter, Query
from typing import Optional, Dict, List
from datetime import datetime
from src.db.client import get_cursor
from src.services.modbus_service import resolve_window, choose_bucket_seconds, seconds_to_interval_str

router = APIRouter(prefix="/data/env", tags=["environment"])

# =============================================================================================================

def _query_series(table: str, key: str, bucket: str, s: datetime, e: datetime) -> List[Dict]:
    sql = f"""
        SELECT time_bucket(%s, ts) AS bucket, avg(value) AS {key}
        FROM {table}
        WHERE ts >= %s AND ts <= %s
        GROUP BY bucket
        ORDER BY bucket
    """
    with get_cursor() as cur:
        cur.execute(sql, (bucket, s, e))
        rows = cur.fetchall()
    out = []
    for bucket_dt, val in rows:
        out.append({
            "bucket": bucket_dt.isoformat(),
            key: round(float(val), 2) if val is not None else None
        })
    return out

# =============================================================================================================

def _merge_by_bucket(temp_rows: List[Dict], hum_rows: List[Dict]) -> List[Dict]:
    m: Dict[str, Dict] = {}
    for r in temp_rows:
        b = r["bucket"]
        m.setdefault(b, {"bucket": b}).update(r)
    for r in hum_rows:
        b = r["bucket"]
        m.setdefault(b, {"bucket": b}).update(r)
    return [m[k] for k in sorted(m.keys())]

# =============================================================================================================

def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats: Dict[str, Dict] = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        stats[k] = (
            {
                "avg": round(sum(vals)/len(vals), 2),
                "max": round(max(vals), 2),
                "min": round(min(vals), 2),
                "count": len(vals),
            } if vals else {"avg": None, "max": None, "min": None, "count": 0}
        )
    return stats

# =============================================================================================================

@router.get("/query")
def env_query(
    preset: Optional[str] = Query(default="1d", description="15m|1h|1d|1w|1mo"),
    start: Optional[str] = None,
    end: Optional[str] = None,
    max_points: Optional[int] = Query(default=500, ge=50, le=5000),
):
    """
    온도+습도 통합 조회 API
    응답: { window, bucket_seconds, limited, series, data[], stats{} }
    - stats.*: 평균/최대/최소/개수(기간 기준)
    """
    s, e = resolve_window(preset, start, end)
    bucket_secs = choose_bucket_seconds(s, e, max_points or 500)
    bucket_str = seconds_to_interval_str(bucket_secs)

    temp_rows = _query_series("temp_data", "temperature", bucket_str, s, e)
    hum_rows  = _query_series("humidity_data", "humidity", bucket_str, s, e)
    merged = _merge_by_bucket(temp_rows, hum_rows)
    stats = _compute_stats(merged, ["temperature", "humidity"])

    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket_seconds": bucket_secs,
        "limited": False,
        "series": ["temperature", "humidity"],
        "data": merged,
        "stats": stats,
    }
    
# =============================================================================================================

@router.get("/latest")
def env_latest():
    """
    온도/습도 최근 1건씩 반환
    """
    with get_cursor() as cur:
        cur.execute("SELECT ts, value FROM temp_data ORDER BY ts DESC LIMIT 1")
        t = cur.fetchone()
        cur.execute("SELECT ts, value FROM humidity_data ORDER BY ts DESC LIMIT 1")
        h = cur.fetchone()

    return {
        "temperature": float(t[1]) if t and t[1] is not None else None,
        "humidity": float(h[1]) if h and h[1] is not None else None,
        "ts_temperature": t[0].isoformat() if t else None,
        "ts_humidity": h[0].isoformat() if h else None,
    }
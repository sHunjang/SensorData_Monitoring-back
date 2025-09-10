"""
solar_service.py
- 일사량(solar_data) 조회 및 통계 계산 로직
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.db.client import get_cursor
from src.services.modbus_service import resolve_window

# 프리셋별 버킷 단위 매핑
BUCKET_MAP = {
    "15m": "1 minute",
    "1h": "5 minutes",
    "1d": "1 hour",
    "1w": "6 hours",
    "1mo": "1 day",
}

def query_solar_window(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str],
    max_points: Optional[int] = None,  # 프론트에서 넘어오는 값 무시
) -> Dict:
    """
    solar_data 테이블에서 지정 기간 일사량을 버킷 단위로 조회
    """
    s, e = resolve_window(preset, start, end)
    bucket_str = BUCKET_MAP.get(preset, "1 hour")

    sql = f"""
        SELECT time_bucket(%s, time_stamp) AS bucket,
               avg(value) AS solar
        FROM solar_data
        WHERE time_stamp >= %s AND time_stamp <= %s
        GROUP BY bucket
        ORDER BY bucket;
    """
    params = [bucket_str, s, e]

    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    data: List[Dict] = []
    for r in rows:
        item = {
            "bucket": r[0].isoformat(),
            "solar": round(float(r[1]), 2) if r[1] is not None else None,
        }
        data.append(item)

    stats = _compute_stats(data)

    return {
        "window": {"start": s.isoformat(), "end": e.isoformat()},
        "bucket": bucket_str,
        "series": ["solar"],
        "data": data,
        "stats": stats,
    }

def _compute_stats(rows: List[Dict]) -> Dict[str, Dict]:
    vals = [float(r["solar"]) for r in rows if r.get("solar") is not None]
    if not vals:
        return {"solar": {"avg": None, "max": None, "min": None, "count": 0}}
    return {
        "solar": {
            "avg": round(sum(vals) / len(vals), 2),
            "max": round(max(vals), 2),
            "min": round(min(vals), 2),
            "count": len(vals),
        }
    }

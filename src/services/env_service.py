"""
env_service.py
- 온습도(env_data) 조회 및 통계 계산 로직
"""

from fastapi import HTTPException
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

def query_env_window(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str],
    max_points: Optional[int] = None,  # 프론트에서 넘어오는 값 무시
) -> Dict:
    """
    env_data 테이블에서 지정 기간 온도/습도를 버킷 단위로 조회
    """
    try:
        s, e = resolve_window(preset, start, end)
        bucket_str = BUCKET_MAP.get(preset, "1 hour")

        sql = f"""
            SELECT time_bucket(%s, time_stamp) AS bucket,
                avg(temperature) AS temperature,
                avg(humidity) AS humidity
            FROM env_data
            WHERE time_stamp >= %s AND time_stamp <= %s
            GROUP BY bucket
            ORDER BY bucket;
        """
        params = [bucket_str, s, e]

        with get_cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            colnames = [d[0] for d in cur.description]

        data: List[Dict] = []
        for r in rows:
            item = {"bucket": r[0].isoformat()}
            for idx, name in enumerate(colnames[1:], start=1):
                v = r[idx]
                item[name] = round(float(v), 2) if v is not None else None
            data.append(item)

        stats = _compute_stats(data, ["temperature", "humidity"])

        return {
            "window": {"start": s.isoformat(), "end": e.isoformat()},
            "bucket": bucket_str,
            "series": ["temperature", "humidity"],
            "data": data,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="센서 연결 필요합니다.")

def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats: Dict[str, Dict] = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        if vals:
            stats[k] = {
                "avg": round(sum(vals) / len(vals), 2),
                "max": round(max(vals), 2),
                "min": round(min(vals), 2),
                "count": len(vals),
            }
        else:
            stats[k] = {"avg": None, "max": None, "min": None, "count": 0}
    return stats

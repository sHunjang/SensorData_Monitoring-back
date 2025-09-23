"""
solar_service.py
- solar_data 집계 조회
- 실패 시에도 200 + 빈 payload 반환
- bucket, window는 KST로 ISO 문자열 반환
"""
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo
from src.db.client import get_cursor
from src.services.modbus_service import resolve_window  # UTC 기반 윈도우 해석

BUCKET_MAP = {
    "15m": "1 minute",
    "1h":  "5 minutes",
    "1d":  "1 hour",
    "1w":  "6 hours",
    "1mo": "1 day",
}

def query_solar_window(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str],
    max_points: Optional[int] = None,
) -> Dict:
    try:
        s_utc, e_utc = resolve_window(preset, start, end)
        bucket_str = BUCKET_MAP.get(preset, "1 hour")

        sql = f"""
            SELECT time_bucket(%s, time_stamp) AT TIME ZONE 'Asia/Seoul' AS bucket_kst,
                   avg(solar) AS solar
            FROM solar_data
            WHERE time_stamp >= %s AND time_stamp <= %s
            GROUP BY bucket_kst
            ORDER BY bucket_kst;
        """
        params = [bucket_str, s_utc, e_utc]

        with get_cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        data: List[Dict] = []
        for r in rows:
            data.append({
                "bucket": r[0].isoformat(),                                 # KST ISO
                "solar":  round(float(r[1]), 2) if r[1] is not None else None,
            })

        stats = _compute_stats(data)

        kst = ZoneInfo("Asia/Seoul")
        return {
            "window": {"start": s_utc.astimezone(kst).isoformat(), "end": e_utc.astimezone(kst).isoformat()},
            "bucket": bucket_str,
            "series": ["solar"],
            "data": data,
            "stats": stats,
        }
    except Exception:
        # 503 대신 빈 payload로 200 응답을 유도
        return {
            "window": None,
            "bucket": BUCKET_MAP.get(preset, "1 hour"),
            "series": ["solar"],
            "data": [],
            "stats": {"solar": {"avg": None, "max": None, "min": None, "count": 0}},
            "error": "solar query failed",
        }

def _compute_stats(rows: List[Dict]) -> Dict[str, Dict]:
    vals = [float(r["solar"]) for r in rows if r.get("solar") is not None]
    return {
        "solar": {
            "avg": round(sum(vals) / len(vals), 2) if vals else None,
            "max": round(max(vals), 2) if vals else None,
            "min": round(min(vals), 2) if vals else None,
            "count": len(vals),
        }
    }

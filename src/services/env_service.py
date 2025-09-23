"""
env_service.py
- env_data 시간창 집계 조회
- 예외 시에도 200 + 빈 payload 반환하도록 라우터에서 그대로 전달
- 버킷과 window는 KST ISO 문자열로 반환
"""
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo
from src.db.client import get_cursor
from src.services.modbus_service import resolve_window  # UTC 윈도우 해석(공용)

# 집계 해상도 매핑
BUCKET_MAP = {
    "15m": "1 minute",
    "1h":  "5 minutes",
    "1d":  "1 hour",
    "1w":  "6 hours",
    "1mo": "1 day",
}

def _compute_stats(rows: List[Dict], keys: List[str]) -> Dict[str, Dict]:
    stats: Dict[str, Dict] = {}
    for k in keys:
        vals = [float(r[k]) for r in rows if r.get(k) is not None]
        stats[k] = {
            "avg": round(sum(vals) / len(vals), 2),
            "max": round(max(vals), 2),
            "min": round(min(vals), 2),
            "count": len(vals),
        } if vals else {"avg": None, "max": None, "min": None, "count": 0}
    return stats

def query_env_window(
    preset: Optional[str],
    start: Optional[str],
    end: Optional[str],
    max_points: Optional[int] = None,
) -> Dict:
    try:
        s_utc, e_utc = resolve_window(preset, start, end)  # 내부 UTC
        bucket_str = BUCKET_MAP.get(preset, "1 hour")

        sql = f"""
            SELECT time_bucket(%s, time_stamp) AT TIME ZONE 'Asia/Seoul' AS bucket_kst,
                   avg(temperature) AS temperature,
                   avg(humidity)    AS humidity
            FROM env_data
            WHERE time_stamp >= %s AND time_stamp <= %s
            GROUP BY bucket_kst
            ORDER BY bucket_kst;
        """
        params = [bucket_str, s_utc, e_utc]

        with get_cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            colnames = [d[0] for d in cur.description]

        data: List[Dict] = []
        for r in rows:
            item = {"bucket": r[0].isoformat()}  # KST naive → ISO
            for idx, name in enumerate(colnames[1:], start=1):
                v = r[idx]
                item[name] = round(float(v), 2) if v is not None else None
            data.append(item)

        stats = _compute_stats(data, ["temperature", "humidity"])
        kst = ZoneInfo("Asia/Seoul")
        return {
            "window": {"start": s_utc.astimezone(kst).isoformat(), "end": e_utc.astimezone(kst).isoformat()},
            "bucket": bucket_str,
            "series": ["temperature", "humidity"],
            "data": data,
            "stats": stats,
        }
    except Exception:
        # 503 대신 빈 payload
        return {
            "window": None,
            "bucket": BUCKET_MAP.get(preset, "1 hour"),
            "series": ["temperature", "humidity"],
            "data": [],
            "stats": {
                "temperature": {"avg": None, "max": None, "min": None, "count": 0},
                "humidity":    {"avg": None, "max": None, "min": None, "count": 0},
            },
            "error": "env query failed",
        }

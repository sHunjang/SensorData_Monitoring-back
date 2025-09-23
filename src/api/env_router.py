"""
/data/env/query
- 목적: 온습도 시계열 조회 (preset or start/end)
- 입력:
    - preset: "15m","1h","1d","1w","1mo" 등 (옵션)
    - start, end: ISO 문자열 (옵션)
    - max_points: 결과 제한
- 반환: make_query_response 형식의 JSON
    - data: [{ bucket: ISOstring, device_id, temperature, humidity }, ...]
- 구현 노트:
    - DB에 저장된 time_stamp 컬럼은 TIMESTAMPTZ. SELECT 시 UTC로 정규화 후 iso화.
    - 프론트는 bucket으로 X축 사용. bucket 값은 tz-aware ISO string.
"""
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/env", tags=["env"])

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
    """
    preset이 주어지면 현재 UTC 기준으로 window 계산.
    반환값: (start_datetime_utc, end_datetime_utc, bucket_label)
    bucket_label은 단순 설명용(프론트에서 적절히 무시/사용).
    """
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m": return now - timedelta(minutes=15), now, "1 minute"
        if preset == "1h": return now - timedelta(hours=1), now, "5 minutes"
        if preset == "1d": return now - timedelta(days=1), now, "1 hour"
        if preset == "1w": return now - timedelta(weeks=1), now, "6 hours"
        if preset == "1mo": return now - timedelta(days=30), now, "1 day"
    # start/end 명시 또는 기본(최근 1시간)
    s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
    e = datetime.fromisoformat(end) if end else now
    if s.tzinfo is None: s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None: e = e.replace(tzinfo=timezone.utc)
    return s, e, "1 hour"

@router.get("/query")
def query_env(preset: Optional[str] = Query(None), start: Optional[str] = Query(None), end: Optional[str] = Query(None), max_points: int = Query(500)):
    s, e, bucket = resolve_window(preset, start, end)
    try:
        with get_cursor() as cur:
            # time_stamp AT TIME ZONE 'UTC' 로 정규화하여 DB로부터 UTC naive 아닌 tz-aware로 처리
            cur.execute("""
                SELECT time_stamp, device_id, temperature, humidity
                FROM env_data
                WHERE time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC
                LIMIT %s
            """, (s, e, max_points))
            rows = []
            for ts, device_id, temperature, humidity in cur.fetchall():
                rows.append({
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": device_id,
                    "temperature": temperature,
                    "humidity": humidity
                })

        # 간단 통계 (프론트에서 추가 집계 가능)
        temps = [r["temperature"] for r in rows if r["temperature"] is not None]
        hums = [r["humidity"] for r in rows if r["humidity"] is not None]
        stats = {
            "temperature": {"avg": sum(temps)/len(temps) if temps else None, "max": max(temps) if temps else None, "min": min(temps) if temps else None, "count": len(temps)},
            "humidity": {"avg": sum(hums)/len(hums) if hums else None, "max": max(hums) if hums else None, "min": min(hums) if hums else None, "count": len(hums)},
        }

        return make_query_response(s, e, bucket, ["temperature", "humidity"], rows, stats)
    except Exception as ex:
        # 에러도 표준 포맷으로 반환
        return make_query_response(None, None, bucket, ["temperature", "humidity"], [], {}, error=str(ex))

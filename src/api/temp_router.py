"""
온도 데이터 API 라우터
- /data/temp : 집계 데이터 조회
"""
from fastapi import APIRouter, Query
from typing import Optional
from src.db.client import get_cursor

router = APIRouter()

@router.get("/temp")
def get_temp(
    interval: str = Query("1h", description="time_bucket 간격 (예: '15 minutes', '1h', '1d')"),
    start: Optional[str] = Query(None, description="조회 시작 시각 (YYYY-MM-DD HH:MM:SS)"),
    end: Optional[str] = Query(None, description="조회 종료 시각 (YYYY-MM-DD HH:MM:SS)")
):
    """
    온도 데이터 집계 조회
    - interval 단위로 평균값 반환
    - start, end가 없으면 전체 기간
    """
    sql = f"""
        SELECT time_bucket(%s, ts) AS bucket, avg(value)
        FROM temp_data
        WHERE (%s IS NULL OR ts >= %s)
          AND (%s IS NULL OR ts <= %s)
        GROUP BY bucket
        ORDER BY bucket;
    """
    with get_cursor() as cur:
        cur.execute(sql, (interval, start, start, end, end))
        rows = cur.fetchall()
    return [{"bucket": r[0], "temperature": round(r[1], 2) if r[1] else None} for r in rows]

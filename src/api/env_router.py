# src/api/env_router.py
"""
/data/env/query
- 목적: 온습도 시계열 조회 (preset or start/end)
- 입력:
    - preset: "15m","1h","1d","1w","1mo" 등 (옵션)
    - start, end: ISO 문자열 (옵션)
    - max_points: 결과 제한 (기본 500)
    - device_id: 선택적 정수. 지정하면 해당 장치 데이터만 반환.
- 반환: make_query_response 형식의 JSON
    - data: [{ bucket: ISOstring, device_id, temperature, humidity }, ...]
- 구현 노트:
    - DB의 time_stamp는 TIMESTAMPTZ 타입으로 가정.
    - SELECT 시 time_stamp는 그대로 읽어 파이썬에서 KST ISO로 변환(iso_kst).
    - device_id 파라미터가 있으면 WHERE 절에 추가.
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/env", tags=["env"])

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]):
    """
    요청된 시간창(preset 또는 start/end)을 UTC 기준 datetime으로 반환.
    반환: (start_datetime_utc, end_datetime_utc, bucket_label)
    - preset 우선. start/end가 명시되면 그 값 사용.
    - 반환되는 datetimes는 tz-aware(UTC).
    """
    now = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m":
            return now - timedelta(minutes=15), now, "1 minute"
        if preset == "1h":
            return now - timedelta(hours=1), now, "5 minutes"
        if preset == "1d":
            return now - timedelta(days=1), now, "1 hour"
        if preset == "1w":
            return now - timedelta(weeks=1), now, "6 hours"
        if preset == "1mo":
            return now - timedelta(days=30), now, "1 day"
    # start/end가 주어졌거나 기본값(최근 1시간)
    s = datetime.fromisoformat(start) if start else now - timedelta(hours=1)
    e = datetime.fromisoformat(end) if end else now
    # fromisoformat이 naive datetime을 반환할 수 있으므로 UTC로 지정
    if s.tzinfo is None:
        s = s.replace(tzinfo=timezone.utc)
    if e.tzinfo is None:
        e = e.replace(tzinfo=timezone.utc)
    return s, e, "1 hour"

@router.get("/query")
def query_env(
    preset: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    max_points: int = Query(500),
    device_id: Optional[int] = Query(None),
):
    """
    엔드포인트:
      /data/env/query?preset=15m&max_points=200
      /data/env/query?start=2025-09-23T00:00:00Z&end=2025-09-23T01:00:00Z&device_id=21
    동작:
      - window 계산
      - SQL을 동적으로 구성하여 (device_id 조건 포함) 조회
      - 각 row의 time_stamp를 iso_kst로 변환하여 'bucket'으로 반환
      - 간단 통계 생성 후 표준 응답 반환
    """
    s, e, bucket = resolve_window(preset, start, end)

    try:
        with get_cursor() as cur:
            # 기본 SQL 및 파라미터 리스트
            sql = """
                SELECT time_stamp, device_id, temperature, humidity
                FROM env_data
                WHERE time_stamp >= %s AND time_stamp <= %s
            """
            params: List[Any] = [s, e]

            # device_id가 명시되면 WHERE 절에 추가
            if device_id is not None:
                sql += " AND device_id = %s"
                params.append(device_id)

            # 정렬 및 제한 추가
            sql += " ORDER BY time_stamp DESC LIMIT %s"
            params.append(max_points)

            cur.execute(sql, tuple(params))

            rows: List[Dict[str, Any]] = []
            for ts, dev_id, temperature, humidity in cur.fetchall():
                rows.append({
                    # iso_kst converts timestamptz -> KST tz-aware ISO string
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev_id,
                    # DB 컬럼명(temperature, humidity)을 API 필드명(temperature, humidity)로 매핑
                    "temperature": temperature,
                    "humidity": humidity
                })

        # 간단 통계(프론트에서 더 자세히 계산할 수도 있음)
        temps = [r["temperature"] for r in rows if r["temperature"] is not None]
        hums = [r["humidity"] for r in rows if r["humidity"] is not None]
        stats = {
            "temperature": {
                "avg": sum(temps) / len(temps) if temps else None,
                "max": max(temps) if temps else None,
                "min": min(temps) if temps else None,
                "count": len(temps)
            },
            "humidity": {
                "avg": sum(hums) / len(hums) if hums else None,
                "max": max(hums) if hums else None,
                "min": min(hums) if hums else None,
                "count": len(hums)
            },
        }

        return make_query_response(s, e, bucket, ["temperature", "humidity"], rows, stats)
    except Exception as ex:
        # 에러도 표준 응답으로 감싸서 반환
        return make_query_response(None, None, bucket, ["temperature", "humidity"], [], {}, error=str(ex))

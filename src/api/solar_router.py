# src/api/solar_router.py
"""
/data/solar/query

기능 요약:
- 일사량 시계열 조회 엔드포인트
- 입력:
    - preset: "15m","1h","1d","1w","1mo" 등 (옵션)
    - start, end: ISO 문자열 (옵션). tz가 없는 naive 문자열은 KST(Asia/Seoul)로 간주.
    - max_points: 결과 제한 (기본 500)
    - device_id: 선택적 정수. 지정하면 해당 장치 데이터만 반환.
- 반환: make_query_response 형식의 JSON
    - data: [{ bucket: ISOstring, device_id, solar }, ...]
- 구현 노트:
    - DB의 time_stamp는 TIMESTAMPTZ 타입으로 가정.
    - 클라이언트가 naive ISO(KST 의도)를 보낼 수 있으므로 naive는 KST로 해석한 뒤 UTC로 변환해 DB를 조회함.
    - API는 bucket으로 KST tz-aware ISO 문자열을 반환함 (프론트에서 바로 파싱 가능).
"""

from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo

from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/solar", tags=["solar"])

KST = ZoneInfo("Asia/Seoul")


def parse_iso_to_utc(iso_str: str) -> datetime:
    """
    - offset-aware ISO -> UTC datetime
    - tz-naive ISO   -> assume KST, then convert to UTC
    """
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        # naive => treat as KST then convert to UTC
        dt = dt.replace(tzinfo=KST).astimezone(timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]) -> Tuple[datetime, datetime, str]:
    """
    요청된 시간창을 UTC tz-aware datetime으로 반환.
    - preset 우선. start/end가 명시되면 그 값을 사용.
    - 반환값: (start_utc, end_utc, bucket_label)
    """
    now_utc = datetime.now(timezone.utc)
    if preset and not (start or end):
        if preset == "15m":
            return now_utc - timedelta(minutes=15), now_utc, "1 minute"
        if preset == "1h":
            return now_utc - timedelta(hours=1), now_utc, "5 minutes"
        if preset == "1d":
            return now_utc - timedelta(days=1), now_utc, "1 hour"
        if preset == "1w":
            return now_utc - timedelta(weeks=1), now_utc, "6 hours"
        if preset == "1mo":
            return now_utc - timedelta(days=30), now_utc, "1 day"

    # start/end 주어짐 또는 기본(최근 1시간)
    if start:
        s_utc = parse_iso_to_utc(start)
    else:
        s_utc = now_utc - timedelta(hours=1)

    if end:
        e_utc = parse_iso_to_utc(end)
    else:
        e_utc = now_utc

    return s_utc, e_utc, "1 hour"


@router.get("/query")
def query_solar(
    preset: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    max_points: int = Query(500),
    device_id: Optional[int] = Query(None),
):
    """
    엔드포인트 예시:
      /data/solar/query?preset=15m&max_points=200
      /data/solar/query?start=2025-09-23T00:00:00&end=2025-09-23T01:00:00&device_id=21

    동작:
      - window 계산 (naive ISO -> KST -> UTC 변환 처리 포함)
      - device_id가 주어지면 WHERE에 추가
      - time_stamp 오름차순(ASC)으로 정렬하여 프론트 차트에 적합한 순서를 보장
      - 각 row의 time_stamp는 iso_kst로 변환해 KST tz-aware ISO 문자열로 반환
      - 간단 통계(solar) 계산
    """
    s, e, bucket = resolve_window(preset, start, end)

    try:
        with get_cursor() as cur:
            # 동적 SQL 빌드 (파라미터화)
            sql = """
                SELECT time_stamp, device_id, solar
                FROM solar_data
                WHERE time_stamp >= %s AND time_stamp <= %s
            """
            params: List[Any] = [s, e]

            if device_id is not None:
                sql += " AND device_id = %s"
                params.append(device_id)

            # ASC 정렬로 반환(차트에서 시간순으로 렌더링하기 위함)
            sql += " ORDER BY time_stamp DESC LIMIT %s"
            params.append(max_points)

            cur.execute(sql, tuple(params))
            fetched = cur.fetchall()

            rows: List[Dict[str, Any]] = []
            for ts, dev_id, solar_val in fetched:
                rows.append({
                    # iso_kst converts timestamptz -> KST tz-aware ISO string
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev_id,
                    # DB 컬럼명(solar) -> API 필드명(solar)
                    "solar": float(solar_val) if solar_val is not None else None,
                })

        # solar 통계 계산
        sols = [r["solar"] for r in rows if r["solar"] is not None]
        stats = {
            "solar": {
                "avg": round(sum(sols) / len(sols), 2) if sols else None,
                "max": max(sols) if sols else None,
                "min": min(sols) if sols else None,
                "count": len(sols),
            }
        }

        return make_query_response(s, e, bucket, ["solar"], rows, stats)
    except Exception as ex:
        # 에러도 표준 응답으로 감싸서 반환 (프론트가 에러 메시지를 보여줄 수 있음)
        return make_query_response(None, None, bucket, ["solar"], [], {}, error=str(ex))

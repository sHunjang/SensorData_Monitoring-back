# src/api/solar_router.py
"""
/data/solar/query
- 안전한 입력 파싱
- 모든 예외를 잡아 표준 응답 형식으로 반환 (HTTP 200 내부에 error 필드)
- device_id 파라미터는 optional
"""
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import logging

from src.db.client import get_cursor
from src.api._utils import make_query_response, iso_kst

router = APIRouter(prefix="/data/solar", tags=["solar"])
KST = ZoneInfo("Asia/Seoul")
log = logging.getLogger("solar_router")

def parse_iso_to_utc(iso_str: str) -> datetime:
    if iso_str is None:
        raise ValueError("iso string is None")
    s = iso_str.strip()
    # trailing Z -> +00:00
    if s.endswith("Z"):
        s2 = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s2)
        return dt.astimezone(timezone.utc)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # treat naive as KST per project convention
        return dt.replace(tzinfo=KST).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]) -> Tuple[datetime, datetime, str]:
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

    # parse start/end safely (may raise ValueError)
    s = parse_iso_to_utc(start) if start else now_utc - timedelta(hours=1)
    e = parse_iso_to_utc(end) if end else now_utc
    return s, e, "1 hour"

@router.get("/query")
def query_solar(
    preset: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    max_points: int = Query(500),
    device_id: Optional[int] = Query(None),
):
    """
    안전한 /data/solar/query 구현.
    모든 오류는 make_query_response(..., error=...)로 감싸서 반환합니다.
    """
    # prepare default bucket for error responses
    bucket_label = "1 hour"
    try:
        # resolve_window may raise ValueError on bad ISO strings
        s, e, bucket_label = resolve_window(preset, start, end)
    except Exception as ex:
        log.exception("window parse failed")
        return make_query_response(None, None, bucket_label, ["solar"], [], {}, error=f"invalid time window: {ex}")

    try:
        with get_cursor() as cur:
            sql = """
                SELECT time_stamp, device_id, solar
                FROM solar_data
                WHERE time_stamp >= %s AND time_stamp <= %s
            """
            params: List[Any] = [s, e]
            if device_id is not None:
                sql += " AND device_id = %s"
                params.append(device_id)
            sql += " ORDER BY time_stamp DESC LIMIT %s"
            params.append(max_points)

            cur.execute(sql, tuple(params))
            fetched = cur.fetchall()

            rows: List[Dict[str, Any]] = []
            for ts, dev_id, solar_val in fetched:
                rows.append({
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev_id,
                    "solar": float(solar_val) if solar_val is not None else None,
                })

        sols = [r["solar"] for r in rows if r["solar"] is not None]
        stats = {
            "solar": {
                "avg": round(sum(sols) / len(sols), 2) if sols else None,
                "max": max(sols) if sols else None,
                "min": min(sols) if sols else None,
                "count": len(sols),
            }
        }

        return make_query_response(s, e, bucket_label, ["solar"], rows, stats)
    except Exception as ex:
        log.exception("query_solar DB/processing failed")
        return make_query_response(None, None, bucket_label, ["solar"], [], {}, error=str(ex))

# src/api/_utils.py
"""
공통 유틸리티: 시간·응답 포맷 표준화
- 순수 함수만 포함. 다른 내부 모듈을 import 하지 않음(순환 import 방지).
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

def iso_kst(dt: Optional[datetime]) -> Optional[str]:
    """
    datetime -> KST tz-aware ISO 문자열.
    - None 입력 시 None 반환.
    - 입력이 naive이면 UTC로 간주 후 KST로 변환.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).isoformat()

def make_query_response(window_start: Optional[datetime], window_end: Optional[datetime],
                        bucket: str, series: List[str],
                        rows: List[Dict[str, Any]],
                        stats: Optional[Dict[str, Any]] = None,
                        error: Optional[str] = None) -> Dict[str, Any]:
    """
    표준화된 시계열 쿼리 응답 구조 생성.
    반환 예:
    {
      "window": {"start": "...+09:00", "end": "...+09:00"},
      "bucket": "1h",
      "series": ["temperature","humidity"],
      "data": [...],
      "stats": {...},
      "error": null
    }
    """
    return {
        "window": {"start": iso_kst(window_start), "end": iso_kst(window_end)} if window_start and window_end else None,
        "bucket": bucket,
        "series": series,
        "data": rows,
        "stats": stats or {},
        "error": error,
    }

def make_realtime_response(device_id: int,
                           time_stamp: Optional[datetime],
                           metrics: Dict[str, Any],
                           raw: Any = None) -> Dict[str, Any]:
    """
    표준화된 realtime snapshot 응답 생성.
    반환 예:
      {"device_id": 11, "time_stamp": "2025-09-23T13:00:00+09:00", "metrics": {...}, "raw": ...}
    """
    return {
        "device_id": int(device_id),
        "time_stamp": iso_kst(time_stamp),
        "metrics": metrics,
        "raw": raw,
    }

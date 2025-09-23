"""
공통 API 유틸리티
- make_query_response: 쿼리형(히스토리) 응답 표준화
- make_realtime_response: 실시간 응답 표준화
- iso_kst: datetime -> KST tz-aware ISO 문자열 변환 헬퍼
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def iso_kst(dt: Optional[datetime]) -> Optional[str]:
    """
    datetime -> KST tz-aware ISO string
    - 입력이 None이면 None 반환
    - tz-aware이면 KST로 변환해 isoformat() 반환
    - tz-naive이면 KST로 간주(=KST 적용) 후 isoformat() 반환
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # naive timestamp: assume it's already KST-local time (original DB usage may vary)
        return dt.replace(tzinfo=KST).isoformat()
    return dt.astimezone(KST).isoformat()


def make_query_response(window_start: Optional[datetime],
                        window_end: Optional[datetime],
                        bucket_label: str,
                        series: List[str],
                        data: List[Dict[str, Any]],
                        stats: Optional[Dict[str, Any]] = None,
                        error: Optional[str] = None) -> Dict[str, Any]:
    """
    통일된 쿼리 응답 포맷.
    - window_start/window_end: datetime (UTC or tz-aware). 반환은 iso_kst로 KST 표기.
    - bucket_label: "1 minute", "5 minutes" 등 (프론트의 버킷 해석 힌트)
    - series: 시리즈 키 목록
    - data: 리스트(각 항목은 'bucket' 포함). 'bucket'이 이미 tz-aware ISO이면 그대로 사용 가능.
    - stats: 요약 통계
    - error: 에러 메시지(있으면 비어있는 data로 응답)
    """
    return {
        "window": {
            "start": iso_kst(window_start) if window_start else None,
            "end": iso_kst(window_end) if window_end else None
        },
        "bucket": bucket_label,
        "series": series,
        "data": data,
        "stats": stats or {},
        "error": error
    }


def make_realtime_response(device_id: int,
                           time_stamp: Optional[Any],
                           metrics: Dict[str, Any],
                           raw: Optional[Any] = None) -> Dict[str, Any]:
    """
    실시간 응답 포맷.
    - time_stamp는 datetime 또는 tz-aware 문자열 가능. 여기서는 iso_kst을 사용하려 시도함.
    - metrics: p_kw, e_kwh 등 메트릭 딕셔너리
    - raw: 원본 DB/서비스 레코드(디버깅용)
    """
    ts_iso = None
    try:
        if time_stamp is None:
            ts_iso = None
        elif isinstance(time_stamp, str):
            # 이미 문자열일 경우 그대로 돌려주되, 클라이언트에서 parse 가능해야 함
            ts_iso = time_stamp
        else:
            ts_iso = iso_kst(time_stamp)
    except Exception:
        ts_iso = None

    return {
        "device_id": device_id,
        "time_stamp": ts_iso,
        "metrics": metrics,
        "raw": raw
    }

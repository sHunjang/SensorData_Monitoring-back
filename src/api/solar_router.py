# src/api/solar_router.py
"""
일사량 센서 API 라우터 - irradiance 컬럼 통일

제공 엔드포인트:
- GET /data/solar/query: 일사량 시계열 데이터 조회

응답 데이터:
- irradiance: 일사량 (W/m²) - 통일된 필드명
- device_id: 센서 장치 ID
- bucket: KST 타임스탬프
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
    """ISO 문자열을 UTC datetime으로 변환"""
    if iso_str is None:
        raise ValueError("iso string is None")
    
    s = iso_str.strip()
    # Z 접미사 처리
    if s.endswith("Z"):
        s2 = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s2)
        return dt.astimezone(timezone.utc)
    
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # naive timestamp를 KST로 간주 후 UTC 변환
        return dt.replace(tzinfo=KST).astimezone(timezone.utc)
    
    return dt.astimezone(timezone.utc)

def resolve_window(preset: Optional[str], start: Optional[str], end: Optional[str]) -> Tuple[datetime, datetime, str]:
    """시간 범위 해석 및 버킷 라벨 결정"""
    now_utc = datetime.now(timezone.utc)
    
    # preset 기반 시간 범위 설정
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
    
    # start/end 파라미터 파싱
    s = parse_iso_to_utc(start) if start else now_utc - timedelta(hours=1)
    e = parse_iso_to_utc(end) if end else now_utc
    
    return s, e, "1 hour"

@router.get("/query")
def query_solar(
    preset: Optional[str] = Query(None, description="시간 범위 프리셋 (15m, 1h, 1d, 1w, 1mo)"),
    start: Optional[str] = Query(None, description="시작 시간 (ISO 문자열)"),
    end: Optional[str] = Query(None, description="종료 시간 (ISO 문자열)"),
    max_points: int = Query(500, description="최대 데이터 포인트 수"),
    device_id: Optional[int] = Query(None, description="특정 센서 장치 ID"),
):
    bucket_label = "1 hour"
    
    try:
        s, e, bucket_label = resolve_window(preset, start, end)
    except Exception as ex:
        log.exception("window parse failed")
        return make_query_response(
            None, None, bucket_label, ["solar"], [], {}, 
            error=f"invalid time window: {ex}"
        )

    try:
        with get_cursor() as cur:
            # DB에서는 irradiance 컬럼을 읽되
            sql = """
            SELECT time_stamp, device_id, irradiance
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
            
            # ✅ 프론트엔드 호환성을 위해 solar 필드로 응답
            rows: List[Dict[str, Any]] = []
            for ts, dev_id, irradiance_val in fetched:
                rows.append({
                    "bucket": iso_kst(ts) if ts else None,
                    "device_id": dev_id,
                    "solar": float(irradiance_val) if irradiance_val is not None else None,  # ✅ solar로 응답
                })
            
            # 통계도 solar 기준으로 계산
            solar_values = [r["solar"] for r in rows if r["solar"] is not None]
            stats = {
                "solar": {
                    "avg": round(sum(solar_values) / len(solar_values), 2) if solar_values else None,
                    "max": round(max(solar_values), 2) if solar_values else None,
                    "min": round(min(solar_values), 2) if solar_values else None,
                    "count": len(solar_values),
                }
            }
            
            return make_query_response(s, e, bucket_label, ["solar"], rows, stats)
            
    except Exception as ex:
        log.exception("query_solar DB/processing failed")
        return make_query_response(
            None, None, bucket_label, ["solar"], [], {}, 
            error=str(ex)
        )

@router.get("/realtime") 
def get_solar_realtime(device_id: Optional[int] = Query(None)):
    try:
        with get_cursor() as cur:
            sql = """
            SELECT DISTINCT ON (device_id) device_id, time_stamp, irradiance
            FROM solar_data
            """
            params = []
            
            if device_id is not None:
                sql += " WHERE device_id = %s"
                params.append(device_id)
                
            sql += " ORDER BY device_id, time_stamp DESC"
            
            cur.execute(sql, tuple(params))
            fetched = cur.fetchall()
            
            # ✅ 프론트엔드 호환성을 위해 solar 필드로 응답
            data = {}
            latest_ts = None
            
            for dev_id, ts, irradiance_val in fetched:
                data[str(dev_id)] = {
                    "solar": float(irradiance_val) if irradiance_val is not None else None  # ✅ solar로 응답
                }
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts
            
            return {
                "timestamp": iso_kst(latest_ts) if latest_ts else None,
                "data": data
            }
            
    except Exception as ex:
        log.exception("get_solar_realtime failed")
        return {
            "timestamp": None,
            "data": {},
            "error": str(ex)
        }
"""
Solar 데이터 API Router - device_id 필터링 지원

변경사항:
- WHERE device_id=%s 조건 추가 (device_id 컬럼 사용)
- Solar는 단일 테이블 유지 (solar_data)
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from src.db.client import get_cursor
import logging


router = APIRouter(prefix="/data/solar", tags=["solar"])
logger = logging.getLogger(__name__)


ALLOWED_PRESETS = {"10s", "1m", "15m", "1h", "1d", "1w", "1mo"}


@router.get("/query")
async def get_solar_data(
    deviceid: int = Query(31, description="Device ID (31)"),
    preset: str = Query(..., description="Time preset: 10s,1m,15m,1h,1d,1w,1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None), 
    end: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Solar Device 일사량 데이터 조회
    
    단일 테이블(solar_data)에서 device_id 필터링으로 조회합니다.
    - device_id = 31 (태양광 센서)
    """
    if preset not in ALLOWED_PRESETS:
        raise HTTPException(status_code=400, detail=f"Invalid preset: {preset}")

    # Device ID 검증
    if deviceid != 31:
        raise HTTPException(status_code=400, detail=f"Invalid device ID: {deviceid}. Must be 31")

    try:
        if start and end:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)
            if preset == '10s':
                start_time = end_time - timedelta(seconds=10)
            elif preset == '1m':
                start_time = end_time - timedelta(minutes=1)
            elif preset == '15m':
                start_time = end_time - timedelta(minutes=15)
            elif preset == '1h':
                start_time = end_time - timedelta(hours=1)
            elif preset == '1d':
                start_time = end_time - timedelta(days=1)
            elif preset == '1w':
                start_time = end_time - timedelta(days=7)
            elif preset == '1mo':
                start_time = end_time - timedelta(days=30)

        with get_cursor() as cursor:
            if preset in ['1w', '1mo']:
                # 일 단위 집계
                query = """
                SELECT 
                    date_trunc('day', time_stamp) AS bucket, 
                    AVG(irradiance) AS irradiance
                FROM solar_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 
                ORDER BY 1 ASC 
                LIMIT %s
                """
            elif preset in ['15m', '1h']:
                # 분 단위 집계
                query = """
                SELECT 
                    date_trunc('minute', time_stamp) AS bucket, 
                    AVG(irradiance) AS irradiance
                FROM solar_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 
                ORDER BY 1 ASC 
                LIMIT %s
                """
            elif preset == '10s':
                # 10초 단위 집계
                query = """
                SELECT 
                    to_timestamp(floor(EXTRACT(EPOCH FROM time_stamp)/10)*10) AT TIME ZONE 'UTC' AS bucket,
                    AVG(irradiance) AS irradiance
                FROM solar_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                GROUP BY 1 
                ORDER BY 1 ASC 
                LIMIT %s
                """
            else:  # '1m' or '1d' - 원본 레코드
                query = """
                SELECT 
                    time_stamp AS bucket, 
                    irradiance
                FROM solar_data
                WHERE device_id=%s AND time_stamp >= %s AND time_stamp <= %s
                ORDER BY time_stamp ASC 
                LIMIT %s
                """

            cursor.execute(query, (deviceid, start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]

            data = []
            for r in rows:
                rd = dict(zip(cols, r))
                if rd.get('bucket'):
                    try:
                        rd['bucket'] = rd['bucket'].isoformat()
                    except Exception:
                        pass
                data.append(rd)

        logger.info(f"Solar 조회: device={deviceid}, preset={preset}, count={len(data)}")
        return {
            "data": data, 
            "count": len(data), 
            "preset": preset, 
            "device_id": deviceid,
            "time_range": {"start": start_time.isoformat(), "end": end_time.isoformat()}
        }

    except Exception as e:
        logger.error(f"Solar 에러 (device={deviceid}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

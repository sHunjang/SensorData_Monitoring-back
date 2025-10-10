"""
Environment 데이터 API Router - 신규 아키텍처 (2025-10-10)

변경사항:
- RAW 테이블 제거: 1m 테이블부터 시작
- bootstrap.py와 칼럼명 100% 동기화
- 온도/습도 데이터 (device_id: 21-23)

작성일: 2025-10-10
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from src.db.client import get_cursor
from src.config.settings import settings
import logging

router = APIRouter(prefix="/data/env", tags=["environment"])
logger = logging.getLogger(__name__)

ALLOWED_PRESETS = {"1m", "15m", "1h", "1d", "1w", "1mo"}


def select_table_by_preset(device_id: int, preset: str) -> str:
    """
    Preset에 따라 적절한 테이블 선택
    
    신규 구조:
    - 1m → env_data_{device_id}_1m
    - 15m → env_data_{device_id}_15m
    - 1h → env_data_{device_id}_1h
    - 1d, 1w, 1mo → env_data_{device_id}_1d
    """
    if preset == '1m':
        return f"env_data_{device_id}_1m"
    elif preset == '15m':
        return f"env_data_{device_id}_15m"
    elif preset == '1h':
        return f"env_data_{device_id}_1h"
    elif preset in ['1d', '1w', '1mo']:
        return f"env_data_{device_id}_1d"
    else:
        return f"env_data_{device_id}_1m"


@router.get("/query")
async def get_env_data(
    deviceid: int = Query(..., description="Device ID (21-23)"),
    preset: str = Query(..., description="Time preset: 1m,15m,1h,1d,1w,1mo"),
    maxpoints: int = Query(100, description="Maximum data points"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Environment Device별 온습도 데이터 조회
    
    신규 계층 구조:
    - 1m → 1분 집계 테이블
    - 15m → 15분 집계 테이블
    - 1h → 1시간 집계 테이블
    - 1d, 1w, 1mo → 1일 집계 테이블
    """
    if preset not in ALLOWED_PRESETS:
        raise HTTPException(status_code=400, detail=f"Invalid preset: {preset}")
    
    # Device ID 검증 (21-23)
    if deviceid not in settings.ENV_DEVICE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid device ID: {deviceid}")
    
    # 테이블 선택
    table_name = select_table_by_preset(deviceid, preset)
    
    try:
        # 시간 범위 계산
        if start and end:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:
            end_time = datetime.now(timezone.utc)
            if preset == '1m':
                start_time = end_time - timedelta(hours=1)
            elif preset == '15m':
                start_time = end_time - timedelta(hours=6)
            elif preset == '1h':
                start_time = end_time - timedelta(days=1)
            elif preset == '1d':
                start_time = end_time - timedelta(days=7)
            elif preset == '1w':
                start_time = end_time - timedelta(days=30)
            elif preset == '1mo':
                start_time = end_time - timedelta(days=180)
        
        # SQL 쿼리
        query = f"""
            SELECT 
                timestamp,
                device_id,
                avg_temperature_c,
                max_temperature_c,
                min_temperature_c,
                avg_humidity_percent,
                max_humidity_percent,
                min_humidity_percent,
                count
            FROM {table_name}
            WHERE timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        
        with get_cursor() as cursor:
            cursor.execute(query, (start_time, end_time, maxpoints))
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            
            # 결과 포맷팅
            data = []
            for r in rows:
                rd = dict(zip(cols, r))
                
                # 시간 ISO 포맷 변환
                if rd.get('timestamp'):
                    try:
                        rd['timestamp'] = rd['timestamp'].isoformat()
                    except Exception:
                        pass
                
                data.append(rd)
            
            logger.info(
                f"Env 조회: device={deviceid}, preset={preset}, "
                f"table={table_name}, count={len(data)}"
            )
            
            return {
                "data": data,
                "count": len(data),
                "preset": preset,
                "device_id": deviceid,
                "table_used": table_name,
                "time_range": {
                    "start": start_time.isoformat(), 
                    "end": end_time.isoformat()
                }
            }
            
    except Exception as e:
        logger.error(f"Env 에러 (device={deviceid}, preset={preset}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime/{device_id}")
async def get_realtime_data(device_id: int) -> Dict[str, Any]:
    """
    실시간 데이터 조회 (최근 1분 데이터)
    
    1분 테이블의 최신 데이터 반환
    """
    if device_id not in settings.ENV_DEVICE_IDS:
        raise HTTPException(status_code=400, detail=f"Invalid device ID: {device_id}")
    
    table_name = f"env_data_{device_id}_1m"
    
    try:
        query = f"""
            SELECT 
                timestamp,
                device_id,
                avg_temperature_c,
                max_temperature_c,
                min_temperature_c,
                avg_humidity_percent,
                max_humidity_percent,
                min_humidity_percent,
                count
            FROM {table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """
        
        with get_cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="No data available")
            
            cols = [d[0] for d in cursor.description]
            data = dict(zip(cols, row))
            
            # 시간 ISO 포맷 변환
            if data.get('timestamp'):
                data['timestamp'] = data['timestamp'].isoformat()
            
            return {
                "device_id": device_id,
                "data": data
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Realtime 에러 (device={device_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

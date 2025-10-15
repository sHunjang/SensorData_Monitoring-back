"""
환경센서(온습도) API 라우터

엔드포인트:
- GET /data/env/query: 시계열 데이터 조회
- GET /data/env/realtime: 실시간 데이터 조회
- GET /data/env/statistics: 통계 조회
- GET /data/env/comfort: 쾌적도 지수 조회

*** 주요 수정 사항 ***
✅ Service 함수 활용: 직접 SQL 작성 대신 env_service 함수 호출

✅ 엔드포인트 추가:

/realtime: 실시간 온습도

/statistics: 통계 조회

/comfort: 쾌적도 지수 (신규)

✅ 에러 처리 개선: 명확한 에러 메시지

✅ 로깅 강화: 성공/실패 로그

✅ 파라미터 검증: device_id 범위 체크 (21~23)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import logging

from src.services import env_service

router = APIRouter(prefix="/data/env", tags=["env"])
logger = logging.getLogger(__name__)


@router.get("/query")
async def get_env_data(
    deviceid: int = Query(..., description="Device ID (21-23)", alias="deviceid"),
    preset: Optional[str] = Query(None, description="Time preset: 1day, 1week, 1month, 1year"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    maxpoints: int = Query(1440, description="Maximum data points", alias="maxpoints")
) -> Dict[str, Any]:
    """
    환경센서 시계열 데이터 조회
    
    Parameters:
        - deviceid: 디바이스 ID (21~23)
        - preset: 시간 범위 프리셋 (1day, 1week, 1month, 1year)
        - start: 시작 시각 (ISO 8601)
        - end: 종료 시각 (ISO 8601)
        - maxpoints: 최대 데이터 포인트 수
        
    Returns:
        {
            "device_id": int,
            "resolution": "1min" | "15min" | "1hour" | "1day",
            "start": ISO string,
            "end": ISO string,
            "data_points": int,
            "data": [
                {
                    "bucket": ISO string,
                    "avg_temperature": float,
                    "min_temperature": float,
                    "max_temperature": float,
                    "avg_humidity": float,
                    "min_humidity": float,
                    "max_humidity": float
                },
                ...
            ]
        }
    """
    try:
        # 디바이스 ID 유효성 검사
        if deviceid not in range(21, 24):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 21-23"
            )
        
        # 서비스 함수 호출
        result = env_service.query_env_data(
            device_id=deviceid,
            preset=preset,
            start=start,
            end=end,
            max_points=maxpoints
        )
        
        logger.info(
            f"Env 조회 성공: device={deviceid}, preset={preset}, "
            f"resolution={result['resolution']}, points={result['data_points']}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Env 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/realtime")
async def get_env_realtime(
    deviceid: int = Query(..., description="Device ID (21-23)", alias="deviceid")
) -> Dict[str, Any]:
    """
    환경센서 실시간 데이터 조회 (최신 1건)
    
    Parameters:
        - deviceid: 디바이스 ID (21~23)
        
    Returns:
        {
            "time_stamp": ISO string,
            "device_id": int,
            "temperature": float,
            "humidity": float
        }
    """
    try:
        if deviceid not in range(21, 24):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 21-23"
            )
        
        result = env_service.query_env_realtime(device_id=deviceid)
        
        if not result:
            return {
                "time_stamp": None,
                "device_id": deviceid,
                "temperature": None,
                "humidity": None,
                "message": "No data available"
            }
        
        logger.info(f"Env 실시간 조회 성공: device={deviceid}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Env 실시간 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    deviceid: int = Query(..., description="Device ID (21-23)", alias="deviceid"),
    days: int = Query(7, description="Statistics period (days)", ge=1, le=365)
) -> Dict[str, Any]:
    """
    환경센서 통계 조회 (최근 N일간)
    
    Parameters:
        - deviceid: 디바이스 ID (21~23)
        - days: 통계 기간 (일)
        
    Returns:
        {
            "device_id": int,
            "avg_temperature": float,
            "min_temperature": float,
            "max_temperature": float,
            "avg_humidity": float,
            "min_humidity": float,
            "max_humidity": float,
            "period_days": int
        }
    """
    try:
        if deviceid not in range(21, 24):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 21-23"
            )
        
        result = env_service.get_env_statistics(device_id=deviceid, days=days)
        result["device_id"] = deviceid
        
        logger.info(
            f"Env 통계 조회 성공: device={deviceid}, days={days}, "
            f"avg_temp={result['avg_temperature']}°C"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Env 통계 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/comfort")
async def get_comfort_index(
    deviceid: int = Query(..., description="Device ID (21-23)", alias="deviceid")
) -> Dict[str, Any]:
    """
    현재 쾌적도 지수 조회
    
    쾌적 기준:
        - 온도: 18~26°C
        - 습도: 40~60%RH
    
    Parameters:
        - deviceid: 디바이스 ID (21~23)
        
    Returns:
        {
            "device_id": int,
            "temperature": float,
            "humidity": float,
            "temp_status": "low" | "comfortable" | "high",
            "humidity_status": "low" | "comfortable" | "high",
            "overall_comfort": "uncomfortable" | "comfortable"
        }
    """
    try:
        if deviceid not in range(21, 24):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 21-23"
            )
        
        result = env_service.get_comfort_index(device_id=deviceid)
        result["device_id"] = deviceid
        
        logger.info(
            f"Env 쾌적도 조회 성공: device={deviceid}, "
            f"temp={result['temperature']}°C, comfort={result['overall_comfort']}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Env 쾌적도 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

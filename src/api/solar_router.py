"""
태양광(일사량) 센서 API 라우터

엔드포인트:
- GET /data/solar/query: 시계열 데이터 조회
- GET /data/solar/realtime: 실시간 데이터 조회
- GET /data/solar/statistics: 통계 조회
- GET /data/solar/efficiency: 발전 효율 추정
- GET /data/solar/today-energy: 오늘 일사량 적산값

*** 주요 수정 사항 ***
✅ Service 함수 활용: 직접 SQL 작성 대신 solar_service 함수 호출

✅ 엔드포인트 추가:

/realtime: 실시간 일사량

/statistics: 통계 조회 (일조 시간 포함)

/efficiency: 발전 효율 추정 (신규)

/today-energy: 오늘 일사량 적산값 (신규)

✅ 에러 처리 개선: 명확한 에러 메시지

✅ 로깅 강화: 성공/실패 로그

✅ 파라미터 검증: device_id 검증 (31만 허용)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import logging

from src.services import solar_service

router = APIRouter(prefix="/data/solar", tags=["solar"])
logger = logging.getLogger(__name__)


@router.get("/query")
async def get_solar_data(
    deviceid: int = Query(31, description="Device ID (31)", alias="deviceid"),
    preset: Optional[str] = Query(None, description="Time preset: 1day, 1week, 1month, 1year"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    maxpoints: int = Query(1440, description="Maximum data points", alias="maxpoints")
) -> Dict[str, Any]:
    """
    태양광 센서 시계열 데이터 조회
    
    Parameters:
        - deviceid: 디바이스 ID (31)
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
                    "avg_irradiance": float,
                    "min_irradiance": float,
                    "max_irradiance": float
                },
                ...
            ]
        }
    """
    try:
        # 디바이스 ID 유효성 검사 (현재는 31만 존재)
        if deviceid != 31:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Only device 31 is available"
            )
        
        # 서비스 함수 호출
        result = solar_service.query_solar_data(
            device_id=deviceid,
            preset=preset,
            start=start,
            end=end,
            max_points=maxpoints
        )
        
        logger.info(
            f"Solar 조회 성공: device={deviceid}, preset={preset}, "
            f"resolution={result['resolution']}, points={result['data_points']}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Solar 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/realtime")
async def get_solar_realtime(
    deviceid: int = Query(31, description="Device ID (31)", alias="deviceid")
) -> Dict[str, Any]:
    """
    태양광 센서 실시간 데이터 조회 (최신 1건)
    
    Parameters:
        - deviceid: 디바이스 ID (31)
        
    Returns:
        {
            "time_stamp": ISO string,
            "device_id": int,
            "irradiance": float (W/m²)
        }
    """
    try:
        if deviceid != 31:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Only device 31 is available"
            )
        
        result = solar_service.query_solar_realtime(device_id=deviceid)
        
        if not result:
            return {
                "time_stamp": None,
                "device_id": deviceid,
                "irradiance": None,
                "message": "No data available"
            }
        
        logger.info(f"Solar 실시간 조회 성공: device={deviceid}, irradiance={result['irradiance']} W/m²")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Solar 실시간 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    deviceid: int = Query(31, description="Device ID (31)", alias="deviceid"),
    days: int = Query(7, description="Statistics period (days)", ge=1, le=365)
) -> Dict[str, Any]:
    """
    태양광 센서 통계 조회 (최근 N일간)
    
    Parameters:
        - deviceid: 디바이스 ID (31)
        - days: 통계 기간 (일)
        
    Returns:
        {
            "device_id": int,
            "avg_irradiance": float (W/m²),
            "max_irradiance": float (W/m²),
            "total_solar_hours": float (시간),
            "period_days": int
        }
    """
    try:
        if deviceid != 31:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Only device 31 is available"
            )
        
        result = solar_service.get_solar_statistics(device_id=deviceid, days=days)
        result["device_id"] = deviceid
        
        logger.info(
            f"Solar 통계 조회 성공: device={deviceid}, days={days}, "
            f"avg_irr={result['avg_irradiance']} W/m²"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Solar 통계 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/efficiency")
async def get_efficiency(
    deviceid: int = Query(31, description="Device ID (31)", alias="deviceid")
) -> Dict[str, Any]:
    """
    태양광 발전 효율 추정
    
    기준:
        - 1000 W/m² = 100% (STC 표준 조건)
        - 현재 일사량 기준 상대 효율 계산
    
    Parameters:
        - deviceid: 디바이스 ID (31)
        
    Returns:
        {
            "device_id": int,
            "current_irradiance": float (W/m²),
            "efficiency_percent": float (%),
            "status": "excellent" | "good" | "fair" | "poor" | "none"
        }
    """
    try:
        if deviceid != 31:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Only device 31 is available"
            )
        
        result = solar_service.estimate_solar_efficiency(device_id=deviceid)
        result["device_id"] = deviceid
        
        logger.info(
            f"Solar 효율 조회 성공: device={deviceid}, "
            f"efficiency={result['efficiency_percent']}%, status={result['status']}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Solar 효율 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/today-energy")
async def get_today_energy(
    deviceid: int = Query(31, description="Device ID (31)", alias="deviceid")
) -> Dict[str, Any]:
    """
    오늘(KST 00:00~현재) 일사량 적산값 조회
    
    Parameters:
        - deviceid: 디바이스 ID (31)
        
    Returns:
        {
            "device_id": int,
            "date": ISO string (today),
            "solar_energy_wh_per_m2": float (Wh/m²)
        }
    """
    try:
        if deviceid != 31:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Only device 31 is available"
            )
        
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        energy = solar_service.get_today_solar_energy(device_id=deviceid)
        today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        
        result = {
            "device_id": deviceid,
            "date": today,
            "solar_energy_wh_per_m2": energy
        }
        
        logger.info(f"오늘 일사량 조회 성공: device={deviceid}, energy={energy} Wh/m²")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"오늘 일사량 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

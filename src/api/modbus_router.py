"""
Modbus(전력량계) API 라우터

엔드포인트:
- GET /data/modbus/query: 시계열 데이터 조회
- GET /data/modbus/realtime: 실시간 데이터 조회
- GET /data/modbus/today-energy: 오늘 누적 에너지
- GET /data/modbus/statistics: 통계 조회

*** 주요 수정 사항 ***
✅ Service 함수 활용: 직접 SQL 작성 대신 modbus_service 함수 호출

✅ 엔드포인트 추가:

/realtime: 실시간 데이터

/today-energy: 오늘 누적 에너지

/statistics: 통계 조회

✅ 에러 처리 개선: 명확한 에러 메시지

✅ 로깅 강화: 성공/실패 로그

✅ 파라미터 검증: device_id 범위 체크

다음은 env_router.py를 보여드리겠습니다.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any
import logging

from src.services import modbus_service

router = APIRouter(prefix="/data/modbus", tags=["modbus"])
logger = logging.getLogger(__name__)


@router.get("/query")
async def get_modbus_data(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid"),
    preset: Optional[str] = Query(None, description="Time preset: 1day, 1week, 1month, 1year"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    end: Optional[str] = Query(None, description="End time (ISO format)"),
    maxpoints: int = Query(1440, description="Maximum data points", alias="maxpoints")
) -> Dict[str, Any]:
    """
    Modbus 시계열 데이터 조회
    
    Parameters:
        - deviceid: 디바이스 ID (11~15)
        - preset: 시간 범위 프리셋 (1day, 1week, 1month, 1year)
        - start: 시작 시각 (ISO 8601)
        - end: 종료 시각 (ISO 8601)
        - maxpoints: 최대 데이터 포인트 수
        
    Returns:
        {
            "device_id": int,
            "wire_type": "4wire" | "3wire",
            "resolution": "1min" | "15min" | "1hour" | "1day",
            "start": ISO string,
            "end": ISO string,
            "data_points": int,
            "data": [...]
        }
    """
    try:
        # 디바이스 ID 유효성 검사
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        # 서비스 함수 호출
        result = modbus_service.query_modbus_data(
            device_id=deviceid,
            preset=preset,
            start=start,
            end=end,
            max_points=maxpoints
        )
        
        logger.info(
            f"Modbus 조회 성공: device={deviceid}, preset={preset}, "
            f"resolution={result['resolution']}, points={result['data_points']}"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/realtime")
async def get_modbus_realtime(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid")
) -> Dict[str, Any]:
    """
    Modbus 실시간 데이터 조회 (최신 1건)
    
    Parameters:
        - deviceid: 디바이스 ID (11~15)
        
    Returns:
        {
            "time_stamp": ISO string,
            "device_id": int,
            "voltage": float,
            "current": float,
            "power": float,
            "energy": float
        }
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        result = modbus_service.query_modbus_realtime(device_id=deviceid)
        
        if not result:
            return {
                "time_stamp": None,
                "device_id": deviceid,
                "voltage": None,
                "current": None,
                "power": None,
                "energy": None,
                "message": "No data available"
            }
        
        logger.info(f"Modbus 실시간 조회 성공: device={deviceid}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus 실시간 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/today-energy")
async def get_today_energy(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid")
) -> Dict[str, Any]:
    """
    오늘(KST 00:00~현재) 누적 에너지 소비량 조회
    
    Parameters:
        - deviceid: 디바이스 ID (11~15)
        
    Returns:
        {
            "device_id": int,
            "date": ISO string (today),
            "energy_kwh": float,
            "wire_type": "4wire" | "3wire"
        }
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        from datetime import datetime
        from zoneinfo import ZoneInfo
        
        energy = modbus_service.get_today_energy_kwh(device_id=deviceid)
        wire_type = "4wire" if modbus_service._is_4wire(deviceid) else "3wire"
        today = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
        
        result = {
            "device_id": deviceid,
            "date": today,
            "energy_kwh": energy,
            "wire_type": wire_type
        }
        
        logger.info(f"오늘 에너지 조회 성공: device={deviceid}, energy={energy} kWh")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"오늘 에너지 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    deviceid: int = Query(..., description="Device ID (11-15)", alias="deviceid"),
    days: int = Query(7, description="Statistics period (days)", ge=1, le=365)
) -> Dict[str, Any]:
    """
    Modbus 통계 조회 (최근 N일간)
    
    Parameters:
        - deviceid: 디바이스 ID (11~15)
        - days: 통계 기간 (일)
        
    Returns:
        {
            "device_id": int,
            "total_energy_kwh": float,
            "avg_power_kw": float,
            "peak_power_kw": float,
            "period_days": int,
            "wire_type": "4wire" | "3wire"
        }
    """
    try:
        if deviceid not in range(11, 16):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid device_id: {deviceid}. Must be 11-15"
            )
        
        result = modbus_service.get_device_statistics(device_id=deviceid, days=days)
        result["device_id"] = deviceid
        result["wire_type"] = "4wire" if modbus_service._is_4wire(deviceid) else "3wire"
        
        logger.info(
            f"Modbus 통계 조회 성공: device={deviceid}, days={days}, "
            f"energy={result['total_energy_kwh']} kWh"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Modbus 통계 조회 실패: device={deviceid}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
